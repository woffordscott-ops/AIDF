---
owner: framework-maintainer
load_when: implementing or reviewing the review head-binding amendment to core/05-review.md
max_length: 1 screen
last_verified: 2026-10-12
---

# Task Contract — Review Head-Binding for Outcome Records

`core/01-lifecycle.md` §4. Class T2 (see Classification); Approved status required from a human under Architect authority before implementation begins. **Status: Approved.**

## Part A — Minimal

- **Intended outcome:** Make `core/05-review.md` §§6–7 satisfiable when a review report, and the fields that record a passed review, must be committed after the review they record — without weakening final-head binding for anything a reviewer judges. Today a report committed on the branch moves the head, so a review can never bind the head that carries its own report, and `security_evidence` can never be filled in a reviewed commit. The T3 chain for `reference-suite-stage1-base-app` ran 17 Verifier and 6 Security rounds partly because of this (friction record: that change's dispositions file, Security round 6 report).
- **Acceptance criteria:**
  1. `core/05-review.md` defines **review-outcome records** by closed list: (a) a review report file added by itself, as a regular non-empty text file at a declared path; (b) the `security_evidence` object of the evidence pack (status, artifact, artifact_sha256, coverage_boundary) and no other field, naming a report added in the same range and its hash; (c) append-only additions at the end of the dispositions file; (d) addition to the Task Contract's declared scope list of the paths of added reports. Nothing else is an outcome record.
  2. It defines the **reviewed content head** R (the head the review examined) and states that a review bound to R covers the final head H if and only if a deterministic comparison of R and H shows only outcome records, with every non-listed path and every change beyond a listed class counting as a difference. Any other difference invalidates the review, as an unexplained diff does today (§6).
  3. The comparison is written as commands a protected gate or the merger can run (`git diff-tree --raw`, blob reads, a strict JSON compare of the pack and contract), with a reference implementation `compare()` in `verification/review_head_binding_evidence.py`; a protected checker for it is **out of scope** and recorded as a follow-up.
  4. The mechanism is **opt-in per Task Contract**: it applies only when an acceptance criterion of the approved contract declares the outcome-record paths. A contract without that criterion keeps today's rule. A pack-sentence correction, a code or test change, a contract-content change, or any edit to an existing dispositions line is not an outcome record and requires re-review (§6).
  5. `templates/review-findings.md`, `templates/evidence-pack.md`, `templates/task-contract.md` and `CHANGELOG.md` gain the matching fields. Also in this change: reviewers report all findings in one pass and list routes tried; an enumerating control (scan, blocklist) is accepted as evidence only if it is closed or backed by a runtime property; a confirmation round after a fix is a valid re-review (all as drafted on `claude/aidf-review-lessons`).
  6. No change to `KERNEL.md`, `core/02-authority.md`, trip-wires, or any section of `core/05-review.md` other than 2, 6 and 7.

  Spec Confidence: Clear at intake (friction evidence in the reference-suite chain; Security round 6 stated the unmet binding and its needed closure).

- **Declared scope:** `core/05-review.md`; `templates/review-findings.md`, `templates/evidence-pack.md`, `templates/task-contract.md`; `CHANGELOG.md`; this contract; `spec/adr/review-outcome-records.md`; `verification/review_head_binding_evidence.py`; `verification/review-head-binding-task-contract.json`; `verification/review-head-binding-evidence-pack.json`; `verification/review-head-binding-verifier-dispositions.md`; the Verifier reports `verification/review-head-binding-verifier-report.md`, `verification/review-head-binding-verifier-report-round2.md`, `verification/review-head-binding-verifier-report-round3.md` and `verification/review-head-binding-verifier-report-round4.md`. **Excluded:** any checker implementation, `KERNEL.md`, `core/02-authority.md`, `profiles/**`, and every file of the reference-app change.

## Part B — Plan

- **Approach:** Edit `core/05-review.md` §§2, 6, 7 and the three templates as drafted, tightening the draft to criteria 1–4; add the opt-in field to the task-contract template; add a CHANGELOG entry classified `migration-required` (previous accepted path remains valid for every contract that does not opt in). Version bump left to the maintainer.
- **Invariants touched:** `core/05-review.md` §§6–7 and the stable surface "required review ordering and provenance" (`spec/PHASE6-COMPATIBILITY-POLICY.md`). `core/02-authority.md` §3 (separation of duties) is not modified; the Verifier-before-Security ordering and distinct instances are unchanged.
- **Evidence strategy:** Counterfactual. A throwaway script (committed under `verification/` as evidence, not a gate) builds a repository, applies the comparison commands, and shows: the reference-suite's real shape (code → pack → report-only child → outcome-field fill) passes; and each of these fails — a code change, a changed existing pack sentence, a deleted dispositions line, an extra file, a changed `security_evidence` field outside the four, a report file that already existed. The comparison must be shown to fail for each, not only to pass.
- **Recovery / reversal approach:** Documents, templates and one evidence script; `git revert` restores today's rule. No consumer is affected unless a Task Contract opts in.

## Classification

Proposed **T2**: it changes a contract (required review ordering and provenance) with project-wide blast radius, and no kernel trip-wire fires. `spec/PHASE6-COMPATIBILITY-POLICY.md` says a change that weakens a mandatory control is governed as an invariant change. This change adds a path and does not alter the default, but if the Architect judges it a weakening, escalate to **T3** (escalation is free). Review required at T2: a Verifier distinct from the Implementer; at T3 also a Security Reviewer.

## Status

- **State:** Approved
- **Established by:** Claude Sonnet 5.5 (Anthropic), under Implementer role, 2026-10-12
- **Approved by:** Scott Wofford, Change Owner and Architect, 2026-10-12 ("Approved as T2, implement it, and run the parallel track")
- **Class:** T2 (confirmed by the Architect on approval)
- **Spec Confidence at intake:** Clear
