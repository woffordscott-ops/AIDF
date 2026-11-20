---
owner: framework-maintainer
load_when: implementing or reviewing the public reference qualification suite
max_length: 1 screen
last_verified: 2026-10-06
---

# Task Contract — Public Reference Qualification Suite

`core/01-lifecycle.md` §4. T3 — both parts required; Approved status required from a human under Architect authority before implementation begins; T3 merge approval is separate and comes after independent review.

## Part A — Minimal

- **Intended outcome:** Ship a real, public, runnable Layer 2 qualification suite that an external adopter can execute against their own tool/model with nothing else to fetch. Today the only suite (`profiles/qualification-eval/suite-v1.1.json`) is pinned to one private pilot repository and revision, and `qualification_check.py` rejects any profile whose repository does not exactly match, so `README.md`'s "qualify your own tool/model" step cannot be followed. The new suite is **additive**: a self-contained multi-tenant SaaS backend fixture (auth, RBAC, tenant isolation, billing invariants) plus a new `suite_id`/`suite_sha256`-bearing suite file.
- **Acceptance criteria:**
  1. **Fixture home.** The reference app lives at `profiles/qualification-eval/reference-app/`, embedded in this repository, not a second repository. *(Spike default (a), confirmed by Scott Wofford, Change Owner, 2026-10-06.)*
  2. **Case counts.** The suite's mandatory cases number exactly **4 / 10 / 3 / 4** for M0 / M1 / M2 / M3 — a fixed target, not open-ended. *(Spike default (b), confirmed 2026-10-06.)*
  3. **Authoring and acceptance.** Defects and invariants are authored by an AI instance under Architect role. Each is independently proven by a real falsification attempt **run by a different instance than its author** (`core/02-authority.md` §3), recorded as evidence, **before** the case is admitted. Scott Wofford reviews and explicitly accepts each case, and the suite as a whole, before it is trusted or advertised. *(Spike default (c), confirmed 2026-10-06; "different instance" is this contract's reading of "independently", flagged for approval.)*
  4. **Per-mode verification method** matches `modes/execution-modes.md`'s own "Verification of its output" column: M0 a deterministic mechanically checkable transform; M1 an evidence pack checkable against an accepted reference implementation or a test suite only a correct implementation passes; M2 graded by human/Architect review of the decision, explicitly not mechanized; M3 a deliberately planted, known defect or invariant violation with objective ground truth, plus the existing "no manufactured findings" check.
  5. **Runnable end to end.** The suite passes `qualification_check.py`'s existing validators unmodified, and a documented dry run by someone other than the author produces a well-formed profile against it.
  6. **Additive only.** No change to `suite-v1.json`, `suite-v1.1.json`, anything under `profiles/qualified/**`, `core/`, `modes/`, `KERNEL.md`, or `qualification_check.py`'s validator logic. Existing digest-bound evidence stays valid.
  7. **No authorization content shipped.** No `profiles/authorization/**` file, protected digest, or qualified profile is produced for any candidate by this work.

  Spec Confidence: Clear at intake via Spike (`spec/SPIKE-REFERENCE-QUALIFICATION-SUITE-PROPOSAL.md`, closed and merged 2026-10-06, MR !43). One gap found while drafting this contract is handled in Part B (revision pinning), not left implicit.

- **Declared scope:** `profiles/qualification-eval/reference-app/**` (fixture tree, including paths named `auth/` and `permissions/`); new `profiles/qualification-eval/suite-v2.json` (name provisional); the authored-case evidence and falsification records for each case; narrowly required additions to `profiles/README.md` and `README.md` "Getting started" describing how to run the public suite; new tests that exercise the suite through `qualification_check.py`. **Excluded:** the validators and schema, `core/`, `modes/`, `KERNEL.md`, the private-pilot suites and all `profiles/qualified/**`, `profiles/authorization/**`, `.gitlab-ci.yml`, and any real candidate qualification run.

## Part B — Plan

- **Approach:** Two delivery stages, in order. **Stage 1:** the fixture tree alone (reference app, planted defects, reference implementations, per-case falsification evidence), reviewed and merged on its own. **Stage 2:** the suite file, pinning Stage 1's merge commit.
  - *Why staged (the revision-pinning gap):* `qualification_check.py` requires `suite.repository.revision` and each case's `source.revision` to be an exact 40-character Git SHA, and a profile's repository must match the suite's exactly. An embedded fixture cannot name the commit that contains itself, so a single change cannot carry both. Staging resolves this with no validator change, as the Spike assumed. Cost: once Stage 2 pins a SHA, any fixture change requires a new suite version, never an in-place edit.
  - Within Stage 1, build per mode in order M0, M1, M2, M3, each case independently falsified before the next depends on it.
- **Invariants touched:** `core/02-authority.md` §3 (separation of duties) applies to authoring versus falsification. The qualification protocol's mandatory-case and evidence-jurisdiction rules are used, not modified. No locked-spec invariant is weakened. Tripwire family `authentication-authorization-session-permissions` is expected to fire on the fixture's own paths and is **not** worked around by renaming; it is the reason for T3.
- **Evidence strategy:** Counterfactual per case. Each M3 planted defect gets a real attempt to find it from the case prompt alone, by a non-author instance, and a defect-free control proving "no manufactured findings" holds. Each M1 case proves its test suite fails on a plausible-but-wrong implementation (a check present but checking the wrong condition, the framework's stated canonical failure). M0 cases prove the transform output is deterministic. M2 cases record the Architect's grading rubric before any candidate sees them. Required T3 artifacts: a real Security Reviewer pass, recovery evidence, and pinned security evidence, produced for this change and not inherited from other contracts.
- **Recovery / reversal approach:** Purely additive and unreferenced until deliberately adopted. Reversal is an ordinary revert of the Stage 2 suite file (which makes the suite unavailable) and then, if wanted, Stage 1. Because the new suite shares nothing with the private-pilot suite, no existing evidence or profile depends on it.
- **Known risks, disclosed:** (1) a public fixture is a public answer key; future candidates may have seen it, so the suite needs a stated refresh/versioning policy, to be decided in Stage 2; (2) an AI-authored, AI-falsified suite has weaker independence than one grounded in real history, which is why AC3 requires different instances and human acceptance; (3) M2 grading remains human judgment, by design.

## Status

- **State:** Approved
- **Established by:** Claude Sonnet 5.5 (Anthropic), under Architect role
- **Approved by:** Scott Wofford, Change Owner and Architect, 2026-10-06
- **Date:** 2026-10-06
- **Class:** T3
- **Spec Confidence at intake:** Clear
- **Re-evaluated to Clear by:** N/A — Clear at intake via Spike (`spec/SPIKE-REFERENCE-QUALIFICATION-SUITE-PROPOSAL.md`)

Changes outside declared scope are re-declared here or split into a separate Task Contract — never absorbed silently.
