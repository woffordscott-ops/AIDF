---
owner: framework-maintainer
load_when: publishing, upgrading, pinning, or reviewing an AIDF framework version
max_length: 4 pages
last_verified: 2026-09-01
---

# AIDF v1.3 Compatibility and Versioning Policy

## Version identity

AIDF uses semantic versioning for the reusable framework beginning with
`v1.3.0`. Locked V1.2.2 remains the immutable architecture baseline from which
this revision is derived. The older Phase 6 roadmap phrase “framework v1.1” is
a historical planning label and does not replace or downgrade V1.2.2.

- **Patch:** editorial corrections and guardrail fixes that preserve every
  public schema, required control, and consumer obligation.
- **Minor:** backward-compatible additions, clarified controls, or a revision
  with a documented migration path that retains the previous accepted path for
  the support window.
- **Major:** removal or incompatible change to a public schema, control
  contract, evidence requirement, or integration surface.

Security impact overrides numbering convenience: a change that weakens or
removes a mandatory control is governed as an invariant change even if its
syntax appears compatible.

## Stable public surfaces

The stable surfaces are the Kernel principles and trip-wires; T0–T3, M0–M3,
and E0–E7 meanings; A/N/P/X authority; Task Contract and evidence semantics;
required review ordering and provenance; published JSON schemas; and protected
checker command behavior. Templates and prose layout may evolve when their
normative meaning and machine-readable fields remain compatible.

No vendor/model qualification, the product contract of any project that consumes the framework, private GitLab
configuration, deployment topology, or commercial offering is part of the
framework compatibility promise.

## Change classification

Every release records each changed surface as `compatible`,
`migration-required`, or `breaking`. A migration-required change keeps the
prior form supported for the declared window and supplies an executable or
mechanically checkable migration. A breaking change requires a major version
and explicit human adoption decision.

Unknown consumer impact fails closed as `migration-required` until evidence
proves compatibility. A green suite cannot decide architectural or risk
acceptability.

## Pinning, support, and deprecation

Projects pin an immutable framework commit or release digest. Floating branches
and tags are not provenance. A project upgrade is a governed change and does
not occur automatically because a newer version exists.

The current minor line and its immediately preceding minor line are supported
for security fixes during Phase 6–8 validation. Deprecation requires a release
record, replacement path, affected-surface list, and a minimum one-minor-version
overlap. Mandatory security controls cannot be deprecated without an approved
equivalent or stronger control.

## Migration and recovery

Each migration-required release provides exact source and target versions,
affected surfaces, a deterministic dry-run, irreversible-effect accounting,
and rollback by restoring the last accepted immutable pin and rerunning the
protected verification graph.

If immutable review history makes an MR ambiguous, retain the history. Use a
fresh MR carrying the unchanged reviewed commit, or another protected mechanism
that produces one unambiguous attestation set. Never edit or delete review notes
to manufacture a passing ledger.

## Release evidence

A release requires final-head E0–E7, migration/recovery evidence, ordered
Bugbot then Security Review attestations, all triggered legal and architecture
decisions, a passed protected pipeline, explicit Change Owner merge
authorization, and a protected-main result bound to the merge commit.
