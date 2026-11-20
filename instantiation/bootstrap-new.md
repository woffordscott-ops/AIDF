---
owner: framework-maintainer
load_when: instantiating AIDF before a new project has code or an incumbent architecture
max_length: 3 pages
last_verified: 2026-10-06
---

# Greenfield decision and bootstrap

Outcome: the **same project context pack** as existing-project discovery, but authored as explicit decisions before implementation rather than inferred from existing code. This path has a synthetic contract fixture, not real pilot experience; its operational effectiveness remains unproven until exercised on a separately governed project.

1. **Establish authority:** name the project, Change Owner, Architect, Task Contract, class, security/dependency/irreversibility trip-wires, and stop conditions. Do not start product code or protected configuration because a template exists. Resolve vague requirements before implementation.
2. **Start honestly empty:** set `entry_path: "greenfield"`, `source_commit: null`, and an empty repository-map inventory with `Source commit: none (pre-code)`. Do not invent observed paths, precedent, a passing test suite, operational targets, or compliance claims. The Pattern Registry starts empty; a proposed convention is not an incumbent `RATIFIED` pattern.
3. **Decide the pack:** draft an architecture overview (≤3 pages), invariants with explicit enforcement status, contract registry, ADR log, security/trust-boundary model, testing strategy, conventions, and deployment/operational model. Record alternatives, unknowns, and decision owners. Do not claim a mechanical invariant is CI-enforced until a positive and negative test actually runs.
4. **Obtain decisions:** the Architect approves boundary, invariant, contract, and durable pattern decisions; dependency, license, and protected-policy changes use their own gates. If a decision is unresolved, label it pending and stop work that relies on it. A blank or fabricated approval is not a pass.
5. **Validate the structural floor:** create `project-context-pack.json` using `fixtures/greenfield-manifest.json`, front-matter all Markdown artifacts, and run the offline checker. On Windows, use a canonical drive-letter or UNC path on a filesystem with stable file identities; unsupported aliases, volume namespaces, and unavailable identities fail closed. Because protected Linux CI does not execute the Windows handle API, record a local real-handle test run and disclose any unavailable reparse-point test before claiming Windows support. It rejects invented incumbents, claimed Git inventory, malformed metadata, unsafe paths, and unsupported schema. Human reviewers still verify substance and approval provenance.
6. **Transition to code:** once the first commit exists, regenerate the map from that exact Git object and record new evidence; do not rewrite the pre-code snapshot. Reclassify later changes under `core/01-lifecycle.md`, load context per `core/06-context-and-cost.md`, and keep the pack current when changes invalidate it.

Both entry paths converge on the artifacts listed in `instantiation/README.md`. This playbook is not authority to deploy, use a qualified profile, set protected variables, or change another project's CI policy.

Once the pack is in place: this playbook does not qualify any tool/model
for your project, and does not enable automatic routing. See
`instantiation/README.md`'s "After Layer 3" section for that separate,
project-specific setup.
