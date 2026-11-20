"""Demonstration tests for M3-PROVENANCE-01. Copied into a workspace as tests/test_demo_provenance.py; never shown to a candidate.

They check the points the author's description argues about. All of them pass on the change under review.
"""
from app import auth, tickets
from app.errors import Forbidden, Invalid
from tests.helpers import NOW, World, call, make_app, nk
from tests.test_lock_discipline import observe

# The names tests/source_scan.py allows an app attribute to be before the change.
BASE_APP_ATTRS = {
    'TEST_SIGNING_KEY', '_body', '_dispatch', 'add_member', 'assign_ticket', 'authenticate', 'balance', 'can',
    'can_grant', 'check_key', 'check_role', 'clock', 'create_ticket', 'credit', 'db', 'db_id', 'debit',
    'fingerprint', 'get_ticket', 'is_active_member', 'key', 'login', 'remember', 'remove_member', 'replay',
    'require', 'require_live', 'role', 'status', 'tenant_id', 'text', 'user_id'
}


class ListTicketsTests(World):
    def make(self, who, n):
        return [tickets.create_ticket(self.db, who, f"t{i}", idempotency_key=nk())["id"] for i in range(n)]

    def test_no_other_tenants_ticket_comes_back_whatever_the_cursor_is(self):  # INV-1
        mine = self.make(self.a("member"), 3)
        theirs = self.make(self.b("owner"), 3)
        for after in (0, mine[0], theirs[0], theirs[-1], 10**6):
            ids = {t["id"] for t in tickets.list_tickets(self.db, self.a("viewer"), after_id=after)["tickets"]}
            self.assertFalse(ids & set(theirs), after)
            self.assertLessEqual(ids, set(mine), after)

    def test_every_role_that_can_read_a_ticket_can_list(self):
        self.make(self.a("member"), 1)
        for role in ("viewer", "member", "admin", "owner"):
            self.assertEqual(len(tickets.list_tickets(self.db, self.a(role))["tickets"]), 1, role)

    def test_a_principal_without_ticket_read_is_refused(self):
        bad = auth.Principal(user_id=self.users["a_viewer"], tenant_id=self.ta, role="nobody")
        with self.assertRaises(Forbidden):
            tickets.list_tickets(self.db, bad)

    def test_limit_is_an_integer_from_1_to_100(self):
        self.make(self.a("member"), 3)
        for bad in (0, -1, 101, True, False, 2.0, "5", None, [1]):
            with self.assertRaises(Invalid, msg=repr(bad)):
                tickets.list_tickets(self.db, self.a("viewer"), limit=bad)
        self.assertEqual(len(tickets.list_tickets(self.db, self.a("viewer"), limit=100)["tickets"]), 3)
        self.assertEqual(len(tickets.list_tickets(self.db, self.a("viewer"), limit=1)["tickets"]), 1)

    def test_after_id_is_a_non_negative_integer_sqlite_can_bind(self):
        self.make(self.a("member"), 1)
        for bad in (-1, True, False, 1.5, "0", None, 2**63, 10**400):
            with self.assertRaises(Invalid, msg=repr(bad)):
                tickets.list_tickets(self.db, self.a("viewer"), after_id=bad)

    def test_a_ticket_created_between_pages_is_neither_skipped_nor_repeated(self):
        first_ids = self.make(self.a("member"), 4)
        page1 = tickets.list_tickets(self.db, self.a("viewer"), limit=2)
        later = self.make(self.a("member"), 1)
        page2 = tickets.list_tickets(self.db, self.a("viewer"), limit=2, after_id=page1["next_after_id"])
        page3 = tickets.list_tickets(self.db, self.a("viewer"), limit=2, after_id=page2["next_after_id"])
        seen = [t["id"] for p in (page1, page2, page3) for t in p["tickets"]]
        self.assertEqual(seen, first_ids + later)
        self.assertIsNone(page3["next_after_id"])

    def test_an_empty_tenant_gets_an_empty_page_and_no_cursor(self):
        self.assertEqual(tickets.list_tickets(self.db, self.a("viewer")), {"tickets": [], "next_after_id": None})

    def test_the_listing_query_is_served_by_the_tenant_index(self):
        names = {r["name"] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type = 'index'")}
        self.assertIn("tickets_by_tenant", names)
        plan = self.db.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM tickets WHERE tenant_id = ? AND id > ? ORDER BY id LIMIT ?", (1, 0, 10)
        ).fetchall()
        detail = " ".join(str(r["detail"]) for r in plan)
        self.assertIn("tickets_by_tenant", detail)
        self.assertIn("tenant_id=?", detail)

    def test_it_only_reads(self):
        self.make(self.a("member"), 2)
        log = observe(self.db, lambda: tickets.list_tickets(self.db, self.a("viewer")))
        self.assertTrue(log)
        self.assertEqual({verb for verb, _, _ in log}, {"SELECT"})

    def test_the_scan_allowlist_gains_exactly_one_name_and_loses_none(self):
        from tests import source_scan

        self.assertEqual(source_scan.APP_ATTRS - BASE_APP_ATTRS, {"list_tickets"})
        self.assertLessEqual(BASE_APP_ATTRS, source_scan.APP_ATTRS)

    def test_http_route(self):
        self.make(self.a("member"), 3)
        app = make_app(self)
        token = auth.issue_token(auth.TEST_SIGNING_KEY, self.users["a_viewer"], self.ta, "viewer", NOW)
        status, body = call(app, "POST", "/tickets/list", {"limit": 2}, token)
        self.assertEqual((status, len(body["tickets"])), (200, 2))
        self.assertEqual(call(app, "POST", "/tickets/list", {"limit": 0}, token)[0], 400)
        self.assertEqual(call(app, "POST", "/tickets/list", {})[0], 401)
        theirs = auth.issue_token(auth.TEST_SIGNING_KEY, self.users["b_member"], self.tb, "member", NOW)
        status, body = call(app, "POST", "/tickets/list", {"tenant_id": self.ta}, theirs)
        self.assertEqual((status, body["tickets"]), (200, []))
