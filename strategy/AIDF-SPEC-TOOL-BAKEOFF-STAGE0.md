---
owner: framework-maintainer
load_when: deciding whether the spec-tool bake-off goes past stage 0, or reading what each arm's protocol and Task Contract mapping would be
max_length: 4 screens
last_verified: 2026-11-05
---

# Stage 0 of the spec-tool bake-off: protocols, step count and field mapping (paper)

Written 2026-11-05 under `spec/AIDF-SPEC-TOOL-BAKEOFF-STAGES-0-1-TASK-CONTRACT.md` (criteria 1 to 4). It is advice to the Change Owner for the gate decision; it decides nothing. Everything about the tools comes from their READMEs (`verification/spec-tool-bakeoff/inputs/readme-extraction-2026-11-05.md`); nothing was run. Where a README is silent the table says "not stated", and stage 1 is where that is observed.

## Pinned inputs (criterion 1)

| | Spec Kit | OpenSpec |
|---|---|---|
| Repository | `github/spec-kit` | `Fission-AI/OpenSpec` |
| Release tag | v1.3.0 (2026-11-03) | v1.16.0 (2026-10-30) |
| Commit of the tag | 34a0d388eac671d656eb05b125ad3ed6056168ed | 27c0515724decc633818c735ee596481eec78a8b |
| README SHA-256 | 20207a2130e3c5ddc1810d3e4786e1105bba6e59baafd5d157fc7bd83200f58e | e19ee7362ad043eeff0d3d1f1f0e5bf1ae195f4b34aa28e0107eae5eeaaad446 |
| Licence | MIT | MIT |
| How the install is pinned | README: not stated (it shows `uv tool install specify-cli`, unpinned). Proposed: install from the git tag; confirmed or refused at stage 1 | README shows `@latest`. Proposed: `@fission-ai/openspec@1.16.0` into a scratch prefix; confirmed or refused at stage 1 |
| Prerequisites stated | Python 3.11+, uv, a supported coding agent | Node.js 22.12.0+ |
| Telemetry | not stated | on unless unset; off in CI; `OPENSPEC_TELEMETRY=0` disables it |

## The stop rule, written before the tables (criterion 4)

Stop the bake-off at stage 0 for a tool if either: (1) **no saving remains that leaves approval and review in place**, that is, no step of A1 or A2 is deleted, merged or moved off the human compared with A0; or (2) **more than half of the Task Contract fields are AIDF-only** for that tool. The verdict below is advice; the Change Owner decides at the gate.

## Protocols (criterion 2)

"Human step" means a point where the process requires a human to act other than stating the task (the same in every arm). It is the unit of the measurement's `decision_points` (T2: one approval).

**A0, AIDF-native (T2).**

| # | Who | Step | Produces |
|---|---|---|---|
| 1 | agent | classifies the task, writes the Task Contract (body and Part B) | contract |
| 2 | **human** | approves the contract | recorded approval |
| 3 | agent | implements, writes the evidence pack | change, pack |
| 4 | script | visible tests and preflight | results |
| 5 | independent agent | reviews (one round at T2; fix cycles if blocked) | report |

Human steps: **1**.

**A1, AIDF + OpenSpec.**

| # | Who | Step | Produces |
|---|---|---|---|
| 1 | agent | runs the OpenSpec propose flow | `openspec/changes/<name>/` with `proposal.md`, `specs/`, `design.md`, `tasks.md` |
| 2 | script | applies the fixed mapping to the change folder | contract body |
| 3 | agent | decides class, trip-wires, authority; writes the AIDF-only fields (see the table) | contract |
| 4 | **human** | approves the contract (which reads the mapped body) | recorded approval |
| 5 | agent | implements; the tool's apply and archive commands are inside the arm and logged | change, pack |
| 6 | script | visible tests and preflight | results |
| 7 | independent agent | reviews | report |

Human steps: **1** if the approval of the contract stands in for the README's own "you review the plan before any code is written"; **2 or more** if the human also reviews the tool's artifacts as the README says. The README gives the human no step to delete.

**A2, AIDF + Spec Kit.**

| # | Who | Step | Produces |
|---|---|---|---|
| 1 | agent | runs `/speckit-specify`, `/speckit-plan`, `/speckit-tasks` (and `/speckit-constitution` once per project) | spec, plan, tasks (paths: not stated) |
| 2 | script | applies the fixed mapping | contract body |
| 3 | agent | decides class, trip-wires, authority; writes the AIDF-only fields | contract |
| 4 | **human** | approves the contract | recorded approval |
| 5 | agent | implements; `/speckit-implement` and `/speckit-converge` (repeat until `Converged`) are inside the arm and logged | change, pack |
| 6 | script | visible tests and preflight | results |
| 7 | independent agent | reviews | report |

Human steps: **1** if the contract approval stands in for the README's "reviewing each result before continuing" (it names that review for every skill, so up to 4 reviews before implement if followed as written); otherwise more.

**Steps deleted, merged or moved off the human:** none. A1 and A2 add steps 1 to 3 (the tool flow, the mapping, the AIDF-only fields) before the approval and leave A0's approval and review where they are. The only candidate for a saving is human *minutes*, not steps: a contract body that is clearer or settles questions the agent would otherwise ask. Paper cannot show it, and the READMEs do not claim it. Agent time can only rise (more steps), which the bake-off's 1.25x cap already allows for.

## Field-level mapping (criterion 3)

Fields are those of `templates/task-contract.md` and the contract JSON. "Supplied" means a named tool artifact can be the field's content as written; "partly" means it can inform it but a part is missing; "AIDF-only" means neither tool has the concept. Spec Kit's artifact paths are not stated in its README, so its cells name the skill that produces the content.

| # | Field | OpenSpec (A1) | Spec Kit (A2) |
|---|---|---|---|
| 1 | Intended outcome | **supplied** by `proposal.md` ("why we're doing this, what's changing") | **supplied** by the `/speckit-specify` output ("what to build and why") |
| 2 | Acceptance criteria | partly: `specs/` holds requirements and scenarios; testability and one-criterion-per-check are AIDF's | partly: the spec; the README does not name acceptance criteria |
| 3 | Spec Confidence line (intake state and re-evaluation) | AIDF-only | AIDF-only (a clarification step is mentioned, not described) |
| 4 | Declared scope (files and modules) | partly: `tasks.md` may name files | partly: the plan and tasks may name files |
| 5 | Outcome records (report and dispositions paths) | AIDF-only | AIDF-only |
| 6 | Approach | **supplied** by `design.md` ("technical approach") | **supplied** by the `/speckit-plan` output |
| 7 | Invariants touched | AIDF-only (the text may inform it) | AIDF-only; the constitution states principles but is not a list of this repository's invariants |
| 8 | Evidence strategy (counterfactual mechanisms) | AIDF-only (`tasks.md` is an implementation checklist) | AIDF-only (`/speckit-bug-test` records a verdict after a fix, not a planned counterfactual) |
| 9 | Protected files touched | AIDF-only | AIDF-only |
| 10 | Recovery / reversal approach | AIDF-only | AIDF-only |
| 11 | Review budget | AIDF-only | AIDF-only |
| 12 | Class (T0 to T3) | AIDF-only | AIDF-only |
| 13 | Trip-wires | AIDF-only | AIDF-only |
| 14 | Dependency changes | partly: `design.md` may name them | partly: the plan names technology choices (the README's example does) |
| 15 | New rule or checker (only when the change adds one) | AIDF-only | AIDF-only |
| 16 | Status block: State, Established by, Approved by, Date (the JSON keys `approved_by` and `approved_date`) | AIDF-only (the human approval is recorded by AIDF) | AIDF-only |
| 17 | `change_id` (contract JSON) | partly: the change folder's name can be the id | partly: the feature directory's name can be the id (observed at stage 1 as `specs/001-...`; the README does not state the path) |
| 18 | `schema_version` (contract JSON) | AIDF-only | AIDF-only |

Count (18 fields: the template's parts and status block and the JSON keys; `spec_confidence` is row 3, `class` row 12, `tripwires` row 13, `dependency_changes` row 14; rows 15 to 18 were added after the first review found them missing from a table of 14): **supplied 2, partly 4, AIDF-only 12** for each tool, the same for both. Spec Kit's **constitution** (principles, written once per project) maps to no field of a Task Contract; it is closest to AIDF's kernel and `core/` rules and is **AIDF-only territory**: if used, it would restate AIDF's rules in a second place and could disagree with them, which stage 1 should note.

## Verdict (criterion 4)

| Tool | Limb 1: a saving that leaves approval and review in place | Limb 2: more than half AIDF-only | Verdict |
|---|---|---|---|
| OpenSpec | **No step is saved** (A1 adds steps 1 to 3) | **Met: 12 of 18** | the stop rule is met on both limbs; **needs the Change Owner's decision** |
| Spec Kit | **No step is saved** (A2 adds steps 1 to 3) | **Met: 12 of 18** | the same |

Two honest notes on the rule before the Change Owner decides:

1. **Limb 2 cannot tell the tools apart and would stop any spec tool.** The twelve AIDF-only fields are governance and bookkeeping (class, trip-wires, approval, evidence, recovery, review budget, the status block, the schema version); no spec tool covers them, and the proposal's own premise was that a tool supplies only the contract body. Applied to all 18 fields the rule is met by construction. Over the six body fields a tool could supply (1, 2, 4, 6, 14 and 17) it is not met: 2 supplied, 4 partly, none AIDF-only. I recommend that the gate treat limb 1 as the real test and limb 2 as informational.
2. **Limb 1 is met, and it is the finding.** Putting either tool in front of AIDF's spec work adds protocol steps and leaves the human's approval and review exactly where they are, so on paper human *steps* cannot fall. What is left is human *minutes* (P3) and rework: does a tool's body give a contract the human approves faster, with fewer clarification exchanges or fewer review findings? The bake-off was designed to measure exactly P3, and the cost of finding out is the harness work of stage 2 and 120 runs.

## Options for the Change Owner at the gate

| Option | What it means |
|---|---|
| **A. Stop here** | Record that the paper count finds no mechanism for fewer steps; shelve the tool question; take the handoff's "make AIDF's common path nearly free" items as the next change |
| **B. Go to stage 1, then decide** | Run the headless probe (two runs). It costs little, answers whether either tool can be driven at all, and shows what a tool actually writes and how long it takes. The bake-off continues only if a tool runs headless and the human-minutes mechanism still looks worth 120 runs |
| **C. Reframe before stage 1** | The alternatives page scored AIDF's workflow low against Spec Kit and BMAD; the cause may be onboarding, living specs (OpenSpec archives a change into the specs), or multi-agent support, none of which is a step count. Decide what "workflow" is to be improved before measuring a tool against it |

I recommend **B**: stage 1 is cheap, nothing is committed beyond a probe record, and it gives the Change Owner a real observation (headless behaviour, writes, time) to set against this paper result. If the probe shows a tool cannot run headless, the answer is A with evidence.

## What this document did not check

The READMEs only; no code, no trial, no documentation beyond them (Spec Kit's walkthrough and the installation pages the README links were not read). The field mapping is the author's reading. It has had no independent review yet (the contract's review is of the change as a whole).
