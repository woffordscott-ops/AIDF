---
owner: framework-maintainer
load_when: assigning or running a qualification against the public reference suite (suite-v2) or another suite that does not belong to the private pilot
max_length: 2 pages
last_verified: 2026-10-20
---

# Qualification Protocol v1.2

Protocol v1.2 is an additive amendment to `profiles/qualification-protocol-v1.1.md`, which is an additive amendment to `profiles/qualification-protocol-v1.md`. It does not replace them and it changes no validator. Everything in v1 and v1.1 applies to a suite that names this file as its `protocol_path`, except where this file says otherwise. The pilot's suite v1 and suite v1.1 keep naming v1 and v1.1 and are not affected.

## What this amendment changes

1. **Jurisdiction.** Where v1 and v1.1 say "the private pilot's repository revision", read "the repository project and revision named by the suite's `repository` field". A run and a profile must name that repository exactly, as the validators already require. This amendment adds no other jurisdiction.
2. **Fixed population.** Where v1 and v1.1 name the pilot's suite v1 or suite v1.1 as the fixed population, the fixed population is the suite file that the run and the profile name by `suite_id`, `suite_version` and `suite_sha256`, whose canonical SHA-256 is supplied independently to the validator by the party running the qualification. Cases are those of that suite, not derived from a private pilot's outcomes. For `suite-v2.json` the cases are the authored case directories under `profiles/qualification-eval/reference-app/cases/` at the pinned revision, and `profiles/qualification-eval/REFERENCE-SUITE.md` states what they cover.
3. **Context and grading declared by a suite.** A suite's documentation may declare that a mode's case context or grading differs from the general description in `modes/execution-modes.md`. For a suite that declares such a difference, the declaration replaces, for that suite, the sentence of v1 and v1.1 that M3 cases receive the requirement, invariants, diff and tests without author rationale and any corresponding general description in `modes/execution-modes.md`; no other rule of v1 or v1.1 is replaced. A profile issued against such a suite must list each declared difference in its `limitations`, and a result holds only for the context and grading so declared. the suite documentation (`REFERENCE-SUITE.md`) declares three for `suite-v2.json`: three of its four M0 cases are graded by an evaluator against an expected disposition and ground truth, not as a mechanically checkable transform; its five negative M1 cases (`M1-SCOPE-01`, `M1-INVARIANT-01`, `M1-EVIDENCE-01`, `M1-AUTHORITY-01`, `M1-PROVENANCE-01`) are graded by an evaluator against an expected disposition and ground truth, not against a reference implementation or a test suite that only a correct implementation passes; and its M3 cases give the candidate the author's description of the change, which `modes/execution-modes.md` excludes from M3 context.
4. **Answer key.** A suite whose ground truth is public (as `suite-v2.json`'s is) is evaluated only on a candidate with no access to that ground truth beyond what each case gives it. A profile against such a suite lists the public answer key in its `limitations`; a result says nothing about a candidate that had access.

## What it does not change

The evaluation unit, exact-identity rule, availability records, environment records, the run-and-profile requirements, role separation, ordered reviewer bindings and the protected-integration digest, result semantics, expiry and requalification, and the security and privacy boundary are as in v1 and v1.1. This amendment does not add a run-record validator, does not make the profile validator accept an inactive review-pending candidate, and does not qualify any tool or model.
