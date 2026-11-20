---
owner: framework-maintainer
load_when: defining, approving, implementing, reviewing, or closing Phase 6
max_length: 4 pages
last_verified: 2026-09-01
---

# Phase 6 Prerequisite Intake — Framework Revision

## Entry decision

**Status:** GO for the approved T3 contract in
`spec/PHASE6-TASK-CONTRACT.md`. This does not authorize integration.

The authoritative build sequence defines Phase 6 as a framework revision based
on the Phase 3 and Phase 5 friction logs, with an expected 20–30% reduction and
metric re-baselining. The reduction is an evidence hypothesis, not a deletion
quota. Mandatory controls may be re-specified but not silently removed.

## Verified Phase 5 baseline

Read-only Git fetches and authenticated GitLab observations on 2026-09-01
verified:

- consumer project 6 protected `main`
  `87fedca3995125fc9042787395fc981a95b12eb1` and passed pipeline `#608`;
- policy project 7 protected `main`
  `2f167479041748108bd33a5a10766db393f065e6`;
- reviewed policy source
  `9c139eeb7d569fe8f013e6ee05ea7520357ffbbb` and the exact live consumer pin;
- merged consumer MR !24 with its source branch retained;
- ordered exact-head Bugbot note `460` then Security Review note `463`, bound
  to project 6, MR !24, base
  `526de28a54f56d51f211a5cb42aafb6d6e68bc28`, head
  `35f5c0c9f0376251024f8b11e2e3561b2bc809b9`, round 1, pipeline `#606`,
  downstream pipeline `#607`, and both evidence digests;
- passed policy pipeline `#607` and verifier job `#1783`;
- live-observation digest
  `84fcd317ded83d0815c037512c97282a0b3bc6ba89c22f8b443005bdf31dd70f`;
- recovery-evidence digest
  `aa0e457f6ea10a89b3d877b4b4cfd6823319f1ad986874534eb313e7cfb4df0c`;
  and
- closed MR !23 with immutable history preserved. MRs !22 and !21 remain
  excluded unless separately proven relevant.

## Available pilot evidence

Phase 3 provides ten T1 changes, zero recorded substantive revisions, a 0-of-3
under-classification calibration result, eight known CI durations totaling 257
seconds with a 30.5-second median, and unknown human active minutes.

Phase 5 provides the fixed T2/T3 population, protected execution evidence, and
qualitative friction from the review-round defect and fresh-MR remediation.
Review precision, disagreement count, finding-driven revision count, false
positives, time to disposition, human minutes, and model/tool cost remain
unknown because reproducible source measurements were not retained.

Phase 6 must preserve those unknowns. It establishes no deployment,
10-Gbit/s, IPS efficacy, platform-fitness, compliance, or commercial-readiness
claim.

## Authority boundary

Scott Wofford authorized the Phase 6 T3 contract, version decision, exact scope,
and `checkpointed` profile on 2026-09-01. Framework `v1.3.0` is the approved
revision identity following locked V1.2.2; the older Phase 6 label “framework
v1.1” is treated as a historical roadmap label, not a version downgrade.

This approval permits implementation only within the exact contract scope.
Each invariant change still requires an ADR; triggered legal decisions require
legal disposition; Bugbot must precede Security Review; and merging any MR
requires separate explicit authorization naming that MR.
