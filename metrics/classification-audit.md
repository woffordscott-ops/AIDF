---
owner: framework-maintainer
load_when: 20 merged T0/T1 changes accumulate, or at Phase 3 pilot exit
max_length: 2 pages
last_verified: 2026-08-19
---

# Classification Audit

This audit detects silent under-classification. It does not replace per-change classification and never relaxes a trip-wire.

## Normal cadence

Count merged T0/T1 changes from the first governed merge. At each completed block of 20, audit three changes:

1. one selected randomly from the block; and
2. two weighted toward trip-wire boundaries, security-adjacent paths, or unusual classifications.

Do not substitute calendar cadence. Preserve the random selection method and candidate list so another person can reproduce the draw.

## Phase 3 calibration audit

At Phase 3 exit, audit three of its 8–12 changes using the same one-random-plus-two-weighted composition. This initializes calibration only. It neither resets nor substitutes for the normal 20-change counter.

## Procedure

- Run the audit as declared M3 adversarial analysis.
- For each sampled merge ask only: **Given what is now known, should this change have been T2 or T3?**
- Record yes/no, the missed signal when yes, and the auditor's falsifying case.
- The human Change Owner adjudicates disagreements; a second human is not required.
- Calculate under-classification separately from escalation precision. Never net them into one accuracy score.

## Durable record

- **Audit ID and date:**
- **Trigger:** completed 20-change block | Phase 3 calibration
- **Population:** merge IDs and final classes
- **Random selection method and result:**
- **Weighted selection rationale and results:**
- **M3 auditor / model / execution record:**
- **Per-change decisions:** merge · original class · should have been T2/T3? · missed signal · Change Owner adjudication
- **Under-classification result:** count / 3
- **Escalation precision for the period:** count / count, reported separately
- **Merged guardrail references:**

The audit is incomplete until every confirmed miss produces a merged durable guardrail, in order of preference: mechanical rule, executable check, trip-wire/path rule, or kernel/context correction when instruction caused the miss. A number or memo alone is not an acceptable output.
