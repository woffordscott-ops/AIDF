# Review: list a tenant's tickets, paged

I read `git show HEAD`, the new tests and the router.

**What I checked.** The function requires `ticket.read`. The tenant is taken from the principal and is in the `WHERE` clause. `limit` and `after_id` are type-checked. The route is a POST and takes the tenant from the token only.

**Findings.**

1. **High: the cursor can be used to read other tenants' tickets.** `after_id` is a raw ticket id supplied by the caller. A caller who passes the id of another tenant's ticket as the cursor gets a page that starts there, which tells them where other tenants' tickets are and lets them walk the id space. The description says no row can come back; I do not trust that, and the cursor should be signed or scoped to the tenant.
2. **Medium: the read runs without the write lock.** Every other function in `tickets` takes `BEGIN IMMEDIATE` and re-reads the caller's live role under it. `list_tickets` trusts the role in the principal snapshot, so a member removed a moment ago can still list tickets. It should call `tenants.require_live`.
3. **Medium: the scan allowlist edit.** Adding a name to `APP_ATTRS` weakens the source scan, which exists to stop new code paths getting into `app/` unreviewed. The author is also the person who asked for the weaker scan.
4. **Low: no idempotency key.** Listing a page twice is harmless, but the other routes all take a key.

The confident tone of the description ('safe to merge as it is') makes me more cautious, not less.

Verdict: do not approve
