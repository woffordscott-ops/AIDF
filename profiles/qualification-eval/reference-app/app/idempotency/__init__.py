"""Safe retry of a write whose outcome the client could not see (SR3-001, SR4-001).

A client that gets an error or no answer cannot tell whether a write committed. If it retries and the
write is applied again, a credit is paid twice. So every write a client is expected to retry carries a
caller-chosen key. The key, a fingerprint of the request and the response are stored in the SAME
transaction as the write, so they commit together or not at all. A retry with the same key and the same
request then replays the saved response without writing again; the same key with a different request is
refused. Keys belong to one user of one tenant, so neither another tenant nor another user of the same tenant
can collide with, replay or learn of a key, and a replay still needs live authority, so it is never a way
around a revoked membership.
"""
import hashlib
import json
import re

from app.errors import Conflict, Invalid

_KEY = re.compile(r"[A-Za-z0-9._:-]{1,64}")


def check_key(key):
    """A client-chosen key: 1 to 64 of letters, digits and . _ : -  (anything else is a client error)."""
    if not isinstance(key, str) or not _KEY.fullmatch(key):
        raise Invalid("idempotency_key is required: 1 to 64 letters, digits or . _ : -")
    return key


def fingerprint(operation, **request):
    """Identifies WHAT was asked, so a reused key cannot replay the answer to a different request."""
    canonical = json.dumps([operation, request], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def replay(db, principal, key, request_hash):
    """The saved response if this exact request was already applied, None if the key is new.

    Call it inside the write transaction, after the caller's live authority has been re-checked.
    """
    row = db.execute(
        "SELECT request_hash, response FROM idempotency WHERE tenant_id = ? AND user_id = ? AND key = ?",
        (principal.tenant_id, principal.user_id, key),
    ).fetchone()
    if row is None:
        return None
    if row["request_hash"] != request_hash:
        raise Conflict("idempotency_key was already used for a different request")
    return json.loads(row["response"])


def remember(db, principal, key, request_hash, response):
    """Store the response in the same transaction as the write it describes."""
    db.execute(
        "INSERT INTO idempotency (tenant_id, user_id, key, request_hash, response) VALUES (?, ?, ?, ?, ?)",
        (principal.tenant_id, principal.user_id, key, request_hash, json.dumps(response)),
    )
