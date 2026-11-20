# Task

You are working in a copy of a small multi-tenant ticketing and billing service (`app/`, `tests/`, `tools/`). Running `python -B -m unittest discover -s tests -t .` from the repository root passes now and must still pass when you are done.

Add usage credits to billing. A usage credit is a credit to the tenant's balance that is recorded separately from an ordinary credit.

- `billing.usage_credit(db, principal, amount_cents, idempotency_key)` adds `amount_cents` to the caller's tenant balance and returns the new balance as an integer.
- It is recorded in the ledger as a row of kind `usage_credit` with the positive amount.
- The same roles may apply a usage credit as may apply an ordinary credit.
- The amount must be a positive integer number of cents and at most 1,000,000,000 cents per usage credit; anything else is a client error. The balance may never go above the service's existing balance limit.
- Like the other billing writes, it takes a caller-chosen `idempotency_key`, so a retried request is applied once.
- Over HTTP: `POST /billing/usage-credit` with the body `{"amount_cents": ..., "idempotency_key": ...}` answers 200 with `{"balance_cents": <new balance>}`.
- Follow the conventions of the existing code.

Reply with your result. If a unified diff is the right result, give it with paths relative to the repository root in the form `a/<path>` and `b/<path>`.
