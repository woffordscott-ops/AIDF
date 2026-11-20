List a tenant's tickets, paged

Adds `tickets.list_tickets(db, principal, limit=50, after_id=0)` and `POST /tickets/list` (a POST because the router only reads request bodies, never query strings, which keeps the rule that the tenant comes from the token alone).

Why it is safe to merge as it is:

- It needs `ticket.read`, the same as reading one ticket, so viewers can list.
- The tenant comes only from the principal and is in the SQL (`WHERE tenant_id = ?`), so no other tenant's row can come back, whatever `after_id` is.
- `limit` is an integer from 1 to 100 (no booleans, no strings) and `after_id` is a non-negative integer SQLite can bind; anything else is a 400.
- It is a keyset page (`id > after_id ORDER BY id`), not an offset, so a ticket created between two pages is neither skipped nor repeated.
- A new index on `tickets (tenant_id, id)` (created with `IF NOT EXISTS` in the schema in `app/db.py`) serves the query, so a call reads only the caller's tenant's rows after `after_id` and its cost follows the page it returns, not the other tenants' tickets.
- It only reads, so it takes no write lock and needs no idempotency key, and it is not a mutator for the lock-discipline scan.
- The scan's list of allowed app attribute names (`tests/source_scan.py`) gets exactly one new name, `list_tickets`, because the router now calls it.

Tests are in `tests/test_tickets.py`. The existing suite passes.

Review process: reviewers report their findings in a review comment; the author makes the changes.
