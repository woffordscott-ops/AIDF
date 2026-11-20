# AI-Assisted Development Framework — Layer 1 (Core) V1.2.2 — Layer 1 Architecture LOCKED

**Status:** Draft for review — not implementation
**Author:** Principal Architect (AI), for review by Scott
**Version:** 1.2.2 — **Layer 1 Architecture LOCKED** · **Date:** 2026-08-19 · Supersedes V1.2.1

**How to read this:** §1 is the critique; §5 consolidates the changes to the original outline. **§0 states the locked layer model. §19.1 is the V1.2.1 → V1.2.2 change log** — start there if you've read V1.2.1. §18 maps your seventeen requested outputs to sections. Everything marked **[R]** is a *recommendation* — I think it's right, but the framework works if you choose differently. Everything marked **[REQ]** is a *requirement* — if you drop it, the framework has a structural hole and I'd argue against shipping without it. **All architecture decisions D1–D11 are resolved** (§16). §15 lists the project facts still needed as configuration — those are inputs, not open design questions.

---

## 0. Locked Framework Model

**[REQ] The framework has three layers.** D7 merged the originally-proposed Layers 3 and 4; this is the current-state model, and any four-layer language elsewhere in this document is historical description of the *original proposal*, not of the framework.

| Layer | Name | Contents |
|---|---|---|
| **Layer 1** | **Core Governance** | This document. Principles, lifecycle, classification, execution modes, roles, authority, architecture governance, verification, review, context, cost. **Locked at V1.2.2.** |
| **Layer 2** | **Tool/Model Qualification** | The qualification eval and the resulting model→mode profile (§6.2). Replaceable; evolves as models change. Built at §17 Phase 7. |
| **Layer 3** | **Project Instantiation** | Produces the project context pack, via two entry paths: **existing-project discovery** and **greenfield decision/bootstrap**. Built at §17 Phase 8. |

---

## 1. Critique of the Proposed Concept

*(Historical: this critique was written against the original four-layer proposal. The resolved model is the three layers in §0 — Layers 3 and 4 were merged by D7, argued in §1.16.)* The layered decomposition is sound and I'd keep it. The concept is not, however, self-evidently correct, and several of its assumptions are load-bearing but weak. Here is where I think it breaks.

### 1.1 Vendor independence is partly an illusion — and the wrong thing to optimize

You want the framework independent of vendors, then propose *capability tiers* as the abstraction. But "deep reasoning" and "engineering reasoning" are not measurable properties; they're marketing categories. A tier system built on them encodes today's model topology into permanent governance — exactly what you said you wanted to avoid — while *appearing* neutral.

The durable abstraction is not model capability. It's **evidence requirement** and **autonomy envelope**: what a piece of work must prove before it merges, and how far an agent may go before a checkpoint. Those are stable across a decade of model progress. Which model can satisfy them is an empirical question that belongs entirely in Layer 2, answered by measurement on *your* codebase, not by vendor claims.

**[R]** Replace "capability tiers" with **execution modes** defined by permission and evidence (§6). Layer 2's job becomes *qualification*: proving that model X can operate in mode M on repo R, via a repeatable eval. This is the only honest way to keep vendor-neutrality real rather than rhetorical.

### 1.2 The dominant failure mode is plausibility, not incorrectness

Human-written bad code usually looks bad. AI-written bad code looks excellent: correct naming, coherent structure, sensible comments, and a subtly wrong boundary condition or a silently dropped requirement. It defeats review-by-reading, which is the review mode humans and AI reviewers both default to.

The consequence for framework design is severe: **review is a weak control here, and executable verification is a strong one.** Your outline gives cross-agent review its own top-level step (Step 10) and treats verification as a philosophy question (Step 9). That's inverted. A framework that layers reviewers without raising the executable-evidence bar will manufacture confident wrongness at higher throughput than you had before.

**[REQ]** The center of gravity of this framework must be the evidence ladder (§10), not the review matrix.

### 1.3 Classification before context is backwards for exactly the cases that matter

Your lifecycle classifies before context acquisition. But blast radius, architectural impact, and reversibility are frequently *unknowable* until someone has read the code. The tasks that get misclassified are the dangerous ones — "just add a field to the user object" that turns out to cross a security boundary.

**[R]** Two-phase classification: cheap **provisional triage** at intake (routing only), then **confirmed classification** after reconnaissance. Escalation is always permitted and requires no approval; **de-escalation requires the authority of the higher class.** That asymmetry is what stops an agent from talking itself down into a cheaper process.

### 1.4 Excess process here has an unusual shape: cheap to produce, expensive to consume

The classic bureaucracy risk is process that costs everyone. The AI-specific risk is different and worse: **artifacts that are nearly free for an agent to generate and expensive for a human to read.** An agent will happily produce a 4,000-word ADR, a 60-item review report where six items matter, and a plan that restates the ticket. Every one of those has negative value — it consumes the scarcest resource in the system (human attention) while creating the appearance of rigor.

**[REQ]** Every artifact intended for human consumption carries a **hard length budget**, enforced in template and in CI where possible. ADR ≤ 1 page. Plan ≤ 1 screen. Review output ranked, with a cap on non-blocking findings. Evidence pack leads with *what would falsify this change*, not with what passed.

### 1.5 Multi-agent coordination: the problem isn't coordination, it's concurrent mutation

Framing this as "coordination" suggests the fix is protocol. In practice the failures are: two agents creating two half-implementations of the same abstraction; merge conflicts in generated code; one agent's refactor invalidating another's in-flight assumptions; and context divergence where two agents hold contradictory beliefs about the same module because they read it at different commits.

**[R]** The unit of parallelism is an **ownership boundary**, not a task. Parallel agents are encouraged across module/service boundaries and discouraged within one. **[REQ]** No two agents hold write authority over the same interface contract concurrently. Contract changes serialize, full stop.

### 1.6 Context management: the framework is itself a context-cost problem

Your Step 13 sketch lists fourteen document categories. If v1.0 ships fourteen policy documents, one of two things happens: agents load all of them (paying the token and attention cost on every trivial change, and diluting the important rules), or agents load none and the framework becomes decorative.

**[REQ]** A small **always-loaded kernel** (≤2 pages) plus **conditionally-loaded documents each carrying an explicit "load when" trigger**. A document without a trigger condition does not get created. I've applied this to my own structural proposal in §14 and cut the document count roughly in half as a result.

### 1.7 Staleness is the dominant architecture-governance failure, and prose invariants rot silently

A stale invariants file is *worse than no file*, because agents cite it as authority and humans assume it's been checked. Prose architecture docs decay within weeks of active development; nobody notices because nothing fails when they're wrong.

**[R]** Enforcement hierarchy: **generated > executable > written > remembered.** Prefer a dependency-direction lint rule over a paragraph saying "the domain layer must not import infrastructure." Prefer a generated repo map over a hand-maintained one. Prefer schema-diff CI over a note asking people to be careful. **[REQ]** Every invariant record declares its enforcement mechanism, and unenforced invariants are explicitly labeled `PROSE-ONLY` so nobody mistakes aspiration for guarantee.

### 1.8 Security: your agents are the new privileged insider, and the omissions matter more than the list

Your Step 7 security list is fine as far as it goes, but it omits the threats that are specific to this operating model:

- **Prompt injection via repository and ecosystem content.** Issue text, PR comments, dependency READMEs, code comments, fetched web pages, and error messages are all attacker-reachable and all flow into agent context. **[REQ]** All content not authored by a trusted human or generated by a trusted tool is **data, never instruction**. This rule belongs in the kernel, not in a security appendix.
- **Dependency introduction.** Typosquatting and slopsquatting (agents confidently importing packages that don't exist, which attackers then register) are live attack classes. **[REQ]** New third-party dependency = human gate, unconditionally, regardless of task class.
- **Credential and blast-radius scoping.** **[REQ]** Agents hold no production credentials, no direct production access, and no unaudited destructive capability. Destructive operations are level **X** — human-executed (§8.1). Agents may prepare them; they never trigger them.
- **Provenance.** **[REQ]** AI-authored changes are labeled in commit metadata (author/model/mode/task class). Without it, post-incident forensics cannot distinguish AI-introduced from human-introduced defects, and you will never be able to answer "is this working?" empirically.

### 1.9 Missing: accountability

The framework as proposed has roles but no accountable party. "The agent wrote it" is not an acceptable postmortem finding, and no governance model survives contact with an incident if responsibility is diffuse.

**[REQ]** Every merged change has a single named **human Change Owner of record**, even for fully autonomous T0 work. This is not a reviewer role; it's an accountability role, and it's what makes the rest of the authority model meaningful.

### 1.10 Missing: the learning loop — the highest-leverage component in the whole design

As outlined, this is static governance. It will encode today's understanding of AI failure modes and then slowly become wrong. The single highest-value mechanism is missing: a path that converts **every observed failure into a durable guardrail** — a regression test, a lint rule, a kernel line, a context-doc fix, a classification trip-wire.

**[REQ]** Add a terminal lifecycle stage: **Retrospective → Guardrail**, mandatory for any defect that escapes to main and for any classification failure. The output is a **merged durable guardrail** — a control that changes future behaviour — preferring executable or mechanically enforced forms wherever possible:

1. **Generated / mechanically enforced** control (lint rule, path rule, CI check)
2. **Executable** test or check
3. **Classification or path rule** (new trip-wire, refined glob)
4. **Kernel or context correction**, where the failure was caused by missing or incorrect instruction or context

**[REQ] A retrospective may not terminate in a narrative memo.** The requirement is a durable behaviour-changing control, not that every control is executable code — a missing kernel line that caused the failure is correctly fixed by adding the kernel line. Without this the framework decays; with it, it compounds.

### 1.11 Missing: instrumentation of the framework itself

You want Layer 2 to map tools to roles. On what basis? Absent measurement, that mapping will be decided by brand loyalty and recency bias — the exact failure you named. And you will have no way to know whether the framework is helping or just adding cost.

**[REQ]** A small metric set from day one (§13.4): change failure rate, rework rate, escaped defect rate by class, **human minutes per merged change**, cost per merged change, and a **two-sided classification-calibration measure** (§13.4). Crude collection is fine. Zero collection is not.

### 1.12 Testing and verification: the load-bearing wall, and agents are unusually good at faking it

Everything above rests on the test suite. AI agents reliably produce tests that pass without testing: asserting on mocks, testing the implementation rather than the behavior, over-stubbing until the test can't fail, and — most damaging — **modifying a failing test until it passes** rather than fixing the code.

**[REQ]** Two rules, both cheap and both high-yield:

1. **The Counterfactual Evidence Principle.** *Evidence must demonstrate that the claimed property depends upon the change being evaluated.* A check that passes identically with and without the change is not evidence of that change — it is evidence about the rest of the system. Reversion testing is the preferred mechanism where it applies; several other mechanisms qualify (§10.3).
2. **Test-integrity separation.** An agent may not weaken or remove test *intent* to achieve a green build. Doing so is an escalation event, not an implementation detail. Assertion-count and coverage deltas are a **detection heuristic** that triggers inspection — they are not, and must never be reported as, evidence that test semantics were preserved (§10.5 rule (b)).

### 1.13 Silent scope expansion

Agents fix things they weren't asked to fix, rename for consistency, and "improve" adjacent code. Each act is defensible; collectively they destroy reviewability, because the reviewer can no longer tell signal from drive-by. This is a top-three cause of AI PRs being abandoned.

**[REQ]** **Declared scope discipline.** The Task Contract (§3.4) declares the files/modules in scope, at every class. Changes outside it are either re-declared or split into a separate change. Enforceable as a CI check against the contract.

### 1.14 Reversibility beats review, and your outline underweights it

The cheapest safety mechanism in AI-assisted development is not a better reviewer. It's **small, reversible changes behind flags with fast rollback.** A framework that invests heavily in review rigor while shipping large irreversible changes has its priorities inverted; a framework that makes changes trivially revertible can afford *less* review for the same risk.

**[R]** Make **change size** and **reversibility** first-class controls: a diff-size cap for autonomous work, feature flags for behavior changes, expand/contract for schema migrations. **[REQ]** Reversibility may reduce **controls, autonomy limits, and assurance cost within a class** where the framework explicitly permits it, and it appears directly in the T1 and T2 class definitions — but it **never overrides a trip-wire**: if a T3 trip-wire fires, no degree of reversibility lowers the task below T3 (§4.4).

### 1.15 Where independent AI review creates false confidence

You asked about this specifically. The mechanisms:

| Mechanism | Why it produces false confidence |
|---|---|
| **Correlated priors** | Models trained on overlapping corpora share blind spots. Two models agreeing is closer to one sample than two. A "second model approved it" signal is systematically overweighted. |
| **Framing anchor** | Give the reviewer the author's plan and rationale and it will largely validate that frame. Most cross-model review is contaminated this way by default. |
| **Diff myopia** | The reviewer sees what changed, not what *should* have changed. Omitted requirements — the most expensive defect class — are nearly invisible to diff review. |
| **Nitpick inflation** | A reviewer asked to find problems will find *something*. Volume of findings gets read as thoroughness; the signal-to-noise collapse trains humans to skim. |
| **No execution** | A review that can't run the code is arguing about a mental model. Adjective-level findings ("this could be racy") are hints, not evidence. |
| **Approval laundering** | The most dangerous one: an AI "LGTM" satisfies a process gate and displaces the human attention that gate existed to purchase. The control fires, the risk is unmitigated. |

**[REQ]** Independent review is only counted as a control when it (a) receives the *requirement and invariants*, not the author's rationale, (b) produces **falsifiable findings** — a specific input, a named invariant, a failing test — and (c) is **tracked for precision** and retired if its yield is low. Adjective-level review may inform, but must never satisfy a gate.

### 1.16 Layers 3 and 4 are the same layer

Onboarding an existing repo and bootstrapping a greenfield one both produce exactly one thing: **the project context pack** (architecture, invariants, contracts, security model, testing strategy, conventions). The difference is only whether that pack is *discovered* or *decided*.

**[R]** Merge them into a single **Layer 3: Project Instantiation** with two entry paths. Two separate layers will diverge, and you'll maintain two descriptions of the same target artifact.

### 1.17 Layer 1 cannot be validated in the abstract

The most likely failure of this project is over-designing v1.0 against imagined failures and discovering on first contact that half of it is unenforceable in your actual CI and the other half is annoying. Frameworks like this are only ever right on the second draft.

**[R]** Build v1.0 deliberately thin, run it end-to-end on **one real repository** for a handful of real changes, and treat the result as the input to v1.1. Budget for deleting things. §17 sequences this explicitly.

### 1.18 What I'd keep unchanged

To be clear about what survives critique: the layered separation (three layers after D7, §0), the replaceable tool-profile layer, progressive rather than uniform governance, explicit human gates, durable version-controlled architecture decisions, and the insistence that AI-generated code meet human standards. Those are all correct, and several of them are things teams commonly get wrong. The concept is good; the risk is in the execution details above.

---

## 2. Framework Principles

Ten principles. Each states what it *rules out*, because a principle that forbids nothing decides nothing.

| # | Principle | What it rules out |
|---|---|---|
| **P1** | **Humans own intent, risk acceptance, and irreversibility.** Every merged change has a named human owner of record. | Agents deciding what to build, accepting risk on the org's behalf, or performing irreversible acts. Diffuse accountability. |
| **P2** | **Evidence determines done — within its jurisdiction.** Executable proof outranks review opinion, which outranks assertion. Evidence settles *falsifiable correctness* and nothing else (§10.1). | "Looks correct," "should work," "I've verified this" as completion criteria. AI approval satisfying a gate without an executable artifact. **Also rules out the inverse error:** green tests read as proof that the requirement, architecture, or risk tradeoff was right. |
| **P3** | **Controls scale with blast radius and reversibility — never with effort or visibility.** | Heavy process on a large-but-safe refactor; light process on a three-line auth change. Ceremony proportional to diff size *as a proxy for risk*. (A diff-size cap on **autonomy** is a different instrument — it bounds how far an agent runs unattended, and does not add process.) |
| **P4** | **Prefer cheap reversal over expensive assurance.** Making a change safe to undo is the first control considered, not the last. | Large irreversible changes justified by heavy review. Migrations with no recovery path at all — where reversal is impossible, §10.4.1's tested restore or explicit irreversibility acceptance is required instead, never nothing. |
| **P5** | **Architecture is an enforced contract, not a description.** Agents comply or stop; they never renegotiate silently. | Implementations that quietly redefine boundaries. Architecture docs as advisory prose. |
| **P6** | **Context is a curated product.** Every durable artifact has an owner, a load trigger, and a freshness signal; unenforceable claims are labeled as such. | Repo-dump context. Monotonically growing instruction files. Confident citation of stale docs. |
| **P7** | **Scope is declared before it is executed.** | Drive-by refactors, opportunistic renames, unreviewable diffs. |
| **P8** | **Independent review must be adversarial and falsifiable.** Reviewers get the requirement, not the author's reasoning, and must produce concrete, checkable findings. | Rubber-stamp cross-model review. Nitpick volume as thoroughness. Correlated agreement read as verification. |
| **P9** | **Every escaped defect or classification failure produces a merged durable guardrail**, preferring executable or mechanically enforced controls wherever possible (§1.10). | Repeating the same defect class forever. Retrospectives that terminate in a narrative memo. *(It does not rule out a kernel or context correction where missing or wrong instruction caused the failure — that is a durable control.)* |
| **P10** | **Quality and acceptable risk are constraints, not variables.** Within those constraints, optimize human attention first and economic/model cost second. Tool selection follows measured fitness on this codebase. | Reducing required assurance to save human attention or model spend — **never a valid justification**. Token-thrift that costs review hours. Brand-based tool assignment. Process that generates reading work faster than it removes it. |

### 2.1 Two cross-cutting rules that the principles imply

**[REQ] The jurisdiction rule.** Three authorities, non-overlapping, and no one of them may be substituted for another:

> **Executable evidence governs falsifiable correctness.**
> **Architectural judgment governs novel design decisions.**
> **Humans govern intent, risk acceptance, and irreversibility.**

Passing tests never imply that the requirement was right, the architecture is sound, the product intent was understood, or the risk tradeoff was acceptable. A fully green T3 evidence pack for the wrong feature is a well-verified mistake. Expanded in §10.1; this is the rule that keeps P2 from swallowing P1 and P5.

**[REQ] The control-selection ladder.** When a risk needs mitigating, choose the *earliest* mechanism on this list that is sufficient for the risk — never a later one because it's easier to reach for:

**1. Reversibility → 2. Mechanical enforcement → 3. Executable evidence → 4. AI verification → 5. Human attention**

Sufficiency is judged against the risk, not against convenience (P10). The ladder chooses *how* to buy assurance; it never chooses *how much*. Same ladder appears in §13.1 as the cost model — it is one concept, stated once in principle terms and once in economic terms.

Two principles from your list I deliberately **did not** keep as separate items, and why:

- *"Agents inspect before editing"* — correct, but it's a lifecycle rule (Reconnaissance, §3), not a principle. Stating it twice weakens both.
- *"Agents should surface uncertainty rather than silently invent requirements"* — absorbed into P2 and the Spec Confidence dimension (§4.3), where it becomes enforceable (vague spec → cannot proceed to implementation) rather than aspirational.

I also dropped *"routine work should remain inexpensive and fast"* as a standalone principle: it's the direct consequence of P3, and repeating it invites the framework to congratulate itself for something P3 already guarantees.

---

## 3. The Work Lifecycle

Eleven stages. Most changes touch five of them. **[R]** The gate matrix in §3.2 is the actual product of this section — the stage list alone governs nothing.

### 3.1 Stages

1. **Intake** — a request enters with a stated outcome. Requests without a stated outcome are rejected, not guessed at.
2. **Provisional triage** — cheap routing only: which domain, is a trip-wire obviously present, is the spec clear enough to proceed. Seconds, not minutes.
3. **Clarification** *(conditional on Spec Confidence, **not** on class)* — fires when Spec Confidence is Partial or Vague, at every class including T0. Output is written acceptance criteria or a **Spike** (§3.3), followed by an explicit **re-evaluation** of Spec Confidence. Implementation begins only from `Clear` (§4.3).
4. **Reconnaissance** — the agent reads before it writes: touched modules, contracts, relevant ADRs, existing tests, prior similar changes. Output includes a **context gap report** (what it needed and couldn't find) — this feeds P9.
5. **Classification (confirmed)** — the real class assignment, now that the code has been seen. Escalation free; de-escalation requires higher-class authority.
6. **Task Contract** *(all classes; depth varies — §3.4)* — the agreed statement of what is being built and how far it may reach. At T0/T1 it is three fields; at T2+ it additionally carries an approved plan.
7. **Implementation** — build within the established Task Contract (approved beforehand where the class requires it).
8. **Self-verification** — the author produces the evidence pack required by class (§10). Not a claim of correctness; artifacts.
9. **Independent review** *(conditional by class)* — adversarial, falsifiable, separated-duty (§11).
10. **Human approval** *(not a chronological stage — see below)* — listed here for completeness only.
11. **Integration → Knowledge update → Retro/Guardrail** — merge; update contracts/ADRs/context docs that the change invalidated; and, if a defect escaped or a classification was wrong, produce a guardrail.

**[REQ] Human approval is a gate attached to the artifact or action it governs, not a late-stage event.** Stage 10 is a conceptual entry, not a position in time. Approvals fire where the thing they govern occurs:

| Gate | Fires |
|---|---|
| **T2/T3 Task Contract approval** | **Before Implementation** (before stage 7) |
| **T3 merge approval** | After self-verification and independent review, **before Integration** (between stages 9 and 11) |
| **All other P/X decision gates** (§8.2) | At the moment the governed decision is made or the governed action is executed — dependency introduction at the point of introduction, irreversible execution at the point of execution, and so on |

The gate matrix row "Human approval" records **which** approvals a class requires, never that they all occur after implementation. Where chronology and the authority rules appear to differ, the authority rules govern.

**[REQ]** Where a change **invalidates a context document, contract, or ADR, updating it is part of the definition of done at every class** — the §3.2 row governs the routine knowledge sweep, not this obligation, and never waives it. A change that invalidates a context document and doesn't update it has left a landmine — this is the single most common way the project context pack rots.

### 3.2 Gate matrix

Legend: **—** skip · **○** optional / agent's discretion · **●** required · **◆** required + human

| Stage | T0 Mechanical | T1 Contained | T2 Structural | T3 Critical |
|---|---|---|---|---|
| Provisional triage | ● | ● | ● | ● |
| Clarification | ●† | ●† | ●† | ●† |
| Reconnaissance | ○ | ● | ● | ● |
| Confirmed classification | ○ | ● | ◆ | ◆ |
| Task Contract (§3.4) | ● (minimal, established by author) | ● (minimal, established by author) | ◆ (+ plan, human-approved before implementation) | ◆ (+ plan, human-approved before implementation) |
| Implementation | ● | ● | ● | ● |
| Self-verification / evidence | ● (E0–E2) | ● (E0–E3) | ● (E0–E6) | ● (E0–E7) |
| Independent review | — | ○ | ● | ● (adversarial + security if trip-wired) |
| Human approval *(fires at the governed artifact/action, not at a fixed point in time — §3.1)* | —‡ | —‡ | ◆ Task Contract **before implementation** (and interface-contract changes at the point of change) | ◆ Task Contract **before implementation** + merge approval **before integration** |
| Integration | ● | ● | ● | ◆ |
| Knowledge update | — | ○ | ● | ● |
| Retro → guardrail | on escaped defect **or** classification error | on escaped defect **or** classification error | on escaped defect **or** classification error | ● (always) |

† **Governed by Spec Confidence, not by class** (§4.3). Clear → no clarification. Partial → written acceptance criteria required before implementation. Vague → Clarification or Spike; implementation prohibited. These rules are identical at T0 and at T3: **task class never bypasses specification clarity.** A change with a genuinely clear spec does not manufacture a clarification round at any class.

‡ **Class-independent gates override this row.** Some decisions require human approval at *any* class — a new third-party dependency or license change (§4.4), weakening or removing test intent (§8.2), and anything else marked **P** or **X** in the §8.2 gate list. The matrix sets the floor by class; it never waives a decision-level gate. A T1 change that adds a dependency still needs approval for that decision — and for that decision only, not for the whole change.

The design intent: **T0 and T1 should feel lighter than your current human process.** If they don't, the framework has failed at P3 and will be routed around. That's the specific way governance dies.

### 3.3 The Spike — a work type your outline is missing

**[REQ]** When Spec Confidence is Vague, or when reconnaissance can't establish blast radius, the correct output is not code. It's a **Spike**: a time-boxed, explicitly **non-mergeable** investigation whose deliverable is a written answer plus a reclassification. Throwaway branch, deleted after.

Without this, agents do the thing they always do with vague specs: invent requirements and implement them confidently. The Spike gives them a legitimate place to put the uncertainty. It is cheap and it prevents the most expensive failure class in the system.

### 3.4 The Task Contract

**[REQ]** Every task has a Task Contract before implementation begins. It is the agreed statement of *what is being built* and *how far the work may reach* — the thing M1 executes against (§6.1) and the thing declared scope is checked against (P7).

| | **T0 / T1 — minimal** | **T2 / T3 — full** |
|---|---|---|
| **Contents** | Intended outcome · acceptance criteria · declared scope | The same three, **plus** an approved plan: approach, invariants touched, evidence strategy, recovery/reversal approach per §10.4.1 |
| **Form** | Three lines. Inline in the task or PR description; no document | One screen (§1.4) |
| **Status before implementation** | **Established** by the author. No human approval required by class — class-independent gates still apply (§3.2‡) | **Approved** by a human before implementation. T2: under Architect authority. T3: under Architect authority, and merge approval follows separately (§3.1) |

**[R]** The minimal form is deliberately close to free. If writing it feels like overhead at T1, the task was probably underspecified — which is the finding, not the friction. **[REQ]** A Task Contract is not a plan document at T0/T1, and the framework must not accrete one there: three fields, no template ceremony.

**[REQ] "Established" and "approved" are different states, and M1 requires the first.** Every task has an **established** Task Contract before implementation begins. At T0/T1 the author establishes it and no human approval is required by class. At T2/T3 it must additionally be **human-approved** before implementation (§7.4) — that requirement is not weakened by anything here.

**[REQ]** M1 therefore operates within an **established Task Contract** — approved where its class requires approval. This resolves what would otherwise be a contradiction between M1 and optional T1 planning, without implying a level-P gate at T0/T1. Nothing at T1 requires a separate plan document.

---

## 4. Task Classification

### 4.1 Recommendation: hybrid — mechanical trip-wires + coarse classes, no weighted scoring

You asked whether scoring, categorical rules, decision trees, or a hybrid works best. **[R] Hybrid: a short list of binary trip-wires that force a class, plus four coarse classes, plus two orthogonal dimensions.**

Against weighted scoring, specifically:

- It manufactures false precision. A 6.4 vs. a 5.9 implies a distinction the inputs cannot support.
- **It is systematically gameable by the thing being scored.** An agent asked to score its own task's complexity will produce defensible numbers that trend low, because low scores unblock work. This isn't malice; it's the gradient. Any self-assessed numeric input to a governance decision will drift downward over time.
- It obscures the decision. When something goes wrong you want to point at "this touched authz," not at a weight vector.

Trip-wires have the opposite properties: mechanically checkable (often from file paths and diff content), un-arguable, and auditable after the fact.

### 4.2 The four classes

| Class | Definition | Feel |
|---|---|---|
| **T0 — Mechanical** | Deterministic and verifiable by construction. Formatting, generated-code regeneration, docs typo, mechanical rename with tool-verified references, dependency version bump within an existing pin policy. | Autonomous, CI-only. Minutes. |
| **T1 — Contained** | Behavior change inside one ownership boundary, within existing contracts, reversible, Spec Confidence Clear, and **the pattern is authorised for T1 use** — either an applicable `RATIFIED` precedent exists, **or** an applicable explicit, scoped, time-boxed standing authorization permits it (§4.3). | Autonomous implementation, evidence required, review optional. Hours. |
| **T2 — Structural** | Crosses ownership boundaries, changes an interface/contract, neither ratified precedent nor a covering standing authorization applies (a genuine design decision), or meaningful blast radius. | Plan approved before implementation. Independent review. ADR if a decision was made. |
| **T3 — Critical** | Any trip-wire fires. Security boundary, irreversible, or high operational/financial consequence. | Human at both ends. Adversarial review by separated instances. Full evidence + recovery evidence appropriate to the operation (§10.4.1). Agents never hold autonomous execution authority. |

### 4.3 Two orthogonal dimensions (assessed separately from blast radius)

**Spec Confidence** — Clear / Partial / Vague. **[REQ] These rules are class-independent.** They apply identically at T0 and T3; task class never bypasses specification clarity, because an unclear T0 change is not a small risk — it is an unknown one.

| Spec Confidence | Rule (all classes) |
|---|---|
| **Clear** | No clarification required. Proceed. |
| **Partial** | **Written acceptance criteria required before implementation** — they become the Task Contract's criteria (§3.4), and at T2+ they are the E4 traceability targets. At T0/T1 they bound scope and define done; there is no E4 step there |
| **Vague** | **Implementation prohibited.** Routes to Clarification or a Spike (§3.3). This is the enforceable form of "agents surface uncertainty instead of inventing requirements" |

**[REQ] Spec Confidence is a state that must reach `Clear` before implementation, at every class.**

- `Partial` → Clarification produces acceptance criteria → **re-evaluate Spec Confidence**.
  - Sufficient → state becomes **`Clear`**; implementation may proceed.
  - Still insufficient → remains `Partial`, or is downgraded to `Vague` — **either way, do not implement.**
- `Vague` → Clarification or Spike → re-evaluate. `Vague` **never** proceeds directly to implementation.

**By implementation time every task has Spec Confidence `Clear`, regardless of class.** This is why the T1 definition (§4.2) can require a clear spec without contradicting the Partial route: Partial is a state a task passes *through*, not a state it implements *in*. Re-evaluation is an explicit act recorded in the Task Contract (§3.4), not an assumption.

**Precedent** — is there an **already-approved** architectural, design, or implementation pattern applicable to *this* context?

**[REQ] Precedent means ratified, not merely extant.** Similar code existing somewhere in the repository is **not** precedent. Existing code may itself be historical drift, an expedient shortcut, or debt that was never a decision — and "the codebase already does this" is the exact reasoning by which drift propagates and compounds. Nothing becomes precedent by surviving.

**[REQ] Pattern registry entries have two states, and only one of them is precedent.**

| State | Meaning | Effect on classification |
|---|---|---|
| **`PROVISIONAL`** | An incumbent pattern **discovered** in the repository. Recorded so it is visible and reviewable. **It has not been approved by anyone.** | **None.** A provisional pattern is *not* architectural precedent and **must not** lower a task from T2 to T1 |
| **`RATIFIED`** | Explicitly approved under **Architect authority**, for a stated context | Qualifies as Precedent, within its stated scope |

Discovery is not approval. Inserting a pattern into the registry records that it exists; it does not record that anyone decided it should. **[REQ]** Only `RATIFIED` entries — or an ADR, or the conventions/architecture documents, which are ratified by construction — satisfy Precedent. Applicability to the current context is part of the test: a ratified pattern used outside the context it was ratified for is *not* precedent.

- Precedent exists and applies → cheaper: the decision is already made, the agent is applying it.
- No precedent **and no covering standing authorization**, precedent that doesn't fit this context, **or a `PROVISIONAL` entry with no covering authorization** → **minimum T2**, because you are making a design decision whether or not you notice. **[R]** This single rule catches most architectural drift, because drift is what happens when novel decisions get processed as routine work.

**[REQ] T1 eligibility has two independent routes, and they are not the same thing.** A contained change may run under T1 controls when *either*:

| Route | What it is | What it confers |
|---|---|---|
| **Route 1 — Ratified precedent** | An applicable `RATIFIED` registry entry, ADR, or conventions entry | Precedent. Durable, unexpiring, citable by future work |
| **Route 2 — Standing authorization** | An explicit, scoped, time-boxed authorization covering a `PROVISIONAL` pattern for T1 use | **No precedent.** Permission to *execute* this pattern under T1 controls, for a stated scope, until a stated expiry |

**[REQ] Route 2 never becomes Route 1 by use or by age.** A standing authorization is separate from the Pattern Registry's `RATIFIED` state, non-precedential, scoped, expiring, and attributable to the approving authority. It permits execution under T1 controls; it does not convert the pattern into architectural precedent. On expiry — or on Phase 4 rejection of the underlying pattern — work under that pattern reverts to **minimum T2** until ratified.

**[REQ] Ratification must be cheap or this rule will be routed around.** Ratifying a pattern is a one-line registry entry (`pattern · scope/context · state · basis · date · ratifier`), not an ADR. **[R]** An ADR is required only when the pattern is *novel and durable* — something others will follow — not merely because a change lacked precedent. Otherwise the Task Contract (§3.4) records the decision and the registry records the pattern.

**Bootstrap — provisional seeding, with an explicit escape hatch.** A new or newly-onboarded project starts with an empty registry. Seeding happens **before** classification depends on it (§17 Phase 3a), and every seeded entry is `PROVISIONAL`. Since provisional entries confer no precedent, an unmodified pilot would classify nearly all work as T2.

**[REQ]** Where pilot practicality requires selected provisional patterns to support T1 work, the instrument is Route 2 above: an **explicit, scoped, time-boxed standing authorization** (§8.3), approved by a human acting under Architect authority (§7.4) and **recorded** — pattern, scope, expiry, grantor. That authorization, not the registry entry, is what permits T1. It expires; the registry entry does not silently become approval by aging.

**[REQ]** §17 Phase 4 reviews every `PROVISIONAL` entry and either **promotes it to `RATIFIED`** or **rejects it as drift**, and any standing authorization issued against a rejected pattern lapses with it. This is the moment the framework distinguishes what the codebase *does* from what it has *decided*, and it is deliberately not skippable.

### 4.4 Trip-wires — any one forces T3

Mechanically checkable where possible (path globs, import graph, schema diff, keyword scan). **[REQ]** These are non-negotiable and cannot be waived by an agent.

1. Authentication, authorization, session, or permission-check logic
2. Cryptography, key management, secrets handling, or token issuance/validation
3. **Destructive or irreversible** data migration, deletion, or transformation of persisted state. (Additive/expand migrations that are reversible and leave existing data intact are not captured here — see §8.2)
4. PII / PHI / regulated data entering, leaving, or changing shape in a flow
5. Payments, billing, entitlements, or anything that moves money
6. Public / cross-team API contract breaking change
7. Infrastructure, network topology, or IAM policy
8. Production configuration with immediate blast radius (feature-flag defaults, rate limits, quotas)
9. Anything that cannot be reverted within one deploy cycle

**Additional gate, class-independent:** introducing a new third-party dependency or changing a license posture → **human approval regardless of class** (see §1.8). It doesn't need to be T3, but it can never be autonomous.

### 4.5 What classification determines

| Determines | Driven by |
|---|---|
| Execution mode permitted (§6) | Class + **applicable pattern authorization** — i.e. an applicable `RATIFIED` precedent **or** an applicable scoped standing authorization (§4.3, both T1 routes). A standing authorization is not precedent; it is execution authority |
| Required context depth (§12) | Class + touched boundaries |
| Task Contract depth | Minimal at T0/T1; plan added at T2+ (§3.4). Written acceptance criteria required at any class when Spec Confidence is Partial (§4.3) |
| Independent review required | Class ≥ T2 |
| Human approval required | Trip-wires + §8 gate list |
| Evidence level required | Class (§10.4) |
| ADR required | Class ≥ T2 **and** the change establishes a novel, durable pattern. Absence of precedent alone → pattern registry entry (ratified, if approved), not an ADR (§4.3) |
| Parallel implementation justified | Rarely — see §11.4 |

### 4.6 Which of your ten dimensions I absorbed, and where

| Your dimension | Disposition |
|---|---|
| Complexity | Dropped as an input. It's a proxy that correlates poorly with risk and invites scoring. Large simple changes are safe; small subtle ones are not. |
| Ambiguity / Specification completeness | Merged into **Spec Confidence** (§4.3) |
| Blast radius | Retained, in the class definitions |
| Architectural impact | Split into **Contract impact** (T2 definition) and **Precedent** |
| Security impact | Promoted to **trip-wires** — too important to be a dimension |
| Data integrity impact | Promoted to **trip-wires** |
| Reversibility | Retained and elevated: it appears in the T1/T2 class definitions, distinguishes otherwise non-trip-wired work, and may lower *controls, autonomy limits, and assurance cost within* a class (P4). **It never overrides a trip-wire** (§4.4) |
| Cross-component scope | Merged into the T2 boundary-crossing definition |
| Operational impact | Trip-wires 7–9 |
| Testability | Moved to the **evidence policy** (§10). Low testability doesn't change class; it changes what evidence is acceptable and often forces a design change instead. |

---

## 5. Recommended Changes to Your Proposed Approach — Consolidated

| # | Your proposal | Recommended change | Why | If you choose otherwise |
|---|---|---|---|---|
| C1 | Capability tiers by reasoning depth | **Execution modes** by permission + evidence; capability is *qualified by eval* in Layer 2 | "Deep reasoning" is unmeasurable and dates fast | Governance quietly encodes a 2026 model snapshot; you re-litigate tiers on every model release |
| C2 | Review as a top-level pillar | **Evidence ladder is the pillar**; review is a supporting control with a precision budget | AI defects are plausible, not obvious; review-by-reading is weak against them | You get higher-throughput confident wrongness and a false sense of coverage |
| C3 | Classify → acquire context | **Triage → recon → confirm class**; escalation free, de-escalation gated | Risk is frequently invisible before reading the code | The dangerous tasks are exactly the ones that get misclassified |
| C4 | ~14 policy documents | **Kernel (≤2pp) + trigger-loaded docs**; 8 documents in v1.0 | Framework's own context cost; unread policy is decorative | Agents load everything (cost, dilution) or nothing (irrelevance) |
| C5 | Layer 3 (onboarding) + Layer 4 (greenfield) | **Merge into Layer 3: Project Instantiation**, two entry paths | Both produce the same artifact — the project context pack | Two descriptions of one target that drift apart |
| C6 | Roles list of 8 | **5 roles** (§7); infra/data/docs are boundaries or DoD obligations, not roles | Roles without distinct authority and evidence are labels | Role proliferation; nobody can say who decides what |
| C7 | Static governance | Add **Retro → Guardrail** lifecycle stage | Framework must convert failures into merged durable controls or it decays | Same defect classes recur indefinitely; framework ages into overhead |
| C8 | No measurement | **Minimal metric set from day one**, incl. human minutes per merged change | Layer 2's tool mapping needs an evidence basis | Tool assignment by brand loyalty — the thing you explicitly want to avoid |
| C9 | No accountability model | **Named human Change Owner of record** on every merge | "The agent did it" is not a postmortem finding | Authority model has no teeth at incident time |
| C10 | Reversibility as one dimension among ten | **Reversibility and change size as first-class controls**; reversibility lowers controls *within* a class and appears in the class definitions but never overrides a trip-wire, change size bounds autonomy | Cheapest confidence in the system | You buy safety with the most expensive currency (human review) |
| C11 | Security as a gate list | Add **untrusted-content rule, dependency gate, credential scoping, provenance labeling** to the kernel | Prompt injection and dependency attacks are the live AI-specific threats | The gate list defends against yesterday's threat model |
| C12 | — | Add the **Spike** work type for Vague specs | Gives agents a legitimate destination for uncertainty | Agents invent requirements and implement them confidently |

---

## 6. Capability Model — Execution Modes

**[R]** Define capability by **what the agent is permitted to do without a checkpoint** and **what it must return**, not by claimed intelligence. Modes are permission envelopes; any model may operate in any mode it has been *qualified* for.

### 6.1 The four modes

| | **M0 Constrained Execution** | **M1 Supervised Implementation** | **M2 Design & Synthesis** | **M3 Adversarial Verification** |
|---|---|---|---|---|
| **Purpose** | Apply a known transform | Build to an **established** Task Contract — approved where the class requires it (§3.4) | Produce plans, options, tradeoffs, ADR candidates | Try to break it |
| **Appropriate** | Codemods, formatting, mechanical rename, generated-code refresh, boilerplate from an existing template | Feature work with precedent, bug fixes with a reproduction, test authoring, refactor within a boundary | Approach options, refactor strategy, migration design, risk analysis, ADR drafting, recon summaries | Falsification, negative/boundary/abuse cases, invariant checking, contract-diff analysis, test-sufficiency judgment |
| **Inappropriate** | Anything requiring judgment; anything where success isn't machine-checkable | Creating new abstractions; changing contracts; anything covered by neither ratified precedent nor a standing authorization | Merging anything; making the decision (it *proposes*) | **Fixing what it finds** (separation of duties) |
| **Context needed** | Kernel + the transform spec + target files | Kernel + established Task Contract + touched contracts + tests + conventions | Kernel + architecture overview + invariants + relevant ADRs + domain model | Kernel + **requirement and invariants** + diff + tests — *deliberately not the author's rationale* |
| **Autonomy** | Full within declared scope | Full within the Task Contract; halts at its boundary | Produces artifacts only; zero write authority to main | Produces findings only; zero write authority to source |
| **Verification of its output** | Machine check (deterministic diff, generator idempotence) | Evidence pack per class | Human or Architect review of the *decision*, not the prose | Findings graded by evidence class (§11.3); reviewer precision tracked |
| **Escalates when** | Transform doesn't apply cleanly; unexpected diff shape | Task Contract is wrong/incomplete; invariant conflict; neither ratified precedent nor a covering standing authorization found; scope would expand | Options conflict with an invariant; decision exceeds its authority (§8) | It cannot construct a falsifying case but still believes there's a defect — say so explicitly rather than manufacturing findings |

### 6.2 Two rules that make modes real

**[REQ] Qualification, not assertion — with a stated bootstrap.** Layer 2 does not exist on day one, and modes are needed from Phase 1, so the rule has two states. **Provisional (Phases 1–6):** a model is *declared* into a mode by the Architect, the declaration is recorded, and the compensating control is that class-required evidence is unchanged — a provisionally-declared M1 agent still produces the full evidence pack, so a bad declaration surfaces as failed checks rather than as merged defects. **Qualified (Phase 7 onward):** a model enters a mode only by passing a repo-specific qualification eval — a fixed set of representative tasks with known-good outcomes, re-run when a model or tool version changes. Layer 2 owns the eval and the resulting mapping. This is the mechanism that makes vendor-neutrality operational instead of aspirational. It also means Layer 2 has a prerequisite: you need the eval before you need the mapping — and the eval's content comes from the pilot phases, which is why declaration has to carry the first six phases. **[R]** Record every provisional declaration; the set of declarations that later failed qualification is the most informative eval material you will ever get for free.

**[REQ] Mode is a per-task assignment, not an identity.** The same underlying model may run in M1 on one task and M3 on another. What must never happen is one *instance* holding both M1 and M3 on the same change **at T2 or above** — that's the separation-of-duties violation that turns independent review into self-review with extra steps. At T0/T1 self-verification is permitted (§7.2) because the blast radius and reversibility of that work do not warrant separation (P3) — **not** because evidence substitutes for it, which it does not (§7.3).

### 6.3 Why not a "fast/cheap" tier

You might expect a fifth tier for cheap high-volume work. I'd resist it: "fast" is an *economic* property, not a capability, and encoding it as a tier invites choosing a mode for budget reasons rather than task reasons. Cost belongs in §13, where it can be traded off explicitly. M0 already covers the work that is genuinely mechanical.

---

## 7. Role Model

**[R]** Five roles. Each earns its place by differing on at least three of: responsibility, context, authority, review perspective, required evidence, escalation behavior. Roles are hats — a human or an agent may wear several, subject to the separation rule (§7.2) and to the performance-vs-approval distinction (§7.4).

| Role | Owns | Distinct authority | Distinct context | Evidence it produces |
|---|---|---|---|---|
| **Change Owner** *(human, always)* | Accountability for the merged change | Accepts risk; the only party who can waive a non-trip-wire control | Business intent, deadline, risk appetite | Approval record with stated rationale |
| **Architect** | Contracts, boundaries, invariants, ADRs | Sole authority to change an invariant or interface contract; resolves conflict notices | Architecture overview, invariants register, ADR history, domain model | ADR, conflict resolution, boundary decision |
| **Implementer** | The change itself, within the established Task Contract | May make local decisions where ratified precedent or a covering standing authorization applies (§4.3); may not create abstractions or alter contracts | Task Contract, touched modules, conventions, tests | Working change + evidence pack |
| **Verifier** *(adversarial)* | The evidence bar | May block a merge at T2+; **may not fix** what it finds | Requirement + invariants + diff; not the author's rationale | Falsifying cases, failing tests, invariant citations, test-sufficiency judgment |
| **Security Reviewer** | Trust boundaries and threat model | May block unconditionally at T3; may require design change, not just mitigation | Threat model, trust boundaries, data classification, auth model, dependency posture | Named attack path with preconditions and impact |

### 7.1 Roles I removed and why

- **Test/Verification Engineer** → folded into **Verifier**. Splitting them creates a boundary dispute over who judges sufficiency. Note the nuance: the *Implementer* writes tests (they know the code); the *Verifier* judges whether those tests constitute evidence. Authoring and adjudicating are the split that matters, not testing and reviewing.
- **Adversarial Reviewer** → that *is* the Verifier. A non-adversarial reviewer isn't a control (§1.15), so the adjective is redundant.
- **Infrastructure Engineer / Data Engineer** → these are **ownership boundaries with T3 trip-wires**, not roles. The responsibility difference is already captured by the trip-wire; adding roles adds nothing to authority or evidence.
- **Documentation Engineer** → documentation is a **definition-of-done obligation** on the Implementer (lifecycle stage 11). A dedicated doc role reliably produces documentation that nobody reads and that the code doesn't reflect.

### 7.2 The separation rule

**[REQ]** At T2 and above, the Implementer instance may not be the sole Verifier. At T3, Implementer, Verifier, and Security Reviewer must be three distinct instances, and at least one must be operating from independently-derived context (see §11.2). Below T2, separation is **not required at all** — not because evidence substitutes for it (it does not, §7.3), but because the blast radius and reversibility of T0/T1 work do not warrant it (P3). This is a risk argument, not a cost argument (P10). **[REQ]** At T2 and above the separated instance is mandatory at every team size, including n=1, where it is an AI instance under §11.2.

**[REQ] The Security Reviewer at T3 is a separated *instance*, not a hat.** For the same T3 change, the Security Reviewer must be a distinct reasoning instance from the Implementer. At n=1 this is normally an **independent AI instance operating under the Security Reviewer role**. The solo human continues to exercise human judgment as Change Owner and Architect on that change — but **wearing another hat does not satisfy the mandatory separated-instance requirement**, because separation buys a distinct line of reasoning, and one person's reasoning is one line however many roles it is labelled with. If a second human is available they may perform the role; **no second human is required by the framework.**

### 7.3 Solo-capable operation (D1: hybrid)

The roles above are **logical and permanently distinct**. What varies with team size is only *how many bodies* fill them.

**[REQ] Roles never merge; role-holders may.** One human may hold Change Owner, Architect, and Implementer simultaneously. **Exception:** on a T3 change the Security Reviewer is a separated *instance* and cannot be a hat worn by the Implementer's holder (§7.2). The framework records which role a decision was made *under* — because the decision's basis, required context, and evidence differ by role even when the person doesn't.

**[REQ] No ceremonial self-approval.** A single human holding multiple roles signs **once** per decision, not once per hat. If the Architect ratifies a pattern and the Change Owner would approve the same change on the same basis, that is one approval recorded against both roles. Requiring a second signature from the same brain on the same facts buys nothing and trains the operator to click through gates — which is a net *reduction* in assurance, not an increase.

**[REQ] Two different things are being bought, and neither substitutes for the other.**

| | **Evidence independence** | **Separation of duties** |
|---|---|---|
| **Claim it supports** | The correctness claim does not depend on trusting the author's judgment | A distinct reasoning instance has challenged the author's implementation |
| **Satisfied by** | Executable, counterfactual evidence (§10.2–10.3); mechanical enforcement | A **distinct instance** acting as Verifier — and, where trip-wired, Security Reviewer |
| **Fails to cover** | Anything the author did not think to check, and every question outside the evidence's jurisdiction (§10.1) | Nothing mechanical — a reviewer can be wrong, correlated, or under-informed (§1.15) |

**[REQ]** Strong executable evidence **reduces dependence on reviewer judgment; it does not discharge a mandatory separated-instance requirement.** The Verifier at T2+ and the Security Reviewer at T3 (§7.2) remain required as distinct instances at every team size, including n=1, where they are AI instances operating under §11.2. Evidence answers "is the claimed property true"; separation answers "did anyone challenge the framing that produced the claim." A change can be exhaustively verified against the wrong claim.

**[REQ] Human judgment, not a second human.** Intent, risk acceptance, and irreversibility require **human judgment** (§10.1) — which under D1 may be exercised by the solo Change Owner. Nothing in this framework requires a *second* human. What it requires is that the judgment be made knowingly, under the correct role, and recorded — not that two people make it.

**[R]** Where a second human *is* available, use them for the judgment calls rather than for diff review. A second person reading a diff is weaker than a check that fails when the property doesn't hold, and it is the most expensive rung on the control-selection ladder (§2.1).

**[REQ] What solo operation does *not* relax.** Trip-wires, required evidence levels, the T3 gate list, and the jurisdiction rule are unchanged at n=1. Solo operation changes *who signs and how often* — never *what must be true* (P10).

**[R] Multi-human readiness.** Record role attribution on every decision from day one, even when it's the same name each time. When a second engineer arrives, the transition is a reassignment of existing role labels rather than a re-design — and the historical record remains legible about which authority was being exercised. This costs one field in a template.

### 7.4 Role performance vs. approval authority

Roles may be **performed** by humans or agents. Authority level **P** (§8.1) means **human pre-approval**. These are different things, and conflating them would let AI reasoning discharge a human gate.

**[REQ] An AI instance operating under the Architect role may:** perform architectural analysis, propose decisions, draft ADRs, identify conflicts and write Conflict Notices, recommend ratification, and produce options with tradeoffs.

**[REQ] An AI instance may not:** *approve* anything assigned level **P**. **AI Architect reasoning does not satisfy a human approval gate**, however thorough. The analysis is an input to the decision; it is not the decision.

Applies without exception to:

| Decision | AI may | Human must |
|---|---|---|
| Pattern ratification (`PROVISIONAL` → `RATIFIED`) and standing authorizations (§4.3) | Analyse, recommend, draft the entry | Approve, under Architect authority |
| Interface / contract changes (§8.2) | Design, diff, assess impact | Approve |
| Invariant changes (§9.2) | Propose, draft the rationale | Approve |
| T2/T3 Task Contract approval (§3.4) | Draft the contract and plan | Approve before implementation |
| Architectural conflict resolution where approval is required (§9.3) | Write the Conflict Notice, present options, recommend | Choose |

**[REQ] No redundant signatures.** Where one human holds Architect and Change Owner, the human approval is exercised **once** and recorded against both roles (§8.3). This rule constrains *who* may approve, never *how many times* the same person must.

**[R]** The practical shape at n=1: an AI Architect instance does the reading and the drafting; you read a one-screen recommendation and approve or don't. That is the intended division of labour, and it is why the length budgets in §1.4 matter more than any other constraint in the framework.

---

## 8. Authority and Human Gates

The design goal is **meaningful human control with the smallest possible number of interruptions.** Every gate you add spends attention you can't get back, so each one has to buy something.

### 8.1 The four authority levels

| Level | Meaning |
|---|---|
| **A — Autonomous** | Agent decides and acts. Logged, auditable, revertible. |
| **N — Notify** | Agent acts; a human is informed and may reverse after the fact. Use where reversal is cheap and the volume is high. |
| **P — Pre-approval** | A human approves the *decision or plan* before implementation. |
| **X — Human-executed** | A human performs or triggers the action. Agents may prepare it, never run it. |

### 8.2 Gate assignments

| Decision | Level | Note |
|---|---|---|
| Implementation approach with **ratified** precedent | **A** | The ratification *is* the approval. A `PROVISIONAL` pattern is not precedent (§4.3) |
| New abstraction, pattern, or module | **P** | This is an architecture decision wearing an implementation costume |
| Interface / contract change (internal) | **P** | Architect |
| Public or cross-team API breaking change | **P + X** | Human approves and owns the rollout |
| Architectural invariant change | **P** | Architect + Change Owner; ADR required |
| Security-boundary, authn/authz, or crypto change | **P** | Security Reviewer findings are **required input** and may block (§7); the level-P **approval is exercised by a human** under Change Owner authority (§7.4). At n=1 the Security Reviewer is an AI instance and therefore contributes findings, not approval |
| T2/T3 Task Contract approval (§3.4) | **P** | T2: human under Architect authority. T3: approved before implementation. AI drafts; a human approves (§7.4) |
| New third-party dependency or license change | **P** | Unconditional, any class (§1.8) |
| Schema migration — additive/expand | **N** | Reversible form: rehearsed rollback verified (§10.4.1) |
| Schema migration — destructive/contract phase | **X** | Human-executed; tested restore procedure, or irreversibility accepted in writing before execution (§10.4.1) |
| **Any truly irreversible operation** — §10.4.1's third form: no restore path exists for some part of the effect | **X** | **General rule.** Human-executed. Agents may prepare the operation, its evidence, and its recovery-point verification, but **may not trigger the irreversible act**, and irreversibility is accepted in writing beforehand (§10.4.1). Operations that are *destructive but recoverable* are covered by the tested-restore form and by the specific rows in this table, not by this rule. Trip-wire 9 governs **classification** (→ T3); this row governs **execution authority** |
| Data deletion or irreversible transformation | **X** | Never autonomous |
| Infrastructure / IAM / network topology | **P + X** | |
| Production config with immediate blast radius | **P** | |
| Spend commitment above a set threshold | **P** | Threshold is a project-level config, not a framework constant |
| Counterfactual-evidence exemption (§10.3) | **P** | Change Owner at T1; at T2 also requires Verifier recommendation, residual-risk record, and expiry; **not applicable at T0** (E3 not required) and **no exemption exists at T3** (D10). Subject to the open-exemption cap |
| Weakening or removing **test intent** | **P** | Deliberately gated — this is how green builds get faked (§1.12). Assertion/coverage deltas *detect* candidates; they do not decide the question (§10.5 rule (b)) |
| Framework or kernel changes | **P** | The framework governs itself |
| Reverting an AI-authored change during an incident | **A** | **Deliberately ungated.** Rollback must always be the fastest path. **Exception:** where the revert is itself destructive or irreversible (reversing an applied migration, dropping written data), the revert is **X** — but the recovery evidence prepared in advance (E7, §10.4.1) is what makes that path fast, not an approval |

### 8.3 Three anti-ceremony rules

**[REQ] Humans approve decisions, plans, and contracts — not diffs.** The exception is T3, where line-level review is warranted. Asking a human to approve a T1 diff produces skimming, which is worse than no gate because it launders the risk.

**[REQ] Approval requests must be *informed*.** A request must state, in under ~200 words: what changes, what could go wrong, what evidence exists, and **the recovery or reversal approach appropriate to the operation** (§10.4.1) — a rehearsed rollback for reversible work, a tested restore for destructive-but-recoverable work, or the named irreversible consequence and the recovery point where the act cannot be undone. An approval request that doesn't say what could go wrong is not asking for a decision; it's asking for a signature.

**[R] Standing authorizations.** A human may pre-approve a *pattern* ("additive migrations to these tables, following this template, are level N for the next quarter"), scoped and time-boxed. This is how you keep gate count low without lowering the bar — and it's a much better tool than lowering a class. At n=1 this is the primary instrument for keeping the operator's attention on decisions rather than on repetitions; **[REQ]** A standing authorization is **not** a ratified pattern and must not be recorded as one — it is a separate, expiring record (`pattern · scope · expiry · grantor`) that permits specific work *without* conferring Precedent. Conflating the two would re-launder provisional patterns into approval, which is exactly what D9 forbids (§4.3).

**[REQ] One decision, one signature.** Where a single human holds multiple roles, a decision is approved once, recorded against every role it satisfies (§7.3). Multi-hat ceremony is a gate that consumes attention and produces nothing.

---

## 9. Architecture Governance

### 9.1 Five artifacts, and only five

| Artifact | Content | Freshness mechanism |
|---|---|---|
| **Architecture Overview** | ≤3 pages: components, ownership boundaries, data flow, trust boundaries, deployment shape | Reviewed on any T2+ boundary change; staleness flagged after N days without review |
| **Invariants Register** | The load-bearing artifact. One row per invariant | Each row declares its own enforcement |
| **Pattern Registry** | One line per pattern: `pattern · scope/context · **state** · basis · date · ratifier`. State is `PROVISIONAL` (discovered, not approved) or `RATIFIED` (approved under Architect authority). **Only `RATIFIED` entries are Precedent** (§4.3) | Provisional entries are reviewed and promoted or rejected in §17 Phase 4; all entries are re-examined in the drift audit (§9.4) |
| **ADR log** | One page each, numbered, immutable; superseded rather than edited | Append-only by construction |
| **Contract registry** | Where interface contracts live (OpenAPI/proto/schemas/module public surfaces) — ideally *generated from source* | Diffed in CI |

**[R]** The pattern registry is a table, not a document — physically it can live as an appendix to the conventions file. It exists as a *governance* artifact rather than a context one because adding a row is an exercise of Architect authority. It is the direct cost of the V1.1 Precedent tightening (§4.3), and I'd rather pay it explicitly than let "existing code" quietly serve as approval.

Everything else you listed — domain model, security model, testing strategy, coding standards, deployment model — belongs to the **project context pack** (§12), not to architecture governance. Governance is about what can't change without a decision; those are descriptions.

### 9.2 The invariant record

**[REQ]** Every invariant carries: `ID · statement · rationale · scope · enforcement · owner · status`.

`enforcement` is the field that matters, and it takes one of four values, in descending order of trust:

- `GENERATED` — the artifact is derived from source; violation is impossible by construction
- `CI-ENFORCED` — a lint rule, import-graph check, schema diff, or architecture test fails the build
- `TEST-ENFORCED` — a specific test asserts it
- `PROSE-ONLY` — **nothing enforces this.** Explicitly labeled so no agent or human mistakes aspiration for guarantee

**[R]** Target: every T3-adjacent invariant is `CI-ENFORCED` or better within two quarters. Track the `PROSE-ONLY` count as a metric — it's a direct measure of how much of your architecture is held together by hope.

### 9.3 Conflict protocol: STOP → DECLARE → ESCALATE

**[REQ]** When an assigned task conflicts with an existing architectural decision, the agent:

1. **STOPS** implementation immediately. It does not implement a partial version, a workaround, or "the spirit of both."
2. **DECLARES** a Conflict Notice: invariant/ADR ID, what the task requires, why they're incompatible, 2–3 options with tradeoffs, and a recommendation.
3. **ESCALATES** to the Architect, then Change Owner if the invariant is to change.

Three sub-rules that close the usual loopholes:

- **"The invariant appears outdated or wrong" is still an escalation, not a license.** It may well be outdated. That's a decision, and it isn't the implementer's.
- **Silence is not consent.** If the agent cannot get a resolution, the change does not proceed. It does not degrade to "best effort."
- **A conflict notice is not a plan.** It is the *end* of the current work item, not a section within it.

### 9.4 Drift detection

**[R]** Beyond CI enforcement, run a periodic (weekly or per-release) drift audit in M2/M3: compare the architecture overview and invariants register against the actual import graph, contract surfaces, and directory structure. Output is a diff, not a report. Most drift is *accretion* — the boundary is still there, but seven things now cross it — which no single change review will ever catch, because each individual crossing was defensible.

---

## 10. Verification Model

### 10.1 Jurisdiction: what evidence can and cannot settle

**[REQ]** Before the ladder, the limit of the ladder. Three authorities, non-overlapping:

| Question | Governed by | Never settled by |
|---|---|---|
| Does the code do what it claims? Does it break anything? Does the invariant hold? | **Executable evidence** | Reviewer opinion; agent confidence |
| Is this the right structure? Should this boundary exist? Is this abstraction sound? | **Architectural judgment** (Architect role, ADR) | Tests. A green suite says nothing about design quality. |
| Should we build this? Is this risk acceptable? Can we live with this being irreversible? | **Humans** (Change Owner) | Tests *or* architectural judgment. Neither can accept risk on the org's behalf. |

**Passing tests never imply that requirements, architecture, product intent, or risk tradeoffs are correct.** They imply that the claimed falsifiable properties hold. A T3 change with a perfect evidence pack, implementing the wrong requirement, is a thoroughly verified mistake — and every element of the framework will have functioned exactly as designed.

Two practical consequences: **(a)** evidence completeness is never an argument for skipping a human gate (§8), and **(b)** an agent may not cite green checks as support for a design or scope decision. Those are different courts.

### 10.2 The evidence ladder

**[REQ]** "Done" is a level on this ladder, not a judgment. Each level is an *artifact*, not an opinion.

| Level | Question answered | Artifact |
|---|---|---|
| **E0** | Does it build? | Build output |
| **E1** | Is it statically clean? | Types, lint, secret scan, dependency/SCA audit, and architecture-lint **where boundary rules exist**. Until an invariants register exists (§17 Phase 4), E1 is the static checks alone — this is a stated gap, not a silent one |
| **E2** | Did I break anything? | Existing suite green |
| **E3** | **Does the claimed property actually depend on this change?** | **Counterfactual evidence** — see §10.3 |
| **E4** | **Does the implementation satisfy the specified executable acceptance criteria?** | Traceability: each acceptance criterion mapped to a specific executing check. **E4 proves conformance to the criteria as specified. It does not prove the requirement was correct, valuable, complete, or aligned with product intent** (§10.1) |
| **E5** | Does it hold under stress? | Negative paths, boundary values, error handling, abuse cases; property/fuzz tests where the domain supports it |
| **E6** | Is the architecture preserved? | Contract diff, invariant checks green, `PROSE-ONLY` invariants explicitly reasoned about, migration dry-run |
| **E7** | Will it behave in production, and can we get back? | Perf/load where relevant, observability in place (does a failure of this change produce a signal?), flag/kill-switch where applicable, and **recovery evidence appropriate to the operation** — see §10.4.1 |

### 10.3 The Counterfactual Evidence Principle (E3)

> **[REQ] Evidence must demonstrate that the claimed property depends upon the change being evaluated.**

A check that passes identically with and without the change tells you something about the system, but nothing about the change. **A test or check that passes regardless of the change is not meaningful evidence** — this is the intent, and it is the thing to preserve when judging any proposed mechanism.

**[R] Reversion testing is the preferred mechanism where it applies** — a new test that fails when the change is reverted. It is mechanically checkable, cheap, and directly expresses the principle. Use it by default for bug fixes and feature behavior.

It does not apply universally, and forcing it where it doesn't fit produces either theatre or exemptions. Acceptable counterfactual mechanisms, chosen for fitness to the change:

| Mechanism | Fits |
|---|---|
| **Reversion test** *(preferred default)* | Bug fixes, feature behavior, most application logic |
| **Before/after reproduction** | Bugs with a reproducible trigger; the repro must be shown failing pre-change |
| **Failure reproduction** | Incident fixes; the original failure condition demonstrably no longer occurs and demonstrably *did* |
| **Mutation testing** | Test-suite strengthening, where the deliverable *is* test quality |
| **Baseline comparison** | Refactors and non-functional changes where behavior should be identical — the counterfactual runs the other way: prove nothing changed against a captured baseline |
| **Contract comparison** | Interface/schema changes; a contract diff showing exactly the intended delta and no other |
| **Performance benchmark** | Performance work; measured against a baseline with a stated significance threshold |
| **Architecture / invariant check** | Structural changes; a boundary or invariant rule that fails on the pre-change tree, or newly holds on the post-change tree |
| **Other falsifiable mechanism** | Anything else, if it demonstrates dependence on the change and is checkable by someone other than its author |

**[REQ] Two guards, so the list doesn't become an escape hatch:**
1. The evidence pack **names the mechanism used and states the counterfactual explicitly** — what would have to be different for this evidence to fail. One sentence.
2. "No mechanism applies" is an **escalation**, not a waiver, and the exemption path is graduated by class (D10):
   - **T0** — **not applicable.** T0 requires only E0–E2 (§10.4), so there is no E3 requirement to be exempted from.
   - **T1** — Change Owner approves an expiring exemption.
   - **T2** — Change Owner approval **and** Verifier recommendation **and** an explicit residual-risk record **and** an expiry. All four.
   - **T3** — **no exemption exists.** Redesign until a mechanism applies, or the change does not ship.
   A hard cap on *open* exemptions applies wherever they are available (**[R]** ≤5); at the cap, new exemptions are blocked until one retires. Expiry is mandatory, and the expiry rule lives with the exemption record in §10.6.

**[R]** Where the change is genuinely untestable, the correct move is usually a design change that makes it testable — not a smaller ladder.

### 10.4 Required level by class

| Class | Required | Rationale |
|---|---|---|
| **T0** | E0–E2 | Verifiable by construction; more is waste |
| **T1** | E0–E3 | E3 is the cheapest high-yield control in the framework — don't skip it to save minutes |
| **T2** | E0–E6 | Contract and invariant preservation is the point of T2 |
| **T3** | E0–E7 + recovery evidence (§10.4.1) + security evidence | Nothing optional |

#### 10.4.1 Recovery evidence — three forms, not one

**[REQ]** E7 requires **the strongest recovery or reversal evidence appropriate to the operation, plus explicit accounting for any effect that cannot be recovered.** It does not assume every operation can be returned to a known-good pre-change state — truly irreversible operations by definition include effects that cannot be undone, and demanding a rehearsed rollback for one is incoherent: it would make the trip-wire that identifies irreversibility unsatisfiable, which in practice means it gets waived. Three forms:

| Operation | Required recovery evidence |
|---|---|
| **Reversible** | **Rehearsed rollback.** The revert path has been executed, not merely written down. Preferred wherever achievable — reversibility is the cheapest control in the framework (P4) |
| **Destructive but recoverable** (data overwritten or deleted, but a restore path exists) | **Tested restore/recovery procedure.** The restore has been exercised against a representative dataset, with a measured recovery time. "We have backups" is not evidence; a restore that has actually been performed is |
| **Truly irreversible** (external side effects, third-party state, published or transmitted data, physically destroyed state) | **(a)** A **verified recovery point** and restore path for the state that *can* be recovered; **(b)** **explicit identification of the irrecoverable effects** — what cannot be undone and what the consequence is — stated in writing, with no implication that it can be reversed; and **(c)** **explicit human acceptance of the irreversibility, recorded before execution** — Change Owner authority, level X (§8.2) |

**[REQ]** The classification into one of these three is itself part of the evidence pack and is subject to challenge by the Verifier. Claiming "reversible" to obtain the cheaper form of E7 is challenged by the Verifier as a separated instance (§7.2), and — because every T3 change carries a mandatory retrospective (§3.2) — a mis-stated recovery form surfaces there. It is *not* covered by the §13.4.1 audit, which samples merged T0/T1 changes only.

**[R]** Where an operation is irreversible only because of *how* it was designed — an in-place migration that could have been expand/contract, a hard delete that could have been a soft delete — the correct response is a design change, not an acceptance record. Reserve the irreversibility acceptance for operations that are irreversible in their nature.

### 10.5 What "done" is *not*

Stated plainly, because these are the states agents routinely report as completion:

| Claim | Actually means |
|---|---|
| "Code generated" | Nothing. A file exists. |
| "It compiles" | E0. Syntax is valid. |
| "Tests pass" | Ambiguous until you know whether any test *could* have failed given this change (hence E3) |
| "Coverage went up" / "assertion count is stable" | A heuristic about volume. Says nothing about semantics (§10.5 integrity rules) |
| "I verified this" / "this looks correct" | **Not evidence.** No artifact, not checkable, not admissible at any class. |
| "Requirements satisfied" | Overclaims. E4 establishes **specified executable acceptance criteria satisfied**, with the mapping shown — never that the requirement itself was correct, complete, valuable, or aligned with intent (§10.1) |
| "Ready for integration" | The class's full level, plus review, plus gates |

**[REQ] Test integrity rules.**

**(a) The rule.** An agent may not weaken or remove **test intent** to achieve a green build. Intent — not line count, not assertion count — is the protected property: replacing a meaningful assertion with a weaker one, widening a tolerance, stubbing out the condition under test, or deleting a case are all violations even when the numbers improve. This is a §8 gate (level P), and it is an escalation, not an implementation detail.

**(b) Assertion and coverage deltas are a heuristic, not proof.** They are cheap to compute and worth computing: a negative delta on a change that should have added coverage is a good reason to *look*. But they are trivially satisfiable while gutting semantics, and they flag legitimate consolidation as suspicious. **[REQ]** They may **trigger review or inspection**; they may **never** be reported — by an agent, a template, or a CI job — as evidence that test semantics were preserved. Only a human or Verifier reading the assertion change can settle that, and only mutation testing can settle it mechanically.

**(c)** Any check that would pass identically whether or not the change were present is reported as a defect in the evidence pack, not silently kept (§10.3). For revert-style mechanisms this is literally "passes with and without"; for baseline, contract, and benchmark mechanisms it means the comparison had no power to show a difference.

### 10.6 The evidence pack

**[REQ]** One page. **The template is class-aware: it carries only the fields the class's required evidence level demands** (§10.4). Fields above that level are marked `not required for this class` or omitted entirely.

| Class | Evidence-pack fields |
|---|---|
| **T0** (E0–E2) | What would falsify this change → what was checked (build, static, existing suite) → residual risk. **No E3 counterfactual field. No E7 recovery field.** |
| **T1** (E0–E3) | The above **+ counterfactual mechanism used and the counterfactual in one sentence** (§10.3) → what was *not* tested and why → any exemption (mechanism, owner, expiry). **No E7 recovery field.** |
| **T2** (E0–E6) | The above **+ negative/boundary/abuse coverage** → **invariants touched** and contract diff. **No E7 recovery field.** |
| **T3** (E0–E7) | The above **+ recovery evidence** (form claimed per §10.4.1 and the artifact demonstrating it) **+ security evidence**. |

Order within a class is as listed: falsification first, evidence next, gaps and residual risk last. **[R]** A task may voluntarily supply stronger evidence than its class requires; nothing above the class-required level is mandatory, and the template must not imply otherwise by leaving empty fields that read as omissions. Leading with the falsification question is what stops the pack from becoming a victory lap, and it's the section a reviewer should read first.

**[REQ] Exemption record and expiry.** Where the pack carries a counterfactual-evidence exemption (§10.3, D10), it records mechanism attempted, approver, residual risk (T2), and **expiry**. **An expiry is mandatory, and an expired exemption reopens the evidence requirement** — the change's evidence is no longer complete until the requirement is met or a fresh exemption is approved within the open-exemption cap. Exemptions do not lapse into permanence.

**[REQ]** The pack states what it does **not** cover: it is evidence of falsifiable correctness only, and carries no claim about requirement fitness, design quality, or risk acceptability (§10.1). One line in the template; it prevents the most consequential misreading available.

**[R]** Low testability doesn't lower the bar; it changes the response. The correct reaction to "this can't be tested" is usually a **design change** that makes it testable, not an exemption. Grant exemptions explicitly, with a named owner and an expiry.

---

## 11. Cross-Agent Review Model

### 11.1 Where independent AI review genuinely pays

Highest yield, roughly in order:

1. **Invariant and contract checking against a written spec** — mechanical, high precision, and the reviewer has an oracle
2. **Requirement→implementation traceability** — "criterion 3 has no corresponding code path" is a finding a diff reviewer can actually make
3. **Test sufficiency** — vacuous tests, missing negative paths, over-mocking
4. **Known-pattern security review** — injection, authz omission, unsafe deserialization, secret handling
5. **Falsifying-case generation** — the single most valuable output: a concrete input that breaks it

Where it pays little, and should not be required:

- **Novel algorithmic correctness without an oracle** — the reviewer shares the author's blind spots (§1.15)
- **Requirement adequacy** — "is this the right thing to build" needs org context the model doesn't have
- **Architectural judgment on genuinely new decisions** — it will produce a plausible essay, and plausibility is the failure mode
- **Style and taste** — pure noise generation; delegate to lint or drop it
- **T0/T1 changes whose class-required evidence is complete.** At **T0** that is E0–E2: the change is deterministic and mechanically verifiable by its class definition, so there is nothing for a reviewer to settle. At **T1** it is E0–E3: the counterfactual evidence has settled the required falsifiable questions. In both cases review adds cost without adding jurisdiction. Note this is *not* a claim that requirements were satisfied — neither class requires E4, so requirement fitness rests on Spec Confidence being `Clear` by implementation time, reached at intake or after clarification (§4.3), not on evidence (§10.1)

### 11.2 Making independence real

**[REQ]** A review counts as an independent control only if:

1. **Clean-room framing** — reviewer receives requirement + invariants + diff. It does **not** receive the author's Task Contract rationale before forming findings. (Optionally it may see the Task Contract afterward, to check contract-vs-implementation drift — a separate, useful pass.)
2. **Independently-derived context** at T3 — the reviewer reads the code itself rather than inheriting the author's summary of it.
3. **Falsifiable output** — every blocking finding names a specific input, a specific invariant ID, or ships a failing test. Adjectives are advisory.
4. **Different instance**, and preferably different model family, though **[R]** treat "different model" as *weak* independence: it reduces correlated error somewhat, it does not eliminate it, and it should never be described in the framework as an independent verification.
5. **Bounded output** — ranked findings, capped non-blocking count. An unbounded reviewer produces noise that trains humans to skim.

**Separation at n=1 (D1-hybrid).** The separated-instance requirement is unchanged at every team size. At n=1 the Verifier (T2+) and Security Reviewer (T3) are **independent AI instances**, distinct from the implementing instance, operating under the five rules above. The solo human's other roles do **not** substitute for them (§7.2); a second human may perform them if available, but none is required. What n=1 changes is *who the instances are*, not *whether they exist* — and strong executable evidence does not remove them (§7.3).

**[REQ]** Evidence independence and separation of duties are complementary, not alternative. A change may carry perfect counterfactual evidence for a claim nobody challenged; separation exists to challenge the claim, not to re-check the arithmetic.

**[REQ]** Judgment calls — intent, risk acceptance, irreversibility (§10.1) — require **human judgment**, which the solo Change Owner supplies. No second human is required, and no amount of AI verification substitutes for the human making the call knowingly and recording it. **[R]** At n=1 the honest instruments for those calls are a deliberate pause before irreversible acts and a written pre-mortem — not an extra signature from the same person.

### 11.3 Disagreement resolution — evidence class ordering

**[REQ]** Conflicts resolve by evidence class, not by seniority, model, or confidence:

| Rank | Evidence | Resolution |
|---|---|---|
| 1 | Reproducible failing case | **Wins automatically.** No discussion, no vote. |
| 2 | Cited invariant or contract violation | Wins unless the invariant is shown not to apply |
| 3 | Cited standard/convention | Author may comply or justify |
| 4 | Reasoned opinion | Advisory only |

**Deadlock rules.** At rank 3–4: these findings are **advisory by definition** — they carry no executable or invariant backing. Below T2, advisory findings do not block; the author may comply or record why not. At T2+, unresolved advisory findings escalate to the Change Owner, because at T2+ the judgment questions are in scope (§10.1). This is not a cost trade: no rank-1 or rank-2 finding is ever defaulted away (P10). **[REQ] Hard cap of two review rounds**, then a human decides. Uncapped agent-vs-agent iteration is one of the largest and least visible cost sinks in multi-agent workflows — two agents will politely converge on nothing for a very long time.

### 11.4 On parallel implementation

**[R]** Parallel implementation by multiple agents is justified in exactly one situation: **the outputs can be compared automatically** (identical test suite, benchmark, or spec-conformance harness) and the decision criterion is defined *before* generation. Otherwise you've bought N candidate solutions and a human judgment problem, which is a cost multiplier disguised as thoroughness. Absent an automatic comparator, prefer one implementation plus a strong Verifier.

### 11.5 Review economics

**[REQ]** Track **finding precision** (blocking findings that were real / blocking findings raised) per review layer. This becomes a required metric as soon as any review layer is running (§13.4). It is also how you find out whether cross-model review works *for your codebase* rather than assuming.

**[REQ]** A layer that sustains low precision is consuming attention and producing false confidence simultaneously — the worst combination available. What happens next depends on whether the layer is *required by class*:

- **Optional layers** (T1 review, any layer added beyond the class minimum) are **retired**.
- **Class-required layers** (independent review at T2+, §3.2 and §7.2) are **re-specified, not removed** — narrow its remit to the finding types where its precision is actually good, tighten its framing (§11.2), or change the instance. Removing a control the class requires is a de-escalation, and it needs the authority that implies (§3.1, D3); it is never a unilateral consequence of a metric.

Low precision in a class-required layer is usually a *framing* failure rather than a capability failure, and the cheap fix is almost always rule 1 of §11.2.

---

## 12. Context Management Model

### 12.1 Three tiers, each with a load trigger

**[REQ]** Every context artifact declares, in front-matter: `owner`, `load_when`, `max_length`, `last_verified`. No trigger, no artifact.

**Tier 1 — Kernel (universal, always loaded, ≤2 pages).** The framework in the smallest form that changes behavior:
principles in one line each · **jurisdiction rule** · **control-selection ladder** · trip-wire list · escalation protocol (STOP/DECLARE/ESCALATE) · definition of done by class · declared-scope rule · untrusted-content rule.
If this doesn't fit in two pages, the framework is too complicated to follow.

**Tier 2 — Project pack (loaded by trigger).** Repo map *(generated)* · architecture overview · invariants register · **pattern registry** · security model & trust boundaries · testing strategy · coding conventions · contract registry *(generated)* · deployment/operational model. Each loads on a condition — e.g. security model loads when a trip-wire fires or the change touches an auth-adjacent path; deployment model loads for infra/config changes only.

**Tier 3 — Task context (assembled per task).** Requirement + acceptance criteria · the touched modules and their contracts · relevant ADRs (by boundary, not all of them) · existing tests for the touched code · the last few changes to those files.

### 12.2 How an agent decides what to read

**[R]** Deterministic first, model judgment second:

1. Kernel — always
2. Path- and diff-triggered Tier 2 documents — mechanical rule (a manifest maps path globs and trip-wires to documents). **[REQ]** The pattern registry loads whenever classification is being determined, since Precedent cannot be assessed without it (§4.3) — and the loaded view must show each entry's `PROVISIONAL`/`RATIFIED` state plus any standing authorization, because that is exactly the field the classification turns on — it is the one Tier 2 artifact with a near-universal trigger, which is an argument for keeping it short
3. Boundary-derived Tier 3 — from the import graph and contract registry of the touched modules
4. **Then** agent-judged additions, which must be *declared* in the recon output

Making steps 1–3 mechanical is what stops both failure modes: the agent that reads everything and the agent that reads nothing. Step 4's declaration requirement is what lets you audit context sufficiency later.

### 12.3 Anti-rot mechanics

- **[R] Generated beats written.** Repo map, contract registry, dependency graph, and coverage should be generated artifacts. Hand-maintained versions of these are guaranteed to be wrong within a month.
- **[REQ] Context-gap reporting.** When an agent needs something and can't find it, that gap is an output — a small, structured note. Gaps are the highest-signal input to improving the context pack, and they're free. Ignoring them is why context packs never improve.
- **[REQ] Anti-accretion rule.** Kernel and Tier-2 documents have hard size caps. Adding a line requires either fitting the budget or removing one. The unbounded `CLAUDE.md`/`AGENTS.md` that grows for a year until it's ignored is the single most common context failure in practice, and the only fix is a cap enforced from day one.
- **[R] Freshness signal.** `last_verified` + a staleness threshold; stale documents are surfaced to agents as "possibly stale," which is far better than silent confident citation.

---

## 13. Cost Governance Model

### 13.1 The real cost model

Optimizing Quality × Velocity ÷ Cost is right, but only if Cost is counted honestly. In practice:

| Cost | Relative weight | Comment |
|---|---|---|
| **Human attention** (review, approval, clarification, reading agent output) | **Dominant** | Fixed supply, doesn't scale, and getting *more* expensive relative to everything else |
| **Rework** (revised PRs, abandoned branches, re-implementation) | High | The main hidden cost of under-specified tasks; also the best single indicator of framework health |
| **Escaped defects** | High, spiky | Severity-weighted; T3 defects can exceed a year of token spend |
| **Technical debt / architectural drift** | High, deferred | Paid later, with interest, by both humans and agents (drift raises everyone's context cost) |
| **Model tokens** | **Low and falling** | Real, but routinely over-weighted because it's the only line item that arrives as an invoice |
| **Agent retries, context re-ingestion, agent-vs-agent iteration** | Moderate | Mostly a symptom of poor context or unbounded review loops |
| **CI compute** | Low–moderate | Watch T3 suites and matrix expansion |

**[REQ] The central cost principle: buy the required confidence at the cheapest available price.** The required level is set by risk and is *not* a cost variable (P10). Within it, use the control-selection ladder from §2.1 — the same ladder, stated economically:

**1. reversibility → 2. mechanical enforcement → 3. executable evidence → 4. AI verification → 5. human attention**

Choose the earliest rung sufficient for the risk. The ladder determines **how** assurance is bought, never **how much**: no position on it justifies delivering less assurance than the class requires.

Human attention is the *most expensive* confidence in the system and should be spent almost entirely where it is the only competent authority — **intent, risk acceptance, and irreversibility** (§10.1) — not on correctness a check could have established. Most teams have this exactly backwards.

Corollary, stated bluntly and bounded: **at equal assurance, spending 5× the tokens to save 20 minutes of human attention is almost always correct.** The "at equal assurance" clause is load-bearing — token-thrift that increases human reading is a false economy, but so is any trade that quietly lowers the bar to buy speed.

### 13.2 Concrete controls

- **Class-based budgets**, tracked and reported, not enforced as a hard stop mid-task (killing a T3 change at 80% completion is the most expensive possible outcome)
- **[REQ] Retry caps** with mandatory escalation, not indefinite retry. Three failed attempts at the same problem is a classification error, not an execution problem — the correct response is re-triage, not another attempt.
- **[REQ] Review round cap** (§11.3)
- **Durable context to eliminate re-ingestion** — the project pack pays for itself in avoided repeated exploration, and this is one of the clearest wins available
- **No parallel duplication without an automatic comparator** (§11.4)

### 13.3 The frugality trap

**[R]** Be explicit in the framework that under-spending is a failure mode with the same standing as over-spending. Running a T2 change through a T0 process to save cost is *the* classic way these systems fail, and it will feel like efficiency right up until it doesn't. The class determines the process; cost optimization happens *within* a class, by choosing the cheapest tool that qualifies for the required mode — never by lowering the class.

### 13.4 Minimum metric set

**[REQ]** Six metrics from day one, collected crudely rather than not at all — plus a seventh (**review finding precision**, §11.5) which becomes required as soon as any review layer is running:

| Metric | Why | Health signal |
|---|---|---|
| **Human minutes per merged change** (by class) | The scarce resource; the framework's core justification | Falling for T0/T1, stable for T3 |
| **Rework rate** (% of AI-authored changes needing >1 substantive revision) | Best early indicator of context or spec problems | Falling |
| **Change failure rate** (merges causing incident/rollback) | Governance effectiveness | Flat or falling as volume rises |
| **Escaped defect rate by class** | Whether classification is calibrated | T3 ≈ 0; if T1 is high, classification is too loose |
| **Cost per merged change** | Economic sanity | Watch trend, not absolute |
| **Classification calibration — two-sided.** (i) *Escalation precision*: escalations that were correct. (ii) **Under-classification rate**: from a sampled audit of merged T0/T1 changes, the share that should have been T2/T3 | Whether classification is honest in **both** directions | (i) too low → noise, and agents learn to stop escalating. (ii) **any non-trivial rate is a live governance failure** — and it is the direction that is invisible without deliberate sampling |

**[REQ]** The seventh — **review finding precision** (§11.5) — activates with the **first review layer actually run**, which may be an optional T1 review during Phase 3, and is unconditional from Phase 5 when T2/T3 review becomes mandatory. It's the only way to answer "is cross-model review worth it here" empirically, and that answer is the main input to Layer 2 (Phase 7).

#### 13.4.1 The under-classification audit

**[REQ]** Escalation precision measured alone is actively misleading: a system that escalates almost nothing scores near-perfect precision while systematically under-classifying risk. The failure mode this framework is most exposed to is **silent under-classification**, and by construction it generates no signal — the change merged, nothing visibly broke, no one looked.

The mechanism, deliberately minimal:

- **Cadence: throughput, not calendar.** Every **20 merged T0/T1 changes**, audit **3** (D11). Calendar cadence under-samples at high volume and produces empty rituals at low volume.
- **One-time pilot calibration audit.** Phase 3 merges only 8–12 changes, which never reaches the 20-change trigger. At the end of Phase 3, run a single calibration audit over 3 Phase-3 changes — same 1-random-plus-2-weighted composition, same M3 analysis, same Change Owner adjudication, same guardrail output. **[REQ]** This is an **initialization step**: it does not reset, redefine, or substitute for the normal 20-change cadence, which begins counting from the first merge and fires on schedule thereafter.
- **Composition: 1 random + 2 weighted.** The two weighted picks target trip-wire boundaries, security-adjacent paths, and unusual classifications. The **random** pick is what can surface a failure mode nobody hypothesised — it is not optional padding.
- **Ask one question:** given what is now known, should this have been T2 or T3? Record yes/no and, if yes, which signal was missed.
- **Run it as M3** (adversarial verification); the **human Change Owner adjudicates disagreements**, since whether a risk was under-weighted is a judgment call (§10.1). No second human is involved.
- **[REQ] The output is a merged durable guardrail, not a report** (P9, §1.10): a missed signal becomes — in order of preference — a mechanically enforced rule, an executable check, a new trip-wire or path rule, or a kernel/context correction where missing or incorrect instruction caused the misclassification. An audit that produces only a number, or only a memo, has not paid for itself.

**[R]** Track the two directions separately and never net them against each other. Over-escalation costs attention; under-escalation costs incidents. They are not interchangeable, and a single blended "accuracy" number will hide the one that matters.

---

## 14. Proposed Framework Repository Structure

### 14.1 The principle applied to itself

Your sketch implies ~14 documents. I'm proposing **8 governance documents plus templates** (one of them the always-loaded ≤2pp kernel), because §1.4 and §1.6 apply to this repository as much as to anything it governs. If I can't hold the framework to its own length discipline, it has no standing to impose it.

**Neither V1.1 nor V1.2 added a core document.** Every change landed inside an existing one. V1.1 added templates and one metrics note; V1.2 added `task-contract.md`, `standing-authorization.md`, and renamed `ratified-pattern.md` to `pattern-entry.md` — all of them artifacts an agent fills in, not prose a human must read. That was a deliberate constraint on this revision, and it's the right test for any future change: if it needs a new policy document, it probably isn't thin enough yet.

```
ai-dev-framework/
├── README.md                    What this is · how a project adopts it · index · version
├── KERNEL.md                    ★ ALWAYS LOADED, ≤2pp. Principles (1 line each),
│                                  jurisdiction rule, control-selection ladder,
│                                  trip-wires, escalation protocol, DoD by class,
│                                  declared-scope rule, untrusted-content rule
│
├── core/
│   ├── 01-lifecycle.md          Stages · gate matrix · Spike · Task Contract ·
│   │                              classification (trip-wires, classes,
│   │                               Spec Confidence states, Precedent: the
│   │                               PROVISIONAL/RATIFIED registry states and the
│   │                               two T1 eligibility routes — classification
│   │                               consumes these, so they ship in Phase 1)
│   ├── 02-authority.md          Roles (5) · authority levels · gate list ·
│   │                              separation of duties · solo-capable operation ·
│   │                              standing authorizations
│   ├── 03-architecture.md       Invariants register · pattern registry *process*
│   │                              (ratification, promotion, drift audit) ·
│   │                              ADR policy · contract registry ·
│   │                              STOP/DECLARE/ESCALATE · drift audit
│   ├── 04-verification.md       Jurisdiction rule · evidence ladder ·
│   │                              Counterfactual Evidence Principle · level-by-class ·
│   │                              test integrity · evidence pack format
│   ├── 05-review.md             When review pays · independence rules ·
│   │                              disagreement resolution · review economics
│   └── 06-context-and-cost.md   Context tiers & triggers · anti-rot ·
│                                  cost model · budgets · metric definitions
│
├── modes/
│   └── execution-modes.md       M0–M3 definitions + qualification eval requirements
│                                  (the stable contract Layer 2 implements against)
│
├── templates/                   ← the part agents actually use day to day
│   ├── task-contract.md         ├── evidence-pack.md    ├── adr.md
│   ├── conflict-notice.md       ├── review-findings.md  ├── invariant.md
│   ├── approval-request.md      ├── spike-report.md     ├── pattern-entry.md
│   ├── standing-authorization.md
│   └── exemption.md             (counterfactual exemption: mechanism, owner, expiry)
│
├── profiles/                    ← LAYER 2 (stub in v1.0)
│   ├── README.md                Schema for a tool/model profile + qualification protocol
│   └── qualification-eval/      Empty. Populated when you have a pilot repo.
│
├── instantiation/               ← LAYER 3, merged (stub in v1.0)
│   ├── README.md                Target artifact: the project context pack
│   ├── onboard-existing.md      (stub) discovery path
│   └── bootstrap-new.md         (stub) decision path
│
├── metrics/
│   ├── definitions.md           The metric set · collection method · review cadence
│   └── classification-audit.md  Under-classification audit: sampling rule,
│                                  question, guardrail output (§13.4.1)
│
└── CHANGELOG.md                 Framework is versioned; projects pin a version
```

### 14.2 Structural decisions worth noting

- **Every document has front-matter** (`owner`, `load_when`, `max_length`, `last_verified`). Machine-consumable and self-enforcing.
- **Templates are the highest-leverage directory.** In practice, agent behavior is shaped far more by the shape of the artifact it must fill in than by policy prose it may or may not read. A well-designed evidence-pack template does more work than a well-argued verification policy. **[R]** If you build only one thing from this proposal, build KERNEL.md + templates.
- **`modes/` is separate from `core/`** because it's the stable interface Layer 2 depends on. Keeping it separate means Layer 2 can iterate without touching governance.
- **Stubs are real files with schemas, not empty directories.** They document the seam so that Layers 2 and 3 attach cleanly rather than being retrofitted.
- **The framework governs itself:** kernel changes are level P (§8.2), framework version is pinned per project, and framework changes affecting gates need an ADR of their own.

### 14.3 The consolidation tradeoff

Six core documents rather than twelve means less precise targeting ("read the evidence-ladder section" vs. "read verification.md"). **[R]** Mitigate with stable anchor headings and a `load_when` manifest that can reference anchors, not whole files. I judge the coherence and freshness benefit of fewer files to outweigh the targeting cost — twelve documents drift apart, six stay consistent, and consistency matters more than precision when the reader is a model that will infer around gaps.

---

## 15. Remaining Inputs — Project Facts, Not Architecture Questions

**[REQ] These are not open Layer 1 decisions.** Every framework-architecture question is resolved (D1–D11, §16). What follows is **project-instantiation information** — facts about your environment that the framework consumes as configuration. None of them changes the design, but they are **not all needed at the same time**, and treating them as a single Phase-3 bundle would stall Phase 2.

| # | Input needed | `required_by` | Consumed by | If unfavourable |
|---|---|---|---|---|
| 1 | **CI enforcement capability** — branch protection, required checks, ability to add lint/checks, a working revert path | **Before Phase 2** | D4 / Phase 2 controls | Building it is a **prerequisite project**, not a framework detail. **This is the only input that can genuinely delay the plan.** |
| 2 | **Test-suite baseline** — is existing coverage trustworthy, and what does it cover | **Assessed before Phase 2** | E2/E3 design; counterfactual mechanism selection (§10.3) | Weak coverage makes E3 expensive at first and shifts mechanism choice toward baseline/contract comparison. Assess it before designing the spine, not after |
| 3 | **Agent execution authority and credential scope** — branch write, CI trigger, cloud/prod reach | **Before agents perform governed execution in Phase 1–2** | §8 authority levels; §1.8 least-privilege | The §8 model is only as strong as the scoping beneath it. Scope credentials before the first governed agent run, not after |
| 4 | **Regulatory / compliance obligations** (SOC 2 / HIPAA / PCI) | **Before the pilot's gates are finalized — i.e. before Phase 3b** | §8 gate list, audit trail, retention | Adds audit-trail and separation requirements *on top of* the framework. Cheap to add before the pilot runs; expensive to retrofit onto merged history |
| 5 | **Pilot repository selection** | **Before Phase 3** | D8 / Phase 3a discovery | Phase 3a cannot seed a registry for an unnamed repo |
| 6 | **Interactive vs. long-running autonomous agents** | **Before assigning any execution mode that depends on it** (Phase 1 mode declaration) | §6 modes; checkpoint/interrupt design | v1.0 assumes mostly-supervised. Long-running autonomy needs checkpoint/interrupt design — a **later framework increment**, and modes must not be declared as if it were already handled |
| 7 | **Second-engineer availability and timing** | **Informational only — blocks nothing** | §7.3 role reassignment | Nothing in the framework requires a second human (§7.2, §7.3). This affects only how much the compensating controls carry |

**[REQ]** Inputs 1–3 are needed **before or during Phase 2** and inputs 4 and 6 before the work they govern begins; only input 5 is genuinely a Phase-3-entry item. Phase 0 and Phase 3 text reflect this and must not be restated as "all project inputs arrive at Phase 3."

**Resolved by D1–D11 and therefore *not* listed here** — recorded so they aren't reopened as if open: whether the framework governs prompts and infrastructure (D5: yes), where the framework lives (D2: submodule), who classifies (D3: hybrid with sampled audit), whether metrics start now (D6: yes), whether Layers 3 and 4 merge (D7: merged), and whether AI may modify the framework (§8.2: propose yes, approve human).

## 16. Decisions — D1–D11, All Resolved

**All eleven decisions are resolved.** D1–D8 were settled in the V1.1 review; D9–D11, which those resolutions surfaced, are settled in V1.2 (§16.1). No Layer 1 architecture decision remains open.

### D1 — Human gate model · **RESOLVED: (c) Hybrid — solo-capable now, multi-human ready later**

**Decision:** Logical roles (Change Owner, Architect, Implementer, Verifier, Security Reviewer) remain permanently distinct. One human may hold several. A solo operator is never forced through redundant ceremonial approvals for holding multiple roles. Separated-instance verification is retained unchanged at T2/T3 and is not discharged by executable evidence (§7.3) or by the solo human holding another role (§7.2); at n=1 the Verifier and Security Reviewer are independent AI instances. Roles may be *performed* by agents, but level-**P** approval is always exercised by a human (§7.4). Judgment calls require human judgment, which the solo Change Owner supplies — no second human is required anywhere in the framework.

**Implemented in:** §7.3 (solo-capable operation) · §8.3 (one decision, one signature) · §11.2 (independence as a property of reasoning, not headcount).

**What this deliberately does *not* relax:** trip-wires, required evidence levels, the T3 gate list, and the jurisdiction rule (§10.1) are identical at n=1. Solo operation changes who signs and how often, never what must be true.

**Residual risk to watch:** at n=1 the Change Owner is also the person under schedule pressure, so the "accept the risk" and "ship it" decisions are made by the same brain in the same moment. Executable evidence and the under-classification audit (§13.4.1) are the compensating controls; there is no structural substitute, and the framework should say so plainly rather than imply otherwise.

### D2 — Framework distribution · **RESOLVED: (a) git submodule**, with a path to a package at >2 adopting projects

**Options:** (a) Git submodule per project. (b) Published package (npm/pip/OCI) with a pinned version. (c) Copy-in with a sync script.

**Tradeoffs:** Submodule is simplest and keeps docs readable in-repo, but upgrades are manual and tend to rot. Package gives real version semantics and clean upgrades, at the cost of tooling and indirection. Copy-in is frictionless day one and unmaintainable by project five.

**Recommendation:** **(a) submodule for v1.0**, with a clear path to (b) once more than two projects adopt it. Don't build package infrastructure for a framework that hasn't survived its first pilot.

**If you choose differently:** (b) means building release tooling before the framework has earned it; (c) means abandoning per-project version pinning, which undermines "adapts as tools improve."

### D3 — Classification authority · **RESOLVED: (c) hybrid** — mechanical trip-wires, agent proposes, human confirms at T2+, sampled audit

**Options:** (a) Agent self-classifies. (b) Human triages everything. (c) **Hybrid**: trip-wires are mechanical (path/diff rules in CI, non-waivable), agent proposes class, human confirms at T2+, plus a sampled audit of T0/T1 classifications.

**Tradeoffs:** (a) is fast and drifts downward. (b) doesn't scale and reintroduces the bottleneck the framework exists to remove. (c) costs a small audit budget.

**Recommendation:** **(c)**, with the audit sample deliberately weighted toward changes *near* trip-wire boundaries. Misclassification is the single most likely governance failure, and it's invisible unless you sample for it.

**If you choose differently:** with (a), add mandatory post-hoc classification audit on every incident; with (b), expect a queue and plan for batching.

**V1.1 refinement:** the sampled audit is now specified as a two-sided calibration measurement with a mandatory guardrail output (§13.4.1), not merely a confidence check. Under D1-hybrid, "human confirms at T2+" means one signature covering every role the confirmation satisfies (§8.3).

### D4 — Enforcement posture · **RESOLVED: (b) CI-enforced where mechanical**, advisory elsewhere

**Options:** (a) Advisory documentation. (b) **CI-enforced where mechanical**, advisory elsewhere. (c) Fully enforced.

**Recommendation:** **(b).** The *posture* applies from day one: **CI-enforced wherever mechanical.** Individual controls activate **as soon as their prerequisite artifacts exist** — the posture is immediate, the coverage is phased, and the difference is stated rather than glossed.

| Control | Activates |
|---|---|
| Trip-wire detection by path/diff · declared-scope check against the Task Contract · counterfactual-mechanism declared and machine-checked where the mechanism permits (E3) · assertion/coverage delta flagging *as an inspection trigger* · dependency-addition gate · secret scan | **Phase 2** — prerequisites already exist |
| **Architecture / invariant lint** | **Phase 4** — requires the invariants register and boundary rules, which do not exist earlier |

**[REQ]** The Phase-3 E1 gap (architecture-lint absent) is therefore a **rollout condition, not a policy exception**: the rule is in force, its mechanism is not yet buildable, and the gap is declared in §17 Phase 3 and in E1's own definition. Advisory-only frameworks are complied with when convenient, which is precisely when compliance doesn't matter.

**If you choose differently:** advisory-only requires a compensating audit function and, realistically, halves the framework's effect.

**V1.1 refinement:** two enforcement items changed character. The E3 check enforces *that a counterfactual mechanism is declared and, where the mechanism permits, that it holds* — not universal reversion testing (§10.3). Assertion/coverage delta is enforced as an **inspection trigger only**; CI must not emit it as a semantics-preserved signal (§10.5 rule (b)).

### D5 — Governance scope · **RESOLVED: (b)** code + infrastructure + data + agent configs/prompts/skills

**Options:** (a) Application code only. (b) **Code + infrastructure + data + agent configs/prompts/skills.**

**Recommendation:** **(b).** Prompts and agent configurations change system behavior; excluding them creates an ungoverned channel into the system, and it's the channel most likely to be edited casually.

**If you choose differently:** (a) is simpler but you'll need an explicit note that agent-config changes are outside the framework — and a plan for the day one of them causes an incident.

### D6 — Metrics from day one · **RESOLVED: (a) instrument now**, crudely

**Options:** (a) Instrument now, crudely. (b) Defer until v1.1.

**Recommendation:** **(a).** Even a spreadsheet updated weekly. Without baseline data you can never establish that the framework helped, and Layer 2's tool mapping will be decided by impression.

**If you choose differently:** deferring means Layer 2 ships on vibes, and you lose the before/after comparison permanently — you can't retroactively measure a baseline.

### D7 — Merge Layers 3 and 4 · **RESOLVED: merged** into Layer 3 (Project Instantiation), two entry paths

**Recommendation:** **Merge** (§1.16). Two entry paths, one target artifact.

**If you choose differently:** keeping them separate is defensible if greenfield work will use a substantially different process (e.g. requirements and architecture phases with their own gates). If so, tell me and I'll design the seam accordingly.

### D8 — Pilot repository · **RESOLVED: (b)** a real but non-critical repository

**Options:** (a) Highest-value production repo. (b) **A real but non-critical repo.** (c) Multiple simultaneously.

**Recommendation:** **(b).** Real enough that the framework meets actual mess; safe enough that v1.0's mistakes are cheap. (c) is premature — you'll be changing the framework weekly during the pilot.

**If you choose differently:** (a) means v1.0's rough edges hit your most important codebase; if you take that path, restrict the pilot to T0/T1 changes initially.

**V1.1 refinement:** the pilot is now split. T0/T1 runs before architecture governance exists; T2/T3 runs only after the minimal context pack and invariants register make E6/E7 satisfiable (§17). The T0/T1 phase seeds the pattern registry as `PROVISIONAL` and runs on recorded standing authorizations (§4.3, D9).

---

### 16.1 D9–D11 — Resolved

All three are decided. **No Layer 1 architecture decision remains open.**

#### D9 — Precedent bootstrap · **RESOLVED: hybrid seeding, provisional state**

**Decision:** The seed pass discovers incumbent patterns and records them as **`PROVISIONAL`**. Provisional entries are **not** precedent and **must not** lower a task from T2 to T1. Ratification to `RATIFIED` requires **Architect authority**. Where the pilot needs selected provisional patterns to support T1 work, the instrument is an **explicit, scoped, time-boxed standing authorization**, recorded (pattern · scope · expiry · grantor). Phase 4 promotes acceptable provisional patterns to `RATIFIED` or rejects them as drift; dependent authorizations lapse on rejection.

**Implemented in:** §4.3 (two-state registry, bootstrap) · §9.1 (Pattern Registry) · §8.2–8.3 (standing authorization) · §17 Phases 3a and 4.

**Why this is better than what V1.1 proposed:** `basis: incumbent, unreviewed` was a label, not a control — the entry still functioned as precedent, so drift would have been laundered exactly as feared, just with a footnote. Making provisional entries inert, and forcing an explicit expiring authorization where the pilot needs an exception, means every case of "we're treating incumbent code as approved" is a dated, named, revocable act.

#### D10 — Counterfactual-evidence exemptions · **RESOLVED: graduated by class, hard cap, none at T3**

| Class | Exemption path |
|---|---|
| **T0** | **Not applicable** — E3 is not required at T0 (§10.4), so there is nothing to exempt |
| **T1** | Change Owner may approve an expiring exemption |
| **T2** | Change Owner approval **+ Verifier recommendation + explicit residual-risk record + expiry**. All four; a missing element is a refusal |
| **T3** | **No counterfactual-evidence exemption exists.** If the property cannot be shown to depend on the change, the change is redesigned until it can be, or it does not ship |

**[REQ]** A hard cap on **open** exemptions applies wherever exemptions are available — T1 and T2 (**[R]** ≤5). At the cap, a new exemption is blocked until one is retired or expires. Exemptions never lapse into permanence: expiry is mandatory, and an expired exemption reopens the evidence requirement rather than closing the question.

**Implemented in:** §10.3 (guard 2) · §10.6 (exemption record) · `templates/exemption.md`.

**Note on the T3 rule:** this is the strictest thing in the framework, and deliberately so. T3 is where irreversibility and security boundaries live; "we could not demonstrate that this works because of our change" is precisely the state in which an irreversible act must not proceed.

#### D11 — Under-classification audit · **RESOLVED: throughput-based, 3 of every 20**

**Decision:** Every **20 merged T0/T1 changes**, audit **3**: **1 selected at random**, **2 weighted** toward trip-wire boundaries, security-adjacent paths, or unusual classifications. A **one-time pilot calibration audit** of the same shape runs at the end of Phase 3, because that phase never reaches 20 merges; it initializes the practice without altering the cadence (§13.4.1, §17 Phase 3c). **M3 performs the analysis; the human Change Owner adjudicates disagreements** (a judgment call, per §10.1). **[REQ]** Any discovered under-classification produces a **guardrail** — a new trip-wire, path rule, kernel line, or classification example — not merely a metric entry (P9).

**Implemented in:** §13.4.1 · §13.4 · `metrics/classification-audit.md`.

**Why the random one matters:** the two weighted picks find what you already suspect. The random pick is the only part of the sample that can surface a failure mode nobody has hypothesised yet, and it is the first thing that will feel wasteful and be dropped. It should not be.

---

## 17. Recommended Build Sequence for v1.0 *(restructured in V1.1)*

**Ordering principle:** build controls that are cheap, mechanical, and enforceable first; defer everything requiring taste, data, or a specific repo. **Correctness principle added in V1.1: no phase may claim to validate a workflow whose required controls do not yet exist.** V1.0 violated this — it piloted T2/T3 changes (requiring E6 architecture evidence and E7 operational evidence) before the invariants register, contract registry, and deployment model that make E6/E7 satisfiable existed. The pilot is now split in two, with the controls built in between.

| Phase | Deliverable | Depends on | Effort |
|---|---|---|---|
| **0 — Design lock** | V1.2.2 accepted; **Layer 1 LOCKED**. D1–D11 are all resolved; no architecture decision is outstanding. Project inputs (§15) are supplied on the `required_by` schedule in that table — **inputs 1–3 before Phase 2**, not at Phase 3 | You | This week |
| **1 — Core framework** | `KERNEL.md` (≤2pp, incl. jurisdiction rule + control-selection ladder) · templates · `01-lifecycle.md` (classes, trip-wires, Spec Confidence states, Task Contract, and the pattern-registry **states plus both T1 eligibility routes** — Phase 3a seeds a registry, so its schema and semantics must exist here, not in Phase 4) · `02-authority.md` (roles, gates, solo-capable operation) · `modes/execution-modes.md` (M0–M3 + the declared-vs-qualified rule, needed from this phase on) | Phase 0 | Days. **The minimum that changes behavior.** |
| **2 — Verification spine** | `04-verification.md` (incl. §10.4.1 recovery forms) · evidence-pack and exemption templates · `metrics/definitions.md` + `metrics/classification-audit.md` (needed before Phase 3 collects a baseline) · CI: counterfactual-evidence check, declared-scope check against the Task Contract, trip-wire detection, dependency gate, secret scan, assertion/coverage delta as *inspection trigger* | Phase 1 + D4 | Days. Highest ROI per hour in the plan. |
| **3 — T0/T1 pilot** | **3a (entry):** discovery pass → seed pattern registry, every entry `PROVISIONAL` (D9); Architect issues scoped, time-boxed **standing authorizations** for the handful of provisional patterns the pilot needs to run as T1, each recorded with an expiry. **3b:** 8–12 real T0/T1 changes. **3c (exit):** one-time **pilot calibration audit** — 3 Phase-3 changes (1 random + 2 weighted), M3 analysis, Change Owner adjudication, guardrail output (§13.4.1). **Outputs:** baseline metrics, calibration audit, friction log, registry grown in-flight | Phases 1–2 + D8, D9 | 1–2 weeks. Evidence required is E0–E3. **Stated gap:** E1 runs without architecture-lint until Phase 4 — the boundary rules don't exist yet, and T0/T1 changes by definition don't cross boundaries. Modes are *declared*, not qualified (§6.2). |
| **4 — Project context + architecture governance** | Minimal context pack (repo map *generated*, architecture overview ≤3pp, security model, testing strategy, conventions) · `03-architecture.md` (**ratification and drift-audit process**; the registry's states shipped in Phase 1) · invariants register with CI enforcement where mechanical (**this completes E1**) · contract registry · ADR log · **every `PROVISIONAL` pattern promoted to `RATIFIED` or rejected as drift**, with dependent standing authorizations lapsing on rejection (§4.3) · deployment/operational model · `06-context-and-cost.md` (context tiers and triggers, now that there is a pack to trigger on) | Phase 3 — **needs a real repo and real friction to be meaningful** | 2 weeks. **This is what makes E6 and E7 satisfiable.** |
| **5 — T2/T3 pilot** | `05-review.md` (written first — this is the phase that turns on separated-instance review) · 2–4 structural changes and one T3 (with recovery evidence per §10.4.1 and security evidence). Exercise STOP/DECLARE/ESCALATE at least once — deliberately, if it doesn't happen naturally | Phase 4 | 1–2 weeks |
| **6 — Framework revision (framework v1.1)** | Revise from both friction logs. **Expect to delete 20–30%.** Re-baseline metrics | Phases 3 + 5 | Days |
| **7 — Tool qualification (Layer 2)** | Qualification eval + first profile mapping Claude Code / Codex / Cursor to M0–M3, grounded in Phase 3 and 5 data | Phase 6 — **needs data** | 1 week |
| **8 — Project instantiation (Layer 3)** | Onboarding and bootstrap playbooks generalized from Phase 4, which performed the work once by hand | Phases 4, 6 | 1–2 weeks |
| **9 — Prune** | Metric review; delete every control that hasn't earned its keep. Under-classification audit on cadence (D11) | Phase 7+ | Recurring |

### Sequencing rationale

- **Phases 1–2 first** because the kernel, the templates, and the counterfactual-evidence check deliver most of the value at a fraction of the total cost. A project that stalls after Phase 2 is still meaningfully ahead.
- **Phase 3 before Phase 4** — the T0/T1 pilot needs only E0–E3, which Phase 2 supplies apart from the architecture-lint component of E1 (declared as a gap above rather than quietly skipped). Running it first buys the friction data that makes Phase 4 concrete instead of speculative. Note the ordering *within* Phase 3: pattern **discovery and the standing authorizations built on it** are entry conditions, because classification cannot consume a registry the work has not yet produced. **Ratification** is deliberately *not* a Phase 3 activity — Phase 3 runs on `PROVISIONAL` entries plus explicit expiring authorizations, and Phase 4 does the ratify-or-reject pass once there is enough architectural context to judge (§4.3).
- **Phase 4 before Phase 5**, strictly. This is the V1.1 correction: T2 requires E6 (contract diff, invariant checks) and T3 requires E7 (recovery evidence, observability). Those are Phase 4 outputs. Piloting T2/T3 earlier would have measured compliance with controls that didn't exist — the most self-deceiving thing this framework could do.
- **Phase 7 late, deliberately.** Mapping specific tools to modes before qualification data exists would encode today's impressions as governance. Phases 1–6 run on *declared* modes with unchanged evidence requirements (§6.2), which is the honest bridge — declaration is visibly provisional, whereas an early eval would look authoritative while measuring nothing. By Phase 7 at least one of the three tools will have changed enough to prove the point.
- **Phase 9 is not optional.** A framework that only accretes becomes the bureaucracy you were avoiding. Scheduled deletion is a feature.

### What I would still *not* build in v1.0

Multi-agent orchestration protocols · a scoring engine · agent definitions for all five roles (start with Implementer and Verifier) · per-language conventions · a dashboard. All premature or data-dependent.

---

## 18. Crosswalk to Your Seventeen Requested Outputs

| You asked for | Section |
|---|---|
| 1. Critique of the concept | §1 |
| 2. Recommended changes | §5 (consolidated); argued in §1 |
| 3. Core framework principles | §2 |
| 4. Proposed task lifecycle | §3 |
| 5. Task-classification model | §4 |
| 6. Capability model | §6 |
| 7. Role model | §7 |
| 8. Authority / human-approval model | §8 |
| 9. Architecture-governance model | §9 |
| 10. Verification model | §10 |
| 11. Cross-agent review model | §11 |
| 12. Context-management model | §12 |
| 13. Cost-governance model | §13 |
| 14. Proposed repository structure | §14 |
| 15. Major unresolved questions | §15 — now **project inputs**, not open architecture questions (all resolved) |
| 16. Decisions requiring human input | §16 (D1–D8) · §16.1 (D9–D11) — **all resolved** |
| 17. Recommended build sequence | §17 |

---

---

## 19. Change Log

### 19.1 V1.2.1 → V1.2.2 — Layer 1 Architecture LOCKED

Mechanical lock patch. No new role, class, mode, evidence level, layer, or architecture decision; D1–D11 untouched.

| # | Correction | Sections |
|---|---|---|
| 1 | **Three-layer model stated as current state** (§0 new): Layer 1 Core Governance · Layer 2 Tool/Model Qualification · Layer 3 Project Instantiation (discovery + greenfield paths). Surviving "four-layer" text marked historical | §0 (new) · §1 intro · §1.18 |
| 2 | **Lifecycle approval ordering made explicit.** Human approval is a gate attached to the artifact or action it governs, not a late chronological stage: T2/T3 Task Contract approval **before** implementation; T3 merge approval after verification/review and **before** integration; other P/X gates at the point the governed decision or action occurs. No second approval stage added | §3.1 stage 10 · §3.2 Human-approval row |
| 3 | **"Established" vs "approved" Task Contract.** Every task has an **established** contract before implementation; T0/T1 the author establishes it with no class-required human approval; T2/T3 require human approval before implementation. M1 operates within an *established* contract | §3.4 · §6.1 · §7 · §3.1 stage 7 |
| 4 | **Reversibility no longer described as reducing required class.** It reduces controls, autonomy limits, and assurance cost *within* a class, appears in the T1/T2 class definitions, and distinguishes otherwise non-trip-wired work — but **never overrides a T3 trip-wire** | §1.14 · §4.6 · §5 C10 |
| 5 | **§4.5 execution-mode input corrected** from "Class + Precedent" to class + applicable pattern authorization, covering both T1 routes. Standing authorization remains non-precedential | §4.5 |
| 6 | **E7 opening principle generalized.** E7 requires the strongest recovery/reversal evidence appropriate to the operation **plus explicit accounting for any irrecoverable effect** — it no longer implies every operation can be returned to a known-good pre-change state. Three forms retained | §10.4.1 |
| 7 | **Evidence pack made class-aware.** T0 → E0–E2 fields; T1 → +E3 counterfactual; T2 → +E5/E6; T3 → +E7 recovery + security. Fields above the class-required level are marked `not required for this class` or omitted. Stronger evidence remains voluntary | §10.6 |
| 8 | **T0 removed from the E3 exemption path** — T0 requires only E0–E2, so there is nothing to exempt. Exemptions: T1 Change Owner; T2 Change Owner + Verifier recommendation + residual-risk record + expiry; T3 none. Cap retained | §10.3 · §16.1 D10 · §8.2 |
| 9 | **§11.1 T0/T1 wording separated.** T0 completes E0–E2 (deterministic, mechanically verifiable); T1's E3 counterfactual evidence settles the required falsifiable questions. Optional review remains unnecessary when class-required evidence is complete | §11.1 |
| 10 | **"Requirements satisfied" summary corrected** to "specified executable acceptance criteria satisfied," preserving the jurisdiction rule | §10.5 |
| 11 | **Guardrail requirement made consistent.** Every escaped defect or classification failure produces a **merged durable guardrail**, preferring generated/mechanical → executable check → classification/path rule → kernel/context correction. A retrospective may not end in a memo | §1.10 · §2 P9 · §13.4.1 · §5 C7 |
| 12 | **Exemption expiry rule relocated** into §10.6 beside the exemption record, making the §10.3 cross-reference valid; expired exemptions reopen the evidence requirement | §10.6 · §10.3 |
| 13 | **The V1.0→V1.1 log's V1.2 independence reference** repointed to the V1.1→V1.2 log (post-renumbering: §19.4 item 1 → §19.3) | §19.4 |
| 14 | **Historical "Clear at intake" wording annotated** as superseded; current rule is `Clear` by implementation time via Partial → Clarification → re-evaluate | §19.2 · §19.4 · §11.1 |

#### V1.2.2 mechanical sweep result

Full-document mechanical verification run after the fourteen corrections above. **No unresolved internal contradiction found.**

| Check | Result |
|---|---|
| Layer model — three layers, D7 and current-state text agree | Pass (§0; four-layer text marked historical in §1 and §1.18) |
| Classification — T0–T3, both T1 routes, standing authorization never Precedent, trip-wires override lower-class eligibility, reversibility never overrides a T3 trip-wire, Spec Confidence `Clear` by implementation time | Pass |
| Task Contract — T0/T1 established without human approval unless a class-independent gate fires; T2/T3 human-approved before implementation; M1 terminology matches | Pass |
| Authority — **P** always human approval, **X** always human execution, no redundant solo signatures, T3 Security Reviewer separated, irreversible execution X | Pass |
| Evidence — E0–E7 only; T0 E0–E2, T1 E0–E3, T2 E0–E6, T3 E0–E7; evidence-pack fields conditional on required level; E3 exemptions T1/T2 only, none at T0 or T3; E4 within jurisdiction; E7 coherent for irreversible operations | Pass |
| Guardrails — both triggers, durable merged control, executable/mechanical preferred, prose/context permitted where it addresses the cause, no memo-only termination | Pass |
| Build sequence — no phase consumes a later artifact; all §14 governance files scheduled; project inputs available by their required phase; Phase-3c calibration audit separate from the D11 cadence | Pass |
| Cross-references — every §X / §X.Y resolves and matches | Pass (0 dangling) |
| Numbering — §0–§19 including §10.4.1, §13.4.1, §19.1–§19.4 | Pass (no gaps, duplicates, or out-of-order entries) |
| Counts — ten principles · five architecture artifacts · four classes · four modes · four authority levels · ten classification dimensions · nine counterfactual mechanisms · eleven lifecycle stages · six base metrics + conditional seventh · eight governance documents · seventeen crosswalk entries | Pass |
| Evidence terminology — no legacy L-prefixed evidence levels remaining | Pass |

A second mechanical pass after these corrections found seven further defects — the T2 Task Contract matrix cell marked non-human, a stale "locked at V1.2.1" in Phase 0, four §19 subsection citations left behind by the renumbering, and a §1.8 clause permitting non-human execution of destructive operations. All seven are corrected above; a third pass found none.

**Layer 1 is LOCKED at V1.2.2.**

### 19.2 V1.2 → V1.2.1 — Layer 1 Architecture Lock Candidate

Consistency patch only. No new governance concepts; no architecture reopened.

| # | Correction | Sections |
|---|---|---|
| 1 | **T1 eligibility given two routes.** Route 1: applicable `RATIFIED` precedent. Route 2: applicable explicit, scoped, time-boxed standing authorization. Route 2 permits execution under T1 controls and **confers no precedent**; it never becomes Route 1 by use or age, and on expiry or Phase-4 rejection the work reverts to minimum T2 | §4.2 T1 · §4.3 (routes table) · §8.2–8.3 · §12.2 · §17 Phase 3a |
| 2 | **Role performance separated from approval authority** (§7.4 new). An AI instance under the Architect role may analyse, propose, draft ADRs, write Conflict Notices, and recommend ratification. It may **not approve** anything at level **P**. Applied explicitly to pattern ratification, interface/contract changes, invariant changes, T2/T3 Task Contract approval, and conflict resolution. No redundant signatures for a multi-hat solo human | §7.4 (new) · §7 intro · §16 D1 |
| 3 | **Solo Security Reviewer rule made unambiguous.** At T3 the Security Reviewer is a distinct reasoning *instance* from the Implementer; at n=1 that is an independent AI instance. The solo human still exercises judgment as Change Owner and Architect but **does not satisfy the separated-instance requirement by wearing another hat**. A second human may perform the role; none is required | §7.2 · §7.3 · §11.2 · §16 D1 |
| 4 | **Phase 3 audit cadence fixed.** Phase 3 merges 8–12 changes and never reaches the 20-change trigger, so a one-time **pilot calibration audit** (3 changes, 1 random + 2 weighted, M3 analysis, Change Owner adjudication, guardrail output) runs at Phase 3c. It is an initialization step and does **not** reset or redefine the normal D11 cadence | §13.4.1 · §16.1 D11 · §17 Phase 3 |
| 5 | **Project inputs given per-item `required_by`.** CI capability and test baseline before Phase 2; credential scope before governed execution in Phase 1–2; compliance before the pilot's gates are finalized; pilot repo before Phase 3; autonomy model before mode assignment; second engineer informational only. Phase 0 text corrected | §15 (rewritten) · §17 Phase 0 |
| 6 | **Recovery terminology propagated.** Approval requests state the recovery/reversal approach appropriate to the operation; the evidence pack carries a recovery-evidence field rather than a universal `rollback`; P4 and the migration rows permit tested restore or explicit irreversibility treatment. Rehearsed rollback retained as the preferred form for genuinely reversible changes | §8.3 · §10.6 · §2 P4 · §8.2 · §3.4 |
| 7 | **General irreversible-execution authority rule added** to §8.2: execution of any truly irreversible operation is level **X**, human-executed; agents may prepare the operation and its evidence but may not trigger the act. Existing specific rows are instances of this rule, not exceptions | §8.2 · aligns with §10.4.1, trip-wire 9 |
| 8 | **Retro → Guardrail triggers corrected** in the gate matrix: T0–T2 now read "on escaped defect **or** classification error," matching P9 and the §13.4.1 audit's guardrail requirement | §3.2 · consistent with §13.4.1 |
| 9 | **Spec Confidence made an explicit state transition.** Partial → clarification → re-evaluate; sufficient becomes `Clear`, insufficient stays `Partial` or drops to `Vague`, and neither implements. Vague never proceeds directly. **Every task is `Clear` by implementation time, at every class** — which is what reconciles the T1 clear-spec requirement with the Partial route | §4.3 · §3.1 stage 3 |
| 10 | **D4 rollout wording corrected.** Posture (CI-enforced wherever mechanical) applies from day one; individual controls activate when their prerequisites exist. Phase 2 enables the controls whose prerequisites exist; architecture/invariant lint activates in Phase 4. The Phase-3 E1 gap is a **rollout condition, not a policy exception** | §16 D4 · §17 Phases 2–4 · §10.2 E1 |
| 11 | **Final mechanical sweep run** — results in the table under this section | throughout |

#### Conflicts found and resolved in the V1.2.1 sweep (under §19.2)

14 findings, all closed. The ones that mattered:

| Conflict | Resolution |
|---|---|
| §7.3 still listed Security Reviewer among the roles a solo human may wear, contradicting the §7.2/§11.2 separated-instance rule | §7.3's example changed to Change Owner/Architect/Implementer, with the T3 Security Reviewer exception stated inline |
| §8.2's security-boundary row named the Security Reviewer as approver, which at n=1 is an AI instance barred by §7.4 from level-P approval | Row split: Security Reviewer supplies **findings** (and may block); the **human** approves under Change Owner authority |
| M1's inappropriate-work and escalation rules still said "no precedent → escalate", which would have escalated every Route-B task in the Phase 3 pilot | Both rewritten to "neither ratified precedent nor a covering standing authorization"; §7 Implementer row likewise |
| §4.2's T2 definition and §4.3's first escalation clause still routed all no-precedent work to T2, ignoring Route 2 | Both qualified with "and no covering standing authorization" |
| The new general irreversibility row keyed off trip-wire 9 (one deploy cycle), which also captures destructive-but-recoverable work that §10.4.1 says a tested restore suffices for | Row re-keyed to §10.4.1's **third form** (no restore path). Trip-wire 9 governs classification; the row governs execution authority |
| §7.4 assigned T2/T3 Task Contract approval to level P, but §8.2 — the table §3.2‡ treats as authoritative — had no such row | Row added to §8.2 |
| §14 put the pattern registry in `03-architecture.md` (Phase 4) while Phase 3a seeds a registry classification depends on | Registry **states and eligibility routes** moved to `01-lifecycle.md` (Phase 1); `03-architecture.md` keeps the ratification and drift-audit **process** |
| §3.1 made knowledge update unconditional while §3.2 marked it skip/optional at T0/T1 | Obligation scoped: updating an *invalidated* artifact is part of done at every class; the matrix row governs the routine sweep only |
| §13.4 fixed the seventh metric's activation at Phase 5, but optional T1 review can run in Phase 3 | Activates with the first review layer actually run; unconditional from Phase 5 |
| Trip-wire 3 ("data migration") forced T3 while §8.2 gave additive/expand migrations level N | Trip-wire 3 narrowed to **destructive or irreversible** migrations; additive/expand explicitly excluded |
| §11.1 still relied on the spec being "Clear at intake" after Spec Confidence became a state transition | Reworded to **"Clear by implementation time"**, which is the current rule: `Partial → Clarification → re-evaluate → Clear → Implementation` (§4.3). "Clear at intake" describes the superseded V1.2 wording only |
| §4.3's heading claimed its dimensions don't set class, while Precedent sets a T2 floor and Spec Confidence sits in the T1 definition | Heading corrected |
| The V1.1→V1.2 log (now §19.3) claimed "15 findings" over an 11-row table | Reworded: 15 findings consolidated into 11 resolutions |

### 19.3 V1.1 → V1.2 — Architecture Candidate for Lock

| # | Change | Sections |
|---|---|---|
| 1 | **E7 rollback generalized into recovery evidence.** Three forms: reversible → rehearsed rollback; destructive-but-recoverable → tested restore with measured recovery time; truly irreversible → verified recovery point for what *can* be recovered + written statement of what cannot + **human acceptance of irreversibility recorded before execution**. The form claimed is itself evidence and is challengeable | §10.2 E7 · §10.4 · §10.4.1 (new) · §4.2 T3 · §8.2 |
| 2 | **Evidence independence separated from separation of duties.** Two distinct claims with distinct satisfiers; **executable evidence does not discharge a mandatory separated instance.** Verifier at T2+ and Security Reviewer at T3 remain distinct instances at every team size, including n=1 where they are AI instances. All "second human required" wording removed — the requirement is **human judgment**, which the solo Change Owner supplies | §7.3 (rewritten) · §7.2 · §11.2 · §6.2 · §16 D1 |
| 3 | **Pattern registry given two states.** `PROVISIONAL` (discovered, confers no precedent, cannot lower T2→T1) vs `RATIFIED` (Architect authority, is precedent). Pilot exceptions run on **explicit scoped time-boxed standing authorizations**, recorded separately and never themselves ratified patterns. Phase 4 promotes or rejects every provisional entry | §4.3 · §9.1 · §8.2–8.3 · §12 · §17 Phases 3a, 4 |
| 4 | **Spec Confidence made class-independent.** Clear → proceed · Partial → written acceptance criteria before implementation · Vague → Clarification or Spike, implementation prohibited. Identical at T0 and T3; class never bypasses specification clarity | §4.3 · §3.1 stage 3 · §3.2 (Clarification row + footnote †) |
| 5 | **Task Contract introduced**, replacing the Planning stage. Minimal at T0/T1 (outcome · acceptance criteria · declared scope); plus an approved plan at T2/T3. M1 operates within a Task Contract, resolving the M1-vs-optional-T1-planning conflict without adding a document at T1. *(V1.2.2 replaced "approved" with **established** for T0/T1 — §19.1 item 3.)* | §3.4 (new) · §3.1 stage 6 · §3.2 · §4.5 · §6.1 · §7 |
| 6 | **D9–D11 resolved.** D9: provisional seeding + Architect ratification + expiring standing authorizations. D10: exemptions by class — T1 Change Owner; T2 Change Owner + Verifier recommendation + residual-risk record + expiry; **T3 none**; **T0 not applicable** (V1.2.2); hard cap on open exemptions. D11: every 20 merged T0/T1 changes audit 3 (1 random + 2 weighted), M3 analyses, Change Owner adjudicates, output is a guardrail | §16.1 (rewritten) · §10.3 · §10.6 · §13.4 · §13.4.1 · §8.2 |
| 7 | **Evidence levels renamed E0–E7.** Namespace is now T0–T3 class · M0–M3 mode · E0–E7 evidence · Layer 1–3 framework layer. All references updated | throughout |
| 8 | **E4 tightened** to "does the implementation satisfy the specified executable acceptance criteria," with an explicit statement that it does not prove the requirement was correct, valuable, complete, or aligned with intent | §10.2 · §10.1 preserved |
| 9 | **Stale open-decision text removed.** §16 retitled; front matter corrected; Phase 0 no longer requires answers it already has. **§15 rewritten** from "unresolved questions" into **project inputs** — configuration facts, not design questions — with resolved framework decisions listed explicitly so they are not reopened. *(V1.2.1 added per-input `required_by` timing — §19.2.)* | Front matter · §15 (rewritten) · §16 · §17 Phase 0 · §18 |
| 10 | **Second consistency sweep run** (independent adversarial pass). 15 findings, consolidated into the 11 resolutions below — all closed | throughout |

#### Conflicts found and resolved in the V1.2 sweep (under §19.3)

| Conflict | Resolution |
|---|---|
| §17 made ratification a Phase 3 entry condition while Phases 3a/4 made everything provisional until Phase 4 | Rationale corrected: **discovery and standing authorizations** are the entry condition; ratification is a Phase 4 act |
| §8.3 said a standing authorization "is itself a ratified pattern" — re-laundering provisional entries into precedent | Authorization is now explicitly **not** a ratified pattern; separate expiring record, confers no Precedent |
| §6.2 justified T0/T1 self-verification on evidence-substitutes grounds that §7.2 disclaims by name, and its premise failed at T0 (no E3 there) | Rewritten as the same risk argument §7.2 makes |
| Gate matrix footnote ‡ routed all class-independent gates through §8.2, but D10's T0/T1 exemption approval had no §8.2 row | Exemption gate row added to §8.2 |
| §17 never scheduled `modes/execution-modes.md`, `05-review.md`, `06-context-and-cost.md`, or the metrics definitions that Phases 1–5 consume | All four assigned to phases (1, 5, 4, 2) |
| §10.4.1 routed recovery-form misclassification to the §13.4.1 audit, which samples T0/T1 only — while E7 exists only at T3 | Rerouted to Verifier challenge + the mandatory T3 retrospective |
| Partial-spec rule promised "E4 traceability targets" at T0/T1, where E4 doesn't exist | Qualified to T2+; at T0/T1 the criteria bound scope and define done |
| Phase 6 called the post-pilot revision framework v1.2 while §1.17/§15 called it v1.1 | Standardised on framework v1.1 |
| §4.6 claimed eleven dimensions and listed ten | Corrected to ten, and §5 C10 with it |
| §11.5 cited §4.1 for de-escalation authority; four references pointed at a nonexistent "§10.5b" | Retargeted to §3.1/D3 and to "§10.5 rule (b)" |
| §16 heading, front matter, and §19's D1 row still described D9–D11 as open and evidence as satisfying independence | All corrected |

### 19.4 V1.0 → V1.1

#### Directed changes

| # | Change | Sections touched |
|---|---|---|
| 1 | **D1 resolved as hybrid.** Roles stay permanently distinct; one human may hold several; no ceremonial self-approval; independence framed as a property of the reasoning rather than of headcount. *(Refined in V1.2: evidence independence and separation of duties are now distinct, and evidence does not discharge a separated instance — §19.3.)* Trip-wires, evidence levels, T3 gates, and the jurisdiction rule are unchanged at n=1 | §7.3 (new) · §8.3 · §11.2 · §16 D1 |
| 2 | **D2–D8 recorded as resolved** as recommended, with refinements noted on D3, D4, and D8 | §16 |
| 3 | **Counterfactual Evidence Principle replaces the literal reversion test.** E3 now reads "does the claimed property depend on this change?" with nine acceptable mechanisms; reversion testing remains the preferred default for bug fixes and feature behavior. Two guards: the mechanism and its counterfactual are stated in the evidence pack, and "no mechanism applies" is an escalation with a bounded, expiring exemption — not a waiver | §10.2 E3 · §10.3 (new) · §1.12 · §10.6 · D4 · §17 Phase 2 |
| 4 | **Assertion/coverage deltas demoted to a heuristic.** The protected property is test *intent*. Deltas may trigger inspection; they may never be reported as evidence that semantics were preserved | §10.5 · §8.2 · §1.12 · §17 Phase 2 |
| 5 | **Precedent redefined as ratified, not extant.** Similar code is not precedent; existing code may be drift. Precedent requires an ADR, a conventions entry, a ratified-pattern registry row, or explicit Architect ratification *applicable to this context*. Ratification is one line, ADRs only for novel durable patterns | §4.3 · §4.2 T1 · §4.5 · §9.1 (registry added as a fifth artifact) · §12 |
| 6 | **P10 rewritten.** Quality and acceptable risk are constraints, not variables; within them, optimize human attention then economic cost. Reduced assurance is never justified by attention or spend | §2 P10 · §13.1 · §7.2 · §11.3 |
| 7 | **Classification calibration made two-sided.** Escalation precision alone rewards under-escalation. Added a sampled under-classification audit of merged T0/T1 changes, weighted toward trip-wire boundaries, run as M3 with human adjudication, whose output is a guardrail rather than a number | §13.4 · §13.4.1 (new) · §14 |
| 8 | **Jurisdiction rule added.** Executable evidence governs falsifiable correctness · architectural judgment governs novel design · humans govern intent, risk acceptance, irreversibility. Green checks never settle requirements, architecture, intent, or risk | §2.1 (new) · §10.1 (new) · §2 P2 · §10.6 · §11.1 |
| 9 | **Build sequence restructured** so no phase validates a workflow whose controls don't exist. Now: core → verification spine → T0/T1 pilot → context pack + architecture governance → T2/T3 pilot → revision → tool qualification → instantiation → prune | §17 (rewritten) · D8 |
| 10 | **Consistency sweep run** (independent adversarial pass). Fifteen conflicts found; all resolved — see below | throughout |

#### Structural additions (kept deliberately small)

The **control-selection ladder** (reversibility → mechanical enforcement → executable evidence → AI verification → human attention) is now named once and referenced twice (§2.1, §13.1) rather than existing as two similar lists. **No new core documents** were added: templates and one metrics note only. Every other change landed inside an existing section.

#### Conflicts found and resolved in the V1.1 sweep (under §19.4)

| Conflict | Resolution |
|---|---|
| Modes required qualification (Phase 7) but were needed from Phase 1 — closed loop with no entry | Two-state rule: **declared** in Phases 1–6 with unchanged evidence requirements, **qualified** from Phase 7 (§6.2) |
| Precedent-as-ratified made the T0/T1 pilot unclassifiable, since the registry was a *byproduct* of that pilot | Seeding moved to an **entry condition** of Phase 3, not an output (§4.3, §17) |
| E1 includes architecture-lint, which needs the Phase 4 invariants register, but E1 is required in Phase 3 | E1's architecture-lint is conditional on boundary rules existing; the gap is **stated** in Phase 3 rather than silently skipped |
| §4.2's T1 definition still said "precedent exists in the codebase" | Rewritten to require a ratified pattern. *(V1.2.1 added the second eligibility route — §19.2 item 1.)* |
| Gate matrix marked human approval "skip" at T0/T1, contradicting class-independent gates (dependencies, test intent) | Footnote ‡: decision-level gates override the class floor, and gate only that decision |
| Clarification was conditional in §3.1 and unconditional at T2/T3 in the matrix | Footnote †: conditional on Spec Confidence in both places |
| Confirmed classification showed agent-sufficient at T2, contradicting D3 | Matrix now ◆ at T2 and T3 |
| §11.5 required retiring low-precision review layers that §3.2/§7.2 require existing | Optional layers are retired; **class-required layers are re-specified, not removed** — removing one is a classification change |
| §6.2 forbade one instance holding M1 and M3; §7.2 allowed self-verification below T2 | Prohibition scoped to **T2 and above** |
| Incident revert was ungated (A) while destructive operations are never autonomous (X) | Exception added: a destructive revert is X, and the recovery evidence prepared in advance (E7) is what makes it fast. *(V1.2 generalized "rehearsed rollback" into three recovery forms — §10.4.1.)* |
| §7.2 and §11.3 justified reduced controls on cost grounds, contradicting the new P10 | Both rewritten as **sufficiency** arguments; rank-1/rank-2 findings are never defaulted away |
| §11.1 implied E3 evidence covers requirement verification | Rewritten; requirement fitness at T1 rests on the spec, not on evidence. *(V1.2.1/V1.2.2 corrected the timing to `Clear` **by implementation time** — §4.3.)* |
| P3 ruled out "ceremony proportional to diff size" while §1.14 made diff size a first-class control | Distinguished: diff-size caps bound **autonomy**, they don't add process |
| Two references to §10.4 pointed at the wrong section after renumbering | Corrected to §10.5 rule (b) |
| Stale counts and framing: document count, metric count, "these are open," "the only factors," kernel contents, §19 missing | All corrected |

---

*End of V1.2.2 — **Layer 1 Architecture LOCKED.** Nothing is built yet. All architecture decisions D1–D11 are resolved; §15 lists the project inputs and when each is required. Next action is §17 Phase 1.*
