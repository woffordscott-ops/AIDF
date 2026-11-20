---
owner: framework-maintainer
load_when: deciding or implementing the mapping-driven Task Contract draft generator (stages 0 and 1)
max_length: an approver's opening, then 1 screen
last_verified: 2026-11-06
---

# Task Contract: a mapping-driven Task Contract draft generator (stages 0 and 1)

`core/01-lifecycle.md` §4. Class T2. **Status: Approved by the Change Owner on 2026-11-06 (see Status).** It implements `strategy/AIDF-SPEC-MAPPER-PROPOSAL.md`, whose five decisions the Change Owner approved as written on 2026-11-06.

## Approver's opening

- **Read this first:** This asks you to approve a new small tool, `verification/spec_mapper.py`, that reads a folder of planning files and a mapping file and writes a draft Task Contract with `TODO` markers where only AIDF can fill a part. Read The change and the decisions at the end. Your approval is on the whole contract. Stage 2 (your reading of one draft) and stage 3 (a customer's format) come later and are not part of this approval.

- **Problem:** A team that plans with OpenSpec, Spec Kit or its own layout has to copy the outcome, the approach, the requirements and the file list from its planning files into a Task Contract by hand. That is slow and invites transcription slips, and AIDF has nothing to help.

- **Why it matters:** The integration guide (`instantiation/spec-tools.md`) tells teams to do this by hand, and you asked for one tool that can serve any format, including a customer's own, without a new converter for each.

- **The change:** One command, `python verification/spec_mapper.py --mapping <name or file> --input <folder> --out <draft.md>`. A mapping is a small JSON file: which files and which headings supply which Task Contract part. Four mappings ship (`openspec`, `speckit`, `kiro-synthetic`, `markdown-sections`); another format is another file. The draft copies what the source says, marks every other part `TODO`, never marks a contract Approved and never classifies it. The tool is offline, standard library only, treats the input as untrusted, and gives the same bytes for the same input. BREAKING: none; it is a new file.

- **Technical details:** New files: `verification/spec_mapper.py`; `instantiation/mappings/openspec.json`, `speckit.json`, `kiro-synthetic.json`, `markdown-sections.json`; `verification/tests/test_spec_mapper.py`; `verification/spec-mapper-fixtures/` (the OpenSpec and Spec Kit outputs of the reading test copied as inputs, a synthetic Kiro-style folder, a hand-made expected draft for each, a malformed and a hostile folder); a section in `instantiation/spec-tools.md`; `CHANGELOG.md`; the outcome records. A mapping has `schema_version`, `name`, `detect` (files that must exist), `rules` (each: `source` glob under the input folder, `operation` one of `file`, `section`, `blocks`, `checklist`, a `heading` or `prefix`, a `target` part, an optional `limit`) and `id_from`. The schema is closed: an unknown key, a wrong type, a glob that leaves the folder or a rule that names a part that does not exist is refused with a message. Exit codes: 0 written, 2 refused. The draft lists at the top which files it read and how many parts it copied and how many remain.

- **What you need to decide:** Assumptions: the Task Contract parts a planning tool can supply are the six of the stage 0 table (outcome and approach in full; criteria, scope, dependencies and id in part). The synthetic Kiro mapping is built from third-party descriptions and says so. Out of scope: any customer format (stage 3), measuring savings (stage 2 is one reading by you), running or approving anything, a graphical interface, a YAML reader. Testing: golden-file tests (the draft equals the hand-made expected draft byte for byte), refusal tests, mutation of each rule, the existing suite and the preflight. Class: T2 (a new checker; no trip-wire), two Verifier rounds with the untrusted-input list as the focus. Main risk: a hostile folder or mapping (a link, a huge file, a path that leaves the folder) making the tool read or write outside its folders, which the refusal tests and the reviewer are to try.

## Part A: Minimal

- **Intended outcome:** A team can turn its OpenSpec, Spec Kit, Kiro-style or custom planning folder into a draft Task Contract with one command and a mapping file, the draft claims only what the source says, and the tool cannot be made to read or write outside the named folders.
- **Acceptance criteria:**
  1. **The schema.** A mapping is accepted only if it has exactly the keys named in Technical details with the right types; any other mapping is refused with exit code 2 and a message naming the key.
  2. **The operations.** `file`, `section`, `blocks` and `checklist` each return exactly the text a test fixture shows, in the order of the source, with the source file named for each passage.
  3. **The built-in mappings.** For the real OpenSpec and Spec Kit outputs of the reading test, the draft equals the committed expected draft byte for byte; for the synthetic Kiro-style folder and a markdown-sections example likewise.
  4. **The draft.** Every part the source supplies is copied with its source file named; every other part is `TODO(author)` or `TODO(AIDF)`; the Status block is `Established` with no approver; no class is chosen; the header says how many parts were copied and how many remain; the approver's opening is filled only where the source supplies it.
  5. **Untrusted input.** The tool follows no symbolic link or junction, reads no file above a size limit, reads only files a rule names and that lie inside the input folder, refuses an output path inside the input folder or an existing output file without `--force`, executes nothing, uses no network, and refuses a hostile fixture (a link, an oversized file, a rule or glob that leaves the folder, a malformed mapping).
  6. **Determinism.** The same input and mapping give the same bytes, on any file-system order.
  7. **The guide.** `instantiation/spec-tools.md` gains a short section on drafting with the mapper, with the exact command, and says what the draft is not (an approval, a classification, evidence).
  8. **Tests.** `verification/tests/test_spec_mapper.py` asserts each criterion; each test fails when the code it names is broken (mutations recorded in the pack).
  9. **Scope.** No change to `core/`, `KERNEL.md`, `templates/`, the preflight, `verification/run_review.py` or the export tool; the new files are covered by the public export without a change to its manifest, or the dispositions say which entries the cut needs.
  10. **Outcome records** (core/05-review.md section 6): the review report patterns are `verification/spec-mapper-verifier-report*.md`; the dispositions file is `verification/spec-mapper-verifier-dispositions.md`. This criterion only declares the outcome-record paths.

  Spec Confidence: Partial until decisions 1 to 4 were answered; Clear after, on 2026-11-06.

- **Declared scope:** `verification/spec_mapper.py`, `instantiation/mappings/**`, `verification/tests/test_spec_mapper.py`, `verification/spec-mapper-fixtures/**`, `instantiation/spec-tools.md` (one section, and the two sentences of the guide that said no tool reads a tool's files or offers a converter), `verification/tests/test_spec_tools_guide.py` (the pins of those sentences and of the new section's heading), `CHANGELOG.md`, `strategy/AIDF-SPEC-MAPPER-PROPOSAL.md` (the approved proposal, committed on this branch), `spec/AIDF-SPEC-MAPPER-STAGES-0-1-TASK-CONTRACT.md`, `verification/spec-mapper-task-contract.json`, `verification/spec-mapper-evidence-pack.json`, `verification/spec-mapper-verifier-dispositions.md`, `verification/spec-mapper-verifier-report*.md`. **Excluded:** everything named in criterion 9.

## Part B: Plan

- **Approach:** a pure module (`load_mapping`, `read_source`, the four operations, `render_draft`) behind a small CLI; hand-made expected drafts are written first from the fixtures and the template, then the code is written to produce them; refusals are tested before features.
- **Invariants touched:** none of the repository's gates; the Task Contract template (`templates/task-contract.md`) is read for its part names and not changed; `instantiation/spec-tools.md` is a live document.
- **Evidence strategy:** golden-file tests; refusal tests with real links where the account allows (Windows junction, POSIX symbolic link on WSL) and skipped otherwise; mutation of each rule, each refusal and the renderer; the existing suite and the preflight `--ci-like`.
- **Protected files touched:** to be confirmed with the preflight before approval; expected `none`.
- **Recovery / reversal approach:** `git revert`; nothing depends on the tool.
- **Review budget (this change):** one preflight run and two Verifier rounds; no security layer (no trip-wire). Accepted limits stated before review: one reader, no customer file, a synthetic Kiro example; the draft is a drafting aid and not a saving that has been measured.

## Classification

Proposed **T2**: a new checker-style tool and a new interface of the process; it holds no credential, makes no network call, writes one named file, and no kernel trip-wire applies.

## Decisions for the Change Owner

1. **Class and review.** (a) [recommended] T2 with two Verifier rounds; (b) T3 with a distinct Security Reviewer because the tool parses untrusted files.
2. **Names and places.** `verification/spec_mapper.py`, `instantiation/mappings/*.json`, fixtures in `verification/spec-mapper-fixtures/`. [recommended] as written.
3. **Fixtures.** (a) [recommended] copy the real OpenSpec and Spec Kit outputs of the reading test into the fixtures (they are committed already and carry no private identifier); (b) generate them again by running the tools (needs the probe and network).
4. **Order with the other open changes.** (a) [recommended] after the customer cut and the guide address change are merged, so the public export picks it up cleanly; (b) now.

## Status

- **State:** Approved
- **Established by** (author): Claude Sonnet 5.5 (Anthropic), under Implementer role, 2026-11-06
- **Approved by** (human, T2/T3 only — role: Architect): Scott Wofford (Change Owner and Architect), 2026-11-06, by his message "lets push and merge, accept your recommendations for the t3 internal-name contract and converter task contract and start verifier round 1": all four decisions as recommended: (1) T2 with two Verifier rounds; (2) the names and places as written; (3) the real OpenSpec and Spec Kit outputs of the reading test are the fixtures; (4) implementation starts after the customer cut and the guide address change are merged.
- **Date:** 2026-11-06
- **Class:** T2
- **Spec Confidence at intake:** Partial (decisions 1 to 4)
- **Re-evaluated to Clear by:** the Change Owner's answers to decisions 1 to 4 (2026-11-06)
