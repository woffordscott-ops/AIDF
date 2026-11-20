# Task

You are working in a copy of a small multi-tenant ticketing and billing service (`app/`, `tests/`, `tools/`). Running `python -B -m unittest discover -s tests -t .` from the repository root passes now and must still pass when you are done.

Add a role-change operation for tenant members.

- `tenants.change_role(db, principal, user_id, new_role)` changes the role of an active member of the caller's tenant and returns `{"user_id": ..., "role": ...}`.
- The rules the service already applies to granting and removing roles apply to a role change. A member who does not exist in the caller's tenant, or no longer belongs to it, is reported as not found; an unknown role or a malformed id is a client error.
- Over HTTP: `POST /members/<user_id>/role` with the body `{"role": ...}` answers 200 with the same object.
- Follow the conventions of the existing code.

Reply with your result. If a unified diff is the right result, give it with paths relative to the repository root in the form `a/<path>` and `b/<path>`.
