"""Untrusted input from an AUTHENTICATED caller must also always yield a controlled response.

The login and body-size boundaries were hardened first; this covers the rest of the surface: ids and
roles of the wrong type or outside SQLite's range, very long or non-ASCII digits in the path, and the
last-resort handler that keeps any unexpected failure inside the WSGI boundary.
"""
import io
import json
import unittest
from unittest import mock

from app import auth, billing, tenants, tickets, validate
from app.errors import Invalid

from tests.helpers import NOW, TEST_LOGIN_PW, World, call, make_app, nk

BAD_IDS = (0, -1, 2**63, 2**70, 10**400, True, False, None, "1", 1.0, [1], {"a": 1})


class DomainValidationTests(World):
    def test_db_id_accepts_only_positive_sqlite_integers(self):
        self.assertEqual(validate.db_id(1), 1)
        self.assertEqual(validate.db_id(validate.MAX_DB_INT), validate.MAX_DB_INT)
        for bad in BAD_IDS:
            with self.assertRaises(Invalid, msg=repr(bad)):
                validate.db_id(bad)

    def test_every_id_taking_operation_rejects_bad_ids_as_invalid(self):
        ticket = tickets.create_ticket(self.db, self.a("owner"), "x", idempotency_key=nk())
        for bad in BAD_IDS:
            with self.assertRaises(Invalid, msg=f"get_ticket {bad!r}"):
                tickets.get_ticket(self.db, self.a("owner"), bad)
            with self.assertRaises(Invalid, msg=f"assign ticket_id {bad!r}"):
                tickets.assign_ticket(self.db, self.a("owner"), bad, self.users["a_member"])
            with self.assertRaises(Invalid, msg=f"assign assignee_id {bad!r}"):
                tickets.assign_ticket(self.db, self.a("owner"), ticket["id"], bad)
            with self.assertRaises(Invalid, msg=f"add_member user_id {bad!r}"):
                tenants.add_member(self.db, self.a("owner"), bad, "member")
            with self.assertRaises(Invalid, msg=f"remove_member user_id {bad!r}"):
                tenants.remove_member(self.db, self.a("owner"), bad)
            with self.assertRaises(Invalid, msg=f"get_invoice {bad!r}"):
                billing.get_invoice(self.db, self.a("owner"), bad)

    def test_roles_that_are_not_known_strings_are_invalid_not_a_type_error(self):
        uid = self._user("newcomer")
        for bad in ([], {}, None, 5, "", "root", ["owner"], {"owner": 1}):
            with self.assertRaises(Invalid, msg=repr(bad)):
                tenants.add_member(self.db, self.a("owner"), uid, bad)


class WsgiInputClassTests(World):
    def setUp(self):
        super().setUp()
        self.app = make_app(self)
        _, body = call(self.app, "POST", "/login", {
            "email": "a_owner@example.test", "password": TEST_LOGIN_PW, "tenant_id": self.ta})
        self.token = body["token"]
        self.ticket = call(self.app, "POST", "/tickets", {"title": "t", "idempotency_key": nk()}, self.token)[1]

    def status(self, method, path, body=None, raw_body=None):
        raw = raw_body if raw_body is not None else (json.dumps(body).encode() if body is not None else b"")
        environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "CONTENT_LENGTH": str(len(raw)),
                   "wsgi.input": io.BytesIO(raw), "HTTP_AUTHORIZATION": "Bearer " + self.token}
        got = []
        self.app(environ, lambda s, h, out=got: out.append(int(s.split()[0])))
        return got[0]

    def test_path_ids_that_cannot_exist_are_404(self):
        tid = self.ticket["id"]
        for method, path, body in (
            ("GET", "/tickets/" + "9" * 19, None),
            ("GET", "/tickets/" + "9" * 5000, None),
            ("GET", "/tickets/٣", None),  # a non-ASCII digit, which int() would accept
            ("DELETE", "/members/" + "9" * 20, None),
            ("POST", "/tickets/" + "9" * 20 + "/assign", {"assignee_id": 1}),
            ("POST", f"/tickets/{tid}x/assign", {"assignee_id": 1}),
        ):
            self.assertEqual(self.status(method, path, body), 404, f"{method} {path[:40]}")

    def test_body_ids_and_roles_of_the_wrong_type_or_range_are_400(self):
        tid = self.ticket["id"]
        for bad in (2**70, {"a": 1}, [1], "1", None, True, 0, -1):
            self.assertEqual(self.status("POST", f"/tickets/{tid}/assign", {"assignee_id": bad}), 400, repr(bad))
            self.assertEqual(self.status("POST", "/members", {"user_id": bad, "role": "member"}), 400, repr(bad))
        for bad_role in ([], {}, None, 5, "root"):
            self.assertEqual(self.status("POST", "/members", {"user_id": 5, "role": bad_role}), 400, repr(bad_role))

    def test_amounts_beyond_what_json_or_sqlite_can_hold_are_400(self):
        for raw in (b'{"amount_cents": 1e999}', b'{"amount_cents": ' + b"9" * 5000 + b"}",
                    b'{"amount_cents": 1180591620717411303424}'):
            for path in ("/billing/credit", "/billing/debit"):
                self.assertEqual(self.status("POST", path, raw_body=raw), 400, f"{path} {raw[:30]!r}")

    def test_an_unexpected_failure_is_a_generic_500_that_leaks_nothing(self):
        failing = mock.patch.object(billing, "balance", side_effect=RuntimeError("secret internal detail"))
        with failing, self.assertLogs("app.web", level="ERROR"):
            environ = {"REQUEST_METHOD": "GET", "PATH_INFO": "/billing/balance", "CONTENT_LENGTH": "0",
                       "wsgi.input": io.BytesIO(b""), "HTTP_AUTHORIZATION": "Bearer " + self.token}
            got = []
            payload = b"".join(self.app(environ, lambda s, h, out=got: out.append(int(s.split()[0]))))
        self.assertEqual(got, [500])
        self.assertEqual(json.loads(payload), {"error": "internal error"})
        self.assertNotIn(b"secret", payload)


class HugeTimeTests(World):
    """Huge integers must be a clean error everywhere a time is read, never OverflowError."""

    KEY = auth.TEST_SIGNING_KEY

    def signed(self, exp_digits):
        body = auth._b64(b'{"uid":1,"tid":1,"role":"owner","exp":' + exp_digits + b"}")
        return body + "." + auth._sign(self.KEY, body)

    def test_minting_rejects_huge_ttl_and_now(self):
        for value in (10**400, -(10**400), auth.MAX_TIME + 1):
            with self.assertRaises(Invalid, msg=repr(value)):
                auth.issue_token(self.KEY, 1, 1, "owner", NOW, ttl=value)
            with self.assertRaises(Invalid, msg=repr(value)):
                auth.issue_token(self.KEY, 1, 1, "owner", value)

    def test_verification_rejects_huge_expiry_and_huge_clock_cleanly(self):
        for digits in (b"9" * 400, b"-" + b"9" * 400):
            with self.assertRaises(auth.AuthError, msg=digits[:10]):
                auth.verify_token(self.KEY, self.signed(digits), NOW)
        good = auth.issue_token(self.KEY, 1, 1, "owner", NOW)
        with self.assertRaises(auth.AuthError):
            auth.verify_token(self.KEY, good, 10**400)

    def test_a_token_with_a_huge_expiry_through_wsgi_is_401_not_an_exception(self):
        app = make_app(self)
        environ = {"REQUEST_METHOD": "GET", "PATH_INFO": "/billing/balance", "CONTENT_LENGTH": "0",
                   "wsgi.input": io.BytesIO(b""), "HTTP_AUTHORIZATION": "Bearer " + self.signed(b"9" * 400)}
        got = []
        app(environ, lambda s, h, out=got: out.append(int(s.split()[0])))
        self.assertEqual(got, [401])


if __name__ == "__main__":
    unittest.main()
