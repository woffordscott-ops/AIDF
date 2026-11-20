"""Role hierarchy and action permissions (INV-2)."""
from app.errors import Forbidden, Invalid

ROLE_RANK = {"viewer": 0, "member": 1, "admin": 2, "owner": 3}

MIN_ROLE = {
    "ticket.read": "viewer",
    "ticket.create": "member",
    "ticket.assign": "member",
    "member.manage": "admin",
    "billing.read": "admin",
    "billing.write": "admin",
}


def check_role(role):
    if not isinstance(role, str) or role not in ROLE_RANK:
        raise Invalid(f"unknown role: {role!r}")
    return role


def can(role, action):
    if action not in MIN_ROLE:
        return False
    return role in ROLE_RANK and ROLE_RANK[role] >= ROLE_RANK[MIN_ROLE[action]]


def require(principal, action):
    if not can(principal.role, action):
        raise Forbidden(f"{principal.role} may not {action}")


def can_grant(granter_role, target_role):
    """A principal may grant only roles at or below their own."""
    return (
        granter_role in ROLE_RANK
        and target_role in ROLE_RANK
        and ROLE_RANK[target_role] <= ROLE_RANK[granter_role]
    )
