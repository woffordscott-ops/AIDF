1. What is recorded. For every state-changing request the log keeps the time, the acting user id, the operation name and the full request, including the headers and body, so that support can reproduce a problem exactly. Nothing is left out.

2. Storage and tenancy. A table `audit_log(id, tenant_id, user_id, operation, request, at)` in the application database. The tenant id comes from the verified token of the caller, as everywhere else in the service.

3. When it is written. A wrapper around each handler writes the record once the handler has returned its response, so the log only contains operations that succeeded. A retried request goes through the wrapper again and is recorded again, which is correct because it was sent again.

4. Who may read. Any member of the tenant can read the log of their tenant through `GET /audit`, because transparency inside a tenant is the point of the feature.

5. Changes after writing. Nothing in the application updates or deletes a record. Operators with database access can fix wrong rows when needed.

6. Tests. A test that creating a ticket adds a row, a test that the row has the right tenant id, and a test that `GET /audit` returns the rows of the caller's tenant.
