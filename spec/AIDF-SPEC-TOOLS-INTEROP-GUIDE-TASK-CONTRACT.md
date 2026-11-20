---
owner: framework-maintainer
load_when: deciding or implementing the guide for using OpenSpec or Spec Kit with AIDF
max_length: an approver's opening, then 1 screen
last_verified: 2026-11-06
---

# Task Contract: a guide for teams that already use OpenSpec or Spec Kit

`core/01-lifecycle.md` §4. Class T2 (see Classification). **Status: Approved by the Change Owner on 2026-11-06 (see Status).**

## Approver's opening

- **Read this first:** This asks you to approve a documentation change: one guide that tells a team that already plans its work with OpenSpec or Spec Kit how to keep doing so under AIDF. Read The change, then the five decisions at the end. Your decision is on the whole contract (Part A, Part B, Status), not on this opening alone.

- **Problem:** Customers use OpenSpec or Spec Kit to write the plan for a change, and AIDF has nothing that says how those plans relate to a Task Contract, an approval or a review. Stage 1 of the spec-tool bake-off showed that both tools run headless and write their planning files, but also that they write agent instruction files and scripts into the working directory, and that their own "apply" step has no pause. Nobody can currently tell a team which of that is safe under AIDF.

- **Why it matters:** A team that wires a tool in without guidance can start an implementation before a human approves anything, or hand a reviewer a checkout that contains files that steer the reviewing agent. The bake-off found no saving from the tools (the stop rule was met and you stopped it), so the guide is for those who already use them, and it must not suggest otherwise.

- **The change:** A new guide, `instantiation/spec-tools.md`, with a one-line pointer from `instantiation/README.md`. It says what a tool's planning files can feed into a Task Contract and what stays AIDF's. It gives the order of steps: the tool plans; the author writes the Task Contract, with its opening; a human approves the contract; only then does the tool's apply step run. It states the safety facts the bake-off recorded and what to do about each. It states what was tested and what was not. No rule of `core/` changes, no code is written, and no converter is built. BREAKING: none.

- **Technical details:** New files: `instantiation/spec-tools.md` (the guide) and `verification/tests/test_spec_tools_guide.py` (presence and citation tests). Edited: `instantiation/README.md` (one line), `CHANGELOG.md` (one entry). The guide has these parts. (1) Scope and honesty: tested only at OpenSpec v1.16.0 and Spec Kit v1.3.0, one run each, `cursor-agent` with `grok-4.7-high` on Windows, no sandbox; no measurement shows a saving; AIDF does not certify a tool. (2) Field map: of the 18 Task Contract fields, a tool supplies the outcome and the approach and informs the criteria, scope, dependencies and id; twelve stay AIDF's (class, trip-wires, approval, evidence strategy, recovery, review budget, status and the rest), each cell citing `strategy/AIDF-SPEC-TOOL-BAKEOFF-STAGE0.md`. (3) The order of steps and the rule that the contract's approval, not the tool's "review the plan", authorises implementation. (4) Safety facts, each citing a committed record: the tools write `.cursor/` commands and skills (12 for OpenSpec, 9 for Spec Kit), which `verification/run_review.py` treats as steering paths and refuses without `--allow-steering-files`; Spec Kit runs PowerShell scripts, one of which can create git branches in a git checkout (by the stage 1 record; not observed, because the probe workspace was no git repository); OpenSpec init refuses without `--tools`, Spec Kit init asks a question and exits 0 when cancelled; telemetry is on by default for OpenSpec (`OPENSPEC_TELEMETRY=0`); neither README gives a pin command. (5) What stays AIDF's: evidence pack, dispositions and review reports; a tool's archive or constitution is an input and never evidence, and a Spec Kit constitution may not restate or override `KERNEL.md`. (6) Declared scope: a tool's directories are listed in the Task Contract when they are committed. (7) The converter: not built; the guide says what would justify one (a customer with a named format and a request).

- **What you need to decide:** The five decisions below. Assumptions: the bake-off records are accurate for what they cover; guide statements about a tool are limited to those records and the READMEs' extraction, so I do not promise they hold for later releases. Out of scope: a converter, any change to `core/`, the preflight, `run_review.py` or the harness, testing other agents or operating systems, and any claim of a saving. Testing: presence tests, a test that every repository path the guide cites exists, mutation of each asserted statement, the existing suite and the preflight `--ci-like`; the Change Owner reads the guide; the Verifier checks each factual sentence against the cited record. Class: T2, because it tells teams how to operate the approval gate. Main risk: a guide written from one run per tool may be wrong for a different agent, OS or release; it says so on its first screen.

## Part A: Minimal

- **Intended outcome:** A team that already uses OpenSpec or Spec Kit can follow one guide to run it under AIDF without bypassing the Task Contract approval, the review or the steering-file rule, and the guide claims no more than the committed records show.
- **Acceptance criteria:**
  1. **The guide.** `instantiation/spec-tools.md` exists with the front matter the repository's documents carry; a first section, "Start here", that gives the one-time setup, the numbered steps to take for each change (classify, plan with the tool and stop, write the Task Contract, human approval, apply, verify and review), what must not happen before approval and what is not promised, with a short statement of why to use it and a link to the how-to of criterion 12; a "A worked example" section (one change, the files each tool wrote, and where each Task Contract part comes from); and then the parts named in Technical details (1) to (7), in that order. (Amended 2026-11-06, twice, see Status.)
  12. **The how-to.** `instantiation/set-up-aidf.md` gives the exact steps to set AIDF up in a project for a reader who knows nothing and has not started: what to install and how to check it (git, Python), the commands to get AIDF and to run its checks on macOS, Linux and Windows, how to name the roles, a starter context pack (`instantiation/starter/`) that passes `instantiation/check_context_pack.py` as shipped, a script for an existing project that is tested to make a pack that passes, how to record the agent's mode with each of the four modes explained (when to use it, what it may and may not do) and three worked declarations, and the instruction to give the agent for the first change; it adds no rule, and the guide and `instantiation/README.md` link to it. (Added 2026-11-06, extended the same day, see Status.)
  2. **Honest scope.** The guide states the tested versions, the agent, the model, the operating system, that each was run once, that no measurement showed a saving, and that AIDF does not certify a tool.
  3. **Field map.** The guide's table has the 18 fields of the stage 0 document with the same supplied / partly / AIDF-only counts (2, 4, 12) and cites that document; the guide contains no field the stage 0 document does not.
  4. **The order of steps.** The guide states that a tool's apply step (`/opsx-apply`, `/speckit-implement`, `/speckit-converge`) runs only after the Task Contract is Approved, and that a tool's own plan review does not replace that approval.
  5. **Safety facts.** The guide states each fact in Technical details (4) and cites the committed record that shows it; every repository path it cites exists.
  6. **What stays AIDF's.** The guide states that evidence packs, dispositions and review reports are AIDF's, that a tool's archive and constitution are inputs and not evidence, and that a constitution does not override `KERNEL.md`.
  7. **The converter.** The guide says no converter exists, names the condition that would justify one, and offers no unbuilt feature as available.
  8. **Tests.** `verification/tests/test_spec_tools_guide.py` asserts the parts and their order, the tested versions, the 2 / 4 / 12 counts, the apply-after-approval rule, the steering-file fact and every cited path; each test fails on the repository without the guide, and the pack's mutation of each asserted statement is killed.
  9. **Reading.** The Change Owner reads the guide as a team lead who already uses one of the tools would, and records whether he can tell from the guide alone what to do first, what must not happen before approval, and what is not promised.
  10. **Scope.** No change to `core/`, `KERNEL.md`, `templates/`, the preflight, `verification/run_review.py`, the measurement harness, the probe or any approved contract.
  11. **Outcome records** (core/05-review.md section 6): the review report patterns are `verification/spec-tools-guide-verifier-report*.md`; the dispositions file is `verification/spec-tools-guide-verifier-dispositions.md`. This criterion only declares the outcome-record paths.

  Spec Confidence: Partial until decisions 1 to 5 were answered; Clear after, on 2026-11-06.

- **Declared scope:** `instantiation/spec-tools.md`, `instantiation/set-up-aidf.md`, `instantiation/starter/**`, `instantiation/README.md` (one line), `verification/tests/test_spec_tools_guide.py`, `CHANGELOG.md`, `spec/AIDF-SPEC-TOOLS-INTEROP-GUIDE-TASK-CONTRACT.md`, `verification/spec-tools-guide-task-contract.json`, `verification/spec-tools-guide-evidence-pack.json`, `verification/spec-tools-guide-verifier-dispositions.md`, and the reports `verification/spec-tools-guide-verifier-report*.md`. **Excluded:** everything named in criterion 10.

## Part B: Plan

- **Approach:** Write the guide only from the committed records (the stage 0 document, the stage 1 findings in the bake-off dispositions, the probe records, the README extraction) and `run_review.py`'s steering rule; do not run the tools again. Add presence and citation tests, then mutate each asserted statement in a scratch copy. Written after the five decisions were answered (2026-11-06).
- **Invariants touched:** the approval gate before implementation (`core/01-lifecycle.md` §4), described and not changed; the steering-file rule of `verification/run_review.py`, described and not changed; `instantiation/` as a live directory.
- **Evidence strategy:** presence tests that fail without the guide; a citation test (every repository path exists); mutation of each asserted statement; the Change Owner's reading; the existing suite and the preflight `--ci-like`.
- **Protected files touched:** to be confirmed with the preflight before approval (whether `instantiation/README.md` is attested); expected `none`.
- **Recovery / reversal approach:** `git revert`; nothing depends on the guide.
- **Review budget (this change):** one preflight run and two Verifier rounds; no security layer (no trip-wire). Accepted limits stated before review: the guide rests on one run per tool and says so; nothing checks that a statement stays true when a tool releases a new version; the Verifier cannot run the tools (no network) and checks statements against the records only.

## Classification

Proposed **T2**: the guide tells teams how to operate around the approval and review gates. It touches no `core/` rule and no trip-wire applies.

## Decisions for the Change Owner

1. **Where the guide lives.** (a) [recommended] `instantiation/spec-tools.md` with a pointer from `instantiation/README.md`: the directory is live, and the guide is about adopting AIDF in a project that already has tooling; (b) a new top-level `integrations/` directory (a new place to maintain); (c) `strategy/` (it is not a user guide).
2. **One guide or two.** (a) [recommended] one guide for both tools, with OpenSpec and Spec Kit differences in short tables; (b) one per tool.
3. **The converter.** (a) [recommended] none now; the guide names the condition (a customer with a named format and a request) and a converter becomes its own Task Contract then; (b) build an OpenSpec change-folder converter in this change (the frozen mapping script exists only as a design).
4. **A customer reading.** (a) [recommended] you ask one customer who uses either tool to read the draft guide before it is merged, and their answer is recorded in the dispositions; it does not gate the merge unless you say so; (b) your reading only; (c) the customer reading is a gate.
5. **Review layers:** Verifier rounds only [recommended], or add the security layer.

## Status

- **State:** Approved
- **Established by** (author): Claude Sonnet 5.5 (Anthropic), under Implementer role, 2026-11-06
- **Approved by** (human, T2/T3 only — role: Architect): Scott Wofford (Change Owner and Architect), 2026-11-06, by his message "I will approve with your recommendations being used for all 5 decisions": (1) the guide lives at `instantiation/spec-tools.md` with a pointer from `instantiation/README.md`; (2) one guide for both tools; (3) no converter now, the guide names the condition; (4) the Change Owner asks one customer to read the draft, the answer is recorded in the dispositions and does not gate the merge; (5) Verifier rounds only.
- **Date:** 2026-11-06
- **Class:** T2
- **Spec Confidence at intake:** Partial (decisions 1 to 5)
- **Re-evaluated to Clear by:** the Change Owner's answers to decisions 1 to 5, as drafted
- **Amended 2026-11-06 (criterion 1):** the Change Owner's first reading of the guide (recorded in `verification/spec-tools-guide-verifier-dispositions.md`) was that he could not tell where to start, what to do first, what must not happen before approval or what is not promised, so criterion 9 was not met. The Implementer added the "Start here" section and criterion 1 now requires it. The Change Owner's acceptance of this amendment is requested with his second reading; the amendment adds a section and removes none.
- **Amended a second time 2026-11-06 (criteria 1 and 12, declared scope):** the Change Owner's second reading: he could tell what must not happen before approval and what is not promised, but wanted a link to a how-to that clearly gives the steps to set AIDF up, and was still unclear on what to do to use the integration and why. Criterion 1 now also requires a short "why" and a worked example; criterion 12 and `instantiation/set-up-aidf.md` are new. The amendments add; none removes a criterion. His acceptance is requested with the third reading.
- **Amended a third time 2026-11-06 (criterion 12, declared scope):** the Change Owner's third message: the steps must be very explicit and assume no prior knowledge (his example: step 1 of the how-to must say how to get AIDF, how to clone the repository and how to run the script). Criterion 12 now requires exact steps from nothing, and `instantiation/starter/**` (the starter context pack) is in scope so that the how-to can give a pack that the checker passes. The address of the AIDF repository is written as a placeholder `<AIDF-REPO-URL>`, because no public address has been decided. Nothing was removed; his acceptance is requested with the next reading.
