---
owner: framework-maintainer
load_when: deciding or implementing the approver's opening of the T2/T3 Task Contract template
max_length: 1 screen
last_verified: 2026-11-05
---

# Task Contract: an approver's opening for the T2/T3 Task Contract template

`core/01-lifecycle.md` §4. Class T2 (see Classification); Approved status required from a human under Architect authority before implementation begins. **Status: Approved by the Change Owner on 2026-11-05 (see Status).** It follows the reading test of the spec-tool bake-off (`verification/spec-tool-bakeoff-stages-0-1-verifier-dispositions.md`, on branch `codex/spec-tool-bakeoff-contract` until that change is merged).

## Why (the evidence)

1. **The Change Owner rejected the AIDF-native contract in 3 minutes, approved a tool's planning set in 5, and approved a rewrite with a structured opening in 4.** The same agent, the same change and the same content: the original contract had the content (its first criterion states that a caller with no parameters stops getting all 250 items) but opened with status boilerplate and a dense outcome, so he wrote "the problem isn't initially clear. I had to infer what we are fixing". Given an opening of Read this first, Problem, Why it matters, The change (breaking changes marked), Technical details and What you need to decide, he approved it at once, noticed the breaking change, and chose it "every time" and for everyday use over all five sets read. A shorter 12-line opening of the agent's own design was judged "partly" clear and he asked for more on the problem.
2. **Two limits of that evidence.** One reader, one change, one agent run per variant. The longer structure ran 3,207 words (about three times the original), and `core/01-lifecycle.md` §4 says a T2/T3 contract is one screen. Decision 1 and criterion 6 deal with both.

## Part A: Minimal

- **Intended outcome:** A T2/T3 Task Contract opens with a short section written for the human who must approve it, so that the approver can find the problem, the change and the decision without reading the formal parts first. The formal parts stay the authority, and T0/T1 contracts do not change.
- **Acceptance criteria:**
  1. **The opening.** `templates/task-contract.md` gains, for T2/T3 only and placed before Part A, an approver's opening with these headings in this order: Read this first, Problem, Why it matters, The change, Technical details, What you need to decide. Each has a one-line guide and a length limit (decision 1: Read this first up to 6 lines; Problem up to 5; Why it matters up to 3 sentences; The change up to 10 lines; Technical details as long as the change needs; What you need to decide up to 15 lines).
  2. **Rules for it.** The template says: the opening is for a reader who has not seen the request; a behaviour change that a caller or consumer must react to is marked BREAKING; the opening is a summary and Part A and Part B control, so the opening adds no requirement, scope or criterion that Part A lacks; the author writes it and the approver's decision is on the whole contract.
  3. **T0/T1 unchanged.** The template says the opening does not apply to T0/T1, and the three-line Part A rule for those classes is untouched.
  4. **The lifecycle.** `core/01-lifecycle.md` §4, the Form row for T2/T3, states the new form (decision 1). No other sentence of the lifecycle changes.
  5. **The existing checks still hold.** The new template text does not use the words of `RULE_VOCABULARY` in `verification/tests/test_review_efficiency_core.py`, so its pinned blocks need no change; every existing test passes unchanged. If a word cannot be avoided, the pin is updated in this change and the reason is recorded.
  6. **Presence tests.** A new test file asserts that the template carries the six headings in order, the T2/T3-only statement, the BREAKING definition and the authority sentence, and that the lifecycle row carries the new form; each test fails on the current template.
  7. **Reading validation before merge.** The AIDF-native arm of `verification/spec_tool_probe.py` writes a contract for two further changes of different kinds, using the template text as proposed (one internal change with no caller impact, one change to process or documents), and the Change Owner reads each with the reading-test form. The results are recorded in the dispositions. If he does not approve either as readable, the template is not merged and the opening is revised.
  8. **Scope.** No change to the measurement harness (`verification/aidf_measurement.py`, `verification/aidf-measurement-round*`), `verification/aidf_check.py`, the preflight, the qualification suite or any approved contract. The harness copies `templates/task-contract.md` into Arm A workspaces, so a later measurement run would use the new text; the dispositions record that, and the committed measurements are not affected.
  9. **Outcome records** (core/05-review.md section 6): the review report patterns are `verification/task-contract-opening-verifier-report*.md`; the dispositions file is `verification/task-contract-opening-verifier-dispositions.md`. This criterion only declares the outcome-record paths.

  Spec Confidence: Partial until decision 1 (the length) was answered; Clear after, on 2026-11-05.

- **Declared scope:** `templates/task-contract.md`, `core/01-lifecycle.md` (the Form row of §4 only), `verification/tests/test_task_contract_template.py`, `verification/tests/test_review_efficiency_core.py` (only if criterion 5 needs a pin), `CHANGELOG.md`, `verification/task-contract-opening-evidence/**` (the two validation contracts and forms), `spec/AIDF-TASK-CONTRACT-OPENING-TASK-CONTRACT.md`, `verification/task-contract-opening-task-contract.json`, `verification/task-contract-opening-evidence-pack.json`, `verification/task-contract-opening-verifier-dispositions.md`, and the reports `verification/task-contract-opening-verifier-report*.md`. **Excluded:** everything named in criterion 8.

## Part B: Plan

- **Approach:** Write the opening as a block of the template between the front matter and Part A, marked T2/T3, with the guide lines and the rules of criterion 2; edit the one lifecycle row; add presence tests. Draft after the stage 0 and 1 change is merged, because criterion 7 uses its probe. Validate on two further changes, then ask the Change Owner.
- **Invariants touched:** the form of the T2/T3 Task Contract (`core/01-lifecycle.md` §4); the template that the measurement harness hands to Arm A; the pinned review-rule blocks of the template (unchanged by criterion 5).
- **Evidence strategy:** presence tests that fail on the current template; the two validation readings; mutation of each asserted phrase in a scratch copy; the existing suite and the preflight `--ci-like`.
- **Protected files touched:** to be confirmed with the preflight before approval (whether `templates/task-contract.md` is attested); expected `none`.
- **Recovery / reversal approach:** `git revert`; contracts already written keep their form, since the opening is an addition.
- **Review budget (this change):** one preflight run and two Verifier rounds; no security layer (no trip-wire). Accepted limits stated before review: the template cannot make an author write a good opening, only say what one holds; no checker reads the opening (a heading check would be a new rule and is not in this change); the evidence is one reader and three changes.

## Classification

Proposed **T2**: it changes the form of the contract that all T2/T3 work follows (an interface of the process) and touches `core/`. No trip-wire applies.

## Decisions for the Change Owner

1. **Length.** `core/01-lifecycle.md` says a T2/T3 contract is one screen, and the opening you preferred ran about three times longer than that. Options: (a) [recommended] the contract stays one screen and the opening is bounded separately (Read this first up to 6 lines; Problem up to 5; Why it matters up to 3 sentences; The change up to 10 lines; Technical details as long as the change needs; What you need to decide up to 15 lines), so the lifecycle row reads "an approver's opening, then the contract of one screen"; (b) the whole file stays one screen, which the evidence did not test; (c) no limits, only the order.
2. **How much validation.** (a) [recommended] two more changes, one internal and one process or documents, read by you with the same form; (b) one more; (c) none, merge on the present evidence (not recommended: one reader, one change).
3. **Who may waive the opening.** (a) [recommended] nobody: it is part of the T2/T3 form; (b) the author may shorten it to the Read this first section for a change the approver can read in one minute.
4. **Review layers:** Verifier rounds only [recommended], or add the security layer.

## Status

- **State:** Approved
- **Established by** (author): Claude Sonnet 5.5 (Anthropic), under Implementer role, 2026-11-05
- **Approved by** (human, T2/T3 only — role: Architect): Scott Wofford (Change Owner and Architect), 2026-11-05, by his message "I accept your recommendations", given in answer to the four decisions above, each with the recommendation as drafted: (1) the contract stays one screen and the opening is bounded separately, with the limits in criterion 1, so that the Form row of the lifecycle reads "an approver's opening, then one screen"; (2) validation on two further changes, one internal and one about process or documents, read by the Change Owner with the same form; (3) nobody waives the opening; (4) Verifier rounds only.
- **Date:** 2026-11-05
- **Class:** T2
- **Spec Confidence at intake:** Partial (decision 1)
- **Spec Confidence now:** Clear. Decision 1 was answered as drafted.
