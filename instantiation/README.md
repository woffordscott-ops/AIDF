---
owner: framework-maintainer
load_when: selecting a Layer 3 entry path or reviewing the project context-pack contract
max_length: 2 pages
last_verified: 2026-10-06
---

# Layer 3 — Project Instantiation

**Status: finished and in use** — merged, tested, and formally accepted by the Change Owner on 2026-09-28; not an experimental draft. The two entry paths are [existing-project discovery](onboard-existing.md) and [greenfield decision/bootstrap](bootstrap-new.md). Neither path authorizes project execution, a protected-policy change, or profile use.

New to AIDF: see [how to set up AIDF in a project](set-up-aidf.md), the steps in order. A team that already plans its changes with OpenSpec or Spec Kit: see [using OpenSpec or Spec Kit with AIDF](spec-tools.md).

Layer 3 produces one target artifact regardless of entry path: the **project context pack** — architecture overview, invariants register, contracts, security model, testing strategy, conventions (locked spec §1.16, §0). There are two entry paths into producing it:

- **Existing-project discovery** (`onboard-existing.md`) — the pack is *discovered*: reverse-engineered from the repository as it stands.
- **Greenfield decision/bootstrap** (`bootstrap-new.md`) — the pack is *decided*: authored deliberately before code exists.

Both paths converge on the same five architecture-governance artifacts defined in `core/03-architecture.md`: architecture overview, invariants register, pattern registry, ADR log, contract registry. They also produce a source-bound repository map, security model, testing strategy, conventions, deployment/operational model, and context/cost triggers under `core/06-context-and-cost.md`. The manifest's required artifact keys are shown in `fixtures/existing-manifest.json` and `fixtures/greenfield-manifest.json`.

## Structural verification boundary

The offline `check_context_pack.py` validates closed schemas, safe regular-file paths, front-matter, exact existing-project Git source/inventory binding, the pre-code greenfield manifest shape, and Pattern Registry state/decision-record shape. It reads only and uses no network. It does **not** verify architectural judgment, authenticate a human approver, execute a project test suite, or establish runtime, deployment, privacy, compliance, or security efficacy. Those remain governed decisions and evidence gates.

On Windows, run the checker from a canonical local drive-letter or canonical UNC path on a filesystem that exposes stable file identities (for example, NTFS). The checker compares opened-file identity tokens, rejects reparse components, and uses path namespaces only to reject aliased roots; substituted drives, mapped-drive aliases, volume-GUID-only paths, and filesystems without stable identities are unsupported and rejected fail closed. Protected Linux CI covers the portable logic and Windows counterfactuals, but it does not execute the Windows handle API. Before claiming Windows support for an instantiated pack, record a local Windows run of the real-handle tests and disclose any unavailable reparse-point test rather than marking it passed.

On Linux, the checker binds artifact traversal and Git inspection to the validated project-root directory identity. Git inspection requires `/proc/self/fd`; a Linux runtime without that descriptor namespace fails closed. This checker makes no macOS support claim.

The pack is deliberately bounded input. Each `max_length` must be between 1 and 20 pages, the generated repository-map inventory participates in that declared limit, and every artifact is limited to 128 KiB. An existing repository whose exact tree cannot fit those bounds must stop and request a separately governed segmented-inventory extension; it must never truncate, summarize, or silently omit tracked paths to obtain a pass.

## After Layer 3: qualifying tools and enabling routing

The project context pack is this document's only outcome. It grants no
tool/model eligibility and no automatic routing — both are separate,
project-specific setup every adopter performs for their own project, never
inherited from this repository or from the private pilot these playbooks
generalize:

- **Layer 2 qualification** (`profiles/qualification-protocol-v1.1.md`) —
  run the mandatory M0–M3 suite against your own chosen tool/model, for
  your own project's exact repository, revision, and environment. A
  profile from another project or past its own per-mode expiry confers no
  eligibility here (`profiles/README.md`'s Assignment rule).
- **Automatic routing** (`profiles/README.md`'s Specialty dimension and
  automatic routing section) is additionally gated on an out-of-band
  `authorization` mapping that `verification/agent_routing_check.py`
  requires and this repository deliberately does not ship. Without your
  own entry in it, every routing candidate resolves to ineligible — that
  is the fail-closed design, not a defect. `profiles/authorization/**` is
  a tripwire path, so building your own real mapping is, correctly, its
  own T3 task under your project's policy; it is not something to route
  around with a smaller or synthetic version of the same path.

## Evidence source

The source pilot is a private project, at protected-main commit `3241d2c2733c1fd82cd5607aeebe0b896d367265`. Its architecture/governance process informs these playbooks; its product-specific invariants, contracts, patterns, and claims do not transfer to other projects.
