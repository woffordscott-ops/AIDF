"""Hidden tests for M1-FLOW-01. Copied into a workspace as tests/test_hidden_flow.py; never shown to a candidate."""
import unittest

from app import tickets
from app.errors import Conflict, Forbidden, Invalid, NotFound
from tests.helpers import World, call, make_app, nk
from tests.test_lock_discipline import assert_disciplined as _disciplined
from tests.test_lock_discipline import observe


def assert_disciplined(case, log, expect_write=True):
    _disciplined(case, log, expect_write)
    case.assertIn(log[-1][0], ("COMMIT", "ROLLBACK"), "nothing may run after the transaction ends")


KEEP = object()


def count(world):
    return world.db.execute("SELECT COUNT(*) FROM comments").fetchone()[0]


class CommentTests(World):
    def setUp(self):
        super().setUp()
        self.ticket = tickets.create_ticket(self.db, self.a("member"), "broken login", idempotency_key=nk())["id"]

    def add(self, who, text="first", ticket=KEEP, key=KEEP):
        return tickets.add_comment(self.db, who, self.ticket if ticket is KEEP else ticket, text,
                                   nk() if key is KEEP else key)

    def test_a_member_comments_and_any_role_in_the_tenant_can_list_them_in_order(self):
        one = self.add(self.a("member"), "  first  ")
        two = self.add(self.a("admin"), "second")
        self.assertEqual(one, {"id": one["id"], "ticket_id": self.ticket,
                               "author_id": self.users["a_member"], "text": "first"})
        self.assertEqual(tickets.list_comments(self.db, self.a("viewer"), self.ticket), [one, two])
        self.assertLess(one["id"], two["id"])
        self.assertEqual((one["author_id"], two["author_id"]), (self.users["a_member"], self.users["a_admin"]))

    def test_comments_are_listed_in_the_order_they_were_added_not_by_their_text(self):
        added = [self.add(self.a("member"), text) for text in ("zebra", "apple", "mango")]
        self.assertEqual(tickets.list_comments(self.db, self.a("viewer"), self.ticket), added)

    def test_a_viewer_cannot_comment_but_can_read(self):
        with self.assertRaises(Forbidden):
            self.add(self.a("viewer"))
        self.assertEqual(count(self), 0)
        self.assertEqual(tickets.list_comments(self.db, self.a("viewer"), self.ticket), [])

    def test_another_tenant_can_neither_comment_on_nor_list_a_ticket(self):  # INV-1
        self.add(self.a("member"), "private note")
        for who in (self.b("owner"), self.b("member")):
            with self.assertRaises(NotFound):
                self.add(who, "intruder")
            with self.assertRaises(NotFound):
                tickets.list_comments(self.db, who, self.ticket)
        self.assertEqual(count(self), 1)
        self.assertEqual([c["text"] for c in tickets.list_comments(self.db, self.a("owner"), self.ticket)],
                         ["private note"])

    def test_a_missing_ticket_is_not_found(self):
        with self.assertRaises(NotFound):
            self.add(self.a("member"), ticket=987654)
        with self.assertRaises(NotFound):
            tickets.list_comments(self.db, self.a("member"), 987654)

    def test_text_must_be_non_blank_valid_text_of_at_most_2000_characters(self):
        for bad in ("", "   ", None, 5, ["x"], "\ud800", "x" * 2001, " " + "x" * 2001):
            with self.assertRaises(Invalid, msg=repr(bad)[:20]):
                self.add(self.a("member"), bad)
        self.assertEqual(count(self), 0)
        self.add(self.a("member"), "x" * 2000)
        self.assertEqual(count(self), 1)

    def test_surrounding_whitespace_does_not_count_towards_the_2000_characters(self):
        self.assertEqual(self.add(self.a("member"), " " + "x" * 2000 + "  ")["text"], "x" * 2000)

    def test_the_limit_counts_characters_not_bytes(self):
        self.assertEqual(self.add(self.a("member"), "\u00e9" * 2000)["text"], "\u00e9" * 2000)
        with self.assertRaises(Invalid):
            self.add(self.a("member"), "\u00e9" * 2001)

    def test_every_role_that_may_comment_can(self):
        for role in ("member", "admin", "owner"):
            self.assertEqual(self.add(self.a(role), role)["author_id"], self.principal(self.ta, f"a_{role}", role).user_id)

    def test_blank_means_any_whitespace_and_trimming_removes_any_whitespace(self):
        for bad in ("\t", "\n", " \t\n ", "\r", "\u00a0", "\u2003", "\x0b\x0c"):
            with self.assertRaises(Invalid, msg=repr(bad)):
                self.add(self.a("member"), bad)
        self.assertEqual(self.add(self.a("member"), "\tx\n")["text"], "x")
        self.assertEqual(self.add(self.a("member"), "\u00a0y\r\u2003")["text"], "y")
        self.assertEqual(self.add(self.a("member"), "\r" + "z" * 2000)["text"], "z" * 2000)

    def test_every_role_that_may_read_the_ticket_may_list_its_comments(self):
        made = self.add(self.a("member"), "visible")
        for role in ("viewer", "member", "admin", "owner"):
            self.assertEqual(tickets.list_comments(self.db, self.a(role), self.ticket), [made], role)

    def test_a_retry_with_different_surrounding_whitespace_is_the_same_request(self):
        key = nk()
        first = self.add(self.a("member"), "same", key=key)
        self.assertEqual(self.add(self.a("member"), "  same\n", key=key), first)
        self.assertEqual(count(self), 1)

    def test_the_stored_text_is_the_trimmed_text(self):
        made = self.add(self.a("member"), "  kept  ")
        stored = self.db.execute("SELECT text FROM comments WHERE id = ?", (made["id"],)).fetchone()[0]
        self.assertEqual(stored, "kept")

    def test_a_replay_needs_live_authority_like_any_other_request(self):  # INV-2
        key = nk()
        snapshot = self.a("member")
        self.add(snapshot, "once", key=key)
        self.db.execute("UPDATE memberships SET active = 0 WHERE user_id = ?", (self.users["a_member"],))
        with self.assertRaises(Forbidden):
            self.add(snapshot, "once", key=key)
        self.assertEqual(count(self), 1)

    def test_the_same_key_for_another_ticket_is_a_different_request(self):
        other = tickets.create_ticket(self.db, self.a("member"), "second", idempotency_key=nk())["id"]
        key = nk()
        self.add(self.a("member"), "same words", key=key)
        with self.assertRaises(Conflict):
            self.add(self.a("member"), "same words", ticket=other, key=key)
        self.assertEqual(tickets.list_comments(self.db, self.a("member"), other), [])
        self.assertEqual(count(self), 1)

    def test_a_replay_returns_the_saved_comment_even_after_later_comments(self):
        key = nk()
        first = self.add(self.a("member"), "first one", key=key)
        later = self.add(self.a("member"), "a later one")
        self.assertEqual(self.add(self.a("member"), "first one", key=key), first)
        self.assertEqual(tickets.list_comments(self.db, self.a("viewer"), self.ticket), [first, later])

    def test_a_bad_ticket_id_is_a_client_error(self):
        for bad in (0, -1, True, "1", None, 2 ** 63):
            with self.assertRaises(Invalid, msg=repr(bad)):
                self.add(self.a("member"), ticket=bad)

    def test_a_retried_request_is_applied_once_and_a_reused_key_for_another_request_is_refused(self):
        key = nk()
        first = self.add(self.a("member"), "once", key=key)
        again = self.add(self.a("member"), "once", key=key)
        self.assertEqual(first, again)
        self.assertEqual(count(self), 1)
        with self.assertRaises(Conflict):
            self.add(self.a("member"), "different text", key=key)
        with self.assertRaises(Invalid):
            self.add(self.a("member"), "once", key=None)
        self.assertEqual(count(self), 1)
        other = self.add(self.a("admin"), "once", key=key)  # a key belongs to one user
        self.assertNotEqual(other["id"], first["id"])
        self.assertEqual(count(self), 2)

    def test_authority_is_the_live_role_not_the_principal_snapshot(self):  # INV-2
        snapshot = self.a("member")
        self.db.execute("UPDATE memberships SET active = 0 WHERE user_id = ?", (self.users["a_member"],))
        with self.assertRaises(Forbidden):
            self.add(snapshot)
        self.db.execute("UPDATE memberships SET active = 1, role = 'viewer' WHERE user_id = ?",
                        (self.users["a_member"],))
        with self.assertRaises(Forbidden):
            self.add(snapshot)
        self.assertEqual(count(self), 0)

    def test_add_comment_is_one_transaction_that_takes_the_lock_first(self):
        assert_disciplined(self, observe(self.db, lambda: self.add(self.a("member"))))
        assert_disciplined(self, observe(self.db, lambda: self.add(self.a("member"), ticket=987654)), expect_write=False)

    def test_http_routes(self):
        app = make_app(self)
        tokens = {}
        for name, tenant in (("a_member", self.ta), ("a_viewer", self.ta), ("b_owner", self.tb)):
            status, body = call(app, "POST", "/login", {"email": f"{name}@example.test",
                                                         "password": "correct-horse", "tenant_id": tenant})
            self.assertEqual(status, 200)
            tokens[name] = body["token"]
        path = f"/tickets/{self.ticket}/comments"
        status, made = call(app, "POST", path, {"text": "via http", "idempotency_key": nk()}, tokens["a_member"])
        self.assertEqual(status, 201)
        self.assertEqual(made["text"], "via http")
        self.assertEqual(call(app, "GET", path, token=tokens["a_viewer"]), (200, {"comments": [made]}))
        self.assertEqual(call(app, "POST", path, {"text": "x", "idempotency_key": nk()}, tokens["a_viewer"])[0], 403)
        self.assertEqual(call(app, "POST", path, {"text": "x", "idempotency_key": nk()}, tokens["b_owner"])[0], 404)
        self.assertEqual(call(app, "GET", path, token=tokens["b_owner"])[0], 404)
        self.assertEqual(call(app, "POST", path, {"text": "", "idempotency_key": nk()}, tokens["a_member"])[0], 400)
        self.assertEqual(call(app, "POST", path, {"text": "x"}, tokens["a_member"])[0], 400)
        self.assertEqual(call(app, "GET", path)[0], 401)
        self.assertEqual(count(self), 1)


if __name__ == "__main__":
    unittest.main()
