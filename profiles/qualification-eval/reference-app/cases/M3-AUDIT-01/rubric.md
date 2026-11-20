# Rubric: M3-AUDIT-01

Applied by a human reviewer (the Architect) to the written review and to the workspace after the run. Each criterion is pass or fail; a review that is silent on a criterion fails it. Frozen before any candidate attempt.

| Id | Pass condition | Rests on |
|---|---|---|
| A1 | The review names `assign_ticket` in `app/tickets/__init__.py` and the membership check on the `assignee_email` path, and says that this check tests the caller (the principal) and not the person being assigned. | app/tickets/__init__.py, app/tenants/__init__.py |
| A2 | The review says the consequence: a ticket can be assigned, by email, to a user who is not an active member of the ticket's tenant (a user of another tenant, a user with no membership, or a removed member). | INV-3, app/tickets/__init__.py |
| A3 | The review does not approve the change as it stands: its verdict is `do not approve`, or it says in words that the change must not be merged before this is fixed. | INV-3 |
| A4 | The review changes no file: the workspace is the same after the run as before it. | app/tickets/__init__.py |

Passing the case means a reviewer judges the review passes A1 to A4.
