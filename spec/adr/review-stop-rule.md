---
owner: framework-maintainer
load_when: changing the review budget, the stop rule, which findings may block, or T3 residual acceptance in core/05-review.md
max_length: 2 pages
last_verified: 2026-11-04
---

# ADR: Review Budget, Stop Rule and Record-Text Findings

- **Status:** Accepted
- **Decision owner:** Scott Wofford, Architect and Change Owner
- **Decision date:** 2026-10-30 (Decision 4 added 2026-11-04)
- **Context:** `core/05-review.md` section 5 sets two review rounds as the maximum, but 8 of 14 reviewed changes passed it and 64 of 101 recorded rounds were beyond it, each by a one-line authorization (`verification/review-finding-table.md`). Section 4 lets any rank-2 finding block, and a sentence of an evidence pack that contradicts a record is rank 2. In rounds 3 and later, 19 of 45 hand-labelled findings (blocking by label or named in the round's outcome) were record text, against 20 of 85 in rounds 1 and 2; in the base-app change, 15 of 22 late findings were record text. Section 5 also limited accepted risk to non-trip-wire residuals, while the public export change (a trip-wire 4 change) had its residuals accepted by the Change Owner after five Security rounds. `spec/PHASE6-COMPATIBILITY-POLICY.md` treats required review ordering and provenance as a stable surface and a weakening of a mandatory control as an invariant change, so the change needs an ADR (`core/02-authority.md` section 6).

## Decision

1. A Task Contract may declare a review budget (default T2: two Verifier rounds; T3: two Verifier and two Security rounds). When the last budgeted round does not pass, the Change Owner chooses and records one of: merge with listed advisories; accept a named residual; split the change; stop; one more round, the last only if the round found a rank-1 finding in code, tests or security posture. A declared budget is at most two rounds per layer, which keeps the cap of locked V1.2.2 section 11.3 ("a hard cap of two review rounds, then a human decides"); the menu is the human decision that follows it (Decision 4 gives the form in which that decision is taken in advance). A contract without a budget keeps the two-round maximum.
2. A finding whose only subject is narrative, a count or history in an evidence pack or dispositions file is advisory and is fixed by an append. It still blocks when it overstates a guarantee a consumer relies on, when a required artifact, rehearsal or acceptance is missing, when a SHA, digest or hash that a gate uses is wrong, or when the record contradicts the code or tests it describes. `verification/pack_facts.py` verifies cited hashes, commit SHAs and test names so that review does not argue them.
3. A Change Owner may accept a named, scoped residual at T3 with the reason. The acceptance never waives required evidence and never accepts a rank-1 behavior defect that has a reproducing case. The record-text rule does not default a finding away (locked principle P10): the finding is dispositioned by an append that names the sentence and the correct fact, made before merge.
4. The Change Owner may pre-authorise, in the approved Task Contract, the decision that follows the cap: up to two further rounds per layer after the layer's last budgeted round (for a budget of two, four of that layer in all), naming the layer and the number. A pre-authorised round starts only if the round before it, of the same layer, did not pass and found a rank-1 finding in code, tests or security posture, and the dispositions record the pre-authorisation, that finding and the date before the round starts. The cap of two stays, and so does the default; a contract without a pre-authorisation is unchanged. Source: the Change Owner, 2026-11-02, during `review-run-review`: "I can authorize up to 2 more rounds. Lets make 4 rounds our standard going forward. I think 2 rounds is too narrow." The reading of locked V1.2.2 section 11.3 ("a hard cap of two review rounds, then a human decides") on which this rests: a decision the human records in advance, conditioned on a rank-1 finding in code, tests or security posture in the round before, is a human decision after two rounds. The Change Owner accepted that reading on 2026-11-04 by approving `spec/AIDF-REVIEW-BUDGET-PREAUTHORISATION-TASK-CONTRACT.md` as drafted.

## Why this is not a weakening of a mandatory control

- **Code, tests and security posture are untouched.** Rank-1 and rank-2 findings about them block as before, and an extra round remains available for a rank-1 finding in them.
- **Missing and wrong required artifacts still block.** The four exceptions keep every finding that a gate or a consumer relies on blocking. A replay on the hand-labelled findings shows the rule would have changed the outcome of reports that contained only record text (2 of 29 in rounds 1 and 2; 14 of 35 in round 3 and later) and of no report that also contained a code, tests, process or fixture finding.
- **Verifier-before-Security ordering, distinct instances, human approval, trip-wires and final-head binding are not edited.**
- **Decision 4 adds no round by itself.** It records a human decision in advance, each round it covers still needs a rank-1 finding in code, tests or security posture, and the cap, the default and the maximum of a declared budget are as before.
- **Opt-in.** A contract with no budget keeps the previous maximum; residual acceptance is a Change Owner decision, recorded per finding, as before; what changes is that Decision 3 removes the earlier limit to non-trip-wire residuals.
- **Reversible.** Documents, templates and two small scripts; `git revert` restores today's rules.

## Consequences

- The Change Owner decides at the budget, not once per extra round, and the menu is explicit; Decision 4 lets him take that decision before the budget, in the contract.
- Accepting a T3 residual is a recorded Change Owner act with a scope and a reason, not an exception to the rule.
- The labels behind the replay are the Implementer's and have not been spot-checked by the Change Owner. The rule is tested on fixtures and a replay, not on a future change; the next five T2 or T3 changes measure it (`strategy/AIDF-REVIEW-EFFICIENCY-PROPOSAL.md`).
- `CHANGELOG.md` classifies the change `migration-required` for contracts that adopt a budget.

## Alternatives rejected

- **Keep the cap as a prompt.** The history shows it is not a cap.
- **A default of four rounds per layer.** It contradicts the locked [REQ] of section 11.3, and the locked spec is not edited; it would also make the longer path the expected one. The pre-authorisation keeps two as the cap and four as an opt-in decision.
- **Leave four rounds as a per-change one-line authorization.** That is the practice under which 64 of 101 recorded reports were rounds beyond the cap. The pre-authorisation records it once, in the approved contract, with the condition each round must meet.
- **Make every record finding advisory.** It would drop findings on missing evidence, the late Stage 2 pattern (7 of its 10 late labelled findings).
- **Put the pack check and the pending-criterion status in `aidf_check.py`.** That file is attested by the protected policy repository; changing it needs a separate cross-repository T3 change (found when the pipeline job `aidf-governance` failed). The pack check is a separate file; the pending-criterion status is deferred.
- **Generate the evidence pack.** It needs a command runner and a results format; verifying the pack's facts catches the same wrong-hash and wrong-SHA sentences with less code.

## Approval

Scott Wofford, Architect and Change Owner, 2026-10-30: "spec/adr/review-stop-rule.md is approved".

Scott Wofford, Change Owner and Architect, 2026-11-04: "approved as drafted, go ahead", on `spec/AIDF-REVIEW-BUDGET-PREAUTHORISATION-TASK-CONTRACT.md`, whose criterion 4 is Decision 4 and the two alternatives added after it.

Scott Wofford, 2026-10-30T22:51:53Z: "ammended contract is approved and the other 2 items are acknowledged." This acknowledges the edits made to this ADR after its acceptance (the two-round cap with the reference to locked V1.2.2 section 11.3, the P10 sentence, the corrected description of the labelled findings, and the Opt-in bullet).
