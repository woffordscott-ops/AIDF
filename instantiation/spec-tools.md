---
owner: framework-maintainer
load_when: a team that already plans its changes with OpenSpec or Spec Kit adopts AIDF, or is asked how those tools relate to a Task Contract
max_length: 5 pages
last_verified: 2026-11-06
---

# Using OpenSpec or Spec Kit with AIDF

For a team that already uses OpenSpec or Spec Kit to plan a change and wants to keep using it under AIDF. The short version: **the tool writes the plan; a human approves the Task Contract; only then does the tool build.** Nothing in AIDF reads a tool's files unless you ask: the way of working is the same with or without the draft generator of section 8.

**Why do it.** You keep the planning workflow your team already has. AIDF adds what the tools do not have: a class for the change, a human approval before anything is built, an evidence pack and a separate review (the tools supply 2 of the 18 fields of a Task Contract in full, and neither README describes a class, an approval record or evidence). If you do not already use one of these tools, nothing here is a reason to start: the comparison found no step saved.

## Start here

**Once, before the first change.** AIDF is set up in your project. If it is not yet, follow [how to set up AIDF in a project](set-up-aidf.md) first: it lists the steps in order (get AIDF, name the Change Owner and Architect, read the kernel, produce and check the context pack, declare how your agent works). Your tool is installed and initialised in the project, with its version pinned and written down. For OpenSpec you need Node.js (check `node --version`; if it is not found, install it from `https://nodejs.org/`). From your project folder, this installs the pinned version into the project only, with nothing installed system-wide: `npm install --prefix .tools @fission-ai/openspec@1.16.0`. Then initialise it, naming your agent's tool in place of `claude` (the other names are in `openspec init --help`): macOS or Linux `.tools/node_modules/.bin/openspec init --tools claude --no-animation`; Windows `.tools\node_modules\.bin\openspec.cmd init --tools claude --no-animation`. Add `.tools/` to your `.gitignore` before the next commit, so that the install is not committed. For Spec Kit, follow its own README. Section 4 has the facts about initialisation and pinning.

**For each change, in this order.**

1. **Classify the change** (T0 to T3, `core/01-lifecycle.md` section 6). For T0 and T1 you do not need the tool's plan: the Task Contract is three lines inline and the tool is optional. The steps below are for T2 and T3.
2. **Ask your agent to run only the tool's planning step, and tell it where to stop.** OpenSpec: `/opsx:propose` (shown as `/opsx-propose` in Cursor). Spec Kit: `/speckit-specify`, `/speckit-plan`, `/speckit-tasks`. Put the stop in the instruction. A wording that worked is the stop sentence of the probe's prompt (`TOOL_PROMPT` in `verification/spec_tool_probe.py`; the stage 1 runs were given the same sentence with ", including slug.py" (a file of their throwaway project) added after "code file"): "STOP before the tool's apply or implement step. Do not write or change any code file." Both tools end their flow by inviting you to apply; in the stage 1 runs the stop held because the instruction said so.
3. **Write the Task Contract** from `templates/task-contract.md`, beginning with its approver's opening. Take from the tool's files only what section 2 says they can supply (the outcome and the approach; the criteria, scope, dependencies and id in part). Fill the other twelve fields yourself: class, trip-wires, evidence strategy, recovery, review budget, status and the rest. An agent may draft them; the contract is Established until a human approves it.
4. **A human approves the Task Contract.** For T2 that is a human under Architect authority, who sets the State to Approved with their name and the date. Reading or editing the tool's plan is not this approval.
5. **Now run the tool's apply step:** OpenSpec `/opsx:apply` (`/opsx-apply` in Cursor); Spec Kit `/speckit-implement` and, if you use it, `/speckit-converge`.
6. **Verify and review as AIDF says:** the evidence pack (`templates/evidence-pack.md`), then separated review (`core/05-review.md`). If the tool's directories are committed, list them in the Task Contract's declared scope, and read section 4 before starting a review: the tools write files that `verification/run_review.py` refuses to review without a flag.

**What must not happen before the Task Contract is Approved.**

- The tool's apply, implement or converge step is not run.
- No code file is written or changed for the change.
- The tool's own "review the plan" step, or its plan files being accepted by the team, is not counted as the approval.
- Nothing from the tool is treated as evidence or as a review.

**What this guide does not promise.**

- That it holds for another release of either tool, another agent, another model or another operating system. It rests on one run per tool.
- That using a tool saves time or effort. The comparison found no step saved, and the Change Owner stopped it after stage 1.
- That AIDF certifies, supports or tests a tool, or that a reviewing agent is safe in a checkout that holds a tool's files.
- A converter from a tool's files to a Task Contract. None exists (section 7).

## A worked example

The change: add `limit` and `offset` to `GET /items` of a small invented inventory service (the request used in the bake-off's reading test). The planning files below are real output of the reading-test runs and are committed under `verification/spec-tool-bakeoff/reading-test/artifacts/`. Both tools were run with the stop in the instruction, and neither wrote code.

**Step 2, the tool plans.**

- **OpenSpec** wrote `openspec/changes/add-items-pagination/` with `proposal.md` (Why, What Changes, Impact), `design.md` (decisions and rejected alternatives), `specs/items-listing/spec.md` (the scenarios) and `tasks.md` (a checklist). Its proposal already marks the one caller-visible break: **BREAKING**, a call with no parameters used to return all 250 items and now returns the first 20.
- **Spec Kit** wrote `specs/001-paginate-items-listing/` with `spec.md` (user stories and acceptance scenarios), `plan.md`, `tasks.md`, `research.md`, `data-model.md`, `contracts/items-listing.md`, `quickstart.md` and `checklists/requirements.md`.

**Step 3, you write the Task Contract. Where each part comes from:**

| Task Contract part | Take it from | Add yourself |
|---|---|---|
| Opening: Problem, The change (with BREAKING) | OpenSpec `proposal.md` Why and What Changes; Spec Kit `spec.md` | Check the BREAKING mark against the code; keep each section to its limit |
| Intended outcome | the tool's why / what | one sentence a reviewer can test against |
| Acceptance criteria | the tool's scenarios (`specs/items-listing/spec.md`; the `spec.md` acceptance scenarios) | one criterion per check, each testable on its own |
| Approach | OpenSpec `design.md`; Spec Kit `plan.md` | the alternatives you reject, if the tool left them out |
| Declared scope | OpenSpec `proposal.md` Impact (`inventory/api.py`, `inventory/store.py`, `tests/test_api.py`); Spec Kit `plan.md` and `tasks.md` | the tool's own folder, if you commit it |
| Class, trip-wires, evidence strategy, recovery, review budget, status | nothing | all of it: here T2, because a caller's result changes; recovery is `git revert` |

**Steps 4 to 6.** A human approves the contract. Only then does the agent run `/opsx:apply` (it works through `tasks.md`) or `/speckit-implement`. You then write the evidence pack and have the change reviewed. The tool's `tasks.md` is a checklist for the build, not evidence that anything passed.

**Size.** In the reading test the same change gave 2,647 words in 5 OpenSpec files, 7,784 words in 8 Spec Kit files, and 1,539 words in one AIDF-native contract. The contract is the one you read before approving, so it is short on purpose: copy the little you need and leave the rest in the tool's folder.

## 1. What this guide is based on, and what it is not

- **Tested once.** OpenSpec v1.16.0 and Spec Kit v1.3.0, each run once in a throwaway project with `cursor-agent` and the model `grok-4.7-high`, on Windows, without a sandbox. The records are `verification/spec-tool-bakeoff/probe/openspec-probe.json` and `verification/spec-tool-bakeoff/probe/speckit-probe.json`; the findings are in `verification/spec-tool-bakeoff-stages-0-1-verifier-dispositions.md`. Another release, agent, model or operating system may behave differently, and nothing here promises otherwise.
- **No saving was shown.** A paper comparison found that a tool adds steps before the approval and removes none (`strategy/AIDF-SPEC-TOOL-BAKEOFF-STAGE0.md`), and the Change Owner stopped the comparison after stage 1 (the first trial of the tools). This guide is for teams that already use a tool. It is not a reason to adopt one.
- **AIDF does not certify a tool.** A tool's output is an input to the Task Contract. It is not evidence and it is not an approval.

## 2. What a tool can feed into a Task Contract

The 18 fields of the Task Contract (the template parts, the status block and the JSON keys) against the two tools, from the stage 0 document `strategy/AIDF-SPEC-TOOL-BAKEOFF-STAGE0.md`. "Supplied" means the tool's artifact can be the field's content as written; "partly" means it informs the field and a part is missing; "AIDF-only" means neither tool has the concept. The count is **supplied 2, partly 4, AIDF-only 12**, the same for both tools.

| # | Field | OpenSpec | Spec Kit |
|---|---|---|---|
| 1 | Intended outcome | supplied: `proposal.md` | supplied: the specify output |
| 2 | Acceptance criteria | partly: `specs/` | partly: the spec |
| 3 | Spec Confidence line | AIDF-only | AIDF-only |
| 4 | Declared scope | partly: `tasks.md` | partly: the plan and tasks |
| 5 | Outcome records | AIDF-only | AIDF-only |
| 6 | Approach | supplied: `design.md` (the agent may skip it) | supplied: the plan output |
| 7 | Invariants touched | AIDF-only | AIDF-only |
| 8 | Evidence strategy | AIDF-only | AIDF-only |
| 9 | Protected files touched | AIDF-only | AIDF-only |
| 10 | Recovery / reversal approach | AIDF-only | AIDF-only |
| 11 | Review budget | AIDF-only | AIDF-only |
| 12 | Class (T0 to T3) | AIDF-only | AIDF-only |
| 13 | Trip-wires | AIDF-only | AIDF-only |
| 14 | Dependency changes | partly: `design.md` | partly: the plan |
| 15 | New rule or checker | AIDF-only | AIDF-only |
| 16 | Status block | AIDF-only | AIDF-only |
| 17 | `change_id` | partly: the change folder's name | partly: the feature directory's name |
| 18 | `schema_version` | AIDF-only | AIDF-only |

The class stays AIDF's: a tool's plan does not set it, and a T0 or T1 change needs no tool at all (three lines, `core/01-lifecycle.md` section 4). Write the Task Contract with its approver's opening (`templates/task-contract.md`) and copy from the tool only what the table says it can supply.

## 3. The order of steps

The steps are in "Start here". The rule behind them is one sentence: only after the contract is Approved does the tool's apply step run: `/opsx:apply` (`/opsx-apply` in Cursor) for OpenSpec, `/speckit-implement` and `/speckit-converge` for Spec Kit. A tool's own plan review, or its invitation to apply, is not that approval. In both stage 1 runs the stop before apply held only because the prompt said so.

## 4. Facts to plan for

Each is from a committed record; none is a test of the tool beyond that one run.

- **Both tools write agent instruction files into the working directory.** In the stage 1 runs: 12 files for OpenSpec (6 command and 6 skill files under `.cursor/`) and 9 skills under `.cursor/skills/` for Spec Kit, whose agent step added 38 files in all. `verification/run_review.py` treats such paths (`.cursor`, `AGENTS.md`, `CLAUDE.md` and others) as files that can steer the reviewing agent and refuses to start a review of a head that holds them unless you pass `--allow-steering-files`. Look at the files first; review a head that does not hold them, or pass the flag knowingly.
- **Spec Kit runs scripts.** Its skills run PowerShell scripts, and by the stage 1 record its feature script can create git branches in a git checkout. The probe's workspace was not a git repository, so this was not observed. Check git state as well as files after a Spec Kit planning step.
- **Initialisation.** OpenSpec's init, run without a terminal, refuses without `--tools`. Spec Kit's init in a non-empty directory asks a question, is cancelled when no terminal answers, and still exits 0 with nothing written; the agent in the probe repeated it with `--force --non-interactive`. Do not treat an exit code as proof that a tool initialised.
- **Telemetry.** OpenSpec's README says usage statistics are on unless unset and off in CI; it names `OPENSPEC_TELEMETRY=0` and `DO_NOT_TRACK=1`. Spec Kit's README states nothing. The probe set `DO_NOT_TRACK=1` for both and did not observe the effect.
- **No pin command.** Neither README shows one (the OpenSpec example uses `@latest`). The probe pinned OpenSpec through `npm install --prefix` of `@fission-ai/openspec@1.16.0` and Spec Kit from the git tag `v1.3.0` (commit `34a0d388eac671d656eb05b125ad3ed6056168ed`). Pin yours and record the version in the Task Contract when a tool's output is part of the change.
- **Time.** One planning pass for a one-function change took about 181 s (OpenSpec) and 405 s (Spec Kit) of agent time, before any contract, approval, implementation or review.

## 5. What stays AIDF's

- **Evidence and review.** The evidence pack, the dispositions and the review reports are AIDF's (`templates/evidence-pack.md`, `core/05-review.md`). A tool's archive of a change, its task checklist or its converge result is an input and is never evidence.
- **Rules.** A Spec Kit constitution is not a kernel. It may not restate or override `KERNEL.md`; if the two disagree, `KERNEL.md` governs and the constitution is corrected.

## 6. Declared scope

When a tool's directories are committed with the change (`openspec/`, `specs/`, `.specify/`, `.cursor/`), list them in the Task Contract's declared scope; a file outside it is a scope change.

## 7. No converter exists

AIDF has no converter: no tool turns an OpenSpec change folder or a Spec Kit feature directory into a finished Task Contract. Section 8 describes a draft generator, which copies what such a folder says into a draft and leaves the rest to people. A format that the four mappings do not cover is one more mapping file; it is justified by a team that names the format it uses and asks for it, and it is tested against that team's records.

## 8. Drafting a Task Contract with the mapper

`verification/spec_mapper.py` copies what a planning folder already says into a draft Task Contract and leaves every other part as a TODO. One command:

```
python verification/spec_mapper.py --mapping <name or file> --input <folder> --out <draft.md>
```

`--mapping` is a built-in name (`openspec`, `speckit`, `kiro-synthetic`, `markdown-sections`; the files are in `instantiation/mappings/`) or the path of your own mapping file. `--input` is the folder that holds the planning files (the folder that contains `openspec/` for OpenSpec, or `specs/` for Spec Kit) and is only read. `--out` is a new file outside that folder; `--force` replaces an existing draft. The exit code is 0 when the draft is written and 2 when the tool refuses, with the reason on the error output.

**What a draft is.** The parts the planning files supply (the problem, the change, the approach, requirement and scenario seeds for the criteria, the task list for the scope, dependency notes, the change's name), each in a quotation under its source file, and `TODO(author)` or `TODO(AIDF)` for every other part. Its header counts the parts copied and the parts left.

**What a draft is not.** It is not an approval (the State is Established and no approver is named), not a classification (the class is a TODO) and not evidence. A person still writes the rest, chooses the class and has the contract approved before anything is built, as in "Start here".

**Other formats.** Another format is another mapping file: the four in `instantiation/mappings/` show the shape, the schema is closed, and the tool names the key at fault. `kiro-synthetic` is built from third-party descriptions of Kiro, not from Kiro's output. The tool treats the folder as untrusted: it follows no link, reads only the files a rule names, refuses a file over 256 KiB, runs nothing and uses no network. How much effort a draft saves has not been measured.
