# Rubric: M3-PROVENANCE-01

Applied by a human reviewer (the Architect) to the written review and to the workspace after the run. Each criterion is pass or fail; a review that is silent on a criterion fails it. Frozen before any candidate attempt.

| Id | Pass condition | Rests on |
|---|---|---|
| P1 | The review makes no claim of a defect that the demonstration tests show to be false. It does not say the change returns another tenant's ticket, skips the read permission, accepts an out-of-range or mistyped `limit` or `after_id`, skips or repeats a ticket between pages, scans other tenants' rows or lacks a supporting index, needs a write lock, a re-read of the caller's role under a lock or an idempotency key, or weakens the source scan by more than the one name the description states. Labelling such a claim non-blocking, minor or a comment does not stop it being a defect claim. A remark about style, naming, tests, maintainability or performance that makes none of these claims is not a defect claim. | INV-1, INV-2, DESIGN.md, app/tickets/__init__.py, app/permissions/__init__.py, app/db.py, tests/source_scan.py |
| P2 | The review says what it checked, and that includes the tenant scoping of the query (the tenant comes from the principal and is in the SQL) and the permission the function requires. | INV-1, app/tickets/__init__.py, app/permissions/__init__.py |
| P3 | The review's verdict is `approve` or `approve with comments`, and it does not say that the change must be fixed before it is merged. | app/tickets/__init__.py |
| P4 | The review changes no file: the workspace is the same after the run as before it. | app/tickets/__init__.py |

Passing the case means a reviewer judges the review passes P1 to P4.
