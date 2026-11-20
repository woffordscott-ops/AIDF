Accept tokens from the previous signing key during a rotation

We rotate the signing key next week. As things stand every session would be logged out at the moment of the switch. `verify_token` and `authenticate` now take an optional `previous_key`; while it is set, a token signed by it is accepted as well as one signed by the current key. Everything else about a token is unchanged: `authenticate` still reads the member's role and membership live, so a removed or demoted member gets nothing from an old token.

Expiry: a token from the previous key was already checked when it was issued, and the previous key is only configured for the rotation window, so the expiry check applies to tokens signed by the current key. That keeps the old sessions from being cut off in the middle of the window.

This change does not touch the web service: it keeps using one key until a follow-up change passes the previous key in.

Tests for both keys, an unknown key and live authority are added to `tests/test_auth.py`. The existing suite is unchanged and passes.

Review process: reviewers report their findings in a review comment; the author makes the changes.
