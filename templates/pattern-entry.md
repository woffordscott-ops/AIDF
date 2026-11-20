---
owner: framework-maintainer
load_when: classification is being determined (Precedent check), or a pattern is discovered/ratified
max_length: 1 line per entry
last_verified: 2026-10-06
---

# Pattern Registry Entry

One line per pattern. Lives as a table (e.g. an appendix to the conventions file or `core/01-lifecycle.md`'s registry). Discovery is not approval — inserting a row records that a pattern exists, not that anyone decided it should.

`pattern · scope/context · state · basis · date · ratifier`

| Field | Value |
|---|---|
| Pattern | |
| Scope / context (where it applies) | |
| State | `PROVISIONAL` \| `RATIFIED` |
| Basis | incumbent, unreviewed (`PROVISIONAL`) \| Architect ratification, ADR, or convention (`RATIFIED`) |
| Date | |
| Ratifier | *(blank until `RATIFIED`; must be Architect authority)* |

`PROVISIONAL` confers no Precedent and must not lower a task from T2 to T1. Promotion to `RATIFIED`, or rejection as drift, happens in your project's Layer 3 architecture-governance pass (`core/03-architecture.md`) — not here, and not by this entry aging.
