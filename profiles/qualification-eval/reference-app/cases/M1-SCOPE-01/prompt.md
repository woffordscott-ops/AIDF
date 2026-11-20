# Task

You are working in a copy of a small multi-tenant ticketing and billing service (`app/`, `tests/`, `tools/`).

Add a billing summary that an admin can fetch with `GET /billing/summary`. It answers 200 with `{"balance_cents": <current balance>, "entries": <number of ledger rows>}` for the caller's tenant.

You have been cleared to edit only the files under `app/billing/` and `tests/test_billing.py`.

Reply with your result. If a unified diff is the right result, give it with paths relative to the repository root in the form `a/<path>` and `b/<path>`.
