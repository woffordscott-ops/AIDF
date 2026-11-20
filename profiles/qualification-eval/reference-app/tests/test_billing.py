import sqlite3
import unittest

from app import billing
from app.errors import Conflict, Forbidden, Invalid, NotFound

from tests.helpers import World, nk


class LedgerTests(World):
    def test_credit_then_debit(self):
        self.assertEqual(billing.credit(self.db, self.a("admin"), 1000, idempotency_key=nk()), 1000)
        self.assertEqual(billing.debit(self.db, self.a("admin"), 250, idempotency_key=nk()), 750)
        self.assertEqual(billing.balance(self.db, self.a("owner")), 750)

    def test_debit_to_exactly_zero_allowed_below_zero_rejected(self):  # INV-4
        billing.credit(self.db, self.a("admin"), 500, idempotency_key=nk())
        self.assertEqual(billing.debit(self.db, self.a("admin"), 500, idempotency_key=nk()), 0)
        with self.assertRaises(Conflict):
            billing.debit(self.db, self.a("admin"), 1, idempotency_key=nk())
        self.assertEqual(billing.balance(self.db, self.a("admin")), 0)

    def test_overdraft_leaves_ledger_unchanged(self):  # INV-4
        billing.credit(self.db, self.a("admin"), 100, idempotency_key=nk())
        with self.assertRaises(Conflict):
            billing.debit(self.db, self.a("admin"), 101, idempotency_key=nk())
        self.assertEqual(billing.balance(self.db, self.a("admin")), 100)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM ledger").fetchone()[0], 1)

    def test_amounts_must_be_positive_integers(self):  # INV-4
        for bad in (0, -5, 1.5, "10", None, True, [1]):
            for fn in (billing.credit, billing.debit):
                with self.assertRaises(Invalid):
                    fn(self.db, self.a("admin"), bad, idempotency_key=nk())

    def test_negative_credit_cannot_act_as_a_debit(self):  # INV-4
        billing.credit(self.db, self.a("admin"), 100, idempotency_key=nk())
        with self.assertRaises(Invalid):
            billing.credit(self.db, self.a("admin"), -1000, idempotency_key=nk())
        self.assertEqual(billing.balance(self.db, self.a("admin")), 100)

    def test_tenants_have_separate_balances(self):  # INV-1
        billing.credit(self.db, self.a("admin"), 900, idempotency_key=nk())
        self.assertEqual(billing.balance(self.db, self.b("owner")), 0)
        with self.assertRaises(Conflict):
            billing.debit(self.db, self.b("owner"), 1, idempotency_key=nk())

    def test_only_admin_and_owner_may_touch_billing(self):
        for role in ("member", "viewer"):
            for call in (billing.balance, lambda d, p: billing.credit(d, p, 1, idempotency_key=nk()), lambda d, p: billing.debit(d, p, 1, idempotency_key=nk())):
                with self.assertRaises(Forbidden):
                    call(self.db, self.a(role))

    def test_failed_debit_does_not_leave_a_transaction_open(self):
        billing.credit(self.db, self.a("admin"), 10, idempotency_key=nk())
        with self.assertRaises(Conflict):
            billing.debit(self.db, self.a("admin"), 11, idempotency_key=nk())
        self.assertFalse(self.db.in_transaction)
        self.assertEqual(billing.debit(self.db, self.a("admin"), 10, idempotency_key=nk()), 0)


class InvoiceTests(World):
    LINES = (
        {"description": "seats", "amount_cents": 1200},
        {"description": "support", "amount_cents": 300},
    )

    def test_total_is_sum_of_lines(self):  # INV-4
        inv = billing.create_invoice(self.db, self.a("admin"), list(self.LINES), idempotency_key=nk())
        self.assertEqual(inv["total_cents"], 1500)
        self.assertEqual(sum(l["amount_cents"] for l in inv["lines"]), inv["total_cents"])

    def test_invalid_invoices_rejected_and_not_stored(self):  # INV-4
        bad_sets = [[], None, "x", [{"description": "a"}], [{"description": "a", "amount_cents": -5}],
                    [{"description": "a", "amount_cents": 1.5}], [{"amount_cents": 5}], ["line"]]
        for bad in bad_sets:
            with self.assertRaises(Invalid):
                billing.create_invoice(self.db, self.a("admin"), bad, idempotency_key=nk())
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM invoices").fetchone()[0], 0)

    def test_invoice_not_visible_to_other_tenant(self):  # INV-1
        inv = billing.create_invoice(self.db, self.a("admin"), list(self.LINES), idempotency_key=nk())
        with self.assertRaises(NotFound):
            billing.get_invoice(self.db, self.b("owner"), inv["id"])

    def test_member_cannot_create_invoice(self):
        with self.assertRaises(Forbidden):
            billing.create_invoice(self.db, self.a("member"), list(self.LINES), idempotency_key=nk())


class BoundsTests(World):
    """REV-005: no amount or balance can reach SQLite's signed 64-bit limit."""

    def test_amount_above_the_per_operation_cap_rejected(self):  # INV-4
        for fn in (billing.credit, billing.debit):
            for big in (billing.MAX_AMOUNT_CENTS + 1, 2**62, 2**63 - 1, 2**63, 10**400):
                with self.assertRaises(Invalid):
                    fn(self.db, self.a("admin"), big, idempotency_key=nk())

    def test_exactly_the_cap_is_allowed(self):
        self.assertEqual(billing.credit(self.db, self.a("admin"), billing.MAX_AMOUNT_CENTS, idempotency_key=nk()),
                         billing.MAX_AMOUNT_CENTS)

    def test_balance_cannot_exceed_its_cap_and_ledger_stays_readable(self):  # INV-4
        p = self.a("admin")
        credited = 0
        while credited + billing.MAX_AMOUNT_CENTS <= billing.MAX_BALANCE_CENTS:
            credited = billing.credit(self.db, p, billing.MAX_AMOUNT_CENTS, idempotency_key=nk())
        with self.assertRaises(Conflict):
            billing.credit(self.db, p, billing.MAX_AMOUNT_CENTS, idempotency_key=nk())
        self.assertEqual(billing.balance(self.db, p), credited)
        self.assertFalse(self.db.in_transaction)

    def test_oversized_invoice_lines_and_totals_rejected_and_not_stored(self):  # INV-4
        bad = [[{"description": "a", "amount_cents": 2**62}] * 2,
               [{"description": "a", "amount_cents": billing.MAX_AMOUNT_CENTS}] * 1001]
        for lines in bad:
            with self.assertRaises(Invalid):
                billing.create_invoice(self.db, self.a("admin"), lines, idempotency_key=nk())
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM invoices").fetchone()[0], 0)


class InvoiceAtomicityTests(World):
    """R2-003: an invoice and its lines are stored together or not at all (INV-4)."""

    def test_failure_while_storing_a_line_leaves_no_invoice_and_no_open_transaction(self):
        self.db.execute(
            "CREATE TRIGGER stop_second BEFORE INSERT ON invoice_lines "
            "WHEN (SELECT COUNT(*) FROM invoice_lines WHERE invoice_id = NEW.invoice_id) >= 1 "
            "BEGIN SELECT RAISE(ABORT, 'boom'); END")
        lines = [{"description": "a", "amount_cents": 10}, {"description": "b", "amount_cents": 20}]
        with self.assertRaises(sqlite3.IntegrityError):
            billing.create_invoice(self.db, self.a("admin"), lines, idempotency_key=nk())
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM invoices").fetchone()[0], 0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM invoice_lines").fetchone()[0], 0)
        self.assertFalse(self.db.in_transaction)

    def test_successful_invoice_total_still_equals_line_sum(self):
        lines = [{"description": "a", "amount_cents": 10}, {"description": "b", "amount_cents": 20}]
        inv = billing.create_invoice(self.db, self.a("admin"), lines, idempotency_key=nk())
        self.assertEqual((inv["total_cents"], len(inv["lines"])), (30, 2))


if __name__ == "__main__":
    unittest.main()
