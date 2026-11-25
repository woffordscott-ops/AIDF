---
owner: framework-maintainer
load_when: any task requiring role attribution, approval, or a gate decision
max_length: 6 pages
last_verified: 2026-08-19
---

# 02 — Roles, Authority, and Human Gates

## 1. Five roles

Roles are logical and permanently distinct. A human or an agent may wear several, subject to the separation rule (§3) and the performance-vs-approval distinction (§5).

| Role | Owns | Distinct authority | Evidence it produces |
|---|---|---|---|
| **Change Owner** *(human, always)* | Accountability for the merged change | Accepts risk; the only party who can waive a non-trip-wire control | Approval record with stated rationale |
| **Architect** | Contracts, boundaries, invariants, ADRs | Sole authority to change an invariant or interface contract; resolves conflict notices | ADR, conflict resolution, boundary decision |
| **Implementer** | The change itself, within the established Task Contract | May make local decisions where ratified precedent or a covering standing authorization applies; may not create abstractions or alter contracts | Working change + evidence pack |
| **Verifier** *(adversarial)* | The evidence bar | May block a merge at T2+; **may not fix** what it finds | Falsifying cases, failing tests, invariant citations, test-sufficiency judgment |
| **Security Reviewer** | Trust boundaries and threat model | May block unconditionally at T3; may require a design change, not just mitigation | Named attack path with preconditions and impact |

There is no separate infrastructure, data, or documentation role: those are ownership boundaries carrying their own trip-wires, or a definition-of-done obligation on the Implementer — not distinct roles.

## 2. Authority levels

| Level | Meaning |
|---|---|
| **A — Autonomous** | Agent decides and acts. Logged, auditable, revertible. |
| **N — Notify** | Agent acts; a human is informed and may reverse after the fact. |
| **P — Pre-approval** | A human approves the decision or plan before implementation. |
| **X — Human-executed** | A human performs or triggers the action. Agents may prepare it, never run it. |

## 3. Separation of duties

**At T2 and above, the Implementer instance may not be the sole Verifier.** At T3, Implementer, Verifier, and Security Reviewer must be three distinct instances, and at least one must be operating from independently-derived context. **This is mandatory at every team size, including n=1**, where the separated instances are independent AI instances.

**Below T2, separation is not required at all** — not because evidence substitutes for it, but because the blast radius and reversibility of T0/T1 work do not warrant it.

**The T3 Security Reviewer is a separated instance, not a hat.** At n=1 this is normally an independent AI instance operating under the Security Reviewer role. The solo human continues to exercise judgment as Change Owner and Architect — but wearing another hat does **not** satisfy the mandatory separated-instance requirement. A second human may perform the role if available; **none is required by the framework.**

## 4. Solo-capable operation

Roles never merge; role-holders may. One human may hold Change Owner, Architect, and Implementer simultaneously. Exception: on a T3 change the Security Reviewer is a separated instance and cannot be a hat worn by the Implementer's holder.

**No ceremonial self-approval.** A human holding multiple roles signs **once** per decision, not once per hat. If the Architect ratifies a pattern and the Change Owner would approve the same change on the same basis, that is one approval recorded against both roles.

Two different things are bought, and neither substitutes for the other:

| | Evidence independence | Separation of duties |
|---|---|---|
| Supports the claim that | The correctness claim doesn't depend on trusting the author's judgment | A distinct reasoning instance has challenged the author's implementation |
| Satisfied by | Executable, counterfactual evidence; mechanical enforcement | A distinct instance acting as Verifier, and where trip-wired, Security Reviewer |
| Does not cover | Anything the author didn't think to check | A reviewer can be wrong, correlated, or under-informed |

Strong executable evidence reduces dependence on reviewer judgment; **it does not discharge a mandatory separated-instance requirement.**

**Human judgment, not a second human.** Intent, risk acceptance, and irreversibility require human judgment — which under solo operation the Change Owner supplies alone. Nothing here requires a second human; what it requires is that the judgment be made knowingly, under the correct role, and recorded.

**What solo operation does not relax:** trip-wires, required evidence levels, the T3 gate list, and the jurisdiction rule are unchanged at n=1. Solo operation changes *who signs and how often*, never *what must be true*.

## 5. Role performance vs. approval authority

Roles may be **performed** by humans or agents. Authority level **P** means human pre-approval. These are different things.

**An AI instance operating under the Architect role may:** perform architectural analysis, propose decisions, draft ADRs, identify conflicts and write Conflict Notices, recommend ratification, produce options with tradeoffs.

**An AI instance may not:** *approve* anything assigned level P, however thorough its reasoning. The analysis is an input to the decision; it is not the decision.

| Decision | AI may | Human must |
|---|---|---|
| Pattern ratification / standing authorizations | Analyse, recommend, draft the entry | Approve, under Architect authority |
| Interface / contract changes | Design, diff, assess impact | Approve |
| Invariant changes | Propose, draft the rationale | Approve |
| T2/T3 Task Contract approval | Draft the contract and plan | Approve before implementation |
| Architectural conflict resolution requiring approval | Write the Conflict Notice, present options, recommend | Choose |

No redundant signatures: where one human holds Architect and Change Owner, the approval is exercised once and recorded against both roles.

## 6. Gate assignments

| Decision | Level | Note |
|---|---|---|
| Implementation approach with ratified precedent | **A** | The ratification *is* the approval. |
| New abstraction, pattern, or module | **P** | An architecture decision wearing an implementation costume. |
| Interface / contract change (internal) | **P** | Architect. |
| Public or cross-team API breaking change | **P + X** | Human approves and owns the rollout. |
| Architectural invariant change | **P** | Architect + Change Owner; ADR required. |
| Security-boundary, authn/authz, or crypto change | **P** | Security Reviewer findings are required input and may block; the level-P **approval is exercised by a human** under Change Owner authority. At n=1 the Security Reviewer is an AI instance and contributes findings, not approval. |
| T2/T3 Task Contract approval | **P** | T2: human under Architect authority. T3: same, approved before implementation. AI drafts; a human approves. |
| New third-party dependency or license change | **P** | Unconditional, any class. |
| Schema migration — additive/expand | **N** | Reversible form: rehearsed rollback verified. |
| Schema migration — destructive/contract phase | **X** | Human-executed; tested restore, or irreversibility accepted in writing before execution. |
| Any truly irreversible operation | **X** | General rule. Agents may prepare the operation, its evidence, and recovery-point verification, but may not trigger the irreversible act. Irreversibility accepted in writing beforehand. |
| Data deletion or irreversible transformation | **X** | Never autonomous. |
| Infrastructure / IAM / network topology | **P + X** | |
| Production config with immediate blast radius | **P** | |
| Spend commitment above a set threshold | **P** | Threshold is project-level config, not a framework constant. |
| Counterfactual-evidence exemption | **P** | Change Owner at T1; at T2 also Verifier recommendation, residual-risk record, expiry. Not applicable at T0. No exemption exists at T3. Subject to the open-exemption cap. |
| Weakening or removing test intent | **P** | Deliberately gated — this is how green builds get faked. |
| Framework or kernel changes | **P** | The framework governs itself. |
| Reverting an AI-authored change during an incident | **A** | Deliberately ungated — rollback is always the fastest path. Exception: where the revert is itself destructive or irreversible, the revert is **X**. |

## 7. Standing authorizations

A human may pre-approve a *pattern* — scoped and time-boxed ("additive migrations to these tables, following this template, are level N for the next quarter") — using `templates/standing-authorization.md`. This is how gate count stays low without lowering the bar.

**A standing authorization is not a ratified pattern and must not be recorded as one.** It is a separate, expiring record (`pattern · scope · expiry · grantor`) that permits specific work without conferring Precedent. Conflating the two re-launders provisional patterns into approval. In a project with no code yet, where there is no incumbent pattern to enter in the registry, the authorization describes the pattern in its own text; the human grantor, the scope and the mandatory expiry are unchanged.

### Project automation policy

A project automation policy is a separate operating authorization, not a
standing pattern authorization and not Precedent. A human Change Owner and
Architect may select bounded risk and involvement profiles for a named project,
with an approval reference and expiry. It can remove optional checkpoints only
for actions already classified level A or N; it cannot grant P or X authority,
change a task's class, or satisfy a mandatory human gate.

The policy record is protected input, strictly validated, secret-free, and
fail-closed. Task-local overrides may only tighten it. T3 implementation still
requires prior human Task Contract approval and every T3 merge still requires
an action-time human approval after evidence and separated review.

## 8. Anti-ceremony rules

1. **Humans approve decisions, plans, and contracts — not diffs.** Exception: T3, where line-level review is warranted. Asking a human to approve a T1 diff produces skimming, which launders risk rather than mitigating it.
2. **Approval requests must be informed.** State, in under ~200 words: what changes, what could go wrong, what evidence exists, and the recovery/reversal approach appropriate to the operation (`templates/approval-request.md`).
3. **One decision, one signature.** Where a single human holds multiple roles, a decision is approved once, recorded against every role it satisfies.

## 9. Truly irreversible operations

Truly irreversible operations (external side effects, third-party state, published/transmitted data, physically destroyed state) are always level **X**. Execution requires, before the act: (a) a verified recovery point and restore path for whatever *can* be recovered, (b) explicit written identification of what cannot be undone and the consequence, and (c) explicit human acceptance of the irreversibility, recorded in advance under Change Owner authority. Agents may prepare all three; they may never trigger the act itself.
