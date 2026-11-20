---
owner: framework-maintainer
load_when: changing framework versioning, compatibility, or review-history recovery
max_length: 3 pages
last_verified: 2026-09-01
---

# ADR — Phase 6 Version Compatibility and Immutable Review Recovery

- **Status:** Accepted for Phase 6 implementation
- **Decision owner:** Scott Wofford, Architect and Change Owner
- **Decision date:** 2026-09-01
- **Context:** Phase 6 follows locked V1.2.2 although its historical roadmap
  row calls the output “framework v1.1.” Phase 5 also proved that valid
  immutable notes can become ambiguous across revisions and must not be erased.

## Decision

Name the revision `v1.3.0`. Treat V1.2.2 as its immutable architecture
baseline. Adopt `spec/PHASE6-COMPATIBILITY-POLICY.md`, including immutable
commit/digest pins, explicit compatibility classifications, and a fresh MR as
the default recovery for ambiguous immutable review history.

## Consequences

- No version-number downgrade or reuse.
- Existing consumers upgrade only through a governed immutable-pin change.
- Missing compatibility evidence fails closed as migration-required.
- Review history is never weakened, rewritten, or deleted to satisfy a gate.
- Major versioning is required for an incompatible public control/schema
  removal without a backward-compatible support window.

## Alternatives rejected

- **v1.1:** collides with the later locked V1.2.2 baseline.
- **v1.2.3:** understates a planned framework revision and new public
  compatibility contract.
- **Repair attestations in place:** makes history alteration part of recovery.
