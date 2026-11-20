"""A failure must not tell a client something false, or reveal something it should not.

Two classes, found by the Security Review after the error boundary was added:
  * login must answer identically whether or not the email exists, for ANY password text;
  * a write that has committed must never be followed by an error, because a client that sees
    an error retries and applies the write twice.
"""
import io
import sqlite3
import unittest
from unittest import mock

from app import auth, billing, tenants, tickets
from app.errors import AuthError, Invalid
from app.web import App

from tests.helpers import NOW, TEST_LOGIN_PW, World, call, nk

LONE_SURROGATE = "\ud800"  # not encodable as UTF-8; arrives over the wire as the JSON escape \ud800


class FailAfterCommit:
    """A connection whose every statement fails once COMMIT has run: the write is durable, the read dies."""

    def __init__(self, conn):
        self._conn = conn
        self.committed = False

    def execute(self, sql, *args):
        if self.committed:
            raise sqlite3.OperationalError("injected read failure after COMMIT")
        result = self._conn.execute(sql, *args)
        if sql.strip().upper() == "COMMIT":
            self.committed = True
        return result

    def __getattr__(self, name):
        return getattr(self._conn, name)


class LoginIsUniformTests(World):
    def setUp(self):
        super().setUp()
        self.app = App(self.db, clock=lambda: NOW)

    def login(self, email, password):
        return call(self.app, "POST", "/login", {"email": email, "password": password, "tenant_id": self.ta})

    def test_unencodable_password_gets_the_same_answer_for_known_and_unknown_emails(self):
        known = self.login("a_owner@example.test", LONE_SURROGATE)
        unknown = self.login("absent@example.test", LONE_SURROGATE)
        self.assertEqual(known, (401, {"error": "invalid credentials"}))
        self.assertEqual(known, unknown)

    def test_unencodable_email_is_the_same_failure(self):
        self.assertEqual(self.login(LONE_SURROGATE, TEST_LOGIN_PW), (401, {"error": "invalid credentials"}))
        self.assertEqual(self.login("a_owner@example.test" + LONE_SURROGATE, "x" * 12),
                         (401, {"error": "invalid credentials"}))

    def test_domain_login_raises_the_same_error_for_known_and_unknown(self):
        for email in ("a_owner@example.test", "absent@example.test"):
            with self.assertRaises(AuthError) as ctx:
                auth.login(self.db, auth.TEST_SIGNING_KEY, email, LONE_SURROGATE, self.ta, NOW)
            self.assertEqual(str(ctx.exception), "invalid credentials")

    def test_an_unknown_email_costs_the_same_password_hash_as_a_known_one(self):
        with mock.patch.object(auth, "verify_password", wraps=auth.verify_password) as spy:
            for email in ("a_owner@example.test", "absent@example.test"):
                spy.reset_mock()
                with self.assertRaises(AuthError):
                    auth.login(self.db, auth.TEST_SIGNING_KEY, email, "wrong-horse!", self.ta, NOW)
                self.assertEqual(spy.call_count, 1, email)

    def test_unencodable_text_is_refused_before_any_lookup_or_hash(self):
        """The early guard, not verify_password's own handler, is what keeps this text off the account path."""
        class CountingDb:
            def __init__(self, conn):
                self.conn, self.statements = conn, []

            def execute(self, sql, *args):
                self.statements.append(sql)
                return self.conn.execute(sql, *args)

        for email, password in (("a_owner@example.test", LONE_SURROGATE), ("absent@example.test", LONE_SURROGATE),
                                (LONE_SURROGATE, TEST_LOGIN_PW)):
            counting = CountingDb(self.db)
            with (mock.patch.object(auth, "verify_password", wraps=auth.verify_password) as spy,
                  self.assertRaises(AuthError)):
                auth.login(counting, auth.TEST_SIGNING_KEY, email, password, self.ta, NOW)
            self.assertEqual((counting.statements, spy.call_count), ([], 0), ascii((email, password)))

    def test_verify_password_treats_unencodable_text_as_a_mismatch(self):
        stored = auth.hash_password(TEST_LOGIN_PW)
        self.assertFalse(auth.verify_password(LONE_SURROGATE, stored))
        self.assertTrue(auth.verify_password(TEST_LOGIN_PW, stored))

    def test_a_correct_login_still_works(self):
        status, body = self.login("a_owner@example.test", TEST_LOGIN_PW)
        self.assertEqual(status, 200)
        self.assertIn("token", body)


class BearerTokenTextTests(World):
    """A bearer header is untrusted text too: a lone surrogate in any part of it is a 401, never a 500."""

    def test_unencodable_text_in_a_token_is_rejected_cleanly(self):
        app = App(self.db, clock=lambda: NOW)
        for header in ("Bearer " + LONE_SURROGATE + ".x", "Bearer x." + LONE_SURROGATE,
                       "Bearer " + LONE_SURROGATE, "Bearer é.x"):
            environ = {"REQUEST_METHOD": "GET", "PATH_INFO": "/billing/balance", "CONTENT_LENGTH": "0",
                       "wsgi.input": io.BytesIO(b""), "HTTP_AUTHORIZATION": header}
            got = []
            b"".join(app(environ, lambda s, h, out=got: out.append(int(s.split()[0]))))
            self.assertEqual(got, [401], ascii(header))

    def test_domain_verify_token_raises_auth_error_for_unencodable_body(self):
        with self.assertRaises(AuthError):
            auth.verify_token(auth.TEST_SIGNING_KEY, LONE_SURROGATE + ".abc", NOW)


class UnstorableTextTests(World):
    def test_text_that_cannot_be_stored_is_a_client_error_not_an_exception(self):
        with self.assertRaises(Invalid):
            tickets.create_ticket(self.db, self.a("owner"), "bad " + LONE_SURROGATE, idempotency_key=nk())
        with self.assertRaises(Invalid):
            billing.create_invoice(self.db, self.a("owner"),
                                   [{"description": LONE_SURROGATE, "amount_cents": 5}], idempotency_key=nk())
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0], 0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM invoices").fetchone()[0], 0)

    def test_through_the_web_layer_it_is_400(self):
        app = App(self.db, clock=lambda: NOW)
        _, body = call(app, "POST", "/login", {
            "email": "a_owner@example.test", "password": TEST_LOGIN_PW, "tenant_id": self.ta})
        token = body["token"]
        self.assertEqual(call(app, "POST", "/tickets", {"title": LONE_SURROGATE, "idempotency_key": nk()}, token)[0], 400)


class NothingFailsAfterCommitTests(World):
    """Every state-changing operation returns normally even if every later statement would fail."""

    def setUp(self):
        super().setUp()
        self.flaky = FailAfterCommit(self.db)

    def test_credit_returns_the_new_balance_and_the_retry_is_not_needed(self):
        self.assertEqual(billing.credit(self.flaky, self.a("owner"), 50, idempotency_key=nk()), 50)
        self.assertTrue(self.flaky.committed)
        self.assertEqual(billing._balance(self.db, self.ta), 50)

    def test_debit_returns_the_new_balance(self):
        billing.credit(self.db, self.a("owner"), 80, idempotency_key=nk())
        self.assertEqual(billing.debit(self.flaky, self.a("owner"), 30, idempotency_key=nk()), 50)
        self.assertTrue(self.flaky.committed)
        self.assertEqual(billing._balance(self.db, self.ta), 50)

    def test_create_invoice_returns_what_it_stored(self):
        invoice = billing.create_invoice(self.flaky, self.a("owner"), [
            {"description": "a", "amount_cents": 5}, {"description": "b", "amount_cents": 7}], idempotency_key=nk())
        self.assertTrue(self.flaky.committed)
        self.assertEqual(invoice, billing.get_invoice(self.db, self.a("owner"), invoice["id"]))
        self.assertEqual(invoice["total_cents"], 12)

    def test_create_ticket_returns_what_it_stored(self):
        ticket = tickets.create_ticket(self.flaky, self.a("owner"), "  fix it  ", idempotency_key=nk())
        self.assertTrue(self.flaky.committed)
        self.assertEqual(ticket, tickets.get_ticket(self.db, self.a("owner"), ticket["id"]))
        self.assertEqual(ticket["title"], "fix it")

    def test_assign_ticket_returns_the_assigned_ticket(self):
        ticket = tickets.create_ticket(self.db, self.a("owner"), "t", idempotency_key=nk())
        result = tickets.assign_ticket(self.flaky, self.a("owner"), ticket["id"], self.users["a_member"])
        self.assertTrue(self.flaky.committed)
        self.assertEqual(result["assignee_id"], self.users["a_member"])

    def test_the_two_remaining_mutators_return_nothing_to_read(self):
        uid = self._user("newcomer")
        tenants.add_member(self.flaky, self.a("owner"), uid, "member")
        self.assertTrue(self.flaky.committed)
        self.flaky.committed = False
        tenants.remove_member(self.flaky, self.a("owner"), uid)
        self.assertTrue(self.flaky.committed)

    def test_a_credit_over_http_is_200_and_applied_exactly_once(self):
        app = App(self.db, clock=lambda: NOW)
        _, body = call(app, "POST", "/login", {
            "email": "a_owner@example.test", "password": TEST_LOGIN_PW, "tenant_id": self.ta})
        token = body["token"]
        flaky_app = App(self.flaky, clock=lambda: NOW)
        status, payload = call(flaky_app, "POST", "/billing/credit", {"amount_cents": 50, "idempotency_key": nk()}, token)
        self.assertEqual((status, payload), (200, {"balance_cents": 50}))
        self.assertEqual(billing._balance(self.db, self.ta), 50)


if __name__ == "__main__":
    unittest.main()
