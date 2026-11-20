---
owner: framework-maintainer
load_when: orienting to framework metrics or deciding which metric artifact to use
max_length: 1 page
last_verified: 2026-10-06
---

# Metrics

**Status: defined and operational; two populated observation records exist.**

- `definitions.md` defines the six day-one metrics, the unconditional review-finding precision metric, and the accompanying disagreement/revision outcomes, including collection method, owner, and cadence.
- `classification-audit.md` defines the 3-of-20 under-classification audit and a one-time calibration audit.
- `change-observation.schema.json` is the record format for a single governed change's populated metric values — every field required, every numeric value paired with a `measured` / `estimated` / `unavailable` / `not_applicable` status, matching the source, population, and reconstruction contracts in `definitions.md`.
- `observations/` holds populated records. `observations/phase8-layer3-git-trust-hardening.json` is the first — a T3 change (framework MR !20), backfilled honestly rather than estimated where source data was never captured in real time. `observations/phase9-ci-policy-security-r1.json` is the second — a Codex (`gpt-5.6-sol`) Security Reviewer pass over `aidf-ci-policy` MR !57, and the first record to attribute a `review_finding_precision` figure to that model identity. Codex's own review reports do not self-report backend model identity ("Model backend identity unavailable, not inferred"), consistent across every review report this model produced; this record's `model_identifier` is instead recorded on Scott Wofford's direct confirmation as the human who installed, configured, and selected that exact model for this deployment -- a human-attested fact, disclosed as such in the record's own `basis` field, not inferred by the collector or claimed by the reviewer's own tooling.

No dashboard or automated collection system exists; population remains two records. The protected provenance gate is separate, later work and is not claimed here. Missing observations are `unknown`/`unavailable`, never zero, and metrics never reduce the evidence or gate required by task class.
