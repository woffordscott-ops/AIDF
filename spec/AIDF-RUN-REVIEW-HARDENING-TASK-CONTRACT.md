---
owner: framework-maintainer
load_when: deciding or implementing the hardening of verification/run_review.py (steering files, reviewer caches, the Outcome line)
max_length: 1 screen
last_verified: 2026-11-04
---

# Task Contract: run_review.py Hardening (refuse steering files, reviewer caches, Outcome line)

`core/01-lifecycle.md` §4. Class T2 (see Classification); Approved status required from a human under Architect authority before implementation begins. **Status: Approved by the Change Owner on 2026-11-04 (see Status).** It builds on `run-review-followups`, merged to main as `9dfe5d8`.

## Why (the evidence)

1. **The tool notes agent steering files in the reviewed head and starts the reviewer anyway.** The reviewer CLI runs with `--trust` in a clone of the head. A head that holds `AGENTS.md`, `CLAUDE.md`, a `.cursor`, `.agents`, `.claude`, `.codex` or `.grok` directory, an MCP configuration, a symbolic link or a name with a control character can steer the reviewer, so the review is no longer of the change alone. The tool prints a NOTE and logs the list; it does not stop. The Change Owner listed "refuse instead of note" as open on 2026-11-03. The head of this repository holds none of these (checked on `9dfe5d8`), so refusing costs the usual case nothing.
2. **Every reviewer that runs the checks meets the same refusal.** In the first real start of `run-review-followups` the reviewer ran `mypy --strict` and `ruff` in its checkout and left `.mypy_cache/` and `.ruff_cache/`; the tool correctly refused to commit ("the run is invalid, nothing committed") after 29 minutes of reviewer time. The brief did not say where the caches should go. The tool already sets `PYTHONDONTWRITEBYTECODE` for the reviewer and can set the others.
3. **A report can carry an `Outcome:` line that is not its last line.** In round 3 of `review-budget-preauthorisation` the reviewer's answer had one in the middle, followed by unrelated text; the strict check reads the last non-empty line only, so the file was committed as written. On 2026-11-04 the Change Owner chose not to include a check for it in `run-review-followups` (Decision 2 there); this contract puts it to him again as a decision of its own.

## Part A: Minimal

- **Intended outcome:** A review cannot start by accident on a head that can steer the reviewer, the common reviewer tools write their caches outside the checkout, and a report with a second Outcome line is not committed as a valid one. Nothing else the tool checks or commits is weakened.
- **Acceptance criteria:**
  1. **Refuse steering files.** Unless the human passes `--allow-steering-files`, the tool refuses to start the reviewer when the head holds any first-rank steering path (`steering_summary`'s first list: the locations the installed CLI reads, symbolic links, names with a control character). The refusal names the first 20 paths, the count and the flag. It happens before the reviewer is started; the log holds the paths and `steering_files_allowed: false`.
  2. **The override is explicit and recorded.** With `--allow-steering-files` the tool prints the same NOTE as today, logs `steering_files_allowed: true` and the paths, and starts the reviewer. The other (second-rank) matches stay a NOTE and never refuse.
  3. **Reviewer caches go outside the checkout.** The reviewer's environment gains `RUFF_CACHE_DIR`, `MYPY_CACHE_DIR`, `PYTHONPYCACHEPREFIX` and `PYTEST_ADDOPTS=-p no:cacheprovider`, pointing into a directory the tool creates under `--out` (not under the clone). The names are logged. The clone-unchanged check is not relaxed: any other file the reviewer leaves in the clone still makes the run invalid.
  4. **A second Outcome line refuses the commit.** If any line of the answer other than the last non-empty line is exactly one of the three Outcome lines, the tool does not commit the report. It saves the answer in `--out` as it does for an answer with no valid last line, and the message names the line number. An indented, quoted or embedded one is not exactly an Outcome line and is not refused.
  5. **Tests.** Each criterion has a test that fails on the current `run_review.py`; the refusal and the override are tested through the tool's fixture runs; the cache variables in `reviewer_environment`; a mutation run covers the refusal condition (first-rank only, not second-rank), the flag, each cache variable and the Outcome line check. The whole suite passes on Windows, on Linux under WSL, and with SIGINT ignored; the preflight (`--ci-like`), ruff and `mypy --strict` pass.
  6. **Usage note and template.** The `--help` note and the template paragraph from `run-review-followups` gain the new flag, the cache variables and the second-Outcome-line rule, with presence tests.
  7. **Scope.** No change to the contract, evidence, brief and head checks, the preflight, the clone, the environment allowlist (the new names are fixed variables, not passed-through ones), the Windows job object, the watchdog, the commit, `core/05-review.md`, `verification/aidf_check.py`.
  8. **Outcome records** (core/05-review.md section 6): the review report patterns are `verification/run-review-hardening-verifier-report*.md`; the dispositions file is `verification/run-review-hardening-verifier-dispositions.md`. This criterion only declares the outcome-record paths.
  9. **Acknowledgement of Item C.** The Change Owner acknowledged on 2026-11-04 ("yes, acknowledged for Item C") the differences between the JSON and the approved Markdown contract of `review-run-review` in AC1, AC3, AC5, AC8 and AC10. This change appends that record to `verification/review-run-review-verifier-dispositions.md` (append only; no existing line changes), which is why that file is in the declared scope.

  Spec Confidence: Clear at intake for criteria 3, 4, 6; Partial for 1 and 2 until the Change Owner answered Decisions 1 and 2 (which paths refuse, and the flag name); both were answered on 2026-11-04.

- **Declared scope:** `verification/run_review.py`, `verification/tests/test_run_review.py`, `templates/review-brief.md`, `CHANGELOG.md`, `verification/public-export-manifest.json` and `verification/tests/test_export_public_tree.py` (the review reports name local paths), `verification/review-run-review-verifier-dispositions.md` (criterion 9, append only), this contract, `verification/run-review-hardening-task-contract.json`, `verification/run-review-hardening-evidence-pack.json`, `verification/run-review-hardening-verifier-dispositions.md`, and the reports `verification/run-review-hardening-verifier-report*.md`. **Excluded:** everything named in criterion 7.

## Part B: Plan

- **Approach:** The refusal sits where the NOTE is printed today, after the clone is made and before the brief and the reviewer; the override is an argparse flag. The cache directory is created under `--out` next to the brief, and `reviewer_environment` takes its path as a new parameter. The Outcome check is a second pass in `outcome_line` over the lines before the last.
- **Invariants touched:** the refusal order (nothing is committed or started after a refusal), the strict Outcome check, the reviewer's environment, the log of the run.
- **Evidence strategy:** reversion tests, mutation of each condition, a real start of the tool on a fixture head with a steering file (refused, then allowed), and the existing suite on the three environments.
- **Review budget (this change):** one preflight run and two Verifier rounds; no security-focused layer unless Decision 3 adds it. A third round needs the Change Owner's recorded reason and a rank-1 finding in code, tests or security posture. Accepted limits stated before review: the list of steering paths is the existing finite list (names an unknown CLI reads are not in it); `--allow-steering-files` is a human override and the tool cannot tell a legitimate use; the Outcome check is on exact lines, so a reviewer who writes the word differently is not caught.
- **Protected files touched:** none.
- **Recovery / reversal approach:** `git revert`; no record depends on the flag, the variables or the check.

## Classification

Proposed **T2**: it edits a tool and its tests with no trip-wire. It makes the tool stricter and adds one write location for the reviewer (a directory under `--out`), which is why Decision 3 asks about the security layer.

## Decisions for the Change Owner

1. **Which paths refuse?** (a) Every first-rank path, symbolic links included [recommended: a link can make any location resolve into a steering directory, and the flag is one word]; or (b) the CLI locations and control-character names only, with links remaining a NOTE.
2. **The flag name:** `--allow-steering-files` [recommended], or another name.
3. **Review layers:** Verifier rounds only [recommended: the change only makes the tool stricter and the new directory is under `--out`, where the reviewer can already write], or add the security-focused layer as `review-run-review` had.
4. **Include criterion 4 (the second Outcome line)?** The Change Owner declined it on 2026-11-04 for `run-review-followups`. Recommended now: include it, because a refused answer is kept in `--out` and costs one rerun, whereas an unnoticed second Outcome line is committed. If not included, say so and criteria 4, 5 and 6 lose that part.

## Status

- **State:** Approved
- **Established by** (author): Claude Sonnet 5.5 (Anthropic), under Implementer role, 2026-11-04
- **Approved by** (human, T2/T3 only — role: Architect): Scott Wofford (Change Owner and Architect), 2026-11-04, by his message "approved as drafted. bake-off design document can be started in parallel with phase 1 if it does not interferre", given in answer to the four decisions above, each with the recommendation as drafted: (1) every first-rank path refuses, symbolic links included; (2) the flag is `--allow-steering-files`; (3) Verifier rounds only; (4) criterion 4 (the second Outcome line) is included. The Implementer read the same message as the go-ahead to start the bake-off design document in parallel, in a separate worktree that shares no file with this change.
- **Date:** 2026-11-04
- **Class:** T2
- **Spec Confidence at intake:** Clear for criteria 3, 4, 6; Partial for 1 and 2
- **Spec Confidence now:** Clear. Decisions 1 and 2 were answered as drafted.
