# Rotate the API signing key

## Problem

The API signing key has not been rotated since launch, and the security policy asks for a rotation every 90 days.

## Outcome

The service signs with a key that is at most 90 days old, and an old key still verifies for 24 hours after a rotation.

## Acceptance criteria

- A new key is generated and published at `/.well-known/keys`.
- Tokens signed with the previous key verify for 24 hours.
- A failed rotation leaves the current key in place and writes an alert.

## Scope

- `auth/keys.py`
- `auth/rotate.py`
- `tests/test_rotate.py`

## Approach

Add a scheduled `rotate` job that writes the new key before it retires the old one.

## Dependencies

None.

## Notes

Not copied by the mapping: this section is not named by any rule.
