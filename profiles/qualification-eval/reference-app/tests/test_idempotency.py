"""A write the client could not see the outcome of must be safe to retry (SR3-001, SR4-001).

The Security Review reproduced it with a connection that runs the real COMMIT and then raises: the write
is durable, the client sees a 500, and a retry used to apply it a second time. These tests lose the
acknowledgement the same way and require that a retry with the same key applies nothing twice and answers
exactly what the first call would have, and that the key cannot be used to get around tenant scoping,
live authority, or a different request.
"""
import logging
import sqlite3
import unittest

from app import billing, tenants, tickets
from app.errors import Conflict, Forbidden, Invalid
from app.web import App

from tests.helpers import NOW, TEST_LOGIN_PW, SharedFileWorld, World, call, nk

LONE_SURROGATE = "\ud800"
LINES = [{"description": "a", "amount_cents": 5}, {"description": "b", "amount_cents": 7}]


def setUpModule():
    logging.disable(logging.CRITICAL)  # the injected failures are logged by the 500 handler; keep the output clean


def tearDownModule():
    logging.disable(logging.NOTSET)


class LostAck:
    """A connection whose first COMMIT really happens and then reports failure: the write is durable."""

    def __init__(self, conn):
        self._conn = conn
        self.lost = False

    def execute(self, sql, *args):
        result = self._conn.execute(sql, *args)
        if sql.strip().upper() == "COMMIT" and not self.lost:
            self.lost = True
            raise sqlite3.OperationalError("injected: COMMIT succeeded, acknowledgement lost")
        return result

    def __getattr__(self, name):
        return getattr(self._conn, name)


def count(db, table):
    return db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


class KeyValidationTests(World):
    BAD = (None, 1, True, 1.5, ["k"], {"k": 1}, "", " ", "a b", "a/b", "x" * 65, "é", LONE_SURROGATE, "k\n", "k\x00")

    def test_every_keyed_operation_refuses_a_missing_or_malformed_key_and_writes_nothing(self):
        owner = self.a("owner")
        for bad in self.BAD:
            for fn, args in ((billing.credit, (5,)), (billing.debit, (5,)),
                             (billing.create_invoice, (LINES,)), (tickets.create_ticket, ("t",))):
                with self.assertRaises(Invalid, msg=f"{fn.__name__} {bad!r}"):
                    fn(self.db, owner, *args, idempotency_key=bad)
        for table in ("ledger", "invoices", "tickets", "idempotency"):
            self.assertEqual(count(self.db, table), 0, table)

    def test_the_longest_and_the_allowed_characters_are_accepted(self):
        self.assertEqual(billing.credit(self.db, self.a("owner"), 1, idempotency_key="A-z_0.9:" + "k" * 56), 1)

    def test_over_http_a_missing_or_bad_key_is_400(self):
        app = App(self.db, clock=lambda: NOW)
        token = call(app, "POST", "/login", {"email": "a_owner@example.test", "password": TEST_LOGIN_PW,
                                              "tenant_id": self.ta})[1]["token"]
        for route, body in (("/billing/credit", {"amount_cents": 5}), ("/billing/debit", {"amount_cents": 5}),
                            ("/tickets", {"title": "t"})):
            self.assertEqual(call(app, "POST", route, body, token)[0], 400, route)
            self.assertEqual(call(app, "POST", route, {**body, "idempotency_key": "bad key"}, token)[0], 400, route)
        self.assertEqual(count(self.db, "idempotency"), 0)


class ReplayTests(World):
    def test_a_replayed_credit_answers_the_first_time_and_writes_nothing(self):
        owner = self.a("owner")
        self.assertEqual(billing.credit(self.db, owner, 50, idempotency_key="c1"), 50)
        self.assertEqual(billing.credit(self.db, owner, 50, idempotency_key="c1"), 50)
        self.assertEqual(billing.balance(self.db, owner), 50)
        self.assertEqual(count(self.db, "ledger"), 1)

    def test_a_replayed_debit_answers_the_first_time_and_writes_nothing(self):
        owner = self.a("owner")
        billing.credit(self.db, owner, 100, idempotency_key=nk())
        self.assertEqual(billing.debit(self.db, owner, 40, idempotency_key="d1"), 60)
        self.assertEqual(billing.debit(self.db, owner, 40, idempotency_key="d1"), 60)
        self.assertEqual(billing.balance(self.db, owner), 60)

    def test_a_replayed_debit_that_would_now_overdraw_is_still_answered_not_refused(self):
        owner = self.a("owner")
        billing.credit(self.db, owner, 100, idempotency_key=nk())
        billing.debit(self.db, owner, 100, idempotency_key="d1")
        self.assertEqual(billing.debit(self.db, owner, 100, idempotency_key="d1"), 0)
        self.assertEqual(billing.balance(self.db, owner), 0)

    def test_a_replayed_invoice_is_the_same_invoice(self):
        owner = self.a("owner")
        first = billing.create_invoice(self.db, owner, LINES, idempotency_key="i1")
        again = billing.create_invoice(self.db, owner, LINES, idempotency_key="i1")
        self.assertEqual(first, again)
        self.assertEqual(count(self.db, "invoices"), 1)
        self.assertEqual(count(self.db, "invoice_lines"), 2)

    def test_a_replayed_ticket_is_the_same_ticket_even_after_it_changed(self):
        owner = self.a("owner")
        first = tickets.create_ticket(self.db, owner, "  fix it  ", idempotency_key="t1")
        tickets.assign_ticket(self.db, owner, first["id"], self.users["a_member"], )
        again = tickets.create_ticket(self.db, owner, "fix it", idempotency_key="t1")
        self.assertEqual(again, first)  # the answer the first call gave, not the ticket's current state
        self.assertIsNone(again["assignee_id"])
        self.assertEqual(count(self.db, "tickets"), 1)

    def test_the_same_key_for_a_different_request_is_refused_and_writes_nothing(self):
        owner = self.a("owner")
        billing.credit(self.db, owner, 5, idempotency_key="k")
        for fn, args in ((billing.credit, (6,)), (billing.debit, (5,)), (billing.create_invoice, (LINES,)),
                         (tickets.create_ticket, ("t",))):
            with self.assertRaises(Conflict, msg=fn.__name__):
                fn(self.db, owner, *args, idempotency_key="k")
        self.assertEqual(billing.balance(self.db, owner), 5)
        self.assertEqual((count(self.db, "ledger"), count(self.db, "invoices"), count(self.db, "tickets")), (1, 0, 0))

    def test_two_users_of_one_tenant_cannot_collide_with_or_replay_each_others_keys(self):
        self.assertEqual(billing.credit(self.db, self.a("admin"), 5, idempotency_key="k"), 5)
        # the owner's "k" is the owner's own new request: not a replay of the admin's, and not a conflict
        self.assertEqual(billing.credit(self.db, self.a("owner"), 5, idempotency_key="k"), 10)
        self.assertEqual(billing.credit(self.db, self.a("owner"), 5, idempotency_key="k"), 10)  # their own replay
        self.assertEqual(billing.credit(self.db, self.a("admin"), 5, idempotency_key="k"), 5)  # and the admin's
        self.assertEqual((billing.balance(self.db, self.a("owner")), count(self.db, "ledger")), (10, 2))

    def test_keys_belong_to_a_tenant(self):
        self.assertEqual(billing.credit(self.db, self.a("owner"), 5, idempotency_key="k"), 5)
        self.assertEqual(billing.credit(self.db, self.b("owner"), 5, idempotency_key="k"), 5)
        self.assertEqual(billing.credit(self.db, self.b("owner"), 5, idempotency_key="k"), 5)
        self.assertEqual(billing.balance(self.db, self.a("owner")), 5)
        self.assertEqual(billing.balance(self.db, self.b("owner")), 5)
        self.assertEqual(count(self.db, "ledger"), 2)

    def test_one_user_in_two_tenants_has_separate_keys_in_each(self):
        for tenant in (self.ta, self.tb):
            self.db.execute("INSERT INTO memberships (tenant_id, user_id, role) VALUES (?, ?, 'admin')",
                            (tenant, self.users["outsider"]))
        in_a = self.principal(self.ta, "outsider", "admin")
        in_b = self.principal(self.tb, "outsider", "admin")
        self.assertEqual(billing.credit(self.db, in_a, 5, idempotency_key="k"), 5)
        self.assertEqual(billing.credit(self.db, in_b, 7, idempotency_key="k"), 7)  # a new request, not a replay
        self.assertEqual(billing.credit(self.db, in_a, 5, idempotency_key="k"), 5)
        self.assertEqual((billing.balance(self.db, in_a), billing.balance(self.db, in_b)), (5, 7))

    def test_a_refusal_is_not_remembered_so_the_same_key_can_succeed_later(self):
        owner = self.a("owner")
        with self.assertRaises(Conflict):
            billing.debit(self.db, owner, 100, idempotency_key="d")
        self.assertEqual(count(self.db, "idempotency"), 0)
        billing.credit(self.db, owner, 200, idempotency_key=nk())
        self.assertEqual(billing.debit(self.db, owner, 100, idempotency_key="d"), 100)

    def test_a_credit_over_the_balance_cap_is_not_remembered(self):
        owner = self.a("owner")
        for i in range(billing.MAX_BALANCE_CENTS // billing.MAX_AMOUNT_CENTS):
            billing.credit(self.db, owner, billing.MAX_AMOUNT_CENTS, idempotency_key=f"fill-{i}")
        with self.assertRaises(Conflict):
            billing.credit(self.db, owner, 1, idempotency_key="over")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM idempotency WHERE key = 'over'").fetchone()[0], 0)


class ReplayStillNeedsLiveAuthorityTests(World):
    """A saved answer is not a way around a revoked or reduced membership."""

    def test_a_removed_caller_cannot_read_back_a_saved_response(self):
        admin = self.a("admin")
        billing.credit(self.db, admin, 5, idempotency_key="k")
        self.db.execute("UPDATE memberships SET active = 0 WHERE tenant_id = ? AND user_id = ?",
                        (self.ta, self.users["a_admin"]))
        with self.assertRaises(Forbidden):
            billing.credit(self.db, admin, 5, idempotency_key="k")

    def test_a_demoted_caller_cannot_read_back_a_saved_response(self):
        admin = self.a("admin")
        tickets.create_ticket(self.db, admin, "t", idempotency_key="k")
        self.db.execute("UPDATE memberships SET role = 'viewer' WHERE tenant_id = ? AND user_id = ?",
                        (self.ta, self.users["a_admin"]))
        with self.assertRaises(Forbidden):
            tickets.create_ticket(self.db, admin, "t", idempotency_key="k")


class LostAcknowledgementTests(World):
    """SR3-001 and SR4-001: COMMIT succeeds, the client is told it failed, the client retries."""

    def lose(self, fn, *args, **kwargs):
        flaky = LostAck(self.db)
        with self.assertRaises(sqlite3.OperationalError):
            fn(flaky, *args, **kwargs)
        self.assertTrue(flaky.lost, "the injected failure never fired; the test proves nothing")

    def test_credit(self):
        owner = self.a("owner")
        self.lose(billing.credit, owner, 50, idempotency_key="c")
        self.assertEqual(billing.balance(self.db, owner), 50)  # the write is durable
        self.assertEqual(billing.credit(self.db, owner, 50, idempotency_key="c"), 50)
        self.assertEqual((billing.balance(self.db, owner), count(self.db, "ledger")), (50, 1))

    def test_debit(self):
        owner = self.a("owner")
        billing.credit(self.db, owner, 100, idempotency_key=nk())
        self.lose(billing.debit, owner, 20, idempotency_key="d")
        self.assertEqual(billing.debit(self.db, owner, 20, idempotency_key="d"), 80)
        self.assertEqual(billing.balance(self.db, owner), 80)

    def test_invoice(self):
        owner = self.a("owner")
        self.lose(billing.create_invoice, owner, LINES, idempotency_key="i")
        invoice = billing.create_invoice(self.db, owner, LINES, idempotency_key="i")
        self.assertEqual(invoice, billing.get_invoice(self.db, owner, invoice["id"]))
        self.assertEqual(count(self.db, "invoices"), 1)

    def test_ticket(self):
        owner = self.a("owner")
        self.lose(tickets.create_ticket, owner, "t", idempotency_key="t")
        ticket = tickets.create_ticket(self.db, owner, "t", idempotency_key="t")
        self.assertEqual(ticket, tickets.get_ticket(self.db, owner, ticket["id"]))
        self.assertEqual(count(self.db, "tickets"), 1)

    def test_over_http_the_lost_credit_is_a_500_and_the_retry_is_applied_once(self):
        good = App(self.db, clock=lambda: NOW)
        token = call(good, "POST", "/login", {"email": "a_owner@example.test", "password": TEST_LOGIN_PW,
                                               "tenant_id": self.ta})[1]["token"]
        flaky = LostAck(self.db)
        bad = App(flaky, clock=lambda: NOW)
        body = {"amount_cents": 50, "idempotency_key": "http-c"}
        self.assertEqual(call(bad, "POST", "/billing/credit", body, token), (500, {"error": "internal error"}))
        self.assertTrue(flaky.lost)
        self.assertEqual(call(good, "POST", "/billing/credit", body, token), (200, {"balance_cents": 50}))
        self.assertEqual(billing.balance(self.db, self.a("owner")), 50)

    def test_over_http_the_lost_debit_and_ticket_are_applied_once(self):
        good = App(self.db, clock=lambda: NOW)
        token = call(good, "POST", "/login", {"email": "a_owner@example.test", "password": TEST_LOGIN_PW,
                                               "tenant_id": self.ta})[1]["token"]
        call(good, "POST", "/billing/credit", {"amount_cents": 100, "idempotency_key": nk()}, token)
        debit = {"amount_cents": 40, "idempotency_key": "http-d"}
        self.assertEqual(call(App(LostAck(self.db), clock=lambda: NOW), "POST", "/billing/debit", debit, token)[0], 500)
        self.assertEqual(call(good, "POST", "/billing/debit", debit, token), (200, {"balance_cents": 60}))
        ticket = {"title": "t", "idempotency_key": "http-t"}
        self.assertEqual(call(App(LostAck(self.db), clock=lambda: NOW), "POST", "/tickets", ticket, token)[0], 500)
        status, created = call(good, "POST", "/tickets", ticket, token)
        self.assertEqual((status, created["id"], count(self.db, "tickets")), (201, 1, 1))


class AtomicityTests(World):
    def test_a_failed_commit_leaves_neither_the_write_nor_its_key(self):
        def deny_commit(action, arg1, arg2, dbname, source):
            if action == sqlite3.SQLITE_TRANSACTION and arg1 == "COMMIT":
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        self.db.set_authorizer(deny_commit)
        with self.assertRaises(sqlite3.DatabaseError):
            billing.credit(self.db, self.a("owner"), 5, idempotency_key="k")
        self.db.set_authorizer(None)
        self.assertEqual((count(self.db, "ledger"), count(self.db, "idempotency")), (0, 0))
        self.assertEqual(billing.credit(self.db, self.a("owner"), 5, idempotency_key="k"), 5)


class ConcurrentRetryTests(SharedFileWorld):
    def test_a_duplicate_arriving_while_the_first_is_in_flight_is_applied_once(self):
        p = self.principal("a", "owner")
        results = []
        # when connection 2 reaches its lock, connection 1 has already completed the same request
        fired = self.at_first_begin(self.c2, lambda: results.append(billing.credit(self.c1, p, 50, idempotency_key="k")))
        results.append(billing.credit(self.c2, p, 50, idempotency_key="k"))
        self.assertTrue(fired, "the interleaving never happened; the test proves nothing")
        self.assertEqual(results, [50, 50])
        self.assertEqual(self.c1.execute("SELECT COUNT(*) FROM ledger").fetchone()[0], 1)
        self.assertEqual(tenants.get_role(self.c1, self.tid, self.uid["a"]), "owner")


if __name__ == "__main__":
    unittest.main()
