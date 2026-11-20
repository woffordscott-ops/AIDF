---
owner: framework-maintainer
load_when: any task, from Provisional triage onward
max_length: 6 pages
last_verified: 2026-08-19
---

# 01 — Lifecycle & Classification

Operational rules for the eleven-stage lifecycle and the classification model. Kernel rules (trip-wires, jurisdiction rule, control-selection ladder) apply throughout and are not repeated here.

## 1. The eleven stages

1. **Intake** — a request enters with a stated outcome. No stated outcome → rejected, not guessed at.
2. **Provisional triage** — cheap routing only: domain, obvious trip-wire presence, is the spec clear enough to proceed. Seconds, not minutes.
3. **Clarification** *(conditional on Spec Confidence, not on class — §3 below)*.
4. **Reconnaissance** — read before writing: touched modules, contracts, relevant ADRs, existing tests, prior similar changes. Output includes a **context gap report** (what was needed and not found) — feeds guardrail generation.
5. **Classification (confirmed)** — real class assignment, now that code has been seen. Escalation is free. **De-escalation requires the authority of the higher class.**
6. **Task Contract** *(§4 below)* — established (T0/T1) or human-approved (T2/T3) before implementation.
7. **Implementation** — build within the established Task Contract.
8. **Self-verification** — the author produces the evidence pack required by class (`templates/evidence-pack.md`). Artifacts, not a claim of correctness.
9. **Independent review** *(conditional by class — required at T2+)* — adversarial, falsifiable, separated-duty.
10. **Human approval** — *not a chronological stage.* Gates fire where the thing they govern occurs, not as a late-stage event. See the gate matrix below.
11. **Integration → Knowledge update → Retro/Guardrail** — merge; update every contract/ADR/context doc the change invalidated (part of the definition of done at every class, not only where the matrix marks the routine sweep required); and, on an escaped defect or classification failure, produce a guardrail.

### Where approval gates actually fire

| Gate | Fires |
|---|---|
| T2/T3 Task Contract approval | Before Implementation (before stage 7) |
| T3 merge approval | After self-verification and independent review, before Integration (between stages 9 and 11) |
| All other P/X gates (see `core/02-authority.md` §Gate assignments) | At the moment the governed decision is made or action executed |

Where chronology and authority rules appear to differ, the authority rules govern.

### Project automation profiles

A project may protect an expiring automation policy that selects a risk threshold
and a human-involvement profile. The policy controls only optional checkpoints
for level-A/N actions. It is evaluated after the Kernel, confirmed task class,
Task Contract, evidence, review, and decision-level gates, and before any action.
The effective permission is the intersection of those controls and any
tighten-only task override.

A profile never lowers a class, suppresses a trip-wire, creates level-P/X
authority, approves a T2/T3 Task Contract, approves a T3 merge, or waives a
dependency, license, test-intent, evidence, or separated-review gate. Missing,
malformed, untrusted, revoked, or expired policy falls back to the
`conservative`/`guided` posture with autonomous merge disabled.

## 2. Gate matrix

Legend: **—** skip · **○** optional / agent's discretion · **●** required · **◆** required + human

| Stage | T0 Mechanical | T1 Contained | T2 Structural | T3 Critical |
|---|---|---|---|---|
| Provisional triage | ● | ● | ● | ● |
| Clarification | ●† | ●† | ●† | ●† |
| Reconnaissance | ○ | ● | ● | ● |
| Confirmed classification | ○ | ● | ◆ | ◆ |
| Task Contract | ● (minimal, author-established) | ● (minimal, author-established) | ◆ (+ plan, human-approved before implementation) | ◆ (+ plan, human-approved before implementation) |
| Implementation | ● | ● | ● | ● |
| Self-verification | ● (E0–E2) | ● (E0–E3) | ● (E0–E6) | ● (E0–E7) |
| Independent review | — | ○ | ● | ● (adversarial + security if trip-wired) |
| Human approval | —‡ | —‡ | ◆ Task Contract before implementation | ◆ Task Contract before implementation + merge approval before integration |
| Integration | ● | ● | ● | ◆ |
| Knowledge update | — | ○ | ● | ● |
| Retro → guardrail | on escaped defect or classification error | on escaped defect or classification error | on escaped defect or classification error | ● (always) |

† Governed by **Spec Confidence**, not class (§3). Clear → no clarification. Partial → written acceptance criteria required first. Vague → Clarification or Spike; implementation prohibited. Identical at T0 and T3.

‡ Class-independent gates override this row. Some decisions require human approval at *any* class (new dependency, license change, weakening test intent — see `core/02-authority.md`). The matrix sets the floor by class; it never waives a decision-level gate.

**Design intent:** T0 and T1 must feel lighter than pre-framework process. If they don't, the framework has failed and will be routed around.

## 3. Spec Confidence — a state machine

Three states, class-independent, apply identically at every class:

| State | Rule |
|---|---|
| **Clear** | No clarification required. Proceed. |
| **Partial** | Written acceptance criteria required before implementation — they become the Task Contract's criteria; at T2+ they are the E4 traceability targets. |
| **Vague** | **Implementation prohibited.** Routes to Clarification or a Spike (§5). |

Transitions: `Partial` → Clarification produces acceptance criteria → re-evaluate → sufficient becomes `Clear` (proceed); insufficient stays `Partial` or drops to `Vague` (do not implement, either way). `Vague` → Clarification or Spike → re-evaluate; never proceeds directly to implementation. **Every task is `Clear` by implementation time, at every class.** Re-evaluation is an explicit act recorded in the Task Contract, not an assumption.

## 4. The Task Contract

Every task has a Task Contract before implementation begins.

| | T0 / T1 — minimal | T2 / T3 — full |
|---|---|---|
| **Contents** | Intended outcome · acceptance criteria · declared scope | The same three, plus an approved plan: approach, invariants touched, evidence strategy, recovery/reversal approach |
| **Form** | Three lines, inline. No document. | An approver's opening, then one screen (`templates/task-contract.md`) |
| **Status before implementation** | **Established** by the author. No human approval required by class — class-independent gates still apply. | **Approved** by a human before implementation. T2: under Architect authority. T3: same, plus separate merge approval. |

"Established" and "approved" are different states. Every task has an established contract before implementation; T2/T3 additionally require human approval. M1 (`modes/execution-modes.md`) operates within an established contract — approved where its class requires it. A Task Contract is not a plan document at T0/T1: three fields, no template ceremony.

## 5. The Spike

When Spec Confidence is Vague, or reconnaissance can't establish blast radius, the output is not code. A **Spike** (`templates/spike-report.md`) is a time-boxed, explicitly **non-mergeable** investigation whose deliverable is a written answer plus a reclassification. Throwaway branch, deleted after. This gives agents a legitimate place for uncertainty instead of inventing requirements.

## 6. Task classes T0–T3

| Class | Definition |
|---|---|
| **T0 — Mechanical** | Deterministic, verifiable by construction: formatting, generated-code regeneration, docs typo, mechanical rename with tool-verified references, dependency version bump within an existing pin policy. |
| **T1 — Contained** | Behavior change inside one ownership boundary, within existing contracts, reversible, Spec Confidence Clear, **and the pattern is authorised for T1 use** — Route 1 or Route 2 below. |
| **T2 — Structural** | Crosses ownership boundaries, changes an interface/contract, neither a ratified precedent nor a covering standing authorization applies (a genuine design decision), or meaningful blast radius. |
| **T3 — Critical** | Any kernel trip-wire fires. Security boundary, irreversible, or high operational/financial consequence. Human at both ends; agents never hold autonomous execution authority. |

Escalation to a higher class is always free and requires no approval. **De-escalation requires the authority of the higher class** — this asymmetry is what stops an agent from talking itself into a cheaper process.

## 7. Precedent and the Pattern Registry

**Precedent means ratified, not merely extant.** Similar code existing in the repository is *not* precedent — it may be drift. Only `RATIFIED` registry entries, an ADR, or the conventions/architecture documents (ratified by construction) satisfy Precedent, and only within the context they were ratified for.

| Registry state | Meaning | Effect on classification |
|---|---|---|
| **`PROVISIONAL`** | An incumbent pattern discovered in the repo. Recorded so it's visible. **Not approved by anyone.** | None. Must not lower a task from T2 to T1. |
| **`RATIFIED`** | Explicitly approved under Architect authority, for a stated context. | Qualifies as Precedent, within that scope. |

No precedent, no covering standing authorization, precedent that doesn't fit the context, or a `PROVISIONAL` entry with no covering authorization → **minimum T2.** You are making a design decision whether or not you notice.

### T1 eligibility — two independent routes

| Route | What it is | Confers |
|---|---|---|
| **Route 1 — Ratified precedent** | An applicable `RATIFIED` registry entry, ADR, or conventions entry | Precedent. Durable, unexpiring, citable by future work. |
| **Route 2 — Standing authorization** | An explicit, scoped, time-boxed authorization (`templates/standing-authorization.md`) covering a `PROVISIONAL` pattern for T1 use | **No precedent.** Permission to execute this pattern under T1 controls, for a stated scope, until a stated expiry. |

**Route 2 never becomes Route 1 by use or by age.** On expiry, or on rejection of the underlying pattern, work under it reverts to minimum T2 until ratified. Ratification is a one-line registry entry (`templates/pattern-entry.md`), not an ADR — an ADR is required only when the pattern is novel and durable, something others will follow.

**Bootstrap:** a new project starts with an empty registry. Seeding happens before classification depends on it, and every seeded entry is `PROVISIONAL`. Where pilot practicality requires a provisional pattern to support T1 work, the instrument is Route 2, approved by a human under Architect authority and recorded (pattern · scope · expiry · grantor).

## 8. Classification authority

Hybrid: trip-wires are mechanical and non-waivable; the agent proposes class at intake (provisional triage); a human confirms at T2+ (◆ in the gate matrix); a sampled audit checks T0/T1 classifications after the fact (`metrics/classification-audit.md`, owned by Phase 2/3). Where one human holds multiple roles, confirmation is one signature recorded against every role it satisfies.

## 9. Escalation and de-escalation

- **Escalation** (to a higher class) is unconditional and requires no approval, at any stage.
- **De-escalation** (to a lower class) requires the authority of the class being left — i.e., the same human authority that would have had to approve work at that higher class.
- A trip-wire firing is never overridden by reversibility, precedent, or any other factor. If a T3 trip-wire fires, no degree of reversibility lowers the task below T3.

## 10. Retro → Guardrail triggers

Stage 11 fires a Retrospective → Guardrail cycle when:

- A defect escapes to main (found after merge), at **any** class.
- A classification was wrong (found via review, incident, or the under-classification audit), at **any** class.
- **Always**, unconditionally, for every T3 change.

**The output is a merged durable guardrail, never a narrative memo alone.** In order of preference: a generated/mechanically enforced control (lint rule, path rule, CI check) · an executable test or check · a classification/path rule (new trip-wire, refined glob) · a kernel or context correction, where missing or incorrect instruction caused the failure. A retrospective that terminates in prose with no behavior-changing control attached has not satisfied this stage.
