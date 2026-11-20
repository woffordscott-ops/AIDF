---
owner: framework-maintainer
load_when: any task, to determine the permission envelope before work begins
max_length: 4 pages
last_verified: 2026-10-06
---

# Execution Modes — M0–M3

Modes are permission envelopes defined by what an agent may do without a checkpoint and what it must return — not by claimed model intelligence. Any model may operate in any mode it has been declared or qualified into (§3). `modes/` is intentionally separate from `core/`: it is the stable interface Layer 2 (tool/model qualification) implements against, so Layer 2 can iterate without touching governance.

## M0 — Constrained Execution

- **Purpose:** apply a known transform.
- **Appropriate work:** codemods, formatting, mechanical rename, generated-code refresh, boilerplate from an existing template.
- **Inappropriate work:** anything requiring judgment; anything where success isn't machine-checkable.
- **Required context:** Kernel + the transform spec + target files.
- **Autonomy envelope:** full within declared scope.
- **Required output:** deterministic diff or generated artifact.
- **Verification of its output:** machine check (deterministic diff, generator idempotence).
- **Escalates when:** the transform doesn't apply cleanly, or the diff shape is unexpected.

## M1 — Supervised Implementation

- **Purpose:** build to an **established** Task Contract — approved where the class requires it (`core/01-lifecycle.md` §4).
- **Appropriate work:** feature work with precedent, bug fixes with a reproduction, test authoring, refactor within a boundary.
- **Inappropriate work:** creating new abstractions; changing contracts; anything covered by neither ratified precedent nor a standing authorization.
- **Required context:** Kernel + established Task Contract + touched contracts + tests + conventions.
- **Autonomy envelope:** full within the Task Contract; halts at its boundary.
- **Required output:** working change + the evidence pack required by class.
- **Verification of its output:** evidence pack per class.
- **Escalates when:** the Task Contract is wrong or incomplete; an invariant conflict appears; neither a ratified precedent nor a covering standing authorization is found; scope would expand beyond what was declared.

## M2 — Design & Synthesis

- **Purpose:** produce plans, options, tradeoffs, ADR candidates.
- **Appropriate work:** approach options, refactor strategy, migration design, risk analysis, ADR drafting, recon summaries.
- **Inappropriate work:** merging anything; making the decision (M2 *proposes*, it does not decide).
- **Required context:** Kernel + architecture overview + invariants + relevant ADRs + domain model.
- **Autonomy envelope:** produces artifacts only; zero write authority to main.
- **Required output:** plans, options, tradeoffs, or ADR candidates; artifacts only.
- **Verification of its output:** human or Architect review of the decision, not the prose.
- **Escalates when:** options conflict with an invariant, or the decision exceeds M2's authority.

## M3 — Adversarial Verification

- **Purpose:** try to break it.
- **Appropriate work:** falsification, negative/boundary/abuse cases, invariant checking, contract-diff analysis, test-sufficiency judgment.
- **Inappropriate work:** **fixing what it finds** — this is the separation-of-duties boundary (`core/02-authority.md` §3).
- **Required context:** Kernel + the requirement and invariants + diff + tests — deliberately *not* the author's rationale (clean-room framing).
- **Autonomy envelope:** produces findings only; zero write authority to source.
- **Required output:** findings only; no source changes.
- **Verification of its output:** findings graded by evidence class; reviewer precision is tracked.
- **Escalates when:** it cannot construct a falsifying case but still believes there's a defect — it says so explicitly rather than manufacturing findings.

## Two rules that make modes real

**Mode is a per-task assignment, not an identity.** The same underlying model may run M1 on one task and M3 on another. What must never happen is one *instance* holding both M1 and M3 on the same change **at T2 or above** — that is the separation-of-duties violation that turns independent review into self-review with extra steps. At T0/T1, self-verification is permitted because the blast radius and reversibility of that work don't warrant separation — not because evidence substitutes for it.

**Profiles narrow checkpoint frequency, not modes.** A valid protected project
automation policy may remove optional checkpoints inside the already assigned
mode and confirmed class. It cannot qualify a model, widen an autonomy envelope,
alter the Task Contract, cross a mode boundary, or automate a level-P/X action.
Any task override is tighten-only; invalid or expired policy restores the most
restrictive checkpoint posture.

**Qualification, not assertion.** Modes are needed during a project's bootstrap, before its Layer 2 qualification regime is established, so the rule has two states (locked spec §6.2):

| State | When | Mechanism | Compensating control |
|---|---|---|---|
| **Provisional** | During the project's pre-qualification bootstrap | A model is *declared* into a mode by the Architect; the declaration is recorded. | Class-required evidence is unchanged — a provisionally-declared M1 agent still produces the full evidence pack, so a bad declaration surfaces as failed checks, not merged defects. |
| **Qualified** | Once the project's Layer 2 qualification regime is established | A model enters a mode only by passing a repo-specific qualification eval — representative tasks with known-good outcomes, re-run on model/tool version change. | Layer 2 owns the eval and the resulting mapping; this is what makes vendor-neutrality operational rather than aspirational. |

Record every provisional declaration — the set that later fails qualification is the most informative eval material available.

## Bootstrapping modes before qualification exists

- During the project's pre-qualification bootstrap, use **declared modes.** Once its Layer 2 qualification regime is established, qualification replaces declaration. A missing, failed, expired, or revoked profile does not permit fallback to declaration; the tool/model/mode combination must qualify before use.
- Mode is assigned **per task**, never permanently to a model.
- T2+ Implementer and Verifier instances remain separated regardless of whether the mode is declared or qualified.
- V1.0 assumes interactive, human-supervised execution. Long-running autonomous operation requires checkpoint/interrupt design in a later framework increment and is not covered by any mode declared here.
- This document defines the mode contract only. It does **not** map any vendor, tool, or specific model to a mode for you — that mapping belongs to Layer 2 and is populated per project, per tool/model (see `profiles/README.md` for this repository's own example, which does not transfer to yours).

## Why not a "fast/cheap" tier

Not included. "Fast" is an economic property, not a capability, and encoding it as a tier invites choosing a mode for budget reasons rather than task reasons. Cost tradeoffs happen explicitly, not by mode selection. M0 already covers genuinely mechanical work.
