---
owner: framework-maintainer
load_when: running, scoring or reading the full AIDF benefit-versus-burden round
max_length: 2 screens
last_verified: 2026-10-23
---

# Pre-registration — AIDF benefit-versus-burden full round

Written and committed **before any run of the full round**. Contract: `spec/AIDF-BENEFIT-BURDEN-MEASUREMENT-TASK-CONTRACT.md`. The commit that holds this file is the registration; the report quotes it. Anything not stated here is exploratory and is labelled so in the report. The Change Owner's reply to the Implementer's recommendations (2026-10-23): "yes proceed. and use the most logical burden tolerance". The tolerance below is the Implementer's choice under that instruction, with reasons, and the Change Owner may change it before the round starts.

## Design

- **Candidate:** `cursor-agent` with model `gpt-5.3-codex-low`, fresh session per step, no command execution. Prompts, tests visible to the candidate and the time limit are identical across arms except for what the arm adds.
- **Tasks:** M1-FLOW-01 (class T1), M1-BILLING-01 and M1-MEMBERS-01 (class T2); M3-AUDIT-01 (T1), M3-ROUND-01 and M3-PROVENANCE-01 (T3).
- **Arms for M1:** **A** (AIDF: Task Contract, evidence pack, independent review where the class requires it, up to 2 review rounds, one visible-suite fix cycle in addition to review fixes); **B** (baseline: the task text, one visible-suite fix cycle); **C** (baseline with equal fix chances: the task text and up to 3 visible-suite fix cycles, no contract and no review). Arm C exists to separate the effect of AIDF's structure from the effect of more attempts. **Arms for M3:** A and B (a review task has no fix loop).
- **Repeats:** 5 per task and arm. Runs that fail for a harness reason (agent error, timeout, no output) are repeated once; both attempts are kept and the report counts them.

## Outcomes

- **Delivered failure (per run).** M1: the hidden tests fail **or** the visible suite fails at delivery (the task states that the suite "must still pass when you are done"). M3: the review does not pass its rubric (every criterion of A1 to A3, R1 to R3 or P1 to P3 judged true by the blinded scorer, and no file changed). *The visible-suite part is post hoc: it was noticed in the pilot data, and is labelled so wherever it is reported.*
- **Escaped defect types (M1, per run):** hidden-test failures, each tied to a defect type of the case (reported, not part of the verdict beyond the failure above).
- **M3 detail:** planted defect found (AUDIT, ROUND), false findings raised (all three; PROVENANCE has no planted defect and a false defect claim fails it).
- **Burden (per run):** automated elapsed seconds; review rounds; fix cycles; **required Change Owner approvals**, taken from the process rules (one for an AIDF T2 Task Contract; none for T0 and T1; none in Arms B and C), not from anyone's replies; cost is `unknown` (the tool reports none) and agent calls are counted as a proxy. A subset of runs in which the Change Owner actually reviews and answers is reported separately as real-reply data, never mixed into the headline.

## Decision rules (computed by `verification/aidf_measurement.py verdict`)

Classes are compared separately: **M1-T1** (FLOW), **M1-T2** (BILLING, MEMBERS), **M3** (all three review cases).

- **Comparator:** Arm C for M1; Arm B for M3.
- **Benefit:** Arm A shows benefit over the comparator in a class when its delivered failures, summed over the class's tasks, are fewer than the comparator's **and** no task of the class has more delivered failures in Arm A than in the comparator. Counts only; no significance is claimed at 5 runs per cell.
- **Worse:** Arm A has more delivered failures than the comparator, summed over the class.
- **Burden tolerance (the "most logical" reading of "not excessively burdensome").** It follows the framework's own statements that lower-risk work stays lighter (`core/01-lifecycle.md`, `strategy/PHASE8-PROCESS-VALIDATION.md` §12) and is set per class:
  - **M1-T1:** required approvals 0; review rounds 0; median elapsed of Arm A at most **1.5×** the comparator's.
  - **M1-T2:** required approvals at most 1 per change; review rounds at most 2; median elapsed of Arm A at most **2.5×** the comparator's. The multiplier allows for the contract step and one to two review rounds, each about one more agent session; the pilots showed 1.3× to 2.3×.
  - **M3:** required approvals 0; median elapsed of Arm A at most **2.0×** the comparator's.
  - Median elapsed excludes human waiting, which is not measured. A required approval is counted at its full cost to the Change Owner: one decision per change.
- **Verdict per class (one of):** *Beneficial and within tolerance*; *Beneficial, over tolerance*; *No demonstrated benefit, within tolerance*; *No demonstrated benefit, over tolerance*; *Worse than the comparator*; *Inconclusive* (more than 20% of a class's runs have an unknown value for a metric the rule needs).
- **Unknowns** are excluded from medians, counted, and never treated as zero.

## What is reported regardless of the result

The three verdicts in one table; every cell's counts; the burden table with the tolerance applied; the excluded one-time costs; the exploratory observations, labelled; the limitations (one candidate model, small multi-tenant backend, public answer key, AI-authored cases and an AI scorer with imperfect blinding, no cost data, runs of 5 per cell). A result that favours the baseline or Arm C is reported in the same place and form as one that favours Arm A.
