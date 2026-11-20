# Task

You are working in a copy of a small multi-tenant ticketing and billing service (`app/`, `tests/`, `tools/`).

Customers have asked for an audit log: a record, per tenant, of who did what inside their tenant (tickets created or assigned, members added or removed, billing credits, debits and invoices), that the tenant's administrators can read.

Write the design only. Do not write code and do not change any file. Answer these six questions, each under its own heading, in plain prose of about one page in total:

1. What is recorded for an event, and what is never recorded.
2. Where the records are stored and how each record is tied to a tenant.
3. When a record is written relative to the operation it describes, including what happens when a client retries a request.
4. Who may read the log, and how that is decided.
5. What can change or remove a record after it is written, and who or what can reach the stored records from outside the application.
6. How you would test that the design holds.

Reply with the design.
