"""Lock discipline, observed from the SQL each operation really executes.

Every operation that changes state must run as ONE transaction that (a) takes the write lock first,
(b) runs every statement its decision depends on while holding it, and (c) performs every write while
holding it; afterwards it may only read. Specific wrong edits (a write moved after COMMIT, a check moved
before BEGIN, a write placed in a second transaction) are instances of this one property, so it is tested
as a property and not mutant by mutant. It is applied to EVERY mutating operation in the app.
"""
import pathlib
import sqlite3
import unittest

from app import billing, tenants, tickets
from app.errors import AppError

from tests import source_scan
from tests.helpers import World, nk


def is_write(sql):
    return source_scan.is_writing(sql)


def observe(conn, fn):
    """Run fn, return [(verb, was_in_transaction, sql)] for every statement conn executed."""
    log = []

    def trace(sql):
        verb = sql.strip().split(None, 1)[0].upper()
        log.append((verb, conn.in_transaction, sql))

    conn.set_trace_callback(trace)
    try:
        fn()
    except AppError:
        pass  # refusal paths are observed too
    finally:
        conn.set_trace_callback(None)
    return log


def assert_disciplined(case, log, expect_write=True):
    verbs = [v for v, _, _ in log]
    case.assertTrue(log, "no SQL observed; the test proves nothing")
    case.assertEqual(verbs[0], "BEGIN", f"the first statement must take the lock, got {log[0][2]!r}")
    case.assertEqual(verbs.count("BEGIN"), 1, "an operation must be exactly one transaction")
    ends = [i for i, v in enumerate(verbs) if v in ("COMMIT", "ROLLBACK")]
    case.assertEqual(len(ends), 1, "the transaction must end exactly once")
    for i, (verb, in_txn, sql) in enumerate(log):
        if is_write(sql):
            case.assertTrue(in_txn, f"write outside the lock: {sql!r}")
        if 0 < i < ends[0]:
            case.assertTrue(in_txn, f"decision statement outside the lock: {sql!r}")
        if i > ends[0]:
            case.assertEqual(verb, "SELECT", f"only reads may follow the transaction, got {sql!r}")
    if expect_write:
        case.assertTrue(any(is_write(sql) for _, _, sql in log), "no write observed; the test proves nothing")


# Every function in app/ that contains a write statement. test_every_mutating_operation_is_covered keeps
# this list honest by finding the writers in the source itself (tests/source_scan.py), so a new one cannot be
# added uncovered. idempotency.remember is the one helper that writes: it only ever runs inside the
# transaction of the four keyed operations, whose traces include its INSERT.
COVERED_MUTATORS = {
    "tenants.create_tenant", "tenants.add_member", "tenants.remove_member",
    "tickets.create_ticket", "tickets.assign_ticket",
    "billing.credit", "billing.debit", "billing.create_invoice",
    "idempotency.remember",
}

APP_ROOT = pathlib.Path(__file__).resolve().parent.parent / "app"


class CoverageOfMutatorsTests(unittest.TestCase):
    def test_every_mutating_operation_is_covered(self):  # SR-003, SR4-002
        writers, problems = source_scan.scan_app(APP_ROOT)
        self.assertEqual(problems, [], "app/ contains SQL the scan cannot read")
        self.assertEqual(
            writers, COVERED_MUTATORS,
            "a function that writes state is not in COVERED_MUTATORS (or the reverse); add a "
            "lock-discipline test for it and list it here",
        )

    def test_the_schema_only_creates_tables(self):
        from app import db as dbmod
        statements = [x.strip() for x in dbmod.SCHEMA.split(";") if x.strip()]
        self.assertTrue(statements)
        for statement in statements:
            self.assertEqual(source_scan.first_keyword(statement), "CREATE", statement[:60])


class SourceScanResistsDisguisesTests(unittest.TestCase):
    """SR4-002: the three disguises Verifier round 5 demonstrated, and neighbours, are all refused."""

    def scan(self, **modules):
        return source_scan.scan_sources(modules)

    def test_sql_assembled_from_pieces_is_refused(self):
        for expr in ('"DEL" + "ETE FROM t"', 'f"DELETE FROM {x}"', "sql", '"DELETE FROM %s" % x',
                     '"DELETE FROM t".format()'):
            _, problems = self.scan(billing=f"def purge(db, x, sql):\n    db.execute({expr})\n")
            self.assertTrue(problems, expr)

    def test_a_write_in_a_module_the_old_scan_never_opened_is_found(self):
        writers, _ = self.scan(web='def purge(db):\n    db.execute("DELETE FROM tickets")\n')
        self.assertEqual(writers, {"web.purge"})

    def test_executescript_is_refused_even_when_its_text_starts_with_a_comment(self):
        for text in ('"-- note\\nINSERT INTO tenants (name) VALUES (1)"', '"/* x */ INSERT INTO t VALUES (1)"',
                     "SCHEMA"):
            _, problems = self.scan(tenants=f"def f(db):\n    db.executescript({text})\n")
            self.assertTrue(problems, text)

    def test_executescript_is_allowed_only_as_db_connect_applying_schema(self):
        ok = "def connect():\n    db.executescript(SCHEMA)\n"
        self.assertEqual(self.scan(db=ok), (set(), []))
        self.assertTrue(self.scan(db=ok.replace("connect", "other"))[1])
        self.assertTrue(self.scan(tenants=ok)[1])

    def test_a_comment_before_the_write_verb_does_not_hide_it(self):
        writers, _ = self.scan(tenants='def f(db):\n    db.execute("/* x */ INSERT INTO t VALUES (1)")\n')
        self.assertEqual(writers, {"tenants.f"})
        writers, _ = self.scan(tenants='def f(db):\n    db.execute("-- x\\nUPDATE t SET a = 1")\n')
        self.assertEqual(writers, {"tenants.f"})

    def test_executemany_and_dynamic_dispatch_are_refused(self):
        for body in ('db.executemany("INSERT INTO t VALUES (?)", [(1,)])', 'getattr(db, "execute")("x")',
                     'eval("1")', 'db.execute(*args)', 'db.execute(sql="DELETE FROM t")'):
            self.assertTrue(self.scan(tenants=f"def f(db, args):\n    {body}\n")[1], body)

    def test_a_statement_that_does_not_start_with_a_write_verb_is_still_a_write(self):  # R11 survivor
        for sql in ("WITH c AS (SELECT 1 AS n) INSERT INTO ledger (tenant_id) SELECT n FROM c",
                    "/* x */ WITH c AS (SELECT 1) UPDATE t SET a = 1", "PRAGMA writable_schema = 1",
                    "CREATE TABLE x (a)", "SAVEPOINT s", "ROLLBACK TO s", "rollback to savepoint s;"):
            writers, problems = self.scan(billing=f"def f(db):\n    db.execute({sql!r})\n")
            self.assertEqual((writers, problems), ({"billing.f"}, []), sql)

    def test_a_bare_rollback_is_not_a_write(self):
        for sql in ("ROLLBACK", "rollback;", "ROLLBACK TRANSACTION", "/* x */ ROLLBACK"):
            self.assertEqual(self.scan(billing=f"def f(db):\n    db.execute({sql!r})\n"), (set(), []), sql)

    def test_indirect_ways_to_reach_the_database_are_refused(self):  # SR5-001: the shapes Verifier rounds 11 and 12 showed
        shapes = (
            'import operator\ndef f(db):\n    operator.methodcaller("execute", "DELETE FROM t")(db)\n',
            'import operator\ndef f(db):\n    operator.methodcaller("executescript", "DELETE FROM t")(db)\n',
            'import operator\ndef f(db):\n    operator.attrgetter("execute")(db)("DELETE FROM t")\n',
            'from operator import attrgetter\ndef f(db):\n    attrgetter("execute")(db)("DELETE FROM t")\n',
            'def f(db):\n    db.execute.__call__("DELETE FROM t")\n',
            'def f(db):\n    run = db.execute\n    run("DELETE FROM t")\n',
            'def f(db):\n    return db.execute\n',
            'def f(db):\n    object.__getattribute__(db, "execute")("DELETE FROM t")\n',
            'def f(db):\n    db.__getattribute__("execute")("DELETE FROM t")\n',
            'import builtins\ndef f(db):\n    builtins.exec("db.execute(x)", {"db": db, "x": "DELETE FROM t"})\n',
            'def f(db):\n    __builtins__["exec"]("1")\n',
            'import importlib\ndef f(db):\n    importlib.import_module("os")\n',
            'def f(db, src):\n    src.backup(db)\n',
            'def f(db):\n    db.blobopen("main", "t", "c", 1)\n',
            'def f(db):\n    db.executemany("INSERT INTO t VALUES (?)", [(1,)])\n',
        )
        for source in shapes:
            _, problems = self.scan(billing=source)
            self.assertTrue(problems, source)

    def test_shapes_that_split_a_method_name_or_avoid_every_named_rule_are_refused(self):  # R13-002
        shapes = (
            'import sys\ndef f(db):\n    sys.modules["importlib"].import_module("operator").methodcaller("ex" + "ecute", "x")(db)\n',
            'import sys\ndef f(db):\n    sys.modules["builtins"].__dict__["get" + "attr"](db, "ex" + "ecute")("x")\n',
            'def f(db):\n    vars(type(db))["ex" + "ecute"].__get__(db)("x")\n',
            'def f(db):\n    db.__class__.__dict__["ex" + "ecute"].__get__(db, type(db))("x")\n',
            'import logging\ndef f(db):\n    logging.sys.modules["operator"].methodcaller("ex" + "ecute", "x")(db)\n',
            'import os\ndef f(db):\n    os.system("x")\n',
            'from logging import sys\ndef f(db):\n    sys.modules\n',
            'def f(db):\n    return db.cursor\n',
        )
        for source in shapes:
            _, problems = self.scan(billing=source)
            self.assertTrue(problems, source)

    def test_a_name_the_app_binds_itself_does_not_open_an_attribute(self):  # R14-001
        shapes = (
            'def f(db, payload, deserialize=None):\n    db.deserialize(payload)\n',
            "def f(db, create_function=None):\n    db.create_function('pwn', 0, lambda: 0)\n",
            'def f(db, commit=None):\n    db.commit()\n',
            "import logging\ndef f(db, os=None, system=None):\n    logging.os.system('x')\n",
            'def f(db, enable_load_extension=None):\n    db.enable_load_extension(True)\n',
            'class Box:\n    def deserialize(self):\n        pass\ndef f(db, p):\n    db.deserialize(p)\n',
            'def f(db, p):\n    deserialize = 1\n    db.deserialize(p)\n',
            'def f(db, p):\n    return [deserialize for deserialize in p], db.deserialize(p)\n',
        )
        for source in shapes:
            _, problems = self.scan(billing=source)
            self.assertTrue(problems, source)

    def test_the_allowed_vocabulary_reaches_nothing_that_runs_code(self):  # R14-001: a closure check, not a list of shapes
        import hashlib
        import hmac
        import json
        import logging
        import re
        import sqlite3
        import types

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        roots = [types.ModuleType("x")]
        roots += [__import__(name) for name in sorted(source_scan.ALLOWED_MODULES)]
        roots += [conn, conn.execute("SELECT 1 AS a"), conn.execute("SELECT 1 AS a").fetchone(), "", b"", [], {},
                  re.compile("x"), hashlib.sha256(), hmac.new(b"k", digestmod="sha256"), logging.getLogger("x"),
                  json.JSONDecoder()]
        names = sorted(source_scan.APP_ATTRS | source_scan.STDLIB_ATTRS)
        seen, queue, danger = set(), list(roots), []
        while queue:
            obj = queue.pop()
            if id(obj) in seen:
                continue
            seen.add(id(obj))
            if isinstance(obj, types.ModuleType) and obj.__name__.split(".")[0] in {
                    "os", "sys", "builtins", "importlib", "ctypes", "subprocess", "posix", "nt"}:
                danger.append(obj.__name__)
            if getattr(obj, "__name__", "") in {"system", "popen", "eval", "exec", "__import__", "open", "deserialize",
                                                "load_extension", "enable_load_extension", "create_function"}:
                danger.append(getattr(obj, "__name__", ""))
            for name in names:
                value = getattr(obj, name, None)  # a name that is not there is simply not reachable
                if value is not None:
                    queue.append(value)
        self.assertEqual(danger, [])

    def test_ordinary_database_use_is_not_refused_by_the_indirect_rules(self):
        src = ('def f(db, x):\n    row = db.execute("SELECT 1 WHERE ?", (x,)).fetchone()\n'
               '    db.execute("INSERT INTO t VALUES (?)", (x,))\n    return row\n')
        self.assertEqual(self.scan(billing=src), ({"billing.f"}, []))

    def test_ordinary_reads_and_writes_in_a_function_are_accepted_and_named(self):
        src = ('def f(db):\n    db.execute("SELECT 1")\n    db.execute("INSERT INTO t VALUES (1)")\n'
               'def g(db):\n    db.execute("BEGIN IMMEDIATE")\n')
        self.assertEqual(self.scan(tenants=src), ({"tenants.f"}, []))


class LockDisciplineTests(World):
    def check(self, fn, expect_write=True):
        assert_disciplined(self, observe(self.db, fn), expect_write)

    def test_add_member(self):
        uid = self._user("newcomer")
        self.check(lambda: tenants.add_member(self.db, self.a("owner"), uid, "member"))

    def test_remove_member(self):
        self.check(lambda: tenants.remove_member(self.db, self.a("owner"), self.users["a_member"]))

    def test_remove_member_refused_as_last_owner(self):
        self.check(lambda: tenants.remove_member(self.db, self.a("owner"), self.users["a_owner"]),
                   expect_write=False)

    def test_create_tenant(self):
        self.check(lambda: tenants.create_tenant(self.db, "fresh", self.users["outsider"]))

    def test_create_ticket(self):
        self.check(lambda: tickets.create_ticket(self.db, self.a("member"), "x", idempotency_key=nk()))

    def test_assign_ticket(self):
        ticket = tickets.create_ticket(self.db, self.a("owner"), "x", idempotency_key=nk())
        self.check(lambda: tickets.assign_ticket(
            self.db, self.a("owner"), ticket["id"], self.users["a_member"]))

    def test_credit(self):
        self.check(lambda: billing.credit(self.db, self.a("admin"), 100, idempotency_key=nk()))

    def test_debit_success_and_refusal(self):
        billing.credit(self.db, self.a("admin"), 100, idempotency_key=nk())
        self.check(lambda: billing.debit(self.db, self.a("admin"), 100, idempotency_key=nk()))
        self.check(lambda: billing.debit(self.db, self.a("admin"), 1, idempotency_key=nk()), expect_write=False)

    def test_a_replayed_request_is_one_transaction_and_writes_nothing(self):
        key = nk()
        billing.credit(self.db, self.a("admin"), 100, idempotency_key=key)
        self.check(lambda: billing.credit(self.db, self.a("admin"), 100, idempotency_key=key),
                   expect_write=False)

    def test_create_invoice(self):
        lines = [{"description": "a", "amount_cents": 10}, {"description": "b", "amount_cents": 20}]
        self.check(lambda: billing.create_invoice(self.db, self.a("admin"), lines, idempotency_key=nk()))

    def test_the_property_rejects_each_known_wrong_shape(self):
        """Guard against a vacuous property: logs shaped like every wrong edit seen in review."""
        begin, commit = ("BEGIN", False, "BEGIN IMMEDIATE"), ("COMMIT", True, "COMMIT")
        select, write = ("SELECT", True, "SELECT 1"), ("INSERT", True, "INSERT INTO t")
        shapes = {
            "write after the transaction ends (R3-001)":
                [begin, select, commit, ("UPDATE", False, "UPDATE t")],
            "decision read before the lock (R3-002)":
                [("SELECT", False, "SELECT SUM(a)"), begin, write, commit],
            "write in a second transaction after the decision (Verifier round 4)":
                [begin, select, commit, begin, write, commit],
            "decision read before the writing transaction, after an empty one (Verifier round 4)":
                [begin, commit, ("SELECT", False, "SELECT 1"), begin, write, commit],
            "no transaction at all (SR-003)":
                [("INSERT", False, "INSERT INTO t"), ("INSERT", False, "INSERT INTO u")],
        }
        for name, log in shapes.items():
            with self.assertRaises(AssertionError, msg=name):
                assert_disciplined(self, log)

    def test_the_property_accepts_the_one_correct_shape(self):
        begin, commit = ("BEGIN", False, "BEGIN IMMEDIATE"), ("COMMIT", True, "COMMIT")
        assert_disciplined(self, [begin, ("SELECT", True, "s"), ("INSERT", True, "i"), commit,
                                  ("SELECT", False, "SELECT balance")])


class FailedCommitTests(World):
    """R3-003: a COMMIT that fails must roll back and leave the connection usable."""

    def test_denied_commit_rolls_back_and_the_connection_recovers(self):
        def deny_commit(action, arg1, arg2, dbname, source):
            if action == sqlite3.SQLITE_TRANSACTION and arg1 == "COMMIT":
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        self.db.set_authorizer(deny_commit)
        with self.assertRaises(sqlite3.DatabaseError):
            billing.credit(self.db, self.a("admin"), 5, idempotency_key=nk())
        self.db.set_authorizer(None)
        self.assertFalse(self.db.in_transaction, "the failed commit left a transaction open")
        self.assertEqual(billing.balance(self.db, self.a("admin")), 0)
        self.assertEqual(billing.credit(self.db, self.a("admin"), 7, idempotency_key=nk()), 7)


if __name__ == "__main__":
    unittest.main()
