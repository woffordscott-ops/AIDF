"""Hidden tests for M1-MEMBERS-01. Copied into a workspace as tests/test_hidden_members.py; never shown to a candidate."""
import unittest

from app import tenants, tickets
from app.errors import Conflict, Forbidden, Invalid, NotFound
from tests.helpers import SharedFileWorld, World, call, make_app
from tests.test_lock_discipline import assert_disciplined as _disciplined
from tests.test_lock_discipline import observe


def assert_disciplined(case, log, expect_write=True):
    _disciplined(case, log, expect_write)
    case.assertIn(log[-1][0], ("COMMIT", "ROLLBACK"), "nothing may run after the transaction ends")


class ChangeRoleTests(World):
    def role(self, name, tenant=None):
        return tenants.get_role(self.db, tenant or self.ta, self.users[name])

    def change(self, who, target, new_role):
        return tenants.change_role(self.db, who, self.users[target], new_role)

    def test_an_owner_changes_any_role_and_the_stored_role_is_updated(self):
        self.assertEqual(self.change(self.a("owner"), "a_member", "admin"),
                         {"user_id": self.users["a_member"], "role": "admin"})
        self.assertEqual(self.role("a_member"), "admin")
        self.change(self.a("owner"), "a_admin", "viewer")
        self.assertEqual(self.role("a_admin"), "viewer")
        self.change(self.a("owner"), "a_viewer", "owner")
        self.assertEqual(self.role("a_viewer"), "owner")

    def test_an_admin_changes_roles_up_to_admin_but_never_to_owner(self):  # INV-2
        self.change(self.a("admin"), "a_member", "admin")
        self.change(self.a("admin"), "a_viewer", "member")
        self.assertEqual((self.role("a_member"), self.role("a_viewer")), ("admin", "member"))
        with self.assertRaises(Forbidden):
            self.change(self.a("admin"), "a_member", "owner")
        self.assertEqual(self.role("a_member"), "admin")

    def test_nobody_changes_the_role_of_someone_above_their_own(self):  # INV-2
        self.change(self.a("owner"), "a_member", "owner")  # two owners, so the last-owner rule is not the reason
        with self.assertRaises(Forbidden):
            self.change(self.a("admin"), "a_owner", "member")
        with self.assertRaises(Forbidden):
            self.change(self.a("admin"), "a_owner", "member")
        with self.assertRaises(Forbidden):
            self.change(self.a("admin"), "a_owner", "admin")
        with self.assertRaises(Forbidden):
            self.change(self.a("admin"), "a_owner", "owner")
        self.assertEqual(self.role("a_owner"), "owner")

    def test_an_admin_may_change_another_admin_and_may_change_their_own_role(self):  # INV-2
        self.change(self.a("owner"), "a_member", "admin")
        self.change(self.a("admin"), "a_member", "viewer")
        self.assertEqual(self.role("a_member"), "viewer")
        self.change(self.a("owner"), "a_member", "admin")
        self.assertEqual(self.change(self.a("admin"), "a_admin", "member"),
                         {"user_id": self.users["a_admin"], "role": "member"})
        self.assertEqual(self.role("a_admin"), "member")

    def test_authority_is_checked_before_the_input_like_the_other_member_writes(self):  # INV-2
        for who in ("member", "viewer"):
            for bad_role, bad_id in (("root", None), (None, None), ("admin", 0), ("admin", 2 ** 70)):
                with self.assertRaises(Forbidden, msg=(who, bad_role, bad_id)):
                    tenants.change_role(self.db, self.a(who), self.users["a_viewer"] if bad_id is None else bad_id, bad_role)

    def test_a_snapshot_that_understates_the_live_role_is_still_refused(self):  # INV-2
        with self.assertRaises(Forbidden):
            self.change(self.principal(self.ta, "a_admin", "viewer"), "a_viewer", "member")
        self.assertEqual(self.role("a_viewer"), "viewer")

    def test_a_member_or_viewer_cannot_change_roles(self):
        for role in ("member", "viewer"):
            with self.assertRaises(Forbidden):
                self.change(self.a(role), "a_viewer", "viewer")
            with self.assertRaises(Forbidden):
                self.change(self.a(role), "a_member", "viewer")

    def test_the_last_owner_cannot_be_demoted_but_one_of_two_can(self):  # INV-2
        with self.assertRaises(Conflict):
            self.change(self.a("owner"), "a_owner", "admin")
        self.assertEqual(self.role("a_owner"), "owner")
        self.change(self.a("owner"), "a_admin", "owner")
        self.change(self.a("owner"), "a_owner", "admin")
        self.assertEqual((self.role("a_owner"), self.role("a_admin")), ("admin", "owner"))
        with self.assertRaises(Conflict):
            self.change(self.principal(self.ta, "a_admin", "owner"), "a_admin", "member")
        self.assertEqual(self.role("a_admin"), "owner")

    def test_an_unknown_role_or_target_is_refused(self):
        for bad in ("root", "", "OWNER", None, 5, ["admin"]):
            with self.assertRaises(Invalid, msg=repr(bad)):
                self.change(self.a("owner"), "a_member", bad)
        for bad in (0, -1, True, "1", None, 2 ** 63, 2 ** 70):
            with self.assertRaises(Invalid, msg=repr(bad)):
                tenants.change_role(self.db, self.a("owner"), bad, "admin")
        with self.assertRaises(NotFound):
            tenants.change_role(self.db, self.a("owner"), 424242, "admin")
        self.assertEqual(self.role("a_member"), "member")

    def test_another_tenant_or_a_removed_member_cannot_be_changed(self):  # INV-1
        with self.assertRaises(NotFound):
            self.change(self.a("owner"), "b_member", "viewer")
        with self.assertRaises(NotFound):
            self.change(self.b("owner"), "a_member", "viewer")
        self.assertEqual((self.role("b_member", self.tb), self.role("a_member")), ("member", "member"))
        tenants.remove_member(self.db, self.a("owner"), self.users["a_viewer"])
        with self.assertRaises(NotFound):
            self.change(self.a("owner"), "a_viewer", "member")
        self.assertIsNone(self.role("a_viewer"))
        active = self.db.execute("SELECT active FROM memberships WHERE user_id = ? AND tenant_id = ?",
                                 (self.users["a_viewer"], self.ta)).fetchone()[0]
        self.assertEqual(active, 0)

    def test_authority_is_the_live_role_not_the_principal_snapshot(self):  # INV-2
        snapshot = self.a("owner")
        self.db.execute("UPDATE memberships SET role = 'member' WHERE user_id = ?", (self.users["a_owner"],))
        self.db.execute("UPDATE memberships SET role = 'owner' WHERE user_id = ?", (self.users["a_admin"],))
        with self.assertRaises(Forbidden):
            self.change(snapshot, "a_viewer", "admin")
        self.db.execute("UPDATE memberships SET active = 0 WHERE user_id = ?", (self.users["a_owner"],))
        with self.assertRaises(Forbidden):
            self.change(snapshot, "a_viewer", "admin")
        self.assertEqual(self.role("a_viewer"), "viewer")

    def test_a_change_in_one_tenant_leaves_the_same_user_in_another_tenant_alone(self):  # INV-1
        self.db.execute("INSERT INTO memberships (tenant_id, user_id, role) VALUES (?, ?, 'admin')",
                        (self.tb, self.users["a_member"]))
        self.change(self.a("owner"), "a_member", "viewer")
        self.assertEqual((self.role("a_member"), self.role("a_member", self.tb)), ("viewer", "admin"))

    def test_the_last_owner_cannot_be_demoted_to_any_role(self):  # INV-2
        for role in ("admin", "member", "viewer"):
            with self.assertRaises(Conflict, msg=role):
                self.change(self.a("owner"), "a_owner", role)
        self.assertEqual(self.role("a_owner"), "owner")

    def test_the_answer_names_the_new_role_for_every_role(self):
        for role in ("viewer", "member", "admin", "owner"):
            self.assertEqual(self.change(self.a("owner"), "a_viewer", role),
                             {"user_id": self.users["a_viewer"], "role": role})

    def test_a_role_change_leaves_the_members_ticket_assignments_alone(self):  # INV-3
        ticket = tickets.create_ticket(self.db, self.a("member"), "x", idempotency_key="k-members-1")
        tickets.assign_ticket(self.db, self.a("member"), ticket["id"], self.users["a_member"])
        self.change(self.a("owner"), "a_member", "viewer")
        self.assertEqual(tickets.get_ticket(self.db, self.a("owner"), ticket["id"])["assignee_id"],
                         self.users["a_member"])

    def test_a_removed_owner_does_not_count_as_an_owner(self):  # INV-2
        self.change(self.a("owner"), "a_admin", "owner")
        tenants.remove_member(self.db, self.a("owner"), self.users["a_admin"])
        with self.assertRaises(Conflict):
            self.change(self.a("owner"), "a_owner", "admin")
        self.assertEqual(self.role("a_owner"), "owner")

    def test_a_caller_demoted_to_admin_can_no_longer_grant_owner(self):  # INV-2
        snapshot = self.a("owner")
        self.db.execute("UPDATE memberships SET role = 'admin' WHERE user_id = ?", (self.users["a_owner"],))
        self.db.execute("UPDATE memberships SET role = 'owner' WHERE user_id = ?", (self.users["a_admin"],))
        with self.assertRaises(Forbidden):
            self.change(snapshot, "a_viewer", "owner")
        self.assertEqual(self.role("a_viewer"), "viewer")

    def test_other_memberships_are_untouched(self):
        query = "SELECT tenant_id, user_id, role, active FROM memberships ORDER BY 1, 2"
        before = self.db.execute(query).fetchall()
        self.change(self.a("owner"), "a_member", "viewer")
        after = self.db.execute(query).fetchall()
        changed = [(tuple(x), tuple(y)) for x, y in zip(before, after) if tuple(x) != tuple(y)]
        self.assertEqual(len(changed), 1)
        self.assertEqual((changed[0][0][:2], changed[0][1][2:]), ((self.ta, self.users["a_member"]), ("viewer", 1)))

    def test_change_role_is_one_transaction_that_takes_the_lock_first(self):
        assert_disciplined(self, observe(self.db, lambda: self.change(self.a("owner"), "a_member", "admin")))
        assert_disciplined(self, observe(self.db, lambda: self.change(self.a("owner"), "a_owner", "admin")),
                           expect_write=False)

    def test_http_route(self):
        app = make_app(self)
        tokens = {}
        for name, tenant in (("a_owner", self.ta), ("a_admin", self.ta), ("a_member", self.ta), ("b_owner", self.tb)):
            _, body = call(app, "POST", "/login", {"email": f"{name}@example.test",
                                                         "password": "correct-horse", "tenant_id": tenant})
            tokens[name] = body["token"]
        path = f"/members/{self.users['a_viewer']}/role"
        self.assertEqual(call(app, "POST", path, {"role": "member"}, tokens["a_admin"]),
                         (200, {"user_id": self.users["a_viewer"], "role": "member"}))
        self.assertEqual(call(app, "POST", path, {"role": "owner"}, tokens["a_admin"])[0], 403)
        self.assertEqual(call(app, "POST", path, {"role": "member"}, tokens["a_member"])[0], 403)
        self.assertEqual(call(app, "POST", path, {"role": "root"}, tokens["a_owner"])[0], 400)
        self.assertEqual(call(app, "POST", path, {}, tokens["a_owner"])[0], 400)
        self.assertEqual(call(app, "POST", path, {"role": "member"}, tokens["b_owner"])[0], 404)
        self.assertEqual(call(app, "POST", path, {"role": "member"})[0], 401)
        own = f"/members/{self.users['a_owner']}/role"
        self.assertEqual(call(app, "POST", own, {"role": "admin"}, tokens["a_owner"])[0], 409)
        self.assertEqual(self.role("a_viewer"), "member")
        self.assertEqual(self.role("a_owner"), "owner")


class RaceTests(SharedFileWorld):
    def setUp(self):
        super().setUp()
        tenants.add_member(self.c1, self.principal("a", "owner"), self.uid["b"], "owner")

    def test_two_owners_demoting_each_other_never_leave_zero_owners(self):  # INV-2
        fired = self.at_first_begin(self.c1, lambda: tenants.change_role(
            self.c2, self.principal("b", "owner"), self.uid["a"], "member"))
        with self.assertRaises((Forbidden, Conflict)):
            tenants.change_role(self.c1, self.principal("a", "owner"), self.uid["b"], "member")
        self.assertTrue(fired, "the interleaving never happened")
        self.assertEqual(self.active_owners(), 1)

    def test_an_actor_demoted_before_the_lock_is_taken_cannot_change_a_role(self):  # INV-2
        tenants.add_member(self.c1, self.principal("a", "owner"), self.uid["m"], "member")
        self.c1.execute("UPDATE memberships SET role = 'admin' WHERE user_id = ?", (self.uid["b"],))
        fired = self.at_first_begin(self.c1, lambda: self.c2.execute(
            "UPDATE memberships SET role = 'viewer' WHERE user_id = ?", (self.uid["b"],)))
        with self.assertRaises(Forbidden):
            tenants.change_role(self.c1, self.principal("b", "admin"), self.uid["m"], "admin")
        self.assertTrue(fired, "the interleaving never happened")
        self.assertEqual(tenants.get_role(self.c1, self.tid, self.uid["m"]), "member")


if __name__ == "__main__":
    unittest.main()
