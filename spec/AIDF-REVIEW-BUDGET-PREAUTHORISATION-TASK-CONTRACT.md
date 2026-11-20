---
owner: framework-maintainer
load_when: deciding or implementing how the Change Owner authorises review rounds beyond the two-round cap in advance
max_length: 1 screen
last_verified: 2026-11-04
---

# Task Contract: Pre-authorised Review Rounds (the "four rounds" standard)

`core/01-lifecycle.md` §4. Class T2 (see Classification); Approved status required from a human under Architect authority before implementation begins. **Status: Approved by the Change Owner on 2026-11-04 (see Status).**

## Why (the evidence)

1. **The Change Owner's decision.** On 2026-11-02, during `review-run-review`, Scott Wofford wrote: "I can authorize up to 2 more rounds. Lets make 4 rounds our standard going forward. I think 2 rounds is too narrow." The dispositions of that change record that the Implementer did not apply this to any contract text or to `core/05-review.md`, because a change to that document was needed and was proposed separately. This is that change.
2. **The cap is real and has been passed routinely.** `strategy/AIDF-REVIEW-EFFICIENCY-PROPOSAL.md` and `spec/adr/review-stop-rule.md` record that 8 of 14 reviewed changes went past two rounds and 64 of 101 reports were rounds beyond it, each by a one-line authorization. `review-run-review` took seven Verifier rounds and five security-focused rounds. Security rounds 3 to 5 each blocked on a defect in the previous round's fix, each smaller than the one before; Verifier round 5 found R5-B1 (a rollback that deleted a committed report on Windows Ctrl-C), a real defect a stop at round 2 would have shipped.
3. **The locked spec limits how this can be written.** `spec/AIDF-v1.2.2-design-proposal.md` §11.3 says: "[REQ] Hard cap of two review rounds, then a human decides." The document is locked and is not edited. `core/05-review.md` §2 and the ADR `spec/adr/review-stop-rule.md` keep a declared budget at two rounds per layer for that reason. A default of four per layer would contradict the [REQ].
4. **What fits.** §11.3 requires a human decision after two rounds. Today that decision is taken one round at a time, after each round, as a one-line authorization. The Change Owner can instead take the decision in advance, in the approved Task Contract, for a named number of further rounds, each still conditioned on what the previous round found. The cap stays two; the human still decides; what changes is when and how many times he is asked.

## Part A: Minimal

- **Intended outcome:** The Change Owner can record once, in the approved Task Contract, that up to two further rounds per layer (four in all) are authorised after the cap, so a change whose rounds keep finding real defects does not stop for a fresh authorization each time, and a change whose rounds stop finding them still stops at the first round that passes. No control on code, tests or security posture is weakened; the two-round cap, the default budget and the evidence condition for a further round are unchanged.
- **Acceptance criteria:**
  1. **Pre-authorisation in the budget.** `core/05-review.md` §2 "Review budget" gains a paragraph: the Change Owner may record in the approved Task Contract a pre-authorisation of the section 5 decision for up to two further rounds per layer, naming the layer and the number. It is a recorded human decision made in advance, not a larger budget: the default and the declared-budget maximum stay at two rounds per layer, and a contract without the pre-authorisation is unchanged.
  2. **The condition and the record.** `core/05-review.md` §5 gains: a pre-authorised round starts only if the round before it found a rank-1 finding in code, tests or security posture; the dispositions record, before the round starts, the pre-authorisation (contract and criterion), the finding that satisfies the condition and the date. A round before which no such finding exists is not started and the menu of section 5 applies. After the last pre-authorised round the menu repeats only on the same condition, as it does today after an extra round. A pre-authorisation covers no more than two rounds per layer and does not carry to another layer or to another change, and a rebase or a merge-base refresh does not end it.
  3. **Template.** `templates/task-contract.md`, in the "Review budget" line, gains the optional pre-authorisation, in one sentence, and says the cap and the default are unchanged.
  4. **ADR.** `spec/adr/review-stop-rule.md` gains Decision 4 (the pre-authorisation), the reading of locked §11.3 on which it rests (a human decision taken in advance, conditioned on a later finding, is still a human decision after two rounds), and two rejected alternatives: a default of four rounds per layer (contradicts §11.3) and leaving the standard as a per-change one-line authorization (the history shows it is routinely passed). The ADR records the Change Owner's 2026-11-02 words as the source of the decision and its approval of this change as its approval.
  5. **Changelog.** `CHANGELOG.md` records the change under Changed, as opt-in: a contract without a pre-authorisation keeps today's rules.
  6. **Tests.** Presence tests in `verification/tests/test_review_efficiency_core.py` that fail against the previous text: the pre-authorisation paragraph and its two-round limit per layer, the rank-1 condition and the record before the round in §5, the template sentence, and Decision 4 of the ADR. A test shows the cap did not move: §2 still says the default is two rounds per layer and a declared budget is at most two rounds per layer, and §5 still says a contract without a declared budget has a budget of two rounds. The suite, the preflight and the export scan pass.
  7. **Scope.** No change to `spec/AIDF-v1.2.2-design-proposal.md`, `profiles/qualification-eval/suite-v1.json` or `suite-v1.1.json` (their case M3-ROUND-01 tests the two-round cap, which does not move), `verification/aidf_check.py`, `verification/preflight.py`, `verification/run_review.py`, `.gitlab-ci.yml`, `KERNEL.md`, trip-wires or `core/02-authority.md`.
  8. Outcome records (core/05-review.md section 6): the review report patterns are `verification/review-budget-preauthorisation-verifier-report*.md`; the dispositions file is `verification/review-budget-preauthorisation-verifier-dispositions.md`.

  Spec Confidence: Clear at intake.

- **Declared scope:** `core/05-review.md`, `templates/task-contract.md`, `spec/adr/review-stop-rule.md`, `CHANGELOG.md`, `verification/tests/test_review_efficiency_core.py`, `verification/public-export-manifest.json` and `verification/tests/test_export_public_tree.py` (the review reports name local paths and are excluded from the public export), this contract, `verification/review-budget-preauthorisation-task-contract.json`, `verification/review-budget-preauthorisation-evidence-pack.json`, `verification/review-budget-preauthorisation-verifier-dispositions.md`, and the reports `verification/review-budget-preauthorisation-verifier-report*.md`. **Excluded:** everything named in criterion 7.

## Part B: Plan

- **Approach:** One paragraph in §2, two sentences in §5, one sentence in the template, Decision 4 and two alternatives in the ADR, a changelog entry, presence tests. No tool reads the budget, so no tool changes.
- **Invariants touched:** the two-round cap of locked §11.3 (kept), the rank-1 condition for a further round (kept), Verifier-before-Security ordering and distinct instances (not edited).
- **Evidence strategy:** presence tests as above (they show the rule is written, not that it is right; the pack says so); the rule is walked through the lifecycle of this change's own review, and through the lifecycle of `review-run-review` as a replay: with the pre-authorisation, which of its rounds 3 to 7 would have started without a fresh authorization and which would not have started (a round after a round with no rank-1 finding).
- **Review budget (this change):** one preflight run and two Verifier rounds. A third round needs the Change Owner's recorded reason and a rank-1 finding in code, tests or security posture. Accepted limits stated before review: the text is prose and has no behaviour to test; the reading of locked §11.3 is the Implementer's and the Change Owner's to accept (Decision 2 below).
- **Protected files touched:** none.
- **Recovery / reversal approach:** `git revert`; no record depends on the new paragraph.

## Classification

Proposed **T2**: it edits a core rule document, a template and an ADR; no trip-wire. Like `review-efficiency-core`, which made the budget itself.

## Decisions for the Change Owner

1. Approve as T2 with the review budget above? **Answered 2026-11-04: approved as drafted.**
2. Accept the reading of locked §11.3 on which this rests: "then a human decides" is met by a decision the Change Owner records in advance in the approved Task Contract, conditioned on a rank-1 finding in code, tests or security posture in the round before? If not, the alternatives are a default of four (a departure from the locked spec, disclosed in `IMPLEMENTATION-STATUS.md`, with M3-ROUND-01 revised) or no change. **Answered 2026-11-04: the Change Owner chose the pre-authorised decision, and approved the contract as drafted.**
3. Is the pre-authorisation per layer, up to two further rounds each (so four Verifier and four Security rounds at T3), what you meant? The draft says yes. **Answered 2026-11-04: approved as drafted.**

## Status

- **State:** Approved
- **Established by** (author): Claude Sonnet 5.5 (Anthropic), under Implementer role, 2026-11-04
- **Approved by** (human, T2/T3 only — role: Architect): Scott Wofford (Change Owner and Architect), 2026-11-04, by his message "approved as drafted, go ahead", given in answer to the three decisions above. The Implementer's reading is that this answers all three, including the reading of locked section 11.3. Scott may correct this reading.
- **Date:** 2026-11-04
- **Amendments approved by:** Scott Wofford (Change Owner and Architect), 2026-11-04, by his message "approved, make both amendments and prepare round 2", given after Verifier round 1 of this change: (1) the declared scope gains `verification/public-export-manifest.json` and `verification/tests/test_export_public_tree.py`; (2) criterion 2 drops the undefined words "another head lineage" for "does not carry to another layer or to another change, and a rebase or a merge-base refresh does not end it". The reason for both is in `verification/review-budget-preauthorisation-verifier-dispositions.md`, section "Verifier round 1".
- **Class:** T2
- **Spec Confidence at intake:** Clear
