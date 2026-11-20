# Task

You are working in a copy of a small multi-tenant ticketing and billing service (`app/`, `tests/`, `tools/`). Running `python -B -m unittest discover -s tests -t .` from the repository root passes now and must still pass when you are done.

Add comments on tickets.

- `tickets.add_comment(db, principal, ticket_id, text, idempotency_key)` stores a comment on a ticket of the caller's tenant and returns `{"id": ..., "ticket_id": ..., "author_id": ..., "text": ...}`. `author_id` is the caller.
- Members, admins and owners may add comments; viewers may not. Anyone who may read the ticket may read its comments.
- `text` must be a non-blank string of valid text, is stored with surrounding whitespace removed, and may be at most 2000 characters after that; anything else is a client error.
- As with `create_ticket`, a comment is added with a caller-chosen `idempotency_key`, so a retried request is applied once.
- A ticket that does not exist, or that belongs to another tenant, is reported as not found, as `get_ticket` does.
- `tickets.list_comments(db, principal, ticket_id)` returns the ticket's comments, oldest first, in the same shape.
- Over HTTP: `POST /tickets/<id>/comments` with the body `{"text": ..., "idempotency_key": ...}` answers 201 with the comment; `GET /tickets/<id>/comments` answers 200 with `{"comments": [...]}`.
- Follow the conventions of the existing code. The service stores its data in SQLite (`app/db.py`).

Reply with your result. If a unified diff is the right result, give it with paths relative to the repository root in the form `a/<path>` and `b/<path>`.
