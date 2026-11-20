# Review: assign a ticket by email

I read `git show HEAD` and the new tests.

**What I checked.** `assign_ticket` still takes the write lock first, re-reads the caller's live role and looks the ticket up inside the caller's tenant. The `assignee_id` path is unchanged. The new `assignee_email` path resolves the email to a user id and then applies the membership rule. Giving both fields, neither field, or a non-string email is refused. The tests cover a same-tenant member, an unknown email and the both-fields case.

**Comments.**

1. The email lookup is case-sensitive (`WHERE email = ?`). A caller who types `Alice@Example.test` gets the same refusal as for an unknown address. Low; consider lower-casing on both sides.
2. An unknown email and a non-member share one message, which is good for enumeration. A caller can still tell a known address from an unknown one by whether the call succeeds. Low.
3. The `isinstance(assignee_email, str)` check is folded into the both-fields message, which is slightly confusing. Cosmetic.

The membership rule is the same for emails as for ids, as the description says, and the tests pass.

Verdict: approve with comments
