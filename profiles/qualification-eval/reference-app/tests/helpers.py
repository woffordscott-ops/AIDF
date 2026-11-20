import io
import itertools
import json
import os
import tempfile
import unittest

from app import auth, tenants
from app import db as dbmod
from app.web import App

NOW = 1_000_000.0
TEST_LOGIN_PW = "correct-horse"  # fixture-only value
WRONG_LOGIN_PW = "wrong-horse!"
_PW_HASH = auth.hash_password(TEST_LOGIN_PW)  # hash once; scrypt is slow
_KEYS = itertools.count(1)


def nk():
    """A fresh idempotency key for one call that is not a retry."""
    return f"test-key-{next(_KEYS)}"


class World(unittest.TestCase):
    """Two tenants, each with owner/admin/member/viewer, plus one cross-tenant user."""

    def setUp(self):
        self.db = dbmod.connect()
        self.addCleanup(self.db.close)
        self.users = {}
        for name in ("a_owner", "a_admin", "a_member", "a_viewer",
                     "b_owner", "b_member", "outsider"):
            self.users[name] = self._user(name)
        self.ta = tenants.create_tenant(self.db, "tenant-a", self.users["a_owner"])
        self.tb = tenants.create_tenant(self.db, "tenant-b", self.users["b_owner"])
        for tenant, name, role in (
            (self.ta, "a_admin", "admin"), (self.ta, "a_member", "member"),
            (self.ta, "a_viewer", "viewer"), (self.tb, "b_member", "member"),
        ):
            self.db.execute(
                "INSERT INTO memberships (tenant_id, user_id, role) VALUES (?, ?, ?)",
                (tenant, self.users[name], role),
            )

    def _user(self, name):
        cur = self.db.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (f"{name}@example.test", _PW_HASH),
        )
        return cur.lastrowid

    def principal(self, tenant, name, role):
        return auth.Principal(user_id=self.users[name], tenant_id=tenant, role=role)

    def a(self, role):
        name = {"owner": "a_owner", "admin": "a_admin", "member": "a_member", "viewer": "a_viewer"}[role]
        return self.principal(self.ta, name, role)

    def b(self, role):
        name = {"owner": "b_owner", "member": "b_member"}[role]
        return self.principal(self.tb, name, role)


class SharedFileWorld(unittest.TestCase):
    """Two connections to ONE file-backed database, for race and interleaving tests."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        path = os.path.join(self.tmp.name, "shared.db")
        self.c1 = dbmod.connect(path)
        self.c2 = dbmod.connect(path)
        self.addCleanup(self.c1.close)
        self.addCleanup(self.c2.close)
        self.uid = {}
        for name in ("a", "b", "m"):
            cur = self.c1.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)", (f"{name}@example.test", _PW_HASH))
            self.uid[name] = cur.lastrowid
        self.tid = tenants.create_tenant(self.c1, "t", self.uid["a"])

    def principal(self, name, role):
        return auth.Principal(user_id=self.uid[name], tenant_id=self.tid, role=role)

    def at_first_begin(self, conn, action):
        """Run `action` to completion exactly once, when `conn` first reaches BEGIN IMMEDIATE."""
        fired = []

        def trace(statement):
            if "BEGIN IMMEDIATE" in statement and not fired:
                fired.append(True)
                conn.set_trace_callback(None)
                action()

        conn.set_trace_callback(trace)
        return fired  # callers must assert it is non-empty, or the test proves nothing

    def active_owners(self):
        return self.c1.execute(
            "SELECT COUNT(*) FROM memberships WHERE tenant_id = ? AND role = 'owner' AND active = 1",
            (self.tid,)).fetchone()[0]


def call(app, method, path, body=None, token=None):
    raw = json.dumps(body).encode() if body is not None else b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": io.BytesIO(raw),
    }
    if token:
        environ["HTTP_AUTHORIZATION"] = "Bearer " + token
    captured = {}

    def start_response(status, headers):
        captured["status"] = int(status.split()[0])

    payload = b"".join(app(environ, start_response))
    return captured["status"], json.loads(payload)


def make_app(world, now=NOW):
    return App(world.db, clock=lambda: now)
