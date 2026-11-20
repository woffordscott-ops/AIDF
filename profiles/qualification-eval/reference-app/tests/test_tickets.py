import unittest

from app import tenants, tickets
from app.errors import Forbidden, Invalid, NotFound

from tests.helpers import SharedFileWorld, World, nk


class TicketTests(World):
    def test_create_and_get(self):
        t = tickets.create_ticket(self.db, self.a("member"), "  broken login  ", idempotency_key=nk())
        self.assertEqual(t["title"], "broken login")
        self.assertEqual(tickets.get_ticket(self.db, self.a("viewer"), t["id"])["id"], t["id"])

    def test_viewer_cannot_create_or_assign(self):
        with self.assertRaises(Forbidden):
            tickets.create_ticket(self.db, self.a("viewer"), "x", idempotency_key=nk())
        t = tickets.create_ticket(self.db, self.a("member"), "x", idempotency_key=nk())
        with self.assertRaises(Forbidden):
            tickets.assign_ticket(self.db, self.a("viewer"), t["id"], self.users["a_member"])

    def test_blank_or_non_string_title_rejected(self):
        for bad in ("", "   ", None, 5):
            with self.assertRaises(Invalid):
                tickets.create_ticket(self.db, self.a("member"), bad, idempotency_key=nk())

    def test_other_tenant_cannot_read_ticket(self):  # INV-1
        t = tickets.create_ticket(self.db, self.a("member"), "private", idempotency_key=nk())
        with self.assertRaises(NotFound):
            tickets.get_ticket(self.db, self.b("owner"), t["id"])

    def test_other_tenant_cannot_assign_ticket(self):  # INV-1
        t = tickets.create_ticket(self.db, self.a("member"), "private", idempotency_key=nk())
        with self.assertRaises(NotFound):
            tickets.assign_ticket(self.db, self.b("owner"), t["id"], self.users["b_member"])
        self.assertIsNone(tickets.get_ticket(self.db, self.a("owner"), t["id"])["assignee_id"])

    def test_assign_to_same_tenant_member(self):
        t = tickets.create_ticket(self.db, self.a("member"), "x", idempotency_key=nk())
        out = tickets.assign_ticket(self.db, self.a("member"), t["id"], self.users["a_admin"])
        self.assertEqual(out["assignee_id"], self.users["a_admin"])

    def test_assign_to_other_tenants_member_rejected(self):  # INV-3
        t = tickets.create_ticket(self.db, self.a("member"), "x", idempotency_key=nk())
        for outsider in ("b_member", "b_owner", "outsider"):
            with self.assertRaises(Invalid):
                tickets.assign_ticket(self.db, self.a("member"), t["id"], self.users[outsider])
        self.assertIsNone(tickets.get_ticket(self.db, self.a("owner"), t["id"])["assignee_id"])

    def test_assign_to_removed_member_rejected(self):  # INV-3
        self.db.execute("UPDATE memberships SET active = 0 WHERE user_id = ?", (self.users["a_member"],))
        t = tickets.create_ticket(self.db, self.a("admin"), "x", idempotency_key=nk())
        with self.assertRaises(Invalid):
            tickets.assign_ticket(self.db, self.a("admin"), t["id"], self.users["a_member"])

    def test_assign_to_nonexistent_user_rejected(self):
        t = tickets.create_ticket(self.db, self.a("member"), "x", idempotency_key=nk())
        with self.assertRaises(Invalid):
            tickets.assign_ticket(self.db, self.a("member"), t["id"], 424242)


class RemovalUnassignsTests(World):
    """REV-002: INV-3 must keep holding after the assignee leaves."""

    def test_removing_member_clears_their_assignments_in_this_tenant(self):
        t = tickets.create_ticket(self.db, self.a("admin"), "x", idempotency_key=nk())
        tickets.assign_ticket(self.db, self.a("admin"), t["id"], self.users["a_member"])
        tenants.remove_member(self.db, self.a("admin"), self.users["a_member"])
        self.assertFalse(tenants.is_active_member(self.db, self.ta, self.users["a_member"]))
        self.assertIsNone(tickets.get_ticket(self.db, self.a("admin"), t["id"])["assignee_id"])

    def test_removal_leaves_other_assignees_and_other_tenants_alone(self):
        t1 = tickets.create_ticket(self.db, self.a("admin"), "x", idempotency_key=nk())
        t2 = tickets.create_ticket(self.db, self.a("admin"), "y", idempotency_key=nk())
        tickets.assign_ticket(self.db, self.a("admin"), t1["id"], self.users["a_member"])
        tickets.assign_ticket(self.db, self.a("admin"), t2["id"], self.users["a_admin"])
        tb_ticket = tickets.create_ticket(self.db, self.b("member"), "b", idempotency_key=nk())
        tickets.assign_ticket(self.db, self.b("member"), tb_ticket["id"], self.users["b_member"])
        tenants.remove_member(self.db, self.a("admin"), self.users["a_member"])
        self.assertEqual(tickets.get_ticket(self.db, self.a("admin"), t2["id"])["assignee_id"],
                         self.users["a_admin"])
        self.assertEqual(tickets.get_ticket(self.db, self.b("owner"), tb_ticket["id"])["assignee_id"],
                         self.users["b_member"])

    def test_readded_member_is_not_silently_reassigned(self):
        t = tickets.create_ticket(self.db, self.a("admin"), "x", idempotency_key=nk())
        tickets.assign_ticket(self.db, self.a("admin"), t["id"], self.users["a_member"])
        tenants.remove_member(self.db, self.a("admin"), self.users["a_member"])
        tenants.add_member(self.db, self.a("admin"), self.users["a_member"], "member")
        self.assertIsNone(tickets.get_ticket(self.db, self.a("admin"), t["id"])["assignee_id"])


class RemovalIsTenantScopedTests(World):
    """R2-004: removal from one tenant must not touch the same user's work in another."""

    def test_removal_from_tenant_a_keeps_the_users_assignment_in_tenant_b(self):  # INV-1
        shared = self.users["outsider"]
        tenants.add_member(self.db, self.a("owner"), shared, "member")
        tenants.add_member(self.db, self.b("owner"), shared, "member")
        ta_ticket = tickets.create_ticket(self.db, self.a("owner"), "in a", idempotency_key=nk())
        tb_ticket = tickets.create_ticket(self.db, self.b("owner"), "in b", idempotency_key=nk())
        tickets.assign_ticket(self.db, self.a("owner"), ta_ticket["id"], shared)
        tickets.assign_ticket(self.db, self.b("owner"), tb_ticket["id"], shared)
        tenants.remove_member(self.db, self.a("owner"), shared)
        self.assertIsNone(tickets.get_ticket(self.db, self.a("owner"), ta_ticket["id"])["assignee_id"])
        self.assertEqual(tickets.get_ticket(self.db, self.b("owner"), tb_ticket["id"])["assignee_id"], shared)
        self.assertTrue(tenants.is_active_member(self.db, self.tb, shared))


class ConcurrentAssignmentTests(SharedFileWorld):
    """Assignment must decide under the write lock (INV-3 holds over time, not only at check time)."""

    def setUp(self):
        super().setUp()
        owner = self.principal("a", "owner")
        tenants.add_member(self.c1, owner, self.uid["m"], "member")
        self.ticket = tickets.create_ticket(self.c1, owner, "x", idempotency_key=nk())

    def assignee(self):
        return self.c1.execute("SELECT assignee_id FROM tickets WHERE id = ?", (self.ticket["id"],)).fetchone()[0]

    def test_assignee_removed_before_the_lock_is_taken_is_never_assigned(self):
        owner = self.principal("a", "owner")
        fired = self.at_first_begin(self.c1, lambda: tenants.remove_member(self.c2, owner, self.uid["m"]))
        with self.assertRaises(Invalid):
            tickets.assign_ticket(self.c1, owner, self.ticket["id"], self.uid["m"])
        self.assertTrue(fired, "the interleaving never happened")
        self.assertIsNone(self.assignee())
        self.assertFalse(tenants.is_active_member(self.c1, self.tid, self.uid["m"]))

    def test_caller_demoted_before_the_lock_is_taken_cannot_assign(self):
        tenants.add_member(self.c1, self.principal("a", "owner"), self.uid["b"], "member")
        fired = self.at_first_begin(self.c1, lambda: self.c2.execute(
            "UPDATE memberships SET role = 'viewer' WHERE user_id = ?", (self.uid["b"],)))
        with self.assertRaises(Forbidden):
            tickets.assign_ticket(self.c1, self.principal("b", "member"), self.ticket["id"], self.uid["m"])
        self.assertTrue(fired, "the interleaving never happened")
        self.assertIsNone(self.assignee())

    def test_sequential_assignment_still_works(self):
        out = tickets.assign_ticket(self.c1, self.principal("a", "owner"), self.ticket["id"], self.uid["m"])
        self.assertEqual(out["assignee_id"], self.uid["m"])


if __name__ == "__main__":
    unittest.main()
