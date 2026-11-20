"""SR-001: a caller removed or demoted just before an operation takes its lock must not complete it.

The Principal a request arrives with is a snapshot. Every state-changing operation re-reads the caller's
authority inside its own transaction. These tests remove or demote the caller at the exact moment the
operation reaches BEGIN IMMEDIATE (deterministic, not scheduler-dependent) and require a refusal with no
effect. Each asserts the interleaving really happened.
"""
import sqlite3
import unittest

from app import billing, tenants, tickets
from app.errors import Forbidden

from tests.helpers import SharedFileWorld, nk


class LiveAuthorityTests(SharedFileWorld):
    def setUp(self):
        super().setUp()
        self.owner = self.principal("a", "owner")
        tenants.add_member(self.c1, self.owner, self.uid["b"], "admin")
        tenants.add_member(self.c1, self.owner, self.uid["m"], "member")
        self.admin = self.principal("b", "admin")
        billing.credit(self.c1, self.owner, 100, idempotency_key=nk())
        self.ticket = tickets.create_ticket(self.c1, self.owner, "seed", idempotency_key=nk())

    def count(self, table):
        return self.c1.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def revoke_at_lock(self, how="remove"):
        if how == "remove":
            action = lambda: tenants.remove_member(self.c2, self.owner, self.uid["b"])
        else:
            action = lambda: self.c2.execute(
                "UPDATE memberships SET role = 'viewer' WHERE user_id = ?", (self.uid["b"],))
        return self.at_first_begin(self.c1, action)

    def refused(self, operation, how="remove"):
        fired = self.revoke_at_lock(how)
        with self.assertRaises(Forbidden):
            operation()
        self.assertTrue(fired, "the interleaving never happened")

    def test_credit(self):
        self.refused(lambda: billing.credit(self.c1, self.admin, 50, idempotency_key=nk()))
        self.assertEqual(billing.balance(self.c1, self.owner), 100)

    def test_debit(self):
        self.refused(lambda: billing.debit(self.c1, self.admin, 50, idempotency_key=nk()))
        self.assertEqual(billing.balance(self.c1, self.owner), 100)

    def test_create_invoice(self):
        self.refused(lambda: billing.create_invoice(
            self.c1, self.admin, [{"description": "a", "amount_cents": 10}], idempotency_key=nk()))
        self.assertEqual(self.count("invoices"), 0)

    def test_create_ticket(self):
        before = self.count("tickets")
        self.refused(lambda: tickets.create_ticket(self.c1, self.admin, "late", idempotency_key=nk()))
        self.assertEqual(self.count("tickets"), before)

    def test_assign_ticket(self):
        self.refused(lambda: tickets.assign_ticket(self.c1, self.admin, self.ticket["id"], self.uid["m"]))
        self.assertIsNone(self.c1.execute("SELECT assignee_id FROM tickets").fetchone()[0])

    def test_demotion_is_treated_like_removal(self):
        self.refused(lambda: billing.credit(self.c1, self.admin, 50, idempotency_key=nk()), how="demote")
        self.assertEqual(billing.balance(self.c1, self.owner), 100)

    def test_a_caller_who_keeps_authority_still_succeeds(self):
        self.assertEqual(billing.credit(self.c1, self.admin, 50, idempotency_key=nk()), 150)


class CreateTenantAtomicityTests(SharedFileWorld):
    def test_a_tenant_never_exists_without_its_first_owner(self):
        self.c1.execute(
            "CREATE TRIGGER stop_owner BEFORE INSERT ON memberships "
            "WHEN NEW.tenant_id > 1 BEGIN SELECT RAISE(ABORT, 'boom'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            tenants.create_tenant(self.c1, "second", self.uid["b"])
        self.assertEqual(self.c1.execute("SELECT COUNT(*) FROM tenants").fetchone()[0], 1)
        self.assertFalse(self.c1.in_transaction)


if __name__ == "__main__":
    unittest.main()
