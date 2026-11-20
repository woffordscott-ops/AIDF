---
owner: framework-maintainer
load_when: implementing or reviewing the review stop rule, record-text findings, human-time timestamps and pending-criterion changes
max_length: 1 screen
last_verified: 2026-10-30
---

# Task Contract: Review Stop Rule, Record-Text Findings, Human-Time Timestamps, Pending Criterion

`core/01-lifecycle.md` §4. Class T2 (see Classification); Approved status required from a human under Architect authority before implementation begins. **Status: Approved.**

Source: items 1, 2, 3 and 7 of `strategy/AIDF-REVIEW-EFFICIENCY-PROPOSAL.md`, approved by the Change Owner on 2026-10-30 as one change. Evidence for the rules: `verification/review-finding-table.md` (hand labels not yet spot-checked by the Change Owner).

## Part A: Minimal

- **Intended outcome:** Cut review rounds that add no assurance, and make the cost to the human measurable, without lowering any control on code, tests or security posture. In 64 of 101 recorded rounds the two-round cap was already passed, and in round 3 and later 42 percent of hand-labelled blocking findings were record text (24 percent in rounds 1 and 2).
- **Acceptance criteria:**
  1. **Stop rule.** `core/05-review.md` §5 and `templates/task-contract.md` define a declared review budget (default T2: two Verifier rounds; T3: two Verifier and two Security rounds). When the last budgeted round is not PASS, the Change Owner chooses and records one of: merge with listed advisories; accept a named residual; split the change; stop; one more round. One more round is allowed only if the last round found a rank-1 finding in code, tests or security posture. §5 states that at T3 a Change Owner may accept a named, scoped residual with the reason; it never waives required evidence and never accepts a rank-1 behaviour defect that has a reproducing case.
  2. **Record text cannot block.** `core/05-review.md` §4 states: a finding whose only subject is narrative, a count or history in an evidence pack or dispositions file is advisory, fixed by an append to the dispositions file with no new round. Exceptions that still block: the sentence overstates a guarantee a consumer relies on; a required artifact, rehearsal, acceptance or SHA/digest is missing or wrong; the record contradicts the code or tests it describes.
  3. **Pack facts are checked, not argued.** `verification/pack_facts.py` (a new file) fails when a committed-blob hash, a commit SHA or a named test cited by an evidence pack does not exist or does not match. `templates/evidence-pack.md` says these facts are verified by that check and need no reviewer pass.
  4. **Human time.** `templates/approval-request.md` gains `Requested (UTC)`, `Answered (UTC)` and `Active minutes (manual)`; `metrics/definitions.md` defines the metric as the upper bound (sum of answered minus requested) with the manual field beside it; `verification/human_time.py` reads those lines from a dispositions file and prints the count, the upper bound and the manual sum.
  5. **Protected checker unchanged.** `verification/aidf_check.py` is attested by the protected policy repository and is not changed by this change; the pending-criterion status (`pending_outcome`, `--final`, `outcome_record_criteria`) is deferred to a later cross-repository T3 change. (Amended 2026-10-30 after the pipeline job `aidf-governance` failed with `attested record hash mismatch`; the Change Owner approved the split.)
  6. Tests: each rule above has a test that fails against the previous text or code (counterfactual). `CHANGELOG.md` records the change as `migration-required` for contracts without a budget, which keep today's two-round rule.
  7. No change to `KERNEL.md`, trip-wires, `core/02-authority.md`, or any section of `core/05-review.md` other than 4, 5 and the budget sentence of 2.
  8. Outcome records (core/05-review.md section 6): the review report patterns are verification/review-efficiency-core-verifier-report*.md; the dispositions file is verification/review-efficiency-core-verifier-dispositions.md. This criterion only declares the outcome-record paths. The merger runs verification/review_head_binding_evidence.py compare() from the reviewed head of the last round to the final head and records its output in the dispositions; the evidence pack does not change after the last review. (Added in the extra round that the Change Owner allowed on 2026-10-30, after Verifier round 2 found that the record-text append needs outcome records.)

  Spec Confidence: Clear at intake (proposal approved; item 3 of this list is the Implementer's reduction of "generate the pack" to "verify the pack's facts", flagged for the Change Owner below).

- **Declared scope:** `core/05-review.md`; `templates/task-contract.md`, `templates/evidence-pack.md`, `templates/approval-request.md`; `metrics/definitions.md`; `verification/aidf_check.py`; `verification/human_time.py`; `verification/review_rule_replay.py` (the replay of criterion 6); their tests under `verification/tests/`; `CHANGELOG.md`; this contract; `spec/adr/review-stop-rule.md`; `verification/review-efficiency-core-task-contract.json`; `verification/review-efficiency-core-evidence-pack.json`; `verification/review-efficiency-core-verifier-dispositions.md`; the Verifier reports `verification/review-efficiency-core-verifier-report*.md`. **Excluded:** `KERNEL.md`, `core/02-authority.md`, trip-wire policy, `profiles/**`, relay automation (item 5), adoption fixes (item 6), the trip-wire 1 carve-out (item 4).

## Part B: Plan

- **Approach:** Edit §§2, 4, 5 of `core/05-review.md` and the three templates; add `verification/pack_facts.py` with tests; add `human_time.py`; one ADR recording the stop rule; CHANGELOG entry. The change dogfoods its own rule: budget below.
- **Invariants touched:** `core/05-review.md` §§4 and 5, and the stable surface "required review ordering and provenance" (`spec/PHASE6-COMPATIBILITY-POLICY.md`). The Verifier-before-Security ordering, distinct instances, rank-1 and rank-2 blocking for code, tests and security posture, and final-head binding are unchanged.
- **Evidence strategy:** Counterfactual per criterion: a record-text-only finding is shown blocking under the old text and advisory under the new, while a missing-artifact finding still blocks; `pack-facts` fails on a wrong hash, a nonexistent SHA and a nonexistent test, and passes on the right ones; `pending_outcome` is accepted before and rejected with `--final` and for an unlisted criterion; `human_time.py` on a fixture with known timestamps. Replay on the 143 labelled findings (`verification/review-finding-labels.csv`): count how many blocking findings the new text would have made advisory, and report the result without adjusting the text to fit it.
- **Review budget (this change):** one pre-check by the Implementer, two Verifier rounds. A third round needs the Change Owner's recorded reason and a rank-1 finding in code, tests or security posture. Accepted limits stated before review: labels are the Implementer's and unchecked; the stop rule is tested on documents and counterfactual fixtures, not on a future change; `verification/pack_facts.py` covers hashes, SHAs and named tests only.
- **Recovery / reversal approach:** `git revert` of the change restores today's rules; contracts without a budget keep the two-round rule, so no existing record is invalidated.

## Classification

Proposed **T2**: it changes review rules with project-wide reach, and no kernel trip-wire fires. Item 2 narrows which findings may block, and `spec/PHASE6-COMPATIBILITY-POLICY.md` says a change that weakens a mandatory control is governed as an invariant change. The change does not alter blocking on code, tests or security posture, and the exceptions in criterion 2 keep missing and wrong required artifacts blocking, but the Architect may judge it a weakening; if so, escalate to **T3** (free). Review at T2: a Verifier distinct from the Implementer; at T3 also a Security Reviewer.

## Decisions for the Change Owner

1. Approve as T2 with the review budget above, or classify T3?
2. Accept the reduction of criterion 3 from "generate the pack" to "verify the pack's facts"? Generation needs a command runner and a results format; verification catches the same false-hash and wrong-SHA sentences with less code.
3. Spot-check the labels (about 20 rows) before this change relies on the replay, or accept the replay as indicative only?

## Status

- **State:** Approved
- **Established by:** Claude Sonnet 5.5 (Anthropic), under Implementer role, 2026-10-30
- **Approved by:** Scott Wofford, Change Owner and Architect, 2026-10-30 ("approve here and build on the same branch"). He answered none of the three decisions separately, so the Implementer records the approval as for the contract as written: T2 with the stated budget, criterion 3 as "verify the pack's facts", and the replay as indicative only (labels unchecked). Any of these can be reopened.
- **Amendments approved by:** Scott Wofford, Change Owner and Architect, 2026-10-30T22:51:53Z: "ammended contract is approved and the other 2 items are acknowledged." The amendments are the Implementer's clarifications at the end of this file, the wording of criterion 3, criterion 8 (a declaration of the outcome-record paths) and the two-round cap on a declared budget.
- **Class:** T2 (as proposed; escalation to T3 remains free)
- **Spec Confidence at intake:** Clear

## Clarifications by the Implementer, 2026-10-30 (for the Change Owner's acknowledgement)

Found by Verifier round 1 (see `verification/review-efficiency-core-verifier-dispositions.md`). They do not change what was approved.

- Criterion 3 as built checks the committed-blob hash of a `security_evidence.artifact` that is a repository path, that a cited hexadecimal string resolves to a git object, and that a cited `test_` name is defined. It does not check other cited report hashes.
- Criterion 6: the CHANGELOG, the ADR and the JSON contract say `migration-required` for contracts that adopt a budget; a contract without a budget is unchanged. The sentence "for contracts without a budget" in criterion 6 above is superseded by that.
- The replay reads `verification/review-finding-table.csv`, whose `type_checked` column is filled from `verification/review-finding-labels.csv`. The labelled findings are those blocking by label or named in a round's outcome.
- A declared budget is at most two rounds per layer (a tightening that keeps the cap of locked V1.2.2 section 11.3).
- Criterion 3 in the JSON contract now reads "git object" and covers an artifact written as a file name followed by prose, which is how two committed packs write it (Verifier round 2, V1-02 and V2-03).
- Criterion 8 is new and only declares the outcome-record paths. The evidence pack carries it as `passed` (the declaration is checked before the review); the comparison from the last reviewed head to the final head is run by the merger and recorded in the dispositions. A first version made it `pending_outcome`, which Verifier round 3 showed can never become `passed` once outcome-record binding applies (V3-01); the JSON contract no longer lists `outcome_record_criteria`.
- **Split (2026-10-30, after the pipeline failure).** Criterion 3 now names `verification/pack_facts.py`; criterion 5 now states that `verification/aidf_check.py` is unchanged and defers the pending-criterion status; `verification/aidf_check.py` is out of the declared scope. The sentences above that still describe `aidf_check.py` changes (the Approach, criteria 3 and 5 as first written) are superseded by this clarification and the Task Contract JSON.
