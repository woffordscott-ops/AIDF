---
owner: framework-maintainer
load_when: recording Phase 3+ change outcomes or reviewing framework health
max_length: 3 pages
last_verified: 2026-08-24
---

# Metric Definitions

Collect crudely from the first governed pilot change. These metrics diagnose the framework; they never lower a task's required controls. Every observation records the final class, population boundary, immutable source reference, collection method, numerator and denominator where applicable, and whether a value is measured, estimated, unavailable, or not applicable.

| Metric | Definition | Minimum collection method | Owner | Review cadence |
|---|---|---|---|---|
| Human minutes per merged change | Total active human minutes spent clarifying, approving, reviewing, resolving, and operating gates for one merged change, grouped by final class | Change record timestamps plus a manually corrected active-minutes field | Change Owner | Every 20 merged changes and Phase 3 exit |
| Rework rate | Percentage of AI-authored merged changes requiring more than one substantive revision; formatting-only or merge-base refreshes do not count | Count substantive revision rounds in the merge request | Framework maintainer | Every 20 merged changes |
| Change failure rate | Percentage of merges that cause an incident, rollback, emergency disablement, or corrective revert within the project's observation window | Link incident/rollback records to merge IDs; declare the observation window | Change Owner | Every 20 merged changes |
| Escaped defect rate by class | Defects discovered after merge divided by merged changes, separately for T0–T3 | Defect record → originating merge → final class | Change Owner | Every 20 merged changes; immediate review for any T3 defect |
| Cost per merged change | Model/tool spend plus CI compute attributable to one merged change; keep human time separate | Provider usage and CI duration mapped to merge ID; estimates labeled as estimates | Framework maintainer | Monthly or every 20 merges, whichever comes first |
| Classification calibration | Two separate measures: escalation precision and under-classification rate; never blend them | Escalation outcomes plus the audit in `metrics/classification-audit.md` | Architect | On the audit cadence |
| Review finding precision | Confirmed blocking findings divided by blocking findings raised, separately by review layer; always report numerator and denominator | Finding disposition in `templates/review-findings.md` | Verifier | Activates with the first review layer; unconditional in Phase 5; then every 20 reviewed changes and at phase exit |
| Review disagreement and revision outcomes | Disagreements, findings causing substantive revision, false positives, re-review rounds, escalations and outcomes, and time to disposition, by review layer | Review record plus merge history bound to the reviewed SHA | Framework maintainer | Every reviewed change; summarize every 20 and at phase exit |

## Counting rules

- **Human minutes, computation:** each approval request records `Requested (UTC)` and `Answered (UTC)` (`templates/approval-request.md`). The sum of answered minus requested over a change is an upper bound on waiting, not on effort, and is reported as such. `Active minutes (manual)` is reported beside it, never instead of it. `python verification/human_time.py <dispositions file>` prints the request count, the upper bound and the manual sum. A request without both timestamps is counted as `unknown`, never zero.
- **Substantive revision:** a change to behavior, contract, tests, architecture, security posture, or acceptance criteria. Formatting and mechanically resolving an updated merge base do not count.
- **Escalation precision:** escalations adjudicated as correctly requiring the higher class divided by all adjudicated escalations. Low volume is reported as a count, not disguised as a stable percentage.
- **Under-classification rate:** audited merged T0/T1 changes adjudicated as having required T2/T3 divided by audited T0/T1 changes.
- **Review finding precision activation:** optional Phase 3 review activates the metric immediately; it becomes unconditional with Phase 5. The numerator is blocking findings finally dispositioned `CONFIRMED_FIXED` or `CONFIRMED_ACCEPTED_RISK`; the denominator is all blocking findings raised. A zero denominator is `not applicable`, not 100%. `FALSE_POSITIVE`, `DUPLICATE`, `WITHDRAWN`, and `SUPERSEDED` remain visible but are not numerator events. `UNRESOLVED` remains in the denominator and blocks completion where required by `core/05-review.md`.
- **Review outcome dimensions:** disagreement, substantive revision, false-positive, re-review, escalation, and disposition-time counts diagnose why precision changed; they are not blended into the precision ratio.
- **Small samples:** report raw counts and `insufficient sample`; do not invent a stable threshold or confidence claim.
- Missing data is `unknown`, never zero. Estimates carry their basis. Never net over-classification against under-classification.
- **Source contract:** a summary without an immutable source reference is commentary, not a metric observation. Record the exact project/change/MR, commit or evidence digest, observation window, collector, and UTC collection time.
- **Population contract:** identify included and excluded changes before calculating a total, median, rate, or ratio. Never combine Phase 3 T1 calibration, Phase 5 T2/T3 review, controlled fixtures, or later qualification populations without reporting each separately.
- **Reconstruction:** when a required source field was not retained, record the value as `unknown`. A later estimate remains an estimate and does not replace the historical unknown.

## Health interpretation

Desired direction: human minutes fall for T0/T1, rework falls, change failure is flat or falling as volume grows, and T3 escaped defects approach zero. Any non-trivial under-classification rate is a live governance failure and must produce a durable guardrail under `core/01-lifecycle.md` §10. Low precision in an optional review layer supports retirement; a class-required layer is re-specified, never silently removed.
