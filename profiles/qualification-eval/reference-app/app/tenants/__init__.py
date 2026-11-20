"""Tenants and memberships (INV-1, INV-2).

add_member and remove_member re-read the caller's own live role and every fact the decision
depends on while holding the write lock, so two concurrent requests cannot jointly break an
invariant that each would have preserved alone (INV-2).
"""
from app import permissions, validate
from app.db import transaction
from app.errors import Conflict, Forbidden, NotFound


def create_tenant(db, name, owner_user_id):
    with transaction(db):  # a tenant never exists without its first owner
        cur = db.execute("INSERT INTO tenants (name) VALUES (?)", (name,))
        tenant_id = cur.lastrowid
        db.execute(
            "INSERT INTO memberships (tenant_id, user_id, role) VALUES (?, ?, 'owner')",
            (tenant_id, owner_user_id),
        )
    return tenant_id


def get_role(db, tenant_id, user_id):
    row = db.execute(
        "SELECT role FROM memberships WHERE tenant_id = ? AND user_id = ? AND active = 1",
        (tenant_id, user_id),
    ).fetchone()
    return row["role"] if row else None


def is_active_member(db, tenant_id, user_id):
    return get_role(db, tenant_id, user_id) is not None


def require_live(db, principal, action):
    """Authorize `action` from the caller's role RIGHT NOW; call it inside the write lock.

    The Principal a request arrives with is a snapshot. Every state-changing operation calls this
    inside its transaction, so a caller removed or demoted a moment ago cannot complete the
    operation (INV-2: authority is lost immediately, not at the next request).
    """
    role = get_role(db, principal.tenant_id, principal.user_id)
    if role is None or not permissions.can(role, action):
        raise Forbidden("membership revoked or insufficient role")
    return role


def _live_actor_role(db, principal):
    return require_live(db, principal, "member.manage")


def add_member(db, principal, user_id, role):
    permissions.require(principal, "member.manage")  # fast fail before taking the lock
    user_id = validate.db_id(user_id, "user_id")
    permissions.check_role(role)
    with transaction(db):
        actor_role = _live_actor_role(db, principal)
        if not permissions.can_grant(actor_role, role):
            raise Forbidden("cannot grant a role above your own")
        if db.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
            raise NotFound("user not found")
        if get_role(db, principal.tenant_id, user_id) is not None:
            raise Conflict("already a member")
        db.execute(
            "INSERT OR REPLACE INTO memberships (tenant_id, user_id, role, active) VALUES (?, ?, ?, 1)",
            (principal.tenant_id, user_id, role),
        )


def _active_owner_count(db, tenant_id):
    return db.execute(
        "SELECT COUNT(*) AS n FROM memberships WHERE tenant_id = ? AND role = 'owner' AND active = 1",
        (tenant_id,),
    ).fetchone()["n"]


def remove_member(db, principal, user_id):
    permissions.require(principal, "member.manage")  # fast fail before taking the lock
    user_id = validate.db_id(user_id, "user_id")
    with transaction(db):
        actor_role = _live_actor_role(db, principal)
        target = get_role(db, principal.tenant_id, user_id)
        if target is None:
            raise NotFound("member not found")
        if not permissions.can_grant(actor_role, target):
            raise Forbidden("cannot remove a member above your own role")
        if target == "owner" and _active_owner_count(db, principal.tenant_id) <= 1:
            raise Conflict("cannot remove the last owner")
        db.execute(
            "UPDATE memberships SET active = 0 WHERE tenant_id = ? AND user_id = ?",
            (principal.tenant_id, user_id),
        )
        db.execute(
            "UPDATE tickets SET assignee_id = NULL WHERE tenant_id = ? AND assignee_id = ?",
            (principal.tenant_id, user_id),
        )
