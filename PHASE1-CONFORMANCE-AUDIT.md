---
owner: framework-maintainer
load_when: validating Phase 1 acceptance or reviewing the corrections it required
max_length: audit record; append-only after acceptance
last_verified: 2026-08-19
---

# Phase 1 Specification-Conformance Audit — AIDF Layer 1 V1.2.2

> **Superseded verdict.** This is the original audit and its verdict below is unchanged. The corrections it required were verified in `PHASE1-CONFORMANCE-REAUDIT.md`, which returned **PASS**. Read that file for the current status. (Pointer added 2026-10-27; the audit body is untouched.)

**Audit type:** Independent specification-conformance audit (read-only)
**Locked architecture:** `spec/AIDF-v1.2.2-design-proposal.md` — Layer 1 LOCKED at V1.2.2
**Implementation assignment:** `spec/PHASE1-IMPLEMENTATION-BRIEF.md`
**Scope:** Phase 1 only (locked §17 Phase 1)
**Date:** 2026-08-19

> **Note on this file.** This is an external review record, not a governance-policy document and
> not part of the locked §14.1 repository structure. It carries context metadata because it is a
> durable artifact retained inside the governed repository. No audited artifact was created,
> modified, renamed, or deleted in producing the original report.

---

## 1. Overall verdict

**CONDITIONAL PASS**

---

## 2. Executive summary

The Phase 1 implementation is a faithful, disciplined rendering of locked Layer 1 V1.2.2. Every artifact required by §17 Phase 1 and by the implementation brief exists. The load-bearing semantics that the locked design spent three revisions stabilising are all correct and consistent across documents: `PROVISIONAL` confers nothing, standing authorization never becomes precedent, both T1 routes are stated identically everywhere, `P` is always human pre-approval, `X` is always human execution, M1 operates within an *established* contract, T2/T3 contracts are human-approved before implementation, Spec Confidence must reach `Clear` at every class, trip-wires force T3 and are never overridden by reversibility, and the T3 separated-instance rule holds at n=1 with an explicit statement that wearing another hat does not satisfy it. Terminology is exact throughout; no new role, class, mode, evidence level, authority level, or layer was invented; no vendor-to-mode mapping exists anywhere.

Deferral discipline is good. Later-phase content is consistently labeled with the phase that will supply it, and `IMPLEMENTATION-STATUS.md` is substantially honest about what is specified versus implemented versus enforced.

One blocking gap: two `[REQ]` security/accountability rules from locked §1.8 — **agent credential and blast-radius scoping**, and **provenance labeling of AI-authored changes** — appear nowhere in the repository. §5 C11 assigns both to the kernel, and §17 never schedules them into any later phase, so they will not self-correct. Six corrective findings follow, all narrow and cheaply fixed: the T3 class definition is narrowed to trip-wires only; the mode document declares autonomy envelopes without recording the locked §15 input-6 constraint that v1.0 assumes supervised operation; the Task Contract template cannot record the Spec Confidence re-evaluation §4.3 requires; two templates cite recovery-form content at locations that do not contain it; the status ledger's conflict record and validation section are incomplete; and the mode table mislabels its verification field as required output.

No genuine implementation conflict was found. Nothing in the locked architecture is unimplementable as written.

---

## 3. Blocking findings

### B1 — Two §1.8 `[REQ]` controls exist nowhere in the framework and are scheduled into no phase

| | |
|---|---|
| **Severity** | Blocking |
| **Locked specification** | §1.8 (Security — omissions), bullets 3 and 4; §5 C11 |
| **Implementation** | `KERNEL.md` (whole file); absent from `core/02-authority.md`, `core/01-lifecycle.md`, `modes/execution-modes.md`, and `IMPLEMENTATION-STATUS.md` §"Intentionally deferred" |

**What the specification requires**

- `[REQ]` "Agents hold no production credentials, no direct production access, and no unaudited destructive capability."
- `[REQ]` "AI-authored changes are labeled in commit metadata (author/model/mode/task class). Without it, post-incident forensics cannot distinguish AI-introduced from human-introduced defects."
- §5 C11: "Add **untrusted-content rule, dependency gate, credential scoping, provenance labeling** to the kernel."

**What the implementation does**

Implements two of the four C11 items (untrusted-content rule, dependency gate). The credential-scoping rule and the provenance-labeling rule are absent from every artifact and are not recorded as deferred. Verified by full-repository search: zero occurrences of `credential`, zero of `provenance` or `commit metadata` outside `spec/`.

**Why the difference matters**

These are not later-phase capabilities that a phase boundary will supply. §17 assigns them to no phase and §12.1's kernel enumeration omits them, so nothing in the locked build sequence will ever create them — the omission is terminal rather than temporary. Concretely: §8.2's `X` rows govern specific *operations* but nothing governs credential *possession*, so an agent holding production credentials violates no rule the implementation states. And provenance labeling is a hard prerequisite for Phase 2's metric set — "escaped defect rate by class" (§13.4) and the under-classification audit (§13.4.1) both presuppose that AI-authored merges are identifiable. Phase 2 would be built on a signal Phase 1 did not establish.

**Note on placement**

§12.1's Tier-1 content list omits both items while §5 C11 assigns both to the kernel. That is an internal tension in the locked spec about *placement*, and the implementation followed §12.1 and the brief's (explicitly non-exhaustive, "including") list. Where these rules live is arguable; that they must exist somewhere in operational Layer 1 is not.

**Minimal corrective action**

Add two lines to `KERNEL.md`, adjacent to the untrusted-content rule — one stating that agents hold no production credentials, no direct production access, and no unaudited destructive capability; one stating that AI-authored changes carry author/model/mode/task-class in commit metadata. Both fit the kernel's remaining budget (currently 812 words against a ~2-page cap). No other document changes.

---

## 4. Corrective non-blocking findings

### C1 — T3 class definition narrowed to trip-wires, dropping the consequence-based route

| | |
|---|---|
| **Severity** | Corrective |
| **Locked specification** | §4.2, T3 row |
| **Implementation** | `core/01-lifecycle.md` §6, T3 row |

**Specification requires:** two independent routes into T3 — *"Any trip-wire fires. Security boundary, irreversible, or high operational/financial consequence."*

**Implementation does:** *"Any kernel trip-wire fires. Human at both ends; agents never hold autonomous execution authority."* The second sentence of the locked definition is replaced by text drawn from the "Feel" column.

**Why it matters:** the trip-wire list is deliberately mechanical and enumerated (§4.1). It is not intended to be exhaustive of T3-worthy risk; the consequence clause is what catches the case no glob matches. Under the implementation's definition, a change with high financial or operational consequence that matches no listed trip-wire has no stated basis for T3, and the agent's default reading is T2. This is precisely the silent under-classification direction §13.4.1 identifies as the framework's dominant exposure. Free escalation (§9) mitigates but does not replace a class definition.

**Corrective action:** restore the locked second sentence to the T3 definition row.

---

### C2 — Autonomy envelopes declared without the locked §15 input-6 constraint

| | |
|---|---|
| **Severity** | Corrective |
| **Locked specification** | §15, input 6 |
| **Implementation** | `modes/execution-modes.md` — M0 line 18, M1 line 28, §"Phase-1 bootstrap rule" lines 67–70 |

**Specification requires:** mode declaration is explicitly gated on this input — *"v1.0 assumes mostly-supervised. Long-running autonomy needs checkpoint/interrupt design — a later framework increment, and **modes must not be declared as if it were already handled**."* `required_by`: before Phase 1 mode declaration.

**Implementation does:** states unqualified autonomy envelopes ("full within declared scope", "full within the Task Contract") and a bootstrap rule covering declaration-vs-qualification, with no record that v1.0 assumes interactive, human-supervised operation and that long-running autonomy is a later framework increment. Verified absent: no occurrence of "supervised operation", "long-running", "checkpoint design", or "interrupt" anywhere outside the mode names themselves. The brief's Operating Environment supplies the assumption, but the brief is an input document, not a framework artifact an agent loads at task time.

**Why it matters:** `modes/execution-modes.md` describes itself as the stable contract Layer 2 implements against. An agent or a Phase-7 eval author reading it sees "Autonomy: full within the Task Contract" with no scope constraint — exactly the reading §15 input 6 forbids. The one project input the locked spec ties directly to Phase 1 is the one Phase 1 did not record.

**Corrective action:** add one line to the Phase-1 bootstrap rule: v1.0 assumes interactive, human-supervised execution; long-running autonomous operation requires checkpoint/interrupt design, which is a later framework increment and is not covered by any mode declared here.

---

### C3 — Task Contract template cannot record the Spec Confidence re-evaluation

| | |
|---|---|
| **Severity** | Corrective |
| **Locked specification** | §4.3 |
| **Implementation** | `templates/task-contract.md`, §Status, final field |

**Specification requires:** *"`Partial` → Clarification produces acceptance criteria → **re-evaluate Spec Confidence**… Re-evaluation is an explicit act recorded in the Task Contract (§3.4), not an assumption."*

**Implementation does:** provides a single field with the answer pre-filled — `- **Spec Confidence at approval:** Clear`. There is no place to record that the task entered at `Partial`, what clarification produced the criteria, or that re-evaluation occurred. The field is also labeled "at approval", which does not apply at T0/T1, where the contract is *established* and no approval exists — yet `Clear` is equally mandatory there.

**Why it matters:** §4.3 explicitly forecloses the assumption reading, and this template is the one artifact the rule names as the record. A pre-filled constant converts a required act into a declaration, which is the failure mode §4.3's final sentence was written to prevent. `core/01-lifecycle.md` §3 states the rule correctly; only the template fails to instrument it.

**Corrective action:** replace the single field with two — *Spec Confidence at intake* (Clear | Partial | Vague) and *Re-evaluated to Clear by* (clarification output or Spike report reference; N/A if Clear at intake). Retain "must be Clear before implementation, every class."

---

### C4 — Two templates cite §10.4.1's three recovery forms at locations that do not contain them

| | |
|---|---|
| **Severity** | Corrective |
| **Locked specification** | §10.4.1; §17 Phase 2 (which correctly schedules this content into `core/04-verification.md`) |
| **Implementation** | `templates/task-contract.md:23`; `templates/evidence-pack.md:36` |

**Implementation does:**

- `task-contract.md:23` — *"Recovery / reversal approach (per the three recovery forms in `core/01-lifecycle.md` / locked spec §10.4.1)"*. `core/01-lifecycle.md` contains no recovery forms; §4 mentions the phrase only as a plan field.
- `evidence-pack.md:36` — E7 recovery evidence *"see `core/02-authority.md` §9"*. §9 covers only the **third** form (truly irreversible operations, execution authority). It does not define rehearsed rollback or tested restore, and it is a §8.2 execution-authority rule, not the §10.4.1 evidence taxonomy.

**Why it matters:** every other forward reference in the repository is correctly marked (`core/06-context-and-cost.md`, Phase 4; `core/03-architecture.md`, "not yet built"; `metrics/definitions.md`, "Phase 2+") — these two are the exceptions, and they present deferred Phase-2 material as already resident. Recovery-form classification is itself evidence and is challengeable by the Verifier (§10.4.1). An agent following either pointer finds nothing and will improvise the taxonomy — and mis-stating "reversible" to obtain the cheaper E7 form is the specific abuse §10.4.1 names. The deferral of the content is correct; only the references are wrong.

**Corrective action:** point both to `locked spec §10.4.1` alone, annotated "(operational form lands in `core/04-verification.md`, Phase 2)". The evidence-pack template already enumerates all three forms inline, so no content moves.

---

### C5 — Status ledger: incomplete conflict record, one overstated row, and an unresolvable validation reference

| | |
|---|---|
| **Severity** | Corrective |
| **Locked specification** | §17 Phase 2; brief §"Architecture Traceability File", completion criteria 6, 8, 9 |
| **Implementation** | `IMPLEMENTATION-STATUS.md` lines 29, 73–76, 80 |

**Implementation does:**

1. **Conflict 1 is incomplete.** It records the README / `profiles/` / `instantiation/` / `metrics/` scope difference, but omits the larger one: locked §17 schedules the **evidence-pack and exemption templates in Phase 2**, alongside `04-verification.md`. The brief requires both at Phase 1, and the implementation built them at Phase 1. The ledger's spec basis for the templates row cites §14.1 (the structure list, which carries no phase), which sidesteps the §17 schedule rather than surfacing it.
2. **Line 29 overstates.** "Standing authorizations, truly-irreversible-operation rule | §8.2–8.3, **§10.4.1** | `core/02-authority.md` §7, §9 | **Implemented**". §10.4.1's three-form recovery-evidence model is *not* implemented — only the §8.2 execution-authority rule for the third form is.
3. **Line 80 is unresolvable.** "See the internal-validation section of **the delivery message**". The delivery message is conversational, not an artifact. The ledger exists specifically so future agents can verify claims; criterion 9's evidence is unreachable.

**Why it matters:** the audit brief instructs that this file not be relied on as proof. Independently verified, three of its claims are inaccurate or uncheckable — a low rate, but each sits in the part of the ledger that carries the honesty burden. Building the Phase-2 verification templates early is defensible and disclosed elsewhere; not recording it as the §17 scope difference it is undercuts the file's stated purpose.

**Corrective action:** extend Conflict 1 to name the evidence-pack and exemption templates as §17 Phase-2 items built early at the brief's direction, with the rationale already given; change line 29's status to "Implemented (§8.2 execution authority only; §10.4.1 recovery forms — Phase 2)"; and inline the validation results into the ledger or into a committed file.

---

### C6 — Mode "Required output" field carries verification content, not output

| | |
|---|---|
| **Severity** | Corrective |
| **Locked specification** | §6.1, row "Verification of its output"; §6 opening ("what it must return") |
| **Implementation** | `modes/execution-modes.md` — M0 line 19, M2 line 39, M3 line 49 |

**Specification requires:** two distinct attributes — what the mode must return, and how that return is verified.

**Implementation does:** collapses them under the "Required output" label. The result is incoherent for M2, whose "required output" now reads as *"human or Architect review of the decision, not the prose"* — something M2 does not produce. M0's required output becomes a machine check rather than a diff. Only M1 survives the merge intact, because its evidence pack is both.

**Why it matters:** the brief's item 4 lists "required output" as a mandatory mode field, and §6 makes "what it must return" half the definition of a mode. As written, M2's return obligation is unstated and the verification obligations for M0/M2/M3 are mislabeled as deliverables.

**Corrective action:** rename the field to "Verification of its output" per §6.1, or split into two fields and fill M0/M2/M3's output line from the locked Autonomy column (deterministic diff; artifacts only, no write authority to main; findings only, no write authority to source).

---

## 5. Informational observations

*Not conformance defects. No action required for Phase 1 acceptance.*

1. **`metrics/README.md` is not in the locked structure.** §14.1 lists `metrics/definitions.md` and `metrics/classification-audit.md` only. The brief said "create only the minimal structure required by the locked repository architecture." The added README is clearly marked not-operational and harms nothing, but it is an extra file.
2. **Phase attribution drift on the metrics files.** `IMPLEMENTATION-STATUS.md:62` and `core/01-lifecycle.md:124` say "Phase 2/3"; §17 assigns both files to **Phase 2** ("needed before Phase 3 collects a baseline"). `metrics/README.md` states Phase 2 correctly, so the repository disagrees with itself.
3. **Inconsistent activation marking across templates.** `invariant.md` states its Phase-4 activation explicitly and well; `adr.md` and `review-findings.md` carry no equivalent note, though the ADR log is Phase 4 and running independent review is Phase 3/5.
4. **Role table drops the "Distinct context" column** (`core/02-authority.md` §1 vs locked §7). The Verifier's clean-room context rule survives in `modes/execution-modes.md` M3 and `templates/review-findings.md`, so nothing is lost operationally, but the role model no longer shows context as a differentiator.
5. **§3.2's T2 human-approval parenthetical dropped.** The locked cell reads "◆ Task Contract before implementation *(and interface-contract changes at the point of change)*"; `core/01-lifecycle.md` §2 omits the parenthetical. Covered by `core/02-authority.md` §6 and by footnote ‡, so no requirement is lost.
6. **§4.5 "What classification determines" is not consolidated anywhere.** Most rows are distributed correctly. The one row with no home is "execution mode permitted = class + applicable pattern authorization"; the pattern-authorization half appears in M1's inappropriate-work rule, but no artifact states which modes a class permits. §17 Phase 1 does not require §4.5, so this is a gap rather than a defect.
7. **Two `[R]` recommendations rendered as binding.** The ≤5 open-exemption cap (`templates/exemption.md`) and "record every provisional declaration" (`modes/execution-modes.md`) are `[R]` in the locked text. Both are defensible — the cap is `[REQ]` and needed a value — but `IMPLEMENTATION-STATUS.md` conflict 2 asserts only that nothing was *downgraded*, and does not note the promotion in the other direction.
8. **`README.md:24`** — "enough to run declared-mode, evidence-light T0/T1 work under real human gates" — could be read as clearing the Phase 3 T0/T1 pilot, which §17 makes dependent on Phases 1 **and 2** plus D8/D9. The sentence is hedged by the disclaimers that follow, and `IMPLEMENTATION-STATUS.md` is unambiguous, so this is a phrasing risk only.

---

## 6. Phase 1 requirement-to-artifact traceability

### From locked §17 Phase 1

| Locked Phase-1 requirement | Artifact | Verified |
|---|---|---|
| `KERNEL.md` ≤2pp | `KERNEL.md` — 812 words / 87 lines / 5.8 KB | PASS — within budget |
| — incl. jurisdiction rule | `KERNEL.md` §"The jurisdiction rule" | PASS — all three authorities, non-substitution stated |
| — incl. control-selection ladder | `KERNEL.md` §"The control-selection ladder" | PASS — five rungs, "chooses how, never how much" preserved |
| — §12.1 Tier-1 contents (8 items) | principles · jurisdiction · ladder · trip-wires · STOP/DECLARE/ESCALATE · DoD by class · declared scope · untrusted content | PASS — 8/8 |
| — §5 C11 kernel additions (4 items) | untrusted content PASS · dependency gate PASS · credential scoping ABSENT · provenance labeling ABSENT | **FAIL — B1** |
| Templates | `templates/` — 11 files, matching §14.1 exactly | PASS |
| `01-lifecycle.md`: classes | §6 | **PARTIAL — C1 (T3)** |
| `01-lifecycle.md`: trip-wires | delegated to `KERNEL.md` (9, verbatim) | PASS |
| `01-lifecycle.md`: Spec Confidence states | §3, full state machine + transitions | PASS |
| `01-lifecycle.md`: Task Contract | §4, established vs approved | PASS |
| `01-lifecycle.md`: registry states + both T1 routes | §7 | PASS |
| `02-authority.md`: roles | §1 (5 roles) | PASS |
| `02-authority.md`: gates | §6 (all 18 §8.2 rows present) | PASS |
| `02-authority.md`: solo-capable operation | §4 | PASS |
| `modes/execution-modes.md`: M0–M3 | full file | **PARTIAL — C6 (field label)** |
| — declared-vs-qualified rule | §"Qualification, not assertion" + bootstrap rule | **PARTIAL — C2 (§15 input 6)** |

### From the brief (additional to §17)

| Brief requirement | Artifact | Verified |
|---|---|---|
| Eleven-stage lifecycle | `01-lifecycle.md` §1 | PASS — 11 stages, verbatim ordering |
| Approval-as-gate semantics | §1 "Where approval gates actually fire" + §2 row | PASS — incl. "authority rules govern" |
| Gate matrix | §2 | PASS — all 12 rows, both footnotes |
| Clarification / Spike | §1 stage 3, §3, §5 | PASS — non-mergeable, throwaway branch |
| Classification authority | §8 | PASS — D3 hybrid |
| Escalation / de-escalation | §5, §9 | PASS — asymmetry preserved |
| Retro → Guardrail triggers | §10 | PASS — both triggers + always-at-T3 + preference order + no-memo rule |
| Role performance vs. P authority | `02-authority.md` §5 + `KERNEL.md` closing | PASS — 5-row AI-may/human-must table |
| Front matter (4 keys) | all 20 implementation `.md` files | PASS — 20/20, all four keys |
| README (8 required topics) | `README.md` | PASS — 8/8 |
| `profiles/README.md` stub | present, no vendor mapping | PASS |
| `instantiation/README.md` stub | present, two entry paths | PASS |
| `metrics/` minimal seam | `metrics/README.md` | PASS — see Informational 1 |
| `IMPLEMENTATION-STATUS.md` | present | **PARTIAL — C5** |

---

## 7. Cross-document consistency results

| Check | Result |
|---|---|
| T1 eligibility identical everywhere | **PASS.** `01-lifecycle.md` §6/§7, `modes/execution-modes.md` M1, `templates/standing-authorization.md`, `templates/pattern-entry.md` all state the same two routes with the same conferrals. No variant phrasing found. |
| `PROVISIONAL` never means approved | **PASS.** Stated as inert in three places; "discovery is not approval" and "not by this entry aging" both preserved. |
| Standing authorization never confers Precedent | **PASS.** Asserted in `01-lifecycle.md` §7, `02-authority.md` §7, and the template itself, which additionally forbids cross-filing as a pattern entry. |
| `P` always human pre-approval | **PASS.** `02-authority.md` §2, §5, §6; `KERNEL.md` closing paragraph. No exception found. |
| `X` always human execution | **PASS.** §2, §6 (4 rows), §9. "Agents may prepare, never trigger" preserved verbatim. |
| M1 requires an established Task Contract | **PASS.** `modes/execution-modes.md` M1 purpose + context + autonomy; `01-lifecycle.md` §4. |
| T2/T3 contracts human-approved before implementation | **PASS.** Gate matrix, §4 status row, `02-authority.md` §5–6, template Part B. |
| Spec Confidence `Clear` before implementation, all classes | **PASS** in policy (kernel, §3, footnote †). Template instrumentation — **C3**. |
| Trip-wire forces T3, non-overridable | **PASS.** Kernel + §9. Reversibility exclusion explicit in both. |
| Escalation free / de-escalation gated | **PASS.** §5 and §9. |
| T2/T3 separation of duties consistent | **PASS.** `02-authority.md` §3 and `modes/execution-modes.md` agree, including the "not because evidence substitutes for it" rationale. |
| T3 three distinct instances incl. n=1 | **PASS.** §3 explicit: hat-wearing does not satisfy it; no second human required. |
| AI role performance ≠ level-P approval | **PASS.** §5 + kernel. |
| Modes declared Phases 1–6, qualified from 7 | **PASS.** Scope caveat missing — **C2**. |
| No vendor/model→mode mapping | **PASS.** Only negative statements, in `profiles/README.md` and `README.md`. |
| Eleven stages + approval-as-gate | **PASS.** |
| Evidence levels / exemptions / recovery / review rules undistorted by templates | **PASS** for evidence levels (class-aware pack, T0 has no E3 field, no E7 field below T3), exemptions (T0 N/A, T1, T2 four-part, T3 none, cap, mandatory expiry, expiry reopens requirement), and review (rank ordering, rank 1–2 never defaulted, two-round cap, clean-room framing, capped non-blocking). Recovery forms — **C4**. |
| Internal references resolve or are marked forward | **PASS with 2 exceptions** — **C4**. All 9 other forward references correctly marked. |
| No future-phase control presented as operational | **PASS.** |
| Terminology preserved | **PASS.** Layer 1–3, T0–T3, M0–M3, E0–E7, PROVISIONAL/RATIFIED, Task Contract, standing authorization, and all five role names used exactly. No synonyms, no "capability tier", no "Layer 4". |

---

## 8. Implementation-status accuracy assessment

Independently verified rather than accepted. **Materially accurate, with three defects (C5).**

- Every "Implemented" row was checked against the named artifact. All exist and contain what is claimed, with one overstatement (line 29, §10.4.1).
- The specified / implemented / operationally enforced distinction is drawn correctly and consistently — the ledger nowhere claims CI enforcement, metrics collection, invariants registry, review operation, or qualification.
- The deferral list is accurate and complete against §17, with the phase attributions correct except "Phase 2/3" for the metrics files (Informational 2).
- Conflict 2 (`[REQ]`/`[R]` tagging) is a sound and honestly-flagged interpretive choice; verified that no rule was downgraded to advisory. It does not mention the two promotions in the other direction (Informational 7).
- Conflict 1 is genuine and correctly reasoned but incomplete — it omits the §17 Phase-2 scheduling of the evidence-pack and exemption templates.
- The validation-results section defers to a non-artifact.

**Net:** the ledger is usable as a starting point for a future agent and does not launder any unearned status. It should not be treated as complete until C5 is closed.

---

## 9. Genuine implementation conflicts

**NONE.**

No locked requirement was found to be unimplementable as written. The two items the implementation recorded as conflicts are correctly characterised as a scope difference between brief and architecture (not a contradiction — §14.1 authorises the stubs) and an interpretive choice about tagging. The §17-vs-brief difference over the evidence-pack and exemption templates is likewise a brief clarification, not a conflict: building a template early does not activate a Phase-2 control, and the templates disclose their dependencies. It should be recorded, not resolved differently.

The §12.1-vs-C11 tension over kernel contents (B1) is an internal inconsistency in the locked spec about *placement*, not about whether the rules are required. It does not require reopening a locked decision — either location satisfies §1.8.

---

## 10. Phase 2 entry prerequisites

**Deliverables Phase 2 must produce (§17 Phase 2):** `core/04-verification.md` incl. §10.4.1 recovery forms · `metrics/definitions.md` · `metrics/classification-audit.md` · CI: counterfactual-evidence check, declared-scope check against the Task Contract, trip-wire detection, dependency gate, secret scan, assertion/coverage delta as inspection trigger only.

The evidence-pack and exemption templates are already built (Phase 1, at the brief's direction) and must be **reconciled** with `04-verification.md` rather than re-created.

### Project inputs (§15), by current state

| # | Input | `required_by` | Status |
|---|---|---|---|
| 1 | CI enforcement capability — branch protection, required checks, ability to add lint/checks, working revert path | Before Phase 2 | **UNKNOWN — potentially blocking.** Recorded nowhere in the repository. §15 names this "the only input that can genuinely delay the plan"; if absent, building it is a prerequisite project. Every Phase-2 CI deliverable depends on it. |
| 2 | Test-suite baseline — is coverage trustworthy, what does it cover | Assessed before Phase 2 | **UNKNOWN — blocking for design, not entry.** Determines E2/E3 design and counterfactual-mechanism selection. §15: assess before designing the spine, not after. |
| 3 | Agent execution authority and credential scope | Before governed execution in Phase 1–2 | **PARTIALLY KNOWN — already due.** The brief's Operating Environment answers it for Phase 1, but that lives in an input document, and the §1.8 rule it should have produced is absent — see **B1**. Close B1 and record the scope in a framework artifact before Phase 2 governed execution. |
| 4 | Regulatory / compliance obligations (SOC 2 / HIPAA / PCI) | Before Phase 3b | **UNKNOWN — not blocking Phase 2 entry.** Cheap now, expensive retrofitted onto merged history. |
| 5 | Pilot repository selection | Before Phase 3 | **UNKNOWN — not blocking Phase 2 entry.** Blocks Phase 3a, which cannot seed a registry for an unnamed repo. |
| 6 | Interactive vs. long-running autonomous agents | Before Phase 1 mode declaration | **KNOWN but unrecorded.** The brief establishes interactive/human-supervised; `modes/execution-modes.md` does not carry it — see **C2**. Answered, not documented. |
| 7 | Second-engineer availability | Informational only | **NOT BLOCKING** by construction (§7.2, §7.3). Correctly reflected: nothing in the implementation requires a second human. |

**Summary:** inputs 1 and 2 are the real Phase-2 gate and are currently unknown. Input 3 is answered for Phase 1 but has an open framework gap (B1). Input 6 is answered but undocumented (C2). Inputs 4, 5, and 7 do not block Phase 2 entry. No §15 input is recorded in any repository artifact — consider capturing the table with its `required_by` schedule in `IMPLEMENTATION-STATUS.md`, since Phase 1 is where the schedule first starts binding.

---

## 11. Final recommendation

**Correct and re-audit — targeted, not full.**

Phase 1 is substantively sound and does not warrant reopening any locked decision. The corrections are seven edits totalling roughly twenty lines, none of which touches the locked architecture or requires a design judgment:

| # | Finding | Edit |
|---|---|---|
| 1 | **B1** | Two lines in `KERNEL.md` — credential scoping; provenance labeling |
| 2 | **C1** | Restore the T3 definition's second sentence in `core/01-lifecycle.md` §6 |
| 3 | **C2** | One line in `modes/execution-modes.md` recording supervised-operation scope per §15 input 6 |
| 4 | **C3** | Split the Spec Confidence field in `templates/task-contract.md` |
| 5 | **C4** | Repoint two recovery-form references |
| 6 | **C5** | Extend the conflict record, correct line 29's status, inline the validation results |
| 7 | **C6** | Rename or split the mode "Required output" field |

Re-audit scope should be limited to these seven items plus a re-run of the cross-document consistency table; a full re-read is not warranted.

**Do not reopen any locked decision** — no finding in this audit originates in the architecture. Once B1 and C1 are closed, Phase 1 can be accepted against locked Layer 1 V1.2.2, and Phase 2 entry then turns entirely on §15 inputs 1 and 2.

---

## Audit conduct

Read in full: `spec/AIDF-v1.2.2-design-proposal.md` (1,359 lines), `spec/PHASE1-IMPLEMENTATION-BRIEF.md`, `KERNEL.md`, `core/01-lifecycle.md`, `core/02-authority.md`, `modes/execution-modes.md`, all 11 files under `templates/`, `README.md`, `IMPLEMENTATION-STATUS.md`, `profiles/README.md`, `instantiation/README.md`, `metrics/README.md`, and the complete repository file inventory (22 files).

Mechanical verification performed: front-matter key presence across all 20 implementation documents; internal file-reference resolution; kernel word/line/byte count against the ≤2-page budget; repository-wide searches for vendor and model names, credential and provenance terms, autonomy-scope terms, and terminology drift (`capability tier`, `Layer 4`, role-name synonyms).

No claim in `IMPLEMENTATION-STATUS.md` was accepted without independent verification against the named artifact.

**Repository state:** no audited artifact was created, modified, renamed, or deleted, and no Git operation was performed. This report is the only file added.

---

## Remediation record

**Remediation date:** 2026-08-19  
**Status:** B1 and C1–C6 corrected; targeted independent re-audit passed; Phase 1 formally accepted.

The original report above is preserved unchanged as the audit-time record. The implementation was subsequently corrected as follows:

- **B1:** credential scoping and AI-change provenance added to `KERNEL.md`.
- **C1:** the full consequence-based T3 definition restored in `core/01-lifecycle.md`.
- **C2:** the interactive, human-supervised execution boundary added to `modes/execution-modes.md`.
- **C3:** the Task Contract now records Spec Confidence at intake and the explicit re-evaluation to `Clear`.
- **C4:** both recovery-form references now point to locked §10.4.1 and identify `core/04-verification.md` as the Phase-2 operational home.
- **C5:** `IMPLEMENTATION-STATUS.md` now records the template-timing difference, narrows the §10.4.1 status claim, and contains self-contained validation results.
- **C6:** every execution mode now distinguishes required output from verification of that output.
- **Audit governance:** this retained audit record now carries the repository's required context metadata.

Targeted independent re-audit `PHASE1-CONFORMANCE-REAUDIT.md` passed. The human Change Owner formally accepted Phase 1 on 2026-08-19 in the originating project task.
