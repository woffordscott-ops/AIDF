---
owner: framework-maintainer
load_when: deciding whether and how AIDF gets one configurable tool that drafts a Task Contract from a team's own planning files (OpenSpec, Spec Kit, Kiro-style or a custom layout)
max_length: 4 screens
last_verified: 2026-11-06
---

# Proposal: a mapping-driven draft generator for Task Contracts

Status: **decisions accepted by the Change Owner on 2026-11-06 ("For the converter proposal, I approve as written on the decisions"): all five as recommended**; nothing is built, and the next step is the Task Contract for stages 0 and 1. Written 2026-11-06 after the Change Owner said yes to a short proposal and asked whether one tool could serve any format, with no customer files in hand.

## What is proposed

One small command, `spec_mapper`, that reads a folder of planning files and a **mapping file** that says which files and headings supply which parts of a Task Contract, and writes a **draft** Task Contract. A format is a mapping file. OpenSpec and Spec Kit ship as the first two; a Kiro-style layout and a generic "markdown sections" mapping follow; a customer's own layout is one more mapping file that the customer or we write in an hour, with no code change.

The draft is a starting point. It copies what the tool's files already say (outcome, approach, requirements and scenarios as criteria seeds, files named for scope, dependencies, the change's name for the id) and writes a `TODO` marker for every part only AIDF can fill: class, trip-wires, evidence strategy, recovery, review budget, status. It never writes **Approved**, never classifies, and says in its header what it copied from which file.

## Why this and not a converter per tool

The comparison in `strategy/AIDF-SPEC-TOOL-BAKEOFF-STAGE0.md` found that a tool's files can supply 2 of the Task Contract's 18 fields in full and 4 in part; the other 12 are AIDF's. Any converter is therefore a **drafting aid** for six fields, whatever the source. The six come from the same few shapes in every format found:

| Shape | OpenSpec | Spec Kit | Kiro (secondhand descriptions) | Notation inside |
|---|---|---|---|---|
| Why / what | `proposal.md` (Why, What Changes, Impact) | `spec.md` (user stories, summary) | `requirements.md` (user stories) | free text |
| Requirements with scenarios | `specs/<domain>/spec.md`: `## ADDED/MODIFIED/REMOVED Requirements`, `### Requirement:`, `#### Scenario:` (GIVEN, WHEN, THEN) | `spec.md`: `FR-001`, `SC-001`, Given/When/Then, `[NEEDS CLARIFICATION]` | `requirements.md`: acceptance criteria in EARS | RFC 2119 SHALL/MUST; Gherkin; EARS (five patterns) |
| Approach | `design.md` | `plan.md` (technical context, constitution check) | `design.md` | MADR-style decisions possible |
| Task checklist | `tasks.md` | `tasks.md`: `- [ ] T001 [P] [US1] …` | `tasks.md` | checkbox lists |
| Change identity | the change folder's name | the feature directory (`specs/001-…`) | the spec folder under `.kiro/specs/` | folder name |

So four extraction operations cover all of them: take a file by glob; take a section by heading; take every block that starts with a given heading prefix (a requirement, a scenario, a story); take a checklist. A mapping file is a list of rules `source operation → Task Contract part`.

## Sources (read 2026-11-06)

OpenSpec: `docs/concepts.md` of `Fission-AI/OpenSpec` (change folder layout, delta sections, `Requirement:`/`Scenario:` headings, RFC 2119 keywords; a third-party guide mentions a `RENAMED` section that the official page does not, so it is unconfirmed). Spec Kit: `templates/spec-template.md`, `plan-template.md` and `tasks-template.md` of `github/spec-kit`. Kiro: third-party descriptions only (three files under `.kiro/specs/`, EARS acceptance criteria); no official page was read, so a Kiro mapping starts as a **synthetic** example, labelled as such. Notations: EARS (Mavin et al., RE'09), Gherkin (Cucumber reference), MADR (`adr/madr`). No existing Spec Kit to OpenSpec converter was found. The repository already holds real output of OpenSpec and Spec Kit for one change (`verification/spec-tool-bakeoff/reading-test/artifacts/`).

## Design

- **Mapping file:** JSON (the standard library has no YAML reader, and JSON can be checked against a closed schema). Fields: `name`, `version`, `detect` (files that must exist), `rules` (each: `source` file glob, `operation`, `heading` or `prefix`, `target` part, optional `limit`), `id_from` (folder name rule). A schema, closed (no unknown keys), is checked first.
- **Command:** `python verification/spec_mapper.py --mapping <file-or-built-in-name> --input <folder> --out <draft.md>`. Standard library only, offline, deterministic (same input and mapping, same bytes), writes only the named output file, refuses an output inside the input folder.
- **Untrusted input:** the input folder is data. The tool follows no symbolic link or junction, ignores files above a size limit, never executes anything, reads only the files a rule names, keeps every path inside the input folder, and writes the draft as text with the source file named for each copied passage. It does not expand a pattern that could read outside the folder.
- **The draft:** the template's approver's opening is filled only where the source supplies it (Problem and The change from why/what; Technical details from design) and carries `TODO(author)` elsewhere; Part A and Part B parts that only AIDF can fill are `TODO(AIDF)`; the Status block is `Established`, empty approver. A count line states how many parts were copied and how many remain.
- **Built-in mappings:** `openspec`, `speckit` (both tested against the real output above), `kiro-synthetic` (a hand-written example from public descriptions, labelled), `markdown-sections` (generic: headings by name from a mapping the user edits).
- **Where it lives:** `verification/spec_mapper.py`, mappings in `instantiation/mappings/`, a how-to section added to `instantiation/spec-tools.md`. It would be included in the public tree because the customer cut keeps the checks.

## Stages

0. **Paper and fixtures** (small): the closed mapping schema; golden-file inputs (the two real outputs, one synthetic Kiro-style folder, one malformed and one hostile folder); the draft layout.
1. **The tool and its tests:** parser, the four operations, the draft writer, refusals; mutation tests; a golden-file test for each built-in mapping (the draft equals a hand-made reference, byte for byte).
2. **Reading check:** the Change Owner reads one generated draft and says whether it saved effort over writing the contract from scratch; this is the only measurement, one reader, and it is stated as such.
3. **A customer's format:** when a customer sends sample files, the first test is whether a mapping file written in an hour covers them. If not, the schema gets the missing operation.

Each stage is its own Task Contract. The tool is class T2 (a new checker; no trip-wire), with two Verifier rounds and attention to the untrusted-input list.

## What it will not do

It does not approve, classify, judge quality, merge two tools' output, run the tool's apply step, or read a network. It does not make the integration cheaper for the approver: the human still reads and approves the contract, which the comparison found to be where the time goes. Its claim is narrower: less copying and fewer transcription slips for the six fields a planning tool can supply.

## Decisions for the Change Owner

1. **Go ahead with stage 0 and 1 as one Task Contract?** [recommended] yes, with the four built-in mappings above.
2. **Mapping format:** JSON [recommended] (closed schema, standard library), or YAML (needs a parser we would have to write or vendor).
3. **Location:** `verification/spec_mapper.py` and `instantiation/mappings/` [recommended].
4. **Customer sample:** ask one customer for a sample planning folder in their format to be used in stage 3; it does not block stages 0 to 2.
5. **Kiro:** accept a synthetic example for now [recommended], replaced when someone supplies real Kiro output.

## What this document did not check

No tool was run for this proposal; the format descriptions come from the pages named above and, for Kiro, from third-party text. The six fields are the stage 0 count (2 supplied, 4 partly); this proposal does not show that a mapping covers any customer's files.
