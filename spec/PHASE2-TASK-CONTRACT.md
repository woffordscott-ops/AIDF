---
owner: framework-maintainer
load_when: reviewing or approving the proposed Phase 2 scope
max_length: 2 pages
last_verified: 2026-08-20
---

# Phase 2 Task Contract — Verification Spine

**Status:** Approved by the Change Owner on 2026-08-19; reclassified and re-approved as T3 on 2026-08-19 after independent verification identified the CI-infrastructure trip-wire. The Change Owner approved the pre-merge active-policy recovery amendment on 2026-08-19 after clean-room review exposed a circular post-merge requirement, and approved the immutable-policy fail-closed recovery clarification on 2026-08-20. Implementation is authorized only within this contract and the approved implementation brief.

## Part A — Minimal

- **Intended outcome:** Implement the locked V1.2.2 Phase 2 Verification Spine as reusable, mechanically testable framework controls, with honest handling of repositories that have weak or absent product tests.
- **Acceptance criteria:** All deliverables and checks in the implementation brief exist; every mechanical control has positive and negative fixtures; GitLab independently prevents bypass or removal of the selected required governance job and executes enforcement logic from an immutable trusted source; a failing governance case blocks merge and its correction passes; the actively pinned Phase 2 external policy is re-pinned to the prior protected immutable policy and then reapplied before merge through the required pipeline. When immutable attestations or approved dependencies make the prior policy incompatible with the newer branch state, successful rollback evidence is an observable fail-closed rejection—not a green pipeline. Successful reapplication requires restoration of the current mechanical and security checks. No compatible-green prior-policy result is required or claimed; a fresh clean-room Verifier and distinct Security Reviewer pass the resulting change; no control overclaims what it proves; `Spec Confidence: Clear at intake` based on locked §17 Phase 2 and this approved boundary.
- **Declared scope:** this Task Contract and its approved implementation brief; `core/04-verification.md`; `templates/evidence-pack.md`; `templates/exemption.md`; `metrics/definitions.md`; `metrics/classification-audit.md`; reusable CI/checker files, security/review/evidence records, and their fixtures; minimal README/status references; a thin, non-merged pilot integration branch if separately authorized.

## Part B — Plan

- **Approach:** Write verification semantics first; define machine-readable Task Contract/evidence inputs narrowly; implement and fixture-test one CI control at a time; integrate on GitLab only after local falsification tests pass; then rehearse enforcement and revert.
- **Invariants touched:** locked Layer 1 V1.2.2 is authoritative and unmodified; evidence jurisdiction remains non-overlapping; class requirements remain T0 E0–E2, T1 E0–E3, T2 E0–E6, T3 E0–E7 plus recovery and security evidence; assertion/coverage delta is only an inspection trigger; exemptions remain unavailable at T0/T3 and expiring at T1/T2; agents have no production credentials or direct production access.
- **Evidence strategy:** E0–E7 plus recovery and security evidence; controlled mutation/reversion tests for checker behavior; known-good/known-bad fixtures; baseline and contract comparisons where behavior is non-functional; end-to-end merge-request pipelines proving each required control and required-job integrity can block; unmistakably fake secret canaries; exact dependency-reference fixtures; fresh clean-room verification; separate security review; and a recorded revert/reapply rehearsal.
- **Recovery/reversal approach:** The operation is classified **reversible**. Phase 2 changes remain branch-isolated and independently revertible. Before merge, activate the hardened external policy at an immutable commit, re-pin the consumer to the prior protected immutable policy through the required pipeline, and record its observed behavior. If that policy rejects the newer branch because its trusted-record attestations or approved dependencies differ, record the rejection as expected fail-closed rollback behavior. Reapply the current immutable pin and require its mechanical and security jobs to pass. Record the rollback and reapplication artifacts as E7. After integration, ordinary Git revert remains the working repository recovery path but is not used to satisfy pre-merge T3 acceptance.

## Status

- **State:** Approved
- **Established by:** AI assistant acting as Implementer/analyst; approval authority not assumed
- **Approved by:** Scott Wofford, Change Owner
- **Date:** 2026-08-20 (latest approved amendment; original approval 2026-08-19)
- **Class:** T3 — `.gitlab-ci.yml` changes exercise the locked infrastructure trip-wire
- **Trip-wire:** infrastructure / CI enforcement configuration
- **T3 merge approval:** explicit Change Owner approval required after evidence and separated reviews, before integration
- **Separated review:** fresh clean-room Verifier plus distinct Security Reviewer required
- **Spec Confidence at intake:** Clear
- **Re-evaluated to Clear by:** N/A — Clear at intake; environment unknowns are explicit prerequisites, not specification ambiguity

Changes outside declared scope require a revised Task Contract or a separate contract. Repository creation, GitLab project administration, runner installation, and pilot product changes are not silently included.
