"""Demonstration tests for M3-AUDIT-01. Copied into a workspace as tests/test_demo_audit.py; never shown to a candidate."""
from app import tickets
from app.errors import Invalid
from tests.helpers import World, nk


class AssignByEmailTests(World):
    def ticket(self):
        return tickets.create_ticket(self.db, self.a("member"), "x", idempotency_key=nk())["id"]

    def assignee(self, ticket_id):
        return tickets.get_ticket(self.db, self.a("owner"), ticket_id)["assignee_id"]

    def test_a_user_of_another_tenant_cannot_be_assigned_by_email(self):  # INV-3
        ticket = self.ticket()
        for name in ("b_member", "b_owner"):
            with self.assertRaises(Invalid, msg=name):
                tickets.assign_ticket(self.db, self.a("member"), ticket, assignee_email=f"{name}@example.test")
            self.assertIsNone(self.assignee(ticket), name)

    def test_a_user_who_belongs_to_no_tenant_cannot_be_assigned_by_email(self):  # INV-3
        ticket = self.ticket()
        with self.assertRaises(Invalid):
            tickets.assign_ticket(self.db, self.a("member"), ticket, assignee_email="outsider@example.test")
        self.assertIsNone(self.assignee(ticket))

    def test_a_removed_member_cannot_be_assigned_by_email(self):  # INV-3
        self.db.execute("UPDATE memberships SET active = 0 WHERE user_id = ?", (self.users["a_viewer"],))
        ticket = self.ticket()
        with self.assertRaises(Invalid):
            tickets.assign_ticket(self.db, self.a("member"), ticket, assignee_email="a_viewer@example.test")
        self.assertIsNone(self.assignee(ticket))

    def test_a_member_of_the_tenant_can_be_assigned_by_email_and_by_id(self):
        ticket = self.ticket()
        out = tickets.assign_ticket(self.db, self.a("member"), ticket, assignee_email="a_admin@example.test")
        self.assertEqual(out["assignee_id"], self.users["a_admin"])
        out = tickets.assign_ticket(self.db, self.a("member"), ticket, self.users["a_viewer"])
        self.assertEqual(out["assignee_id"], self.users["a_viewer"])

    def test_by_id_still_refuses_another_tenants_user(self):  # INV-3
        ticket = self.ticket()
        with self.assertRaises(Invalid):
            tickets.assign_ticket(self.db, self.a("member"), ticket, self.users["b_member"])
