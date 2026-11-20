---
owner: framework-maintainer
load_when: assembling task context, configuring Layer 3 pack triggers, or auditing context cost and freshness
max_length: 3 pages
last_verified: 2026-10-06
---

# 06 — Context and Cost

Apply locked V1.2.2 §12 and this framework's own version-compatibility policy (`spec/PHASE6-COMPATIBILITY-POLICY.md`). Load enough context to satisfy the controls, but do not bulk-load unrelated material or drop a required control to save time or tokens.

## Triggered tiers

- **Tier 1 — universal:** `KERNEL.md`, the current Task Contract, active trip-wires, and stop conditions. The Kernel remains within its two-page cap.
- **Tier 2 — project pack:** load by a declared path/diff/trip-wire manifest. The Pattern Registry is near-universal for classification and must display state plus any applicable standing authorization. Load the security model for security-sensitive paths; the deployment model for infra/config changes; relevant invariants, contracts, architecture, testing strategy, and conventions for touched boundaries.
- **Tier 3 — task context:** requirement, acceptance criteria, touched modules/contracts, relevant ADRs, adjacent tests, and recent changes. Agent-judged additions are declared in reconnaissance.

Every durable context artifact declares `owner`, `load_when`, `max_length`, and `last_verified`. A missing trigger is a context gap. A stale verification date is a warning requiring reinspection, not proof of validity. The Task Contract or Evidence Pack records the highest tier loaded and why. Instantiated context packs express `max_length` as `N page` or `N pages`, where `N` is from 1 through 20 and one page is a deterministic ceiling of 500 whitespace-delimited words; the offline checker rejects malformed or out-of-range caps and documents that exceed them.

## Generation and anti-rot

Prefer reproducible generation for repository maps, contract inventories, dependency graphs, and coverage. Record the generator, exact source commit, command/version, and drift rule. A generated inventory remains part of its document's declared cap; if an exact inventory cannot fit the bounded artifact, stop and govern a segmented representation rather than truncating or summarizing it. Never silently rewrite an historical map to match a newer tree. Check links and identifiers at an architecture-affecting merge and at phase boundaries; preserve superseded records and flag orphans. Adding a line to a capped document requires fitting the cap or removing another line without losing a required control.

When information needed to decide is absent, output a short context-gap record naming the missing source, affected decision, and owner. Unknown is not zero. A project with no executable tests or deployment evidence must say so.

## Cost and escalation

Stop, declare, split, or escalate when the same source is reread without a new question, the declared context budget is exceeded, two review rounds do not converge, evidence only duplicates an existing artifact, three material ambiguities remain, a task crosses separable trust roots or approval gates, or loaded sources contradict each other. A compressed context digest retains source commit, decision, open questions, authority, affected IDs, evidence links, adverse findings, and retained unknowns. It cannot compress away approval or evidence gates.

Measure token, latency, review, and human costs where data exists. Missing measurements stay unknown; cost pressure never lowers class, omits a triggered document, or turns a failed gate into a pass.
