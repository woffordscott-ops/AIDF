# Review: accept tokens from the previous signing key during a rotation

I read `git show HEAD`, the new tests and the callers of `verify_token`.

**What I checked.**

- The signature comparison still uses `hmac.compare_digest` on ASCII input, for both keys. A token that matches neither key is `bad signature`.
- `authenticate` still reads the member's role and membership from the database, so an old token cannot keep a removed or demoted member's authority.
- With no `previous_key` the behaviour is the one the existing tests pin, and they pass. The new tests cover both keys, an unknown key and live authority.
- The payload is parsed in one place and the same claims are read for both keys.

**Comments.**

1. `_signer` compares against the current key first and the previous key second, so a previous-key token costs two HMACs. That is fine, and the two comparisons are both constant-time. Low.
2. The rotation window has no end in the code: it lasts as long as `previous_key` is configured. Say in the runbook who removes it, and when. Low.
3. `"current"` and `"previous"` are strings; an enum would be tidier. Cosmetic.

The description's reasoning for the expiry rule is sound: the previous key is configured only for the window, and role and membership are live. I see no problem with merging.

Verdict: approve with comments
