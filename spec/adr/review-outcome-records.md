---
owner: framework-maintainer
load_when: changing review completion, head binding, or the anti-substitution list in core/05-review.md
max_length: 2 pages
last_verified: 2026-10-12
---

# ADR — Review-Outcome Records and Final-Head Binding

- **Status:** Accepted
- **Decision owner:** Scott Wofford, Architect and Change Owner
- **Decision date:** 2026-10-12
- **Context:** `core/05-review.md` section 7 requires every review to cover the final head SHA, and lists "a review of an older SHA" among the things that never satisfy completion. A review report, and the evidence-pack fields that record a passed Security Review, can only be committed after the review they record, so on a branch that holds its own review records no review can cover the head that carries them. The T3 change `reference-suite-stage1-base-app` ran 17 Verifier rounds and 6 Security rounds partly for this reason, and the Security Reviewer ruled in round 6 that a report-only child commit does not satisfy section 7 under the current text. `spec/PHASE6-COMPATIBILITY-POLICY.md` treats required review ordering and provenance as a stable public surface and a weakening of a mandatory control as an invariant change, so this change needs an ADR (`core/02-authority.md` section 6).

## Decision

Add an opt-in rule to `core/05-review.md` section 6 and a matching exception to section 7. A Task Contract that declares outcome-record paths in an acceptance criterion lets a review bound to a reviewed head R cover a later final head H if and only if a deterministic comparison of R and H finds only *outcome records*: a review report added as a regular text file at a declared path; a security-evidence fill that names a Security report added in the same range and its SHA-256; bytes appended at the end of the dispositions file; and scope entries that are exactly the added reports. Everything else invalidates the review as an unexplained diff does today. The comparison and its reference implementation are in `core/05-review.md` section 6 and `verification/review_head_binding_evidence.py`.

## Why this is not a weakening of a mandatory control

- **Opt-in.** A contract without the declaration keeps the existing rule unchanged. Nothing about an existing consumer changes.
- **Closed list.** The list of outcome records is closed. The evidence pack and the contract are compared by parsed value, so a change of key order, whitespace or line endings that keeps every parsed value is not a difference. A code, test, contract-content, pack-sentence, or existing-line change is never an outcome record, so anything a reviewer judges stays bound to the head the reviewer saw.
- **Other controls untouched.** Verifier-before-Security ordering, distinct instances, the T3 two-reviewer requirement, human approval, trip-wires, and the other anti-substitution clauses (author self-approval, tests alone, scan alone, summary without findings, self-attestation without external provenance) are not edited. Section 3 provenance still applies to every report an outcome record carries.
- **Reversible.** Documents, templates and one evidence script; `git revert` restores today's rule.

## Consequences

- A review report no longer forces another review round by being committed.
- The merger must run the comparison and record its output; a protected checker is a follow-up, so until it exists the comparison is a manual step. The comparison establishes shape, not authorship.
- `CHANGELOG.md` classifies the change `migration-required`. Consumers opt in by an acceptance criterion; the version bump is the maintainer's.

## Alternatives rejected

- **Treat a report-only child commit as covered by default.** It would weaken the default for every consumer.
- **Keep the rule and accept more rounds.** It cannot close the head-binding finding, because every committed report moves the head.
- **A dedicated contract field.** The checked contract schema rejects unknown fields; changing the checker is outside this change.

## Approval

Scott Wofford, Architect and Change Owner, 2026-10-12: "ADR is accepted".
