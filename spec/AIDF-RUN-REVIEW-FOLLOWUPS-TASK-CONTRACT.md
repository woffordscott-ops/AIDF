---
owner: framework-maintainer
load_when: deciding or implementing the follow-ups to verification/run_review.py (usage note, Windows console signals)
max_length: 1 screen
last_verified: 2026-11-04
---

# Task Contract: run_review.py Follow-ups (usage note, Windows Ctrl-C and Ctrl-Break)

`core/01-lifecycle.md` §4. Class T2 (see Classification); Approved status required from a human under Architect authority before implementation begins. **Status: Approved by the Change Owner on 2026-11-04 (see Status).** It builds on `review-run-review`, merged to main as `dc606ad`.

## Why (the evidence)

1. **Four refusals in three uses of the tool were the human's first meeting with a rule nobody had told them.** On the real run of `review-run-review` the tool refused because `cursor-agent` is not on PATH on Windows (it needs `--reviewer-executable` with the launcher's full path). In `review-budget-preauthorisation` it refused to start round 3 because the report path was not named in the contract's `declared_scope`, and refused twice because `--out` was not empty (a stale output directory from the refused start). Each refusal text was correct and the fix was one line, but each cost a relay. `--help` lists the options and says none of this.
2. **A known gap on Windows is written in the pack of `review-run-review` and was not closed.** Its `residual_risk` says: on Windows, a console Ctrl-C also reaches the git programs that run inside the report window, so the tool can report REFUSED instead of INTERRUPTED, leave a stale index lock, or, rarely, report REFUSED after the branch has moved; SIGBREAK and a closing console are not held. On POSIX the same window holds SIGINT, SIGTERM, SIGHUP and SIGQUIT and the git programs do not see the signal. The Change Owner listed the fix as a follow-up on 2026-11-03.
3. **A third item was observed and is offered, not assumed.** In round 3 of `review-budget-preauthorisation` the reviewer's answer contained an `Outcome:` line in the middle, followed by unrelated text, and ended with the real last line. The strict check looks at the last line only, so it passed and the file was committed as written. See Decision 2.

## Part A: Minimal

- **Intended outcome:** A human who runs `verification/run_review.py` for the first time is told by `--help` and by the review brief template the four things that stopped the earlier runs, and on Windows a Ctrl-C or Ctrl-Break during the window in which the report moves is held and raised after it, without being delivered to the git programs that run inside it. No control on what the tool checks or commits is weakened, and nothing changes on POSIX.
- **Acceptance criteria:**
  1. **Usage note in `--help`.** `python verification/run_review.py --help` ends with a short usage note that says: (a) a reviewer CLI that is not on PATH is named with `--reviewer-executable` and its full path (on Windows `cursor-agent` is a `.cmd` launcher in the user's local application directory, and the path of the launcher is given); (b) the report path must be named by an entry of the JSON contract's `declared_scope` (a path or a pattern) before the run; (c) `--out` must be a new or empty directory and a refused start leaves its log there, so clear it before the next start; (d) the tool never pushes and commits the report alone.
  2. **The same note in the template.** `templates/review-brief.md` gains the same four points as one short paragraph where it says `run_review.py` is run by the human.
  3. **Git in the window leaves the console's Ctrl-C alone (Windows).** Every git program the tool starts between the first and the last step of the window in which the report is written (`commit_report`) is created with `CREATE_NEW_PROCESS_GROUP` and `CREATE_NO_WINDOW` on Windows, so neither a console Ctrl-C nor a console Ctrl-Break is delivered to it. On POSIX no creation flag is passed and the call is unchanged.
  4. **Ctrl-Break is held (Windows).** `signals_deferred` holds `SIGBREAK` as it holds `SIGINT` on Windows: the signal is recorded in the window and a `KeyboardInterrupt` is raised when the window ends. A closing console, logoff and shutdown are not held; the pack says so.
  5. **Evidence that a console event is not delivered.** A Windows test (or, where it cannot be made reliable, a documented one-time run recorded in the dispositions) shows a console Ctrl-C and a console Ctrl-Break reaching a child process created without the flags and not reaching one created with them, using a console that is not the test runner's. Tests also show: the flags are passed to the window's git calls and to no other git call; `SIGBREAK` is held and raised after the window; with the flags removed, the test fails.
  6. **Tests.** Presence tests for the usage note in `--help` and in the template (they show the text is written, not that it is right); the Windows tests of criteria 3 to 5, skipped with a stated reason on POSIX; a POSIX test that no creation flag is passed. The whole suite passes on Windows, on Linux under WSL, and with SIGINT ignored; the preflight (`--ci-like`), ruff and `mypy --strict` pass.
  7. **Scope.** No change to what the tool checks or commits (the contract, evidence, brief and head checks, the preflight, the strict Outcome check, the clone, the environment allowlist, the Windows job object, the watchdog), to `core/05-review.md` or any other core document, to `verification/aidf_check.py`, or to the pack, contract and dispositions of `review-run-review`.
  8. Outcome records (core/05-review.md section 6): the review report patterns are `verification/run-review-followups-verifier-report*.md`; the dispositions file is `verification/run-review-followups-verifier-dispositions.md`.

  Spec Confidence: Clear at intake for criteria 1, 2, 4 and 6; Partial for 3 and 5 (what a console delivers to a process in a new group, and whether a hidden console can be made reliable under the test runner, is settled by an experiment before the code, and the result goes in the dispositions).

- **Declared scope:** `verification/run_review.py`, `verification/tests/test_run_review.py`, `templates/review-brief.md`, `CHANGELOG.md`, `verification/public-export-manifest.json` and `verification/tests/test_export_public_tree.py` (the review reports name local paths and are excluded from the public export), this contract, `verification/run-review-followups-task-contract.json`, `verification/run-review-followups-evidence-pack.json`, `verification/run-review-followups-verifier-dispositions.md`, and the reports `verification/run-review-followups-verifier-report*.md`. **Excluded:** everything named in criterion 7.

## Part B: Plan

- **Approach:** An experiment first (a hidden or new console, a child with and without `CREATE_NEW_PROCESS_GROUP`, a Ctrl-C event), recorded in the dispositions. Then an `isolated` option on the tool's `git()` helper that adds the creation flag on Windows, used by the calls inside `commit_report`'s window; `SIGBREAK` added to the Windows branch of `signals_deferred`; the usage note as the parser's epilog and one paragraph in the template.
- **Invariants touched:** the window in which the report moves (file, index entry, branch last), the held signals, the stale-lock and REFUSED-instead-of-INTERRUPTED risks recorded in the pack of `review-run-review`.
- **Evidence strategy:** a reversion test (the new tests fail on the current `run_review.py`), the console experiment, mutation of the flag (removed from one call, added to another call), the existing signal tests on Windows and Linux and with SIGINT ignored, as `review-run-review` found CI starts jobs with SIGINT ignored.
- **Review budget (this change):** one preflight run and two Verifier rounds; no security-focused layer (see Decision 1). A third round needs the Change Owner's recorded reason and a rank-1 finding in code, tests or security posture. Accepted limits stated before review: the usage note and the template paragraph are prose with presence tests only; a console close, logoff and shutdown are not held; the stale-lock and branch-moved cases are reduced, not proved gone.
- **Protected files touched:** none.
- **Recovery / reversal approach:** `git revert`; no record depends on the new flag or text.

## Classification

Proposed **T2**: it edits a tool and its tests, with no trip-wire; the tool starts a process and writes to the repository, which is why criterion 5 asks for an experiment and not only for tests.

## Decisions for the Change Owner

1. Approve as T2 with Verifier rounds only (the change adds no trust boundary: the git calls are the tool's own, with the same arguments and environment), or add the security-focused layer as `review-run-review` had? **Answered 2026-11-04: as drafted (Verifier rounds only).**
2. Include a fourth criterion: the strict Outcome check also refuses an answer that has an `Outcome:` line anywhere but its last line? It would have refused the answer of round 3 of `review-budget-preauthorisation`, which was a valid report; the alternative is to leave the check as it is and note the residue in the dispositions, as was done. Default in this draft: not included. **Answered 2026-11-04: as drafted (not included).**
3. If a hidden console cannot be made reliable under the test runner, accept a documented one-time manual check in place of the automated test of criterion 5, run by the Change Owner or the Implementer in a real console and recorded in the dispositions? **Answered 2026-11-04: as drafted (accepted).**

## Status

- **State:** Approved
- **Established by** (author): Claude Sonnet 5.5 (Anthropic), under Implementer role, 2026-11-04
- **Approved by** (human, T2/T3 only — role: Architect): Scott Wofford (Change Owner and Architect), 2026-11-04, by his message "MR !65 merged. go ahead as drafted.", given in answer to the three decisions above (Verifier rounds only; no Outcome-line check; a manual check accepted if a hidden console is unreliable).
- **Amended by** the Change Owner on 2026-11-04, by his message "check in when round 1 finishes", given in answer to the Implementer's request for two amendments: criterion 3 names `CREATE_NEW_PROCESS_GROUP` and `CREATE_NO_WINDOW` (the experiment showed a process group alone shields from Ctrl-C only), and criterion 5 covers a console Ctrl-C and a console Ctrl-Break. The Implementer read that message as the approval; it is recorded in the dispositions.
- **Date:** 2026-11-04
- **Class:** T2
- **Spec Confidence at intake:** Clear for criteria 1, 2, 4, 6; Partial for 3 and 5
- **Spec Confidence now:** Clear. The Partial parts (what a console delivers to a process in a new group; whether a hidden console is reliable under the test runner) were settled by the console experiment before any code; see `verification/run-review-followups-verifier-dispositions.md`, "Console experiment".
