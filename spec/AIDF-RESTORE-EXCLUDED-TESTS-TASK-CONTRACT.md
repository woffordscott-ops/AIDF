---
owner: framework-maintainer
load_when: deciding or implementing the return of three test files to the public export
max_length: an approver's opening, then 1 screen
last_verified: 2026-11-09
---

# Task Contract: return three test files to the public export

`core/01-lifecycle.md` §4. Class T2 (decision 1). **Status: Approved by the Change Owner on 2026-11-09 (see Status).** Follow-up to the change that removed the pilot project's name from the public export (T3, MR !75), which left out three test files because each reads a file that is left out.

## Approver's opening

- **Read this first:** This asks you to approve a change to three test files, the export's manifest and its test, so that the first GitHub publication keeps the framework's qualification, gate-checker and reference-suite tests and skips only the tests that read a file the public copy does not hold. Your approval is on the whole contract, not on this opening alone. Nothing is pushed to GitHub by this change.
- **Problem:** The public copy's own suite runs 388 tests. `test_qualification_check.py`, `test_aidf_check.py` and `test_reference_suite_v2.py` are left out whole, although a dry run shows that only 50 of their 172 tests read a left-out file (all 42 of the first, 7 of 118 of the second, 1 of 12 of the third). A reader of the public copy loses the tests of the checks they are asked to rely on.
- **The change:** Each test that reads a left-out file gets a guard that skips it when the file is absent: the whole module of `test_qualification_check.py`, 7 tests of `test_aidf_check.py`, 1 of `test_reference_suite_v2.py`. A new test in the private tree asserts that every guarded file exists there, so a guard cannot hide a failure in the private suite. The manifest stops leaving the three files out; its notes sentence and the export test's pins follow. BREAKING: none; the private suite is unchanged (every test still runs there).
- **Technical details:** (1) `verification/tests/test_qualification_check.py`: a class guard on `profiles/qualification-eval/suite-v1.json`, `profiles/environments/phase7-local-windows.json` and the three records `profiles/unqualified/*-unavailable.json` that the tests open. (2) `verification/tests/test_aidf_check.py`: a guard on `verification/fixtures/positive/automation-policy-expanded-streamlined.json` on the seven tests that load it. (3) `verification/tests/test_reference_suite_v2.py`: a guard on `profiles/qualification-eval/suite-v1.json` and `suite-v1.1.json` on the one test that reads their digests. (4) `verification/public-export-manifest.json`: the three entries leave `exclude_files`, and the notes sentence is reworded. (5) `verification/tests/test_export_public_tree.py`: the pinned list and the notes pin follow, and a test asserts that the guarded files exist in the private tree and that the three test files are published. (6) `CHANGELOG.md`.
- **What you need to decide:** Assumptions: skipping a test whose input the public copy does not hold is acceptable, and the skip reason says why. Out of scope: the left-out files themselves (the pilot profiles, the fixture, the two v1 suites), the fourth left-out test (`test_agent_routing_check.py`, which needs the pilot's checker), the push. Class: T2 (test and manifest changes, no code). Main risk: a guard that skips in the private tree and hides a failure; the new pin test closes that.

## Part A: Minimal

- **Intended outcome:** The public copy's suite runs the tests of the qualification, gate-checker and reference-suite checks that do not need a left-out file, and skips the 50 that do, while the private suite runs all of them.

- **Acceptance criteria** (identical to `verification/restore-excluded-tests-task-contract.json`):
  1. **Guards.** The 50 tests that read a left-out file (all of `test_qualification_check.py`, the seven named tests of `test_aidf_check.py`, the named test of `test_reference_suite_v2.py`) carry a guard on the existence of the files they read, with a reason that names the file; no other test is guarded.
  2. **Private suite unchanged.** In the private tree no guarded test is skipped: the suite's skip count is the same as at the base and its test count is the base's plus the tests this change adds.
  3. **Pin.** A test in the private tree asserts that every guarded file exists and is tracked; a mutation that renames or removes a guarded file is failed by a test.
  4. **Published.** The manifest no longer excludes the three test files and is otherwise changed only in the notes sentence; the export test's pins and notes pin follow, and a test asserts the three files are published.
  5. **The export passes.** `python verification/export_public_tree.py --out <empty directory outside the repository> --run-tests` reports compile, exported suite, scan and byte identity as PASS; the exported suite's test and skip counts are recorded in the dispositions and are about 120 tests higher than the base's 388.
  6. **No other change.** `verification/export_public_tree.py` is byte-identical to the base; no core, template, preflight or `run_review.py` change; no left-out file is published.
  7. **Outcome records.** Report patterns `verification/restore-excluded-tests-verifier-report*.md`; dispositions file `verification/restore-excluded-tests-verifier-dispositions.md`.

- **Scope:** `verification/tests/test_qualification_check.py`, `verification/tests/test_aidf_check.py`, `verification/tests/test_reference_suite_v2.py`, `verification/public-export-manifest.json`, `verification/tests/test_export_public_tree.py`, `CHANGELOG.md` and this change's own records.

## Part B: Plan

- **Approach:** add the guards; remove the manifest entries and reword the notes; update the pins and add the test; run the private suite, the export dry run and the mutations; write the pack.
- **Invariants touched:** the export only excludes and never rewrites a file; the scan covers every published file; each test of a check still runs wherever its input exists.
- **Evidence strategy:** the private suite (skip count unchanged), the export dry run, the pin test with two mutations (a guarded file renamed, a guard removed so the exported suite fails), the preflight `--ci-like`.
- **Protected files touched:** to be confirmed with the preflight; expected none.
- **Recovery / reversal:** `git revert`; nothing is published by this change.
- **Review budget:** one preflight run and two Verifier rounds; no security layer. Accepted limit stated before review: a guard skips on a missing file in any tree, so a deleted input in the private tree is caught only by the pin test.

## Classification

Proposed **T2**: test and manifest changes only, nothing that decides what is published beyond three test files, and the scan still guards the published tree.

## Decisions for the Change Owner

1. **Class.** T2 with Verifier rounds [recommended]. Decided 2026-11-09: T2, two Verifier rounds.
2. **Design.** Guards with a pin test, not a rewrite of the tests. Decided 2026-11-09: approved.

## Status

- **State:** Approved
- **Established by** (author): Claude Sonnet 5.5 (Anthropic), under Implementer role, 2026-11-09
- **Approved by** (human, T2/T3 only — role: Architect): Scott Wofford (Change Owner and Architect), 2026-11-09, by his message "approved" to the proposal of class T2, two Verifier rounds and the design above.
- **Date:** 2026-11-09
- **Class:** T2
- **Spec Confidence at intake:** Clear
