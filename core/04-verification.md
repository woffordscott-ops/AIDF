---
owner: framework-maintainer
load_when: lifecycle stage 8, selecting evidence, reviewing an evidence pack, or operating a verification gate
max_length: 6 pages
last_verified: 2026-10-06
---

# 04 — Verification

Operational semantics for locked Layer 1 §10. Verification establishes falsifiable correctness only. It never decides whether a requirement is right, an architecture is sound, or a risk is acceptable.

## 1. Evidence jurisdiction

| Question | Authority | Evidence that cannot settle it |
|---|---|---|
| Does the change do what it claims, avoid regression, and preserve a stated invariant? | Executable evidence | Agent confidence or reviewer opinion |
| Is the structure or boundary the right design? | Architect judgment and, where required, an ADR | A green suite |
| Should the change exist, is its risk acceptable, or may an irreversible action proceed? | Human Change Owner | Tests or architectural judgment |

Green checks never justify skipping a human gate and must not be cited as support for a design, scope, or risk-acceptance decision.

## 2. Evidence ladder and class floor

Each level is a checkable artifact, not a completion claim.

| Level | Required artifact |
|---|---|
| E0 | Build output, or an explicit `not applicable` explanation when the repository has no buildable product |
| E1 | Type/lint/static results, secret scan, dependency/SCA result, and architecture lint once your project's architecture governance (`core/03-architecture.md`) supplies boundary rules |
| E2 | Existing suite result plus its stated coverage boundary; `unavailable` is honest evidence when no suite exists, not a green signal |
| E3 | A named counterfactual mechanism, its artifact, and one sentence stating what would make the evidence fail |
| E4 | Each executable acceptance criterion mapped to a specific executing check |
| E5 | Negative paths, boundaries, errors, abuse cases, and property/fuzz evidence where suitable |
| E6 | Contract diff, invariants touched, mechanical invariant results, prose-only invariant reasoning, and migration dry-run where relevant |
| E7 | Relevant performance/operational evidence, failure observability, kill-switch/flag evidence where applicable, and the recovery form in §4 |

| Class | Required floor |
|---|---|
| T0 | E0–E2 |
| T1 | E0–E3 |
| T2 | E0–E6 |
| T3 | E0–E7, recovery evidence, and security evidence |

Voluntary stronger evidence is welcome, but a template or checker must not imply that evidence above the class floor is mandatory.

## 3. Counterfactual evidence (E3)

Evidence must demonstrate that the claimed property depends on the evaluated change. Prefer a reversion test for behavior changes. Other acceptable mechanisms are before/after reproduction, failure reproduction, mutation testing, baseline comparison, contract comparison, performance benchmark, architecture/invariant check, or another independently checkable falsifying mechanism.

Every E3 record must contain:

1. the selected mechanism;
2. the artifact or command/result that demonstrates it; and
3. one sentence stating what would have to differ for the evidence to fail.

A check that passes with and without the relevant change is defective evidence and must be reported as a gap.

### E3 exemptions

"No mechanism applies" escalates; it never silently waives E3.

| Class | Exemption path |
|---|---|
| T0 | None needed because E3 is not required |
| T1 | Expiring Change Owner approval |
| T2 | Expiring Change Owner approval, Verifier recommendation, explicit residual risk, and expiry |
| T3 | No exemption; redesign or do not ship |

No more than five open exemptions may exist. Expiry reopens E3 immediately. Retiring an exemption requires either satisfactory E3 evidence or retirement of the governed change.

An Evidence Pack may reference an exemption only by `exemption_id`. The checker resolves that identifier to exactly one versioned registry record and requires its `change_id`, class, Open status, and unexpired date to match. Embedded approval text is not an exemption and cannot bypass the five-open cap.

## 4. Recovery evidence (E7)

The evidence pack classifies the operation and supplies the strongest applicable form. The Verifier challenges any classification that understates irreversibility.

| Operation | Required evidence |
|---|---|
| Reversible | Rehearsed rollback: the revert path was executed and its result recorded |
| Destructive but recoverable | Tested restore against representative data, including measured recovery time |
| Truly irreversible | Verified recovery point and restore path for recoverable state; written list and consequence of every irrecoverable effect; explicit Change Owner level-X acceptance recorded before execution |

If design choices created avoidable irreversibility, redesign is preferred over accepting it.

## 5. Evidence-pack rules

Use `templates/evidence-pack.md`. Keep the pack to one page and class-aware: omit fields above the class floor or mark them `not required for this class`. Order is falsification first, evidence next, uncovered areas and residual risk last.

Every result names its artifact or command. `passed`, `green`, or `verified` without a reproducible reference is not evidence. An unavailable product suite is recorded as an E2 gap with a coverage boundary; it is never converted into success.

The pack must state: **This evidence addresses falsifiable correctness only; it does not establish requirement fitness, design quality, or acceptable risk.**

### Trust boundary

Task Contracts, Evidence Packs, and repository policy files on a merge-request branch are untrusted data. Protected CI executes checker code from an immutable trusted source and integrity-binds the approved T2/T3 contract and completed evidence record. Non-empty approval names or artifact prose are not proof of authorization or execution by themselves.

## 6. Test integrity

An Implementer must never weaken or remove test intent to obtain green status. Removing a meaningful assertion, widening a tolerance without approved intent, stubbing away the governed condition, or deleting a case is a level-P escalation.

Assertion and coverage deltas are inspection triggers only. They may identify where a human or separated Verifier should look, but they are never evidence that semantics were preserved. Mutation testing may establish that mechanically where suitable.

## 7. Mechanical enforcement

The mechanical checkers fail safely on malformed or missing governance input and report the failed condition plus remediation. They enforce only claims they can settle:

- evidence-record completeness and E3 exemption rules;
- changed paths against declared scope;
- configured trip-wire path/content signals—and any declared trip-wire—forcing class T3 across all nine locked trip-wire families;
- dependency-manifest changes requiring exact, immutable dependency references bound to recorded human approval;
- high-confidence secret patterns in added content; and
- assertion/coverage deltas as non-blocking inspection output.

Project-specific path rules live in an immutable trusted policy source when they gate merge. A checker finding is data for classification or remediation; it is not permission to reinterpret the locked architecture.
