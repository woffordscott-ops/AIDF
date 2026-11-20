# Task Contract (DRAFT, not approved)

Drafted by `spec_mapper` with the mapping `markdown-sections`. A draft is not an approval, a classification or evidence: a person fills each TODO, chooses the class and has it approved before any implementation.
Every line copied from a planning file sits in a quotation under its source file; nothing else in this draft comes from the sources.

- **Change id:** `sections-input` (the name of the folder that holds `plan.md`)
- **Files read:** `plan.md`
- **Parts copied from the source:** 6 of 17. **Parts left as TODO:** 11.

## Approver's opening

- **Read this first:** TODO(author)
- **Problem:**
  - Source: `plan.md` (section)
    > ## Problem
    >
    > The API signing key has not been rotated since launch, and the security policy asks for a rotation every 90 days.
- **Why it matters:** TODO(author)
- **The change:** TODO(author)
- **Technical details:** TODO(author)
- **What you need to decide:** TODO(author)

## Part A: Minimal

- **Intended outcome:**
  - Source: `plan.md` (section)
    > ## Outcome
    >
    > The service signs with a key that is at most 90 days old, and an old key still verifies for 24 hours after a rotation.
- **Acceptance criteria:**
  - Source: `plan.md` (section)
    > ## Acceptance criteria
    >
    > - A new key is generated and published at `/.well-known/keys`.
    > - Tokens signed with the previous key verify for 24 hours.
    > - A failed rotation leaves the current key in place and writes an alert.
- **Declared scope:**
  - Source: `plan.md` (section)
    > ## Scope
    >
    > - `auth/keys.py`
    > - `auth/rotate.py`
    > - `tests/test_rotate.py`
- **Outcome records:** TODO(AIDF)

## Part B: Plan

- **Approach:**
  - Source: `plan.md` (section)
    > ## Approach
    >
    > Add a scheduled `rotate` job that writes the new key before it retires the old one.
- **Invariants touched:** TODO(AIDF)
- **Evidence strategy:** TODO(AIDF)
- **Protected files touched:** TODO(AIDF)
- **Recovery / reversal approach:** TODO(AIDF)
- **Review budget:** TODO(AIDF)
- **Dependency changes:**
  - Source: `plan.md` (section)
    > ## Dependencies
    >
    > None.

## Status

- **State:** Established
- **Established by (author):** TODO(author)
- **Approved by (human, T2/T3 only, role: Architect):** none
- **Date:** TODO(author)
- **Class:** TODO(AIDF)
- **Spec Confidence at intake:** TODO(AIDF)
- **Re-evaluated to Clear by:** TODO(AIDF)
