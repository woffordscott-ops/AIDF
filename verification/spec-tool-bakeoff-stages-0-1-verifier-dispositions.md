---
owner: framework-maintainer
load_when: reading the record of decisions, probe runs and review findings of stages 0 and 1 of the spec-tool bake-off
max_length: 3 screens
last_verified: 2026-11-05
---

# Dispositions: spec-tool bake-off, stages 0 and 1

Append only. Contract: `spec/AIDF-SPEC-TOOL-BAKEOFF-STAGES-0-1-TASK-CONTRACT.md` (approved 2026-11-05).

## Gate decision at the end of stage 0 (2026-11-05)

Stage 0 (`strategy/AIDF-SPEC-TOOL-BAKEOFF-STAGE0.md`) found the stop rule met for both tools on both limbs (no step saved; 9 of 14 contract fields AIDF-only) and gave the verdict "needs the Change Owner's decision". The Change Owner chose **option B** (go to stage 1, then decide) with the words "Go with B", and the Implementer read that as the gate decision to build the snapshot tool and the probe. Running the probe was a separate go: "go, run the probes" (2026-11-05).

## Probe runs and the faults in the probe itself

Records are in `verification/spec-tool-bakeoff/probe/`. The probe ran on Windows in a scratch directory outside the repository, without a sandbox (the agent CLI supports it only on macOS and Linux, and the WSL machine here holds no `cursor-agent`, `node` or `uv`), as decision 3 of the contract allows; the records say so.

| Run | Result | Cause and disposition |
|---|---|---|
| OpenSpec, first | invalid, no record kept | My fault: `npm install` ran without `--prefix`, so the binary was not on the probe's PATH; `openspec` was "not found". Fixed in the script with a test. No agent was started |
| OpenSpec run 1 (`openspec-probe-run1-init-needs-tools-flag.json`) | install and `--version` 1.16.0 worked; `openspec init` exited 1 | A finding about the tool: run without a terminal, `init` refuses without `--tools` (it lists about 50 valid tools). The probe now passes `--tools cursor` |
| OpenSpec run 2 (`openspec-probe-run2-agent-model-usage-limit.json`) | init wrote 15 files; the agent step exited 1 with "You've hit your usage limit" | Not the tool: the account's usage limit for `gpt-5.6-sol-high` (resets 2026-11-25). No spend limit was changed; the Change Owner had not asked for that |
| OpenSpec run 3 (`openspec-probe.json`, `grok-4.7-high`) | valid | See the findings below |

## Decision on the candidate model (2026-11-05)

The cap on `gpt-5.6-sol-high` made the candidate of the proposal unavailable until 2026-11-25. The Change Owner asked for a suggestion and replied "I accept your recommendations": **`grok-4.7-high` is the stage 3 candidate and `composer-2.5` the stage 4 second candidate**; the scorer must be a vendor other than the candidate's (a Claude model or `composer-2.5`; quota to be checked at stage 2); the in-arm reviewer is a different model from the candidate, fixed identically for all three arms in the pre-registration; no spend limit is raised for this; two candidates are not run at stage 3. The proposal's Candidate section is amended when the gate decision is recorded, not before.

Note, same day: the Change Owner added that Codex is available with tokens and can run `gpt-5.6-sol-high`. No decision was taken. The Implementer suggested keeping the accepted candidate (`grok-4.7-high` on `cursor-agent`), considering Codex as the stage 4 second candidate (reported as "a different model and shell", not a pure model effect), and deciding at the gate whether the stage 2 contract includes a Codex probe (`codex exec`, its sandbox); that is outside the scope of the present contract.

## What the probe found (stage 1, `grok-4.7-high` on `cursor-agent`, Windows, no sandbox)

One valid run per tool (`openspec-probe.json`, `speckit-probe.json`). Two runs show what happened once, not what always happens. Everything below is from the records; no code of the tools was read.

| Question | OpenSpec 1.16.0 | Spec Kit 1.3.0 |
|---|---|---|
| (a) Pinned install without a global change | Yes: `npm install --prefix <scratch>`, 57 packages, 4.5 s; `--version` 1.16.0 | Yes, after putting a pinned `uv` 0.13.7 into the scratch directory with pip (the machine has none): installed from the git tag, 44 packages, `specify 1.3.0`, resolved to commit 34a0d388 |
| (b) What init writes | Non-interactive init **refuses without `--tools`**; with `--tools cursor` it wrote 15 files: 6 command files and 6 skill files under `.cursor/`, `openspec/config.yaml`, two `.gitkeep` | Init in a non-empty directory **asks "Do you want to continue? [y/N]", is cancelled when no terminal answers, and still exits 0** (nothing written). The agent then ran `specify init --here --force --non-interactive --integration cursor-agent` itself: about 30 files, among them 9 skills under `.cursor/skills/`, `.specify/` templates, PowerShell scripts, a workflow registry and an unfilled `constitution.md` |
| (c) Drives the flow headless | Yes: the agent followed `.cursor/skills/openspec-propose/SKILL.md` and ran the `openspec` CLI (about 12 commands) | Yes: it followed the specify, plan and tasks skills and ran their PowerShell scripts |
| (d) Writes, and does the stop hold | 4 files under `openspec/changes/add-slugify/` (`proposal.md`, a spec, `tasks.md`, `.openspec.yaml`); it **skipped `design.md`** as the tool's instructions allow; no code file written; stop held | 8 planning files under `specs/001-add-title-slug/` (spec, plan, research, data model, contract, quickstart, tasks, a checklist) plus the scaffold; no code file written; `/speckit-implement` and `/speckit-converge` not run; stop held |
| (e) Telemetry | Setting applied (`OPENSPEC_TELEMETRY=0`, `DO_NOT_TRACK=1`); effect not observed | `DO_NOT_TRACK=1`; the README states nothing; effect not observed |
| (f) Time | agent 181 s, one call | agent 405 s, one call |

Facts for stage 2 if it happens (each from a record):
- **Both tools write agent instruction files into the working directory** (`.cursor/commands`, `.cursor/skills`): 12 for OpenSpec, 9 for Spec Kit. Under AIDF's steering-file rule these are first-rank paths; in an arm they would sit in the checkout the agent works in.
- **Spec Kit's scripts are executable steps** (PowerShell run by the agent). They can change state a file snapshot does not see: its feature script creates git branches in a git checkout. The probe workspace was not a git repository, so no branch was created and none was observed. A mutation log for Spec Kit has to log git state as well as files.
- **The stop held in both runs because the prompt said so.** Both tools end their flow with an invitation to apply ("run `/opsx-apply`").
- **Exit codes are unreliable as an outcome:** Spec Kit's init exits 0 when cancelled. A harness must check what was written.
- The agent time of one planning pass for a one-function change was 181 s and 405 s, before any contract, approval, implementation or review.

## The reading test, round 1 (2026-11-05, one reader, one change, one run per arm)

The Change Owner read three sets in the order fixed by `reading-test/ORDER.md` and filled the form, kept byte for byte as `verification/spec-tool-bakeoff/reading-test/form-filled-by-change-owner.md`. Mapping of the sets (unblinded after the form was returned): **Set-1 OpenSpec** (5 files, 2,647 words, agent 418 s), **Set-2 Spec Kit** (8 files, 7,784 words, agent 731 s), **Set-3 AIDF-native** (1 file, 1,539 words, agent 266 s). All with `grok-4.7-high` on `cursor-agent`; none wrote code.

| | Set-1 OpenSpec | Set-2 Spec Kit | Set-3 AIDF-native |
|---|---|---|---|
| Minutes to decide | 5 | 15 | 3 |
| Decision | approve | approve | reject |
| Could tell what changes, what is tested, what is out of scope | yes | partly | no |
| Noticed that a no-parameter caller stops getting all 250 items | yes | no | not sure |
| His words | (no questions) "did not know where to start. What document do I open first?" | "too complex to read to get to the issue and resolution"; skipped the data model; same "where to start" | "The problem isn't initially clear. I had to infer what we are fixing"; "Needs clarity" |

In chat the Change Owner said that Set-1 is the one he would most likely approve consistently, and, after the unblinding, that he "did appreciate the single file format from AIDF". Not on the form: which set he would least want, and the sentence of why (the Implementer read "least" as Set-3 and asked him to say if that is wrong).

Reading of the result (the Implementer's, not a finding): the human-minutes mechanism the bake-off was built to find shows up, but as a presentation effect (a clear opening: the problem, what changes, a BREAKING note for existing callers), not as something that needs a third-party tool. The AIDF contract had the content (it states the no-parameter change in its first criterion) and failed on where it puts it; none of the three packs says where to start. Caveats: one reader; OpenSpec was read first and the AIDF contract last (fatigue could have hurt it, learning should have helped it); the AIDF contract is one run of one agent following the template.

## Decision after the reading test (2026-11-05): option E

The Implementer recommended a cheap re-test instead of stage 2: write a short "read first" opening for the AIDF-native contract (the problem, what changes with any behaviour change for existing callers named, scope, what is tested), run the AIDF-native arm again on the same change with that opening, and have the Change Owner read the new contract blind. The Change Owner answered "Lets follow your suggestions". The opening is tried as an extra instruction in the probe's prompt only; `templates/task-contract.md` is not touched by this contract, and a change to the template would be its own Task Contract after the result. If the revised contract reads as well as OpenSpec's did, the tool integration stops with that evidence; if OpenSpec still wins clearly, stage 2 has a reason.

## The reading test, round 2 (2026-11-05, same reader, same change)

The form is kept byte for byte as `verification/spec-tool-bakeoff/reading-test/form-round2-filled-by-change-owner.md`. Mapping of the sets (unblinded after the form was returned, `reading-test/ORDER-round2.md`): **Set-1 = round 3, the structure the Change Owner asked for** (Read this first, Problem, Why it matters, The change, Technical details, What you need to decide, then the template; 3,207 words, agent 444 s); **Set-2 = round 2, the Implementer's short opening** (a 12-line "Read this first" with five items, then the template; 1,341 words, agent 307 s). For comparison, the round 1 AIDF-native contract was 1,539 words and 266 s, and the OpenSpec set 2,647 words and 418 s. All `grok-4.7-high` on `cursor-agent`.

| | Set-1 (his structure) | Set-2 (short opening) |
|---|---|---|
| Minutes to decide | 4 | 3 |
| Decision | approve | approve |
| Could tell what changes, what is tested, what is out of scope | yes | partly |
| Knew where to start | yes | yes |
| Noticed the no-parameter caller no longer gets all 250 items | yes | yes |
| Questions or changes | none | "additional clarity on the problem" |
| Compared with the round 1 OpenSpec set (5 minutes, approved) | approve more readily | approve less readily |

His words: "I would want Set-1 every time and would use this for everyday use. It is clearer and easier to read and make a decision on." (He chose Set-1 both as the better of the two and as his everyday pick among all five sets.)

Result, as the Implementer reads it (not a measurement: one reader, one change, one run per variant, the order of reading Set-1 first): with a clear structured opening the AIDF-native contract was approved in 3 to 4 minutes, against the 3-minute rejection of the original (Set-3 of round 1) and the 5-minute approval of OpenSpec. The structure the Change Owner specified beat both the Implementer's shorter opening and the OpenSpec set on his own account. Nothing in this result needs a third-party tool. The cost of the better structure was longer files and more agent time (444 s against 266 s for the original on this change, one run each).

## Implementation checks before review (2026-11-05)

- `python -m unittest discover -s verification/tests`: 731 tests, OK (20 skipped) on Windows with Python 3.14; the two new modules (45 tests) OK with none skipped on Linux under WSL with Python 3.14.6, also with SIGINT ignored.
- Mutation run: 36 mutations of the snapshot tool (12) and the probe (24), each killed by a named test under WSL; two needed a second pass (see e3 of the pack): the first link-following mutation was equivalent (the code tests for a link before it descends) and was replaced by one that also removes that test; the forward-slash redaction form is killed on Windows only.
- ruff, `mypy --strict` on the two modules, the export scan and `pack_facts` on the pack: clean.
- First preflight `--ci-like` at `ceed219`: FAILED on the secrets check: the made-up values in `verification/tests/test_spec_tool_probe.py` (a token-shaped string and a proxy URI with credentials) were read as real. Fixed in `f9d8599` by building the values from parts. Second preflight `--ci-like` at `f9d8599`: ALL OK (the pack-wording notes are advisory).
- Not run: the attestation lookup is offline-equivalent here (no remote needed for `--ci-like`); the review rounds are not started (they are run by the Change Owner or on his explicit say).

## First start of Verifier round 1 (invalid run, nothing committed)

On `ae82c8f` the tool started the real `cursor-agent` on `grok-4.7-high` (2026-11-05, 19:26 to 20:02 UTC, preflight exit 0, reviewer exit 0). The reviewer's answer is a full report ending `Outcome: BLOCKED`. The tool refused to commit it: "the run is invalid, nothing committed: the repository the tool ran in changed (HEAD, a ref or a tracked change)". The cause is the Implementer's: while the reviewer ran, the Implementer committed on another branch of the same repository (the draft and then the implementation of the template contract, `codex/task-contract-opening`, a worktree of the same repository), which moves a ref. The tool was right to refuse. The answer is kept as `answer.bin` in the output directory and is not committed or part of the record except through this section. The Implementer read it for its findings, as for the earlier invalid starts of other changes; the round is not a round of the budget. **Rule from now on: no git write of any kind (commit, branch, worktree) in this repository, from any worktree, while a review run is going.**

| Finding of the saved answer | Disposition | What was done |
|---|---|---|
| V1 (rank 2, high): the outcome paragraph added to the proposal is outside the closed list of criterion 9, and the proposal still says nothing was run and headless behaviour is unknown | FIXED | The Change Owner had accepted the step ("I accept your recommendations", answering the plan whose step 1 was to update the proposal to say why the bake-off stopped). Criterion 9 (Markdown and JSON) now names the outcome paragraph and the correction of the stale sentences, with the acceptance recorded in the Status. The status sentence and the "Not known" bullet of the proposal are corrected |
| V2 (rank 2, medium; record text, exception: contradicts the code): e6 says the probe writes only a redacted record into the repository, but `--collect` also writes redacted artifacts, with no check that the directory is outside the repository | FIXED | e6 and e5 now say it; the reading-test artifacts in the repository were collected that way. No code change: committing them is the purpose of the option |
| V3 (rank 1, medium; record text): narrowing the stop condition so that a failed uv bootstrap continues leaves all 27 probe tests green, against the pack's counterfactual sentence | FIXED | `test_a_failed_uv_bootstrap_stops_the_probe` added (28 tests); the mutation is killed (the 37th mutation). The size clause of the snapshot comparison also survives its removal and is recorded in the pack as an equivalent mutation (a change of size is a change of digest) |
| V4 (rank 2, medium): the stage 0 mapping table covers 14 rows, not every field of the template and the JSON | FIXED | Rows 15 to 18 added (New rule or checker; the status block and the JSON `approved_by` and `approved_date`; `change_id`; `schema_version`). The count is now 18 fields: supplied 2, partly 4, AIDF-only 12, for each tool; the stop rule's limb 2 is still met. The pack, the stage 0 text and the verdict table are updated. The figure "9 of 14" in the gate record above is the figure of the first table and stays as written |
| V5 (rank 1, informational; counts) | CORRECTED | Whitespace-separated word counts: round 2 contract 1,357 words and round 3 contract 3,221 (the dispositions above say 1,341 and 3,207, which were `wc -w` counts); round 1 arms 2,647, 7,784 and 1,539 are the same by both methods. The OpenSpec install step took 4.6 s in the record (the table says 4.5). Neither changes a conclusion |

The reviewer also checked and found without a finding: 731 tests OK, ruff, mypy, the export scan and the offline preflight; the probe and snapshot mutations (all killed on this Windows account except the three link tests, which skip here and run under WSL); no certificate, live credential or weak digest; the committed records name no path of this machine; the dispositions match the records except the counts above; and the Implementer's chat-quoted words cannot be checked by it.

The change is now at 732 tests (28 probe tests). The next start of round 1 runs on the fixed head.

## Verifier round 1 (grok-4.7-high, head 5b156be, report commit a8dee44): BLOCKED

The second start of round 1 was valid (preflight exit 0, reviewer exit 0; the report is committed verbatim by the tool). It found AC1 to AC4 and AC6 to AC13 met and AC5 not met, confirmed the fixes V1 to V5, and raised one blocking finding, the first mutation-based find in the snapshot tool that this account could reproduce (the symbolic-link tests skip here).

| Finding | Disposition | What was done |
|---|---|---|
| B1 (rank 1, medium): a Windows directory junction in the recorded tree is followed and the outside files are recorded as workspace files; `Path.is_symlink` is false for a junction, and the link tests skip on this account | FIXED | `_is_link` treats `is_junction` like `is_symlink`; `test_a_directory_junction_is_recorded_and_not_followed` (runs on Windows, builds the junction with `mklink /J`) fails on the old code |
| A1 (rank 1, low): `write_record` accepts an output path that is a hard link to a file in the recorded tree | FIXED | refuses a file with more than one link; `test_an_output_path_that_is_a_hard_link_is_refused` |
| A2 (rank 1, low): only `.py` counts as code in the stop summary, so a `.js` or `.ps1` write reads "none" | FIXED | a finite suffix list outside the tools' scaffold directories (`.specify/`, `.cursor/`, `openspec/`, `aidf/`); a code file with another suffix still passes, which e5 now states. The two committed probe records were made before this and are not regenerated: their `writes` lists show the files |
| A3 (rank 1, low): an exact artifact root (`task-contract.md`) was matched by prefix, so `task-contract.md.evil` was collected | FIXED | `_under_root`: a root ending in `/` is a directory, any other root an exact name; `test_a_file_named_like_an_exact_root_but_longer_is_not_collected` |
| A4 (rank 4, informational): the Spec Kit cell for `change_id` implies a path the README does not state | FIXED | the cell says the directory name was observed at stage 1 and is not stated by the README; the count stays 12 of 18 |

Counts noted by the reviewer, advisory under `core/05-review.md` section 4 (no exception): the round 2 short opening's "Read this first" section was a heading plus seven lines (its limit was 12), not a 12-line section as the round 2 text above can be read.

The change is now at 736 tests on Windows (20 skipped; 50 in the two modules, with 3 skipped link tests that run under WSL), 42 mutations. Round 2 of the budget is the confirmation round on the delta from `5b156be`, which includes code and tests.

## Verifier round 2 (grok-4.7-high, head 7c74ecd, previous head 5b156be, report commit e78c2bd): BLOCKED

Valid run (preflight exit 0, reviewer exit 0). B1, A1 to A4 were confirmed fixed by mutation on a scratch copy; 736 tests, ruff, mypy, the export scan and the offline preflight passed. The report ends with a stray sentence after the Outcome line (the reviewer printed its closing remark after it); it is committed verbatim, and its last line is the Outcome line.

| Finding | Disposition | What was done |
|---|---|---|
| B2 (rank 1, medium): after the junction fix a junction under an artifact root is an "added" path, `collect_artifacts` reads it as text and raises `PermissionError`; no probe record is written | FIXED | `collect_artifacts` skips a link (symbolic or junction) and anything that is not a regular file; `test_a_junction_or_a_directory_under_an_artifact_root_is_skipped_not_read` and `test_a_symbolic_link_to_a_file_outside_is_skipped_not_read`. The link clause is redundant for a junction (a directory is skipped anyway): that mutation survives on Windows and is killed under WSL by the symbolic-link test (e3 says so) |
| A5 (rank 1, low): `write_probe_record` accepts a record path that is a hard link to another file | FIXED | refuses a file with more than one link; `test_a_record_path_that_is_a_hard_link_is_refused` |

The reviewer also reported, without a finding, e5 lacking the junction-under-an-artifact-root shape; e5 now states the --collect skip. Two whole-module survivors it noted (the dangling-link branch, the Spec Kit init flags) are not behaviour the contract requires and are left as they are.

**Round 3 approved by the Change Owner (2026-11-05, "round 3 is approved")**, beyond the budget of two, as a narrow confirmation round on the delta from `7c74ecd` (the fix of B2 and A5). The change is now at 739 tests on Windows (21 skipped), 53 in the two modules (WSL: OK, skipped=1; SIGINT ignored: OK), 45 mutations.

## Verifier round 3 (grok-4.7-high, head 560055d, previous head 7c74ecd, report commit 45c9965): PASS

Valid run (preflight exit 0, reviewer exit 0), a narrow confirmation round on the delta from `7c74ecd`. B2 and A5 were confirmed fixed by running the code and by mutation (removing both skip clauses, or only the directory clause, or the link-count check, or changing its comparison, each made the named test fail); the reviewer found no finding. It noted, as not new defects, that the stop summary still lists a skipped junction named like a code file (e5 defines that summary as a suffix rule) and that a junction placed at the record filename fails closed with `PermissionError`. It could not check the stage 0 document against the READMEs and did not re-read the parts the delta does not touch; round 2 covered them.
