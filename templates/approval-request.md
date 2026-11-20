---
owner: framework-maintainer
load_when: any level-P gate (core/02-authority.md §Gate assignments)
max_length: ~200 words
last_verified: 2026-08-19
---

# Approval Request

Humans approve decisions, plans, and contracts — not diffs (exception: T3 line-level review). An approval request that doesn't say what could go wrong is a signature request, not a decision request. Keep the whole request under ~200 words.

- **Decision requested:**
- **What changes:**
- **What could go wrong:**
- **Evidence that exists:**
- **Recovery / reversal approach** appropriate to the operation (rehearsed rollback | tested restore | named irreversible consequence + recovery point):
- **Gate / level:** (e.g. new dependency — P; invariant change — P; irreversible op — X)
- **Requested of** (role: Change Owner | Architect):
- **Requested (UTC):** *(when the request was sent to the human, ISO 8601 with Z, for example 2026-10-30T15:00:00Z)*
- **Answered (UTC):** *(when the human replied, same form)*
- **Active minutes (manual):** *(the human's own estimate of time spent, a number; the elapsed time above is only an upper bound)*
- **Decision:** Approved | Denied | Needs more information
- **Recorded against roles:** *(one signature, listed against every role it satisfies — core/02-authority.md §8)*
- **Date:**
