---
owner: framework-maintainer
load_when: creating a project context pack, classifying precedent, or changing an architecture boundary
max_length: 4 pages
last_verified: 2026-10-06
---

# 03 — Architecture Governance

This is the reusable process distilled from a private pilot's own experience. It does not import the pilot's product decisions. The locked V1.2.2 specification §§4.3, 9, 12, and 17 and `core/01-lifecycle.md` govern if wording differs.

## Five governance artifacts

1. **Architecture overview:** at most three pages, naming components, owners, data flow, trust boundaries, and deployment shape. Mark an unknown as unknown, not absent.
2. **Invariants register:** one stable ID per invariant with statement, rationale, scope, enforcement, owner, and status. Use only `GENERATED`, `CI-ENFORCED`, `TEST-ENFORCED`, or `PROSE-ONLY`. A prose-only rule is not a passing mechanical check.
3. **Pattern registry:** a table of pattern, scope/context, `PROVISIONAL` or `RATIFIED` state, basis, date, and ratifier. Discovery creates only `PROVISIONAL` entries. Only an Architect decision can ratify a pattern; age, repetition, and existing code cannot. A rejected pattern is documented as drift, not silently erased from history. The Layer 3 structural checker uses a closed JSON representation of this table.
4. **ADR log:** numbered, append-only decisions for novel durable architecture; supersede rather than rewrite. Routine conformity to precedent does not require an ADR.
5. **Contract registry:** stable identifiers and versions for interface contracts, with their authoritative source paths. Generate from source where possible; otherwise record the manual-maintenance gap and inspect contract diffs at each affected change.

Security model, testing strategy, conventions, generated repository map, and deployment/operational model are **project context**, not extra governance authorities. Both Layer 3 entry paths produce the same set; see `instantiation/README.md`.

## Discovery, decision, and drift

- On an existing project, inventory the exact Git source commit and observe incumbent behavior without treating it as approved. Seed each observed pattern as `PROVISIONAL`, with evidence and scope. A scoped, expiring standing authorization may allow T1 work under `core/01-lifecycle.md`, but grants no precedent.
- On a greenfield project, start with an empty registry. Architecture choices are proposals until the Architect approves the relevant invariants, contracts, boundary decisions, and any durable pattern. Do not manufacture an incumbent history.
- For every architecture-affecting change, name affected invariant, contract, pattern, convention, and ADR IDs. Compare the current tree, generated map, overview, registries, and changed paths. Classify each difference as conforming implementation, approved evolution, or drift. Drift blocks integration until removed or explicitly governed.
- Missing, duplicate, unknown, stale, or unresolved identifiers fail closed. A parser may reject unsupported fields but must not silently drop them. Stable IDs are never reused; superseded records stay addressable.
- Run a drift audit on affected merge requests and at phase closure. Escalate when an unknown or contradiction crosses an ownership or trust boundary. The Architect alone resolves invariant/contract changes and ratification; an Implementer may recommend but cannot self-approve.

## Enforcement and evidence boundary

Every mechanical rule must have a falsifiable positive and negative case before it is called enforced. A project-specific CI rule is activated only after its inputs and protected policy are approved. The offline Layer 3 checker verifies structure, safe paths, metadata, and exact source-tree inventory; it cannot validate the truth of architectural prose, authenticate a human approval, or establish runtime fitness. Those require explicit human review and applicable E0–E7 evidence. Preserve unknowns instead of presenting missing tests or deployment evidence as green.

Recovery uses ordinary Git revert for project context changes and the approved immutable-pin rollback/reapplication path for protected policy. Closed pilot records remain immutable.
