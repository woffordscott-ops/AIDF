Layer 1 architecture is now **LOCKED at V1.2.2**.

The authoritative architecture specification is:

`AIDF-v1.2.2-design-proposal.md`

You are now acting as the **Phase 1 implementation engineer**.

This is no longer an architecture-design exercise.

# Governing Rule

**Do not modify, reinterpret, simplify, expand, or redesign the locked Layer 1 architecture while implementing it.**

The design document is the specification.

If implementation exposes an ambiguity, contradiction, or requirement that cannot be implemented as written:

1. Do not silently resolve it.
2. Do not modify the architecture document.
3. Record an **Implementation Conflict** containing:

   * specification section
   * implementation problem
   * why the requirement cannot be implemented literally
   * available implementation options
   * your recommendation
4. Continue implementing everything not blocked by that conflict.

An implementation difficulty is not automatically an architecture defect.

Prefer the simplest implementation that faithfully satisfies the locked architecture.

# Operating Environment for Phase 1

For this phase, assume:

* Development is **interactive and human-supervised**.
* You may read and write files inside this framework repository.
* You may run local tests, validation scripts, linters, and repository-local tooling.
* You may use Git locally and create branches/commits if appropriate.
* You have **no production credentials**.
* You have **no production or cloud execution authority**.
* Do not perform external destructive operations.
* Do not modify infrastructure outside this repository.
* Any operation that would exceed these boundaries must stop and be reported.

This satisfies the Phase-1 execution-authority and autonomy assumptions until Layer 2 qualification is built.

# Phase 1 Objective

Implement **Phase 1 — Core Framework** exactly as defined in §17 of the locked specification.

Phase 1 must produce the minimum usable framework that changes development behavior without prematurely implementing later phases.

## Required Phase 1 Deliverables

Implement:

### 1. `KERNEL.md`

The always-loaded framework kernel.

Requirements:

* Maximum approximately 2 pages
* Concise enough to be loaded for every task
* Must include the behavior-changing rules specified by the architecture, including:

  * core principles in compressed form
  * jurisdiction rule
  * control-selection ladder
  * T3 trip-wires
  * STOP → DECLARE → ESCALATE
  * definition of done by task class
  * declared-scope discipline
  * untrusted-content rule
  * human ownership/accountability requirement
* Do not turn the kernel into a summary of the whole framework.
* Every line should change agent behavior.

### 2. `core/01-lifecycle.md`

Implement the locked lifecycle and classification model, including:

* eleven-stage lifecycle
* approval-as-gate semantics
* gate matrix
* Clarification
* Spike
* Task Contract
* Spec Confidence state machine
* T0–T3 task classes
* trip-wires
* Pattern Registry states:

  * `PROVISIONAL`
  * `RATIFIED`
* both T1 eligibility routes:

  * applicable ratified precedent
  * applicable scoped/time-boxed standing authorization
* classification authority rules
* escalation/de-escalation rules
* Retro → Guardrail triggers

Do not implement Phase-4 architecture-governance machinery here beyond the schema/semantics Phase 1 explicitly needs for classification.

### 3. `core/02-authority.md`

Implement:

* five logical roles
* separation of duties
* solo-capable operation
* role performance vs approval authority
* authority levels:

  * A
  * N
  * P
  * X
* gate assignments
* human approval requirements
* no ceremonial self-approval
* T3 separated Verifier/Security Reviewer behavior
* standing authorizations
* truly irreversible operation rule
* class-independent human gates

Maintain the distinction:

> AI may perform reasoning under a role.

versus:

> Level-P approval is exercised by a human.

### 4. `modes/execution-modes.md`

Implement M0–M3:

* M0 — Constrained Execution
* M1 — Supervised Implementation
* M2 — Design & Synthesis
* M3 — Adversarial Verification

Include:

* purpose
* appropriate work
* inappropriate work
* required context
* autonomy envelope
* required output
* escalation conditions

Include the Phase-1 bootstrap rule:

* Phases 1–6 use **declared modes**
* Phase 7 replaces declaration with **repo-specific qualification**
* mode is assigned per task, not permanently to a model
* T2+ Implementer and Verifier instances remain separated

Do not create vendor-specific Claude/Codex/Cursor mappings yet.

Those belong to Layer 2 / Phase 7.

### 5. Phase-1 templates

Implement the templates required by the locked repository structure that are necessary to support Phase 1 behavior.

At minimum:

* `templates/task-contract.md`
* `templates/conflict-notice.md`
* `templates/approval-request.md`
* `templates/spike-report.md`
* `templates/pattern-entry.md`
* `templates/standing-authorization.md`
* `templates/adr.md`
* `templates/invariant.md`
* `templates/review-findings.md`
* `templates/evidence-pack.md`
* `templates/exemption.md`

Some templates will not be fully operational until later phases.

That is acceptable.

Where later-phase fields exist:

* define the schema,
* mark when they become active,
* do not invent later-phase policy.

Templates must enforce the framework's human-attention budgets.

Favor structured, short fields over open-ended prose.

# Front Matter

Apply the context-management metadata required by the locked framework wherever appropriate:

* `owner`
* `load_when`
* `max_length`
* `last_verified`

Use sensible initial values.

For framework-owned documents, the initial owner may be the framework maintainership role rather than a project-specific person.

Do not fabricate project-specific facts.

# README

Create or update `README.md` sufficiently to explain:

* what AIDF is
* the locked three-layer model
* current implementation status
* how the repository is structured
* what Phase 1 contains
* what is intentionally not implemented yet
* the implementation sequence from the locked architecture
* where the locked architecture specification lives

Keep it concise.

The README is orientation, not another policy document.

# Stubs for Later Layers

Create the repository seams required by the locked architecture without implementing them prematurely.

At minimum:

`profiles/README.md`

Explain that Layer 2 will eventually contain:

* qualification protocol
* model/tool profiles
* model→execution-mode qualification

Do not map Claude, Codex, Cursor, or specific models yet.

`instantiation/README.md`

Explain that Layer 3 produces the project context pack through:

* existing-project discovery
* greenfield decision/bootstrap

Do not build the actual onboarding/bootstrap workflow yet unless the locked Phase-1 specification explicitly requires a schema stub.

# Metrics Directory

Create only the minimal structure required by the locked repository architecture.

Phase 2 owns the operational metrics implementation.

Do not prematurely build dashboards, collection systems, or CI instrumentation.

# Implementation Quality Rules

While implementing:

* Prefer normative, concise language.
* Use `REQ` and `R` consistently with the locked design.
* Avoid copying large explanatory passages from the architecture proposal when a shorter operational rule will do.
* The implementation documents should be **significantly shorter than the design proposal**.
* Preserve terminology exactly:

  * Layer 1–3
  * T0–T3
  * M0–M3
  * E0–E7
  * PROVISIONAL / RATIFIED
  * Task Contract
  * standing authorization
  * Change Owner
  * Architect
  * Implementer
  * Verifier
  * Security Reviewer
* Do not introduce synonyms that create competing terminology.
* Do not create new roles, modes, task classes, evidence levels, authority levels, framework layers, or architecture decisions.

# Internal Validation

After implementing Phase 1, perform a validation pass.

Check:

## Traceability

For every Phase-1 requirement in locked §17, identify the implementation artifact that satisfies it.

## Cross-document consistency

Verify that:

* T1 eligibility is identical everywhere
* PROVISIONAL never means approved
* standing authorization never means precedent
* P always means human approval
* X always means human execution
* M1 uses an established Task Contract
* T2/T3 Task Contracts require human approval
* Spec Confidence must be Clear before implementation
* trip-wires force T3
* reversibility never overrides a trip-wire
* T3 separated-instance rules are consistent
* AI role performance never satisfies human P approval
* no future-phase control is presented as already operational

## Context budget

Verify:

* `KERNEL.md` stays within its hard budget
* templates are concise
* every context document has an explicit load trigger
* Phase-1 files do not duplicate one another unnecessarily

## Repository completeness

Verify every artifact scheduled for Phase 1 exists.

# Architecture Traceability File

Create:

`IMPLEMENTATION-STATUS.md`

This is not a new governance policy.

It is an implementation ledger showing:

* locked architecture version: V1.2.2
* current implementation phase
* Phase-1 deliverables
* status of each
* architecture section → implementation artifact mapping
* intentionally deferred Phase-2+ capabilities
* any Implementation Conflicts discovered

Keep it concise and machine-readable where practical.

This file will allow future agents to distinguish:

> specified

from

> implemented

from

> operationally enforced.

That distinction is important.

# Completion Criteria

Phase 1 is complete only when:

1. Every Phase-1 artifact exists.
2. Required templates exist.
3. Kernel respects its size budget.
4. Internal links resolve.
5. Terminology is consistent.
6. Phase-1 architecture traceability is complete.
7. No later-phase capability is falsely represented as operational.
8. Any unresolved implementation conflict is explicitly recorded.
9. You have run the final validation pass.

# Final Response

Do not return a long narrative.

Return:

1. **Files created/modified**
2. **Phase-1 traceability summary**
3. **Validation results**
4. **Implementation conflicts:** `NONE` or exact list
5. **Deferred Phase-2+ capabilities**
6. **YES / NO — Phase 1 implementation complete**
7. If YES:
   **“Phase 1 is complete against locked Layer 1 architecture V1.2.2. Ready for Phase 2 prerequisites and Verification Spine.”**

Do not begin Phase 2.
