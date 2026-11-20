import unittest

from app import permissions, tenants
from app.errors import Conflict, Forbidden, Invalid, NotFound

from tests.helpers import SharedFileWorld, World


class PermissionTests(unittest.TestCase):
    def test_matrix(self):
        expect = {
            "ticket.read": {"viewer", "member", "admin", "owner"},
            "ticket.create": {"member", "admin", "owner"},
            "ticket.assign": {"member", "admin", "owner"},
            "member.manage": {"admin", "owner"},
            "billing.read": {"admin", "owner"},
            "billing.write": {"admin", "owner"},
        }
        for action, allowed in expect.items():
            for role in permissions.ROLE_RANK:
                self.assertEqual(permissions.can(role, action), role in allowed, (action, role))

    def test_unknown_action_and_role_denied(self):
        self.assertFalse(permissions.can("owner", "tenant.delete"))
        self.assertFalse(permissions.can("superuser", "ticket.read"))

    def test_can_grant_never_exceeds_own_rank(self):  # INV-2
        for g, gr in permissions.ROLE_RANK.items():
            for t, tr in permissions.ROLE_RANK.items():
                self.assertEqual(permissions.can_grant(g, t), tr <= gr)
        self.assertFalse(permissions.can_grant("owner", "root"))


class MembershipTests(World):
    def new_user(self, name="newbie"):
        self.users[name] = self._user(name)
        return self.users[name]

    def test_admin_adds_member_but_cannot_grant_owner(self):  # INV-2
        uid = self.new_user()
        with self.assertRaises(Forbidden):
            tenants.add_member(self.db, self.a("admin"), uid, "owner")
        tenants.add_member(self.db, self.a("admin"), uid, "member")
        self.assertEqual(tenants.get_role(self.db, self.ta, uid), "member")

    def test_member_and_viewer_cannot_manage(self):
        uid = self.new_user()
        for role in ("member", "viewer"):
            with self.assertRaises(Forbidden):
                tenants.add_member(self.db, self.a(role), uid, "viewer")

    def test_unknown_role_user_and_duplicate(self):
        uid = self.new_user()
        with self.assertRaises(Invalid):
            tenants.add_member(self.db, self.a("owner"), uid, "root")
        with self.assertRaises(NotFound):
            tenants.add_member(self.db, self.a("owner"), 9999, "member")
        with self.assertRaises(Conflict):
            tenants.add_member(self.db, self.a("owner"), self.users["a_member"], "member")

    def test_membership_is_per_tenant(self):  # INV-1
        uid = self.new_user()
        tenants.add_member(self.db, self.a("owner"), uid, "admin")
        self.assertIsNone(tenants.get_role(self.db, self.tb, uid))

    def test_admin_cannot_remove_owner(self):  # INV-2
        with self.assertRaises(Forbidden):
            tenants.remove_member(self.db, self.a("admin"), self.users["a_owner"])

    def test_last_owner_cannot_be_removed_even_by_themselves(self):  # INV-2
        with self.assertRaises(Conflict):
            tenants.remove_member(self.db, self.a("owner"), self.users["a_owner"])
        self.assertEqual(tenants.get_role(self.db, self.ta, self.users["a_owner"]), "owner")

    def test_owner_removable_when_another_owner_exists(self):
        uid = self.new_user()
        tenants.add_member(self.db, self.a("owner"), uid, "owner")
        tenants.remove_member(self.db, self.a("owner"), self.users["a_owner"])
        self.assertIsNone(tenants.get_role(self.db, self.ta, self.users["a_owner"]))

    def test_cannot_remove_across_tenants(self):  # INV-1
        with self.assertRaises(NotFound):
            tenants.remove_member(self.db, self.a("owner"), self.users["b_member"])

    def test_removed_member_can_be_readded(self):
        tenants.remove_member(self.db, self.a("admin"), self.users["a_member"])
        tenants.add_member(self.db, self.a("admin"), self.users["a_member"], "viewer")
        self.assertEqual(tenants.get_role(self.db, self.ta, self.users["a_member"]), "viewer")


class ConcurrentMembershipTests(SharedFileWorld):
    """R2-001: decisions must be made under the write lock, not before it (INV-2)."""

    def setUp(self):
        super().setUp()
        tenants.add_member(self.c1, self.principal("a", "owner"), self.uid["b"], "owner")

    def test_two_owners_removing_each_other_never_leaves_zero_owners(self):
        # B's removal of A runs to completion at the moment A's removal of B reaches the lock.
        fired = self.at_first_begin(self.c1, lambda: tenants.remove_member(
            self.c2, self.principal("b", "owner"), self.uid["a"]))
        with self.assertRaises((Forbidden, Conflict)):
            tenants.remove_member(self.c1, self.principal("a", "owner"), self.uid["b"])
        self.assertTrue(fired, "the interleaving never happened")
        self.assertEqual(self.active_owners(), 1)

    def test_actor_demoted_before_the_lock_is_taken_cannot_remove(self):
        tenants.add_member(self.c1, self.principal("a", "owner"), self.uid["m"], "member")
        self.c1.execute("UPDATE memberships SET role = 'admin' WHERE user_id = ?", (self.uid["b"],))
        fired = self.at_first_begin(self.c1, lambda: self.c2.execute(
            "UPDATE memberships SET role = 'viewer' WHERE user_id = ?", (self.uid["b"],)))
        with self.assertRaises(Forbidden):
            tenants.remove_member(self.c1, self.principal("b", "admin"), self.uid["m"])
        self.assertTrue(fired, "the interleaving never happened")
        self.assertEqual(tenants.get_role(self.c1, self.tid, self.uid["m"]), "member")

    def test_actor_demoted_before_the_lock_is_taken_cannot_add(self):
        self.c1.execute("UPDATE memberships SET role = 'admin' WHERE user_id = ?", (self.uid["b"],))
        fired = self.at_first_begin(self.c1, lambda: self.c2.execute(
            "UPDATE memberships SET role = 'viewer' WHERE user_id = ?", (self.uid["b"],)))
        with self.assertRaises(Forbidden):
            tenants.add_member(self.c1, self.principal("b", "admin"), self.uid["m"], "member")
        self.assertTrue(fired, "the interleaving never happened")
        self.assertIsNone(tenants.get_role(self.c1, self.tid, self.uid["m"]))

    def test_sequential_last_owner_rule_still_holds(self):
        tenants.remove_member(self.c1, self.principal("a", "owner"), self.uid["b"])
        with self.assertRaises(Conflict):
            tenants.remove_member(self.c1, self.principal("a", "owner"), self.uid["a"])
        self.assertEqual(self.active_owners(), 1)


if __name__ == "__main__":
    unittest.main()
