"""Tenant-scoped tickets (INV-1, INV-3)."""
from app import idempotency, permissions, tenants, validate
from app.db import transaction
from app.errors import Invalid, NotFound


def _row(r):
    return {
        "id": r["id"],
        "title": r["title"],
        "created_by": r["created_by"],
        "assignee_id": r["assignee_id"],
    }


def create_ticket(db, principal, title, idempotency_key):
    permissions.require(principal, "ticket.create")
    if not isinstance(title, str) or not title.strip():
        raise Invalid("title is required")
    validate.text(title, "title")
    key = idempotency.check_key(idempotency_key)
    request_hash = idempotency.fingerprint("ticket.create", title=title.strip())
    with transaction(db):
        tenants.require_live(db, principal, "ticket.create")
        saved = idempotency.replay(db, principal, key, request_hash)
        if saved is not None:
            return saved  # this exact request was already applied: answer it again, write nothing
        cur = db.execute(
            "INSERT INTO tickets (tenant_id, title, created_by) VALUES (?, ?, ?)",
            (principal.tenant_id, title.strip(), principal.user_id),
        )
        ticket = get_ticket(db, principal, cur.lastrowid)  # read back under the lock, before COMMIT
        idempotency.remember(db, principal, key, request_hash, ticket)
    return ticket


def get_ticket(db, principal, ticket_id):
    permissions.require(principal, "ticket.read")
    ticket_id = validate.db_id(ticket_id, "ticket_id")
    row = db.execute(
        "SELECT * FROM tickets WHERE id = ? AND tenant_id = ?",
        (ticket_id, principal.tenant_id),
    ).fetchone()
    if row is None:
        raise NotFound("ticket not found")
    return _row(row)


def assign_ticket(db, principal, ticket_id, assignee_id):
    permissions.require(principal, "ticket.assign")  # fast fail before taking the lock
    ticket_id = validate.db_id(ticket_id, "ticket_id")
    assignee_id = validate.db_id(assignee_id, "assignee_id")
    with transaction(db):
        # Everything the decision depends on is read here, under the write lock, so a concurrent
        # removal of the assignee (or of the caller) cannot slip in between check and write.
        tenants.require_live(db, principal, "ticket.assign")
        get_ticket(db, principal, ticket_id)  # tenant-scoped existence check
        if not tenants.is_active_member(db, principal.tenant_id, assignee_id):
            raise Invalid("assignee must be an active member of this tenant")
        db.execute(
            "UPDATE tickets SET assignee_id = ? WHERE id = ? AND tenant_id = ?",
            (assignee_id, ticket_id, principal.tenant_id),
        )
        ticket = get_ticket(db, principal, ticket_id)  # read back under the lock, before COMMIT
    return ticket
