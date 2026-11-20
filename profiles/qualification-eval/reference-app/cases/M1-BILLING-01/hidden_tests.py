"""Hidden tests for M1-BILLING-01. Copied into a workspace as tests/test_hidden_billing.py; never shown to a candidate."""
import unittest

from app import billing
from app.errors import Conflict, Forbidden, Invalid
from tests.helpers import World, call, make_app, nk
from tests.test_lock_discipline import assert_disciplined as _disciplined
from tests.test_lock_discipline import observe


def assert_disciplined(case, log, expect_write=True):
    _disciplined(case, log, expect_write)
    case.assertIn(log[-1][0], ("COMMIT", "ROLLBACK"), "nothing may run after the transaction ends")


KEEP = object()
CAP = 10 ** 15


def rows(world):
    return world.db.execute("SELECT tenant_id, kind, amount_cents FROM ledger ORDER BY id").fetchall()


class UsageCreditTests(World):
    def use(self, amount, who=None, key=KEEP):
        return billing.usage_credit(self.db, who or self.a("admin"), amount, nk() if key is KEEP else key)

    def test_a_usage_credit_adds_to_the_balance_and_is_recorded_as_a_positive_usage_credit_row(self):
        self.assertEqual(self.use(250), 250)
        billing.credit(self.db, self.a("owner"), 100, nk())
        self.assertEqual(self.use(5), 355)
        self.assertEqual(billing.balance(self.db, self.a("admin")), 355)
        self.assertEqual([tuple(r) for r in rows(self)],
                         [(self.ta, "usage_credit", 250), (self.ta, "credit", 100), (self.ta, "usage_credit", 5)])

    def test_only_admin_and_owner_may_apply_one(self):
        for role in ("viewer", "member"):
            with self.assertRaises(Forbidden):
                self.use(1, self.a(role))
        self.assertEqual(self.use(1, self.a("owner")), 1)

    def test_one_operation_is_at_most_a_billion_cents(self):
        self.assertEqual(self.use(10 ** 9 - 1), 10 ** 9 - 1)
        self.assertEqual(self.use(1), 10 ** 9)
        with self.assertRaises(Invalid):
            self.use(10 ** 9 + 1)
        self.assertEqual(billing.balance(self.db, self.a("admin")), 10 ** 9)

    def test_the_limit_is_per_usage_credit_not_cumulative(self):
        self.assertEqual(self.use(600_000_000), 600_000_000)
        self.assertEqual(self.use(600_000_000), 1_200_000_000)

    def test_exactly_the_limit_is_accepted_in_one_credit(self):
        self.assertEqual(self.use(10 ** 9), 10 ** 9)

    def test_every_amount_above_the_limit_is_refused(self):
        for amount in (10 ** 9 + 2, 10 ** 9 + 3, 10 ** 9 + 4, 10 ** 9 + 5, 10 ** 10, 10 ** 12):
            with self.assertRaises(Invalid, msg=amount):
                self.use(amount)
        self.assertEqual(rows(self), [])

    def test_no_amount_above_the_limit_is_accepted_whatever_its_form(self):
        above = {10 ** 9 + k for k in range(1, 300)}
        above |= {2 ** n + d for n in range(30, 63) for d in (-1, 0, 1) if 2 ** n + d > 10 ** 9}
        above |= {10 ** n + d for n in range(9, 16) for d in (0, 1) if 10 ** n + d > 10 ** 9}
        above |= {7 * 10 ** 9, 123_456_789_012, 10 ** 15 - 1}
        for amount in sorted(above):
            with self.assertRaises(Invalid, msg=amount):
                self.use(amount)
        self.assertEqual(rows(self), [])

    def test_a_replay_returns_the_saved_answer_not_the_current_balance(self):  # INV-4
        key = nk()
        self.assertEqual(self.use(30, key=key), 30)
        self.assertEqual(self.use(5), 35)
        self.assertEqual(self.use(30, key=key), 30)
        self.assertEqual(billing.balance(self.db, self.a("admin")), 35)

    def test_a_replay_needs_live_authority_like_any_other_request(self):  # INV-2
        key = nk()
        snapshot = self.a("admin")
        self.assertEqual(self.use(30, snapshot, key=key), 30)
        self.db.execute("UPDATE memberships SET active = 0 WHERE user_id = ?", (self.users["a_admin"],))
        with self.assertRaises(Forbidden):
            self.use(30, snapshot, key=key)
        self.assertEqual(len(rows(self)), 1)

    def test_the_amount_must_be_a_positive_integer(self):
        for bad in (0, -5, True, False, 1.5, 2.0, "5", None, [5], float("nan")):
            with self.assertRaises(Invalid, msg=repr(bad)):
                self.use(bad)
        self.assertEqual(rows(self), [])

    def test_the_balance_never_passes_its_cap(self):  # INV-4
        self.db.execute("INSERT INTO ledger (tenant_id, kind, amount_cents) VALUES (?, 'credit', ?)",
                        (self.ta, CAP - 5))
        with self.assertRaises(Conflict):
            self.use(6)
        self.assertEqual(billing.balance(self.db, self.a("admin")), CAP - 5)
        self.assertEqual(self.use(5), CAP)
        with self.assertRaises(Conflict):
            self.use(1)

    def test_a_tenant_balance_is_its_own(self):  # INV-1
        self.use(40)
        self.assertEqual(billing.balance(self.db, self.b("owner")), 0)
        self.assertEqual(self.use(7, self.b("owner")), 7)
        self.assertEqual(billing.balance(self.db, self.a("admin")), 40)

    def test_a_retried_request_is_applied_once(self):  # INV-4, retry safety
        key = nk()
        self.assertEqual(self.use(30, key=key), 30)
        self.assertEqual(self.use(30, key=key), 30)
        self.assertEqual(len(rows(self)), 1)
        with self.assertRaises(Conflict):
            self.use(31, key=key)
        with self.assertRaises(Conflict):
            billing.credit(self.db, self.a("admin"), 30, key)  # same key, a different operation
        with self.assertRaises(Conflict):
            billing.debit(self.db, self.a("admin"), 30, key)  # and a debit is a different operation too
        with self.assertRaises(Invalid):
            self.use(30, key=None)
        self.assertEqual(billing.balance(self.db, self.a("admin")), 30)

    def test_the_idempotency_key_follows_the_same_format_as_the_other_billing_writes(self):
        for bad in ("bad key", "x" * 65, "", "a/b", "café"):
            with self.assertRaises(Invalid, msg=repr(bad)):
                self.use(30, key=bad)
        self.assertEqual(rows(self), [])
        self.assertEqual(self.use(30, key="x" * 64), 30)
        self.assertEqual(self.use(5, key="A.b_c:d-1"), 35)

    def test_authority_is_the_live_role_not_the_principal_snapshot(self):  # INV-2
        snapshot = self.a("admin")
        self.db.execute("UPDATE memberships SET role = 'viewer' WHERE user_id = ?", (self.users["a_admin"],))
        with self.assertRaises(Forbidden):
            self.use(5, snapshot)
        self.db.execute("UPDATE memberships SET active = 0 WHERE user_id = ?", (self.users["a_admin"],))
        with self.assertRaises(Forbidden):
            self.use(5, snapshot)
        self.assertEqual(rows(self), [])

    def test_usage_credit_is_one_transaction_that_takes_the_lock_first(self):
        assert_disciplined(self, observe(self.db, lambda: self.use(5)))
        self.db.execute("INSERT INTO ledger (tenant_id, kind, amount_cents) VALUES (?, 'credit', ?)", (self.ta, CAP))
        assert_disciplined(self, observe(self.db, lambda: self.use(5)), expect_write=False)

    def test_http_route(self):
        app = make_app(self)
        tokens = {}
        for name, tenant in (("a_admin", self.ta), ("a_member", self.ta), ("b_owner", self.tb)):
            _, body = call(app, "POST", "/login", {"email": f"{name}@example.test",
                                                         "password": "correct-horse", "tenant_id": tenant})
            tokens[name] = body["token"]
        body = {"amount_cents": 125, "idempotency_key": nk()}
        self.assertEqual(call(app, "POST", "/billing/usage-credit", body, tokens["a_admin"]), (200, {"balance_cents": 125}))
        self.assertEqual(call(app, "POST", "/billing/usage-credit", body, tokens["a_admin"]), (200, {"balance_cents": 125}))
        self.assertEqual(call(app, "GET", "/billing/balance", token=tokens["a_admin"]), (200, {"balance_cents": 125}))
        self.assertEqual(call(app, "GET", "/billing/balance", token=tokens["b_owner"]), (200, {"balance_cents": 0}))
        self.assertEqual([r[1] for r in rows(self)], ["usage_credit"])
        self.assertEqual(call(app, "POST", "/billing/usage-credit",
                              {"amount_cents": 10 ** 9 + 1, "idempotency_key": nk()}, tokens["a_admin"])[0], 400)
        self.assertEqual(call(app, "POST", "/billing/usage-credit", body, tokens["a_member"])[0], 403)
        self.assertEqual(call(app, "POST", "/billing/usage-credit", {"amount_cents": 0, "idempotency_key": nk()},
                              tokens["a_admin"])[0], 400)
        self.assertEqual(call(app, "POST", "/billing/usage-credit", {"amount_cents": 5}, tokens["a_admin"])[0], 400)
        self.assertEqual(call(app, "POST", "/billing/usage-credit", {"amount_cents": 5, "idempotency_key": nk()})[0], 401)
        self.assertEqual(len(rows(self)), 1)


if __name__ == "__main__":
    unittest.main()
