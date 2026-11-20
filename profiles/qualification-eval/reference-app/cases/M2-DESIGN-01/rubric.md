# Rubric: M2-DESIGN-01

Graded by a human reviewer (the Architect) against the written answer. Each criterion is pass or fail on the text of the answer; a design that is silent on a criterion fails it. Frozen before any candidate attempt.

| Id | Pass condition | Rests on |
|---|---|---|
| D1 | Every record carries the tenant id taken from the authenticated principal (the verified token), never from the request body, query string or headers, and every read of the log filters by the caller's own tenant id. | INV-1 |
| D2 | The record is written inside the same database transaction as the operation it describes, so both commit or both roll back; the answer does not write it after the operation's COMMIT or from a separate step that can be lost. | app/db.py |
| D3 | A retried request that the idempotency mechanism replays does not write a second record, and a request refused or rolled back writes no record of success. | app/idempotency/__init__.py |
| D4 | Reading the log needs an explicit action in the permission table at admin or above, checked against the caller's live membership role on every request, and the answer says a viewer or member cannot read it. | INV-2 |
| D5 | The answer lists what is never recorded and that list includes passwords or password hashes, bearer tokens or signing keys, and the contents of request bodies beyond the fields named in question 1. | app/auth/__init__.py |
| D6 | No operation of the application changes or deletes a record after it is written (append only), and the answer says who can reach the storage outside the application. | app/db.py |
| D7 | The test plan includes a test that a user of one tenant cannot read another tenant's records, and a test that a failed operation leaves no record. | INV-1, app/db.py |

Passing the case means a reviewer judges the answer passes D1 to D7 and the response is a design only (no code, no changed file).
