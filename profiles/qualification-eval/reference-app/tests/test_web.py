import io
import unittest

from app import auth, web

from tests.helpers import NOW, TEST_LOGIN_PW, WRONG_LOGIN_PW, World, call, make_app, nk


class WebTests(World):
    def setUp(self):
        super().setUp()
        self.app = make_app(self)

    def login(self, name, tenant, pw=TEST_LOGIN_PW):
        status, body = call(self.app, "POST", "/login",
                            {"email": f"{name}@example.test", "password": pw, "tenant_id": tenant})
        return status, body.get("token")

    def test_login_then_ticket_flow(self):
        status, token = self.login("a_member", self.ta)
        self.assertEqual(status, 200)
        status, ticket = call(self.app, "POST", "/tickets", {"title": "hello", "idempotency_key": nk()}, token)
        self.assertEqual(status, 201)
        status, got = call(self.app, "GET", f"/tickets/{ticket['id']}", token=token)
        self.assertEqual((status, got["title"]), (200, "hello"))

    def test_missing_or_bad_token_is_401(self):
        self.assertEqual(call(self.app, "GET", "/tickets/1")[0], 401)
        self.assertEqual(call(self.app, "GET", "/tickets/1", token="junk")[0], 401)

    def test_expired_token_is_401(self):
        _, token = self.login("a_member", self.ta)
        late = make_app(self, now=NOW + auth.TOKEN_TTL_SECONDS + 1)
        self.assertEqual(call(late, "GET", "/tickets/1", token=token)[0], 401)

    def test_tenant_comes_from_token_not_request_body(self):  # INV-1
        _, token_a = self.login("a_member", self.ta)
        _, ticket = call(self.app, "POST", "/tickets", {"title": "a-only", "idempotency_key": nk()}, token_a)
        _, token_b = self.login("b_owner", self.tb)
        status, _ = call(self.app, "GET", f"/tickets/{ticket['id']}", {"tenant_id": self.ta}, token_b)
        self.assertEqual(status, 404)
        status, _ = call(self.app, "POST", "/tickets", {"title": "x", "tenant_id": self.ta, "idempotency_key": nk()}, token_b)
        self.assertEqual(status, 201)
        self.assertEqual(
            self.db.execute("SELECT tenant_id FROM tickets WHERE title = 'x'").fetchone()[0], self.tb)

    def test_status_codes(self):
        _, viewer = self.login("a_viewer", self.ta)
        self.assertEqual(call(self.app, "POST", "/tickets", {"title": "x", "idempotency_key": nk()}, viewer)[0], 403)
        _, member = self.login("a_member", self.ta)
        self.assertEqual(call(self.app, "POST", "/tickets", {"title": "", "idempotency_key": nk()}, member)[0], 400)
        self.assertEqual(call(self.app, "GET", "/tickets/999", token=member)[0], 404)
        self.assertEqual(call(self.app, "GET", "/nope", token=member)[0], 404)

    def test_billing_overdraft_is_409_and_login_failure_is_401(self):
        _, admin = self.login("a_admin", self.ta)
        self.assertEqual(call(self.app, "POST", "/billing/credit", {"amount_cents": 50, "idempotency_key": nk()}, admin)[0], 200)
        self.assertEqual(call(self.app, "POST", "/billing/debit", {"amount_cents": 51, "idempotency_key": nk()}, admin)[0], 409)
        self.assertEqual(self.login("a_admin", self.ta, pw=WRONG_LOGIN_PW)[0], 401)

    def test_member_management_over_http(self):
        _, owner = self.login("a_owner", self.ta)
        uid = self.users["outsider"]
        self.assertEqual(call(self.app, "POST", "/members", {"user_id": uid, "role": "viewer"}, owner)[0], 201)
        self.assertEqual(call(self.app, "DELETE", f"/members/{uid}", token=owner)[0], 200)
        self.assertEqual(call(self.app, "DELETE", f"/members/{self.users['a_owner']}", token=owner)[0], 409)

    def test_malformed_bodies_are_400(self):
        import io
        _, member = self.login("a_member", self.ta)
        for raw in (b"not json", b"[1,2]"):
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/tickets", "CONTENT_LENGTH": str(len(raw)),
                       "wsgi.input": io.BytesIO(raw), "HTTP_AUTHORIZATION": "Bearer " + member}
            statuses = []
            self.app(environ, lambda s, h, out=statuses: out.append(int(s.split()[0])))
            self.assertEqual(statuses, [400])


class WebRegressionTests(World):
    """Verifier round 1 regressions, driven through the real WSGI entrypoint."""

    def setUp(self):
        super().setUp()
        self.app = make_app(self)

    def login(self, name, tenant):
        return call(self.app, "POST", "/login",
                    {"email": f"{name}@example.test", "password": TEST_LOGIN_PW,
                     "tenant_id": tenant})[1]["token"]

    def raw(self, method, path, token, query="", headers=None):
        environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": query,
                   "CONTENT_LENGTH": "0", "wsgi.input": io.BytesIO(b""),
                   "HTTP_AUTHORIZATION": "Bearer " + token, **(headers or {})}
        got = []
        self.app(environ, lambda s, h, out=got: out.append(int(s.split()[0])))
        return got[0]

    def test_tenant_is_never_read_from_query_string_or_headers(self):  # REV-004 / INV-1
        ta_ticket = call(self.app, "POST", "/tickets", {"title": "secret", "idempotency_key": nk()},
                         self.login("a_member", self.ta))[1]
        token_b = self.login("b_owner", self.tb)
        path = f"/tickets/{ta_ticket['id']}"
        self.assertEqual(self.raw("GET", path, token_b), 404)
        self.assertEqual(self.raw("GET", path, token_b, query=f"tenant_id={self.ta}"), 404)
        self.assertEqual(
            self.raw("GET", path, token_b, headers={"HTTP_X_TENANT_ID": str(self.ta)}), 404)

    def test_stale_token_cannot_keep_acting_after_removal(self):  # REV-001 / INV-2
        outsider, owner_a, owner_b = self.users["outsider"], self.users["a_owner"], self.users["a_admin"]
        self.db.execute("UPDATE memberships SET role = 'owner' WHERE user_id = ?", (owner_b,))
        stale_a = self.login("a_owner", self.ta)
        token_b = self.login("a_admin", self.ta)
        self.assertEqual(call(self.app, "DELETE", f"/members/{owner_a}", token=token_b)[0], 200)
        status, _ = call(self.app, "POST", "/members", {"user_id": outsider, "role": "owner"}, stale_a)
        self.assertEqual(status, 401)
        self.assertIsNone(self.db.execute(
            "SELECT 1 FROM memberships WHERE tenant_id = ? AND user_id = ? AND active = 1",
            (self.ta, outsider)).fetchone())
        self.assertEqual(call(self.app, "DELETE", f"/members/{owner_b}", token=stale_a)[0], 401)

    def test_removed_member_cannot_create_tickets_with_old_token(self):  # REV-001
        token = self.login("a_member", self.ta)
        call(self.app, "DELETE", f"/members/{self.users['a_member']}", token=self.login("a_admin", self.ta))
        self.assertEqual(call(self.app, "POST", "/tickets", {"title": "x", "idempotency_key": nk()}, token)[0], 401)

    def test_demoted_admin_cannot_keep_granting_admin(self):  # REV-001 / INV-2
        token = self.login("a_admin", self.ta)
        self.db.execute("UPDATE memberships SET role = 'viewer' WHERE user_id = ?", (self.users["a_admin"],))
        status, _ = call(self.app, "POST", "/members",
                         {"user_id": self.users["outsider"], "role": "admin"}, token)
        self.assertEqual(status, 403)

    def test_balance_route(self):  # route-coverage gap noted by the Verifier
        admin = self.login("a_admin", self.ta)
        call(self.app, "POST", "/billing/credit", {"amount_cents": 700, "idempotency_key": nk()}, admin)
        self.assertEqual(call(self.app, "GET", "/billing/balance", token=admin),
                         (200, {"balance_cents": 700}))
        self.assertEqual(
            call(self.app, "GET", "/billing/balance", token=self.login("a_member", self.ta))[0], 403)

    def test_oversized_amounts_are_client_errors_not_crashes(self):  # REV-005
        admin = self.login("a_admin", self.ta)
        for _ in range(2):
            status, _ = call(self.app, "POST", "/billing/credit", {"amount_cents": 2**62, "idempotency_key": nk()}, admin)
            self.assertEqual(status, 400)
        self.assertEqual(call(self.app, "GET", "/billing/balance", token=admin)[1],
                         {"balance_cents": 0})

    def test_malformed_login_types_are_401_not_crashes(self):  # REV-006
        for tenant in ({"a": 1}, [1], "1", None, True):
            status, body = call(self.app, "POST", "/login",
                                {"email": "a_admin@example.test", "password": TEST_LOGIN_PW,
                                 "tenant_id": tenant})
            self.assertEqual((status, body), (401, {"error": "invalid credentials"}))


class InputBoundaryTests(World):
    """SR-004 / SR-005: untrusted input must always produce a controlled response, never an escape."""

    def setUp(self):
        super().setUp()
        self.app = make_app(self)

    def run_raw(self, method, path, body=b"", length=None, headers=None, stream=None):
        environ = {"REQUEST_METHOD": method, "PATH_INFO": path,
                   "CONTENT_LENGTH": str(len(body) if length is None else length),
                   "wsgi.input": stream if stream is not None else io.BytesIO(body), **(headers or {})}
        got = []
        payload = b"".join(self.app(environ, lambda s, h, out=got: out.append(int(s.split()[0]))))
        return got[0], payload

    def test_non_ascii_or_garbage_bearer_tokens_are_401(self):  # SR-004
        for token in ("x.\u00e9", "\u00e9.\u00e9", "\u202e", "a.b.c", "....", "x" * 10_000):
            status, _ = self.run_raw("GET", "/billing/balance", headers={"HTTP_AUTHORIZATION": "Bearer " + token})
            self.assertEqual(status, 401, repr(token[:20]))

    def test_deeply_nested_json_is_400_not_an_exception(self):  # SR-005
        deep = b"[" * 20000 + b"0" + b"]" * 20000
        status, _ = self.run_raw("POST", "/login", deep)
        self.assertEqual(status, 400)

    def test_oversized_bodies_are_413_and_never_read(self):  # SR-005
        class Unreadable(io.BytesIO):
            def read(self, *args, **kwargs):
                raise AssertionError("an oversized body must be rejected before it is read")

        status, _ = self.run_raw("POST", "/login", length=web.MAX_BODY_BYTES + 1, stream=Unreadable())
        self.assertEqual(status, 413)
        status, _ = self.run_raw("POST", "/login", length=10**12, stream=Unreadable())
        self.assertEqual(status, 413)

    def test_a_body_of_exactly_the_limit_is_still_processed(self):
        padding = b"x" * (web.MAX_BODY_BYTES - len(b'{"email":""}'))
        body = b'{"email":"' + padding + b'"}'
        self.assertEqual(len(body), web.MAX_BODY_BYTES)
        status, _ = self.run_raw("POST", "/login", body)
        self.assertEqual(status, 401)  # reached the login logic and failed it normally

    def test_negative_or_malformed_content_length_is_400(self):  # SR-005
        for length in ("-1", "-9999", "abc", "1.5"):
            status, _ = self.run_raw("POST", "/login", b'{"a":1}', length=length)
            self.assertEqual(status, 400, length)

    def test_non_standard_json_constants_are_400(self):  # SR-002 at the web boundary
        for raw in (b'{"amount_cents": NaN}', b'{"amount_cents": Infinity}', b'{"x": -Infinity}'):
            status, _ = self.run_raw("POST", "/login", raw)
            self.assertEqual(status, 400, raw)


if __name__ == "__main__":
    unittest.main()
