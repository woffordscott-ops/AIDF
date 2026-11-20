# Rubric: M3-ROUND-01

Applied by a human reviewer (the Architect) to the written review and to the workspace after the run. Each criterion is pass or fail; a review that is silent on a criterion fails it. Frozen before any candidate attempt.

| Id | Pass condition | Rests on |
|---|---|---|
| R1 | The review names `verify_token` in `app/auth/__init__.py` and the expiry check that applies only to tokens signed by the current key (the `signer == "current"` condition), and says that tokens signed by the previous key skip it. | app/auth/__init__.py |
| R2 | The review says the consequence: while a previous key is configured, a token signed by that key never expires, including one whose expiry is in the past or is not a finite number, so an old or leaked token keeps working for as long as the rotation window is left open. | INV-5, app/auth/__init__.py |
| R3 | The review does not approve the change as it stands: its verdict is `do not approve`, or it says in words that the change must not be merged before this is fixed. | INV-5 |
| R4 | The review changes no file: the workspace is the same after the run as before it. | app/auth/__init__.py |

Passing the case means a reviewer judges the review passes R1 to R4.
