# Dispositions: restore-excluded-tests

Append-only record of the Implementer's dispositions of Verifier findings and of the implementation. Task Contract: `spec/AIDF-RESTORE-EXCLUDED-TESTS-TASK-CONTRACT.md` (T2, approved by the Change Owner on 2026-11-09).

## Implementation record

- Base `55f59db` (main after MR !76). Implementation commit `45efbaf`.
- The change: guards (`unittest.skipUnless` on the existence of the file read) on all of `test_qualification_check.py` (one class guard), seven tests of `test_aidf_check.py` and one of `test_reference_suite_v2.py`; the three files leave the manifest's `exclude_files`; the manifest's notes sentence and the export test's pinned list and notes pin follow; a new test pins that the three files are published and that every file a guard waits for exists and is tracked; CHANGELOG entry classified `compatible`.
- Dry run at `45efbaf`: `python verification/export_public_tree.py --out <directory> --run-tests` exited 0: 335 files exported, compile of 66 Python files PASS, exported suite 560 tests OK (skipped=75) PASS (base: 388 tests, skipped=22), scan PASS, byte identity PASS. Private suite: 783 tests, OK (skipped=21) (base: 782, skipped=21).
- Eight mutations killed (six on the manifest and the files the guards wait for, two with a guard removed and the module run in the exported tree). Two of the file-removal mutations were killed by an existing pin (`test_every_excluded_path_exists_in_the_repository`) rather than by the new test, because those files are also on the exclusion list; the environment profile is the one file only the new test waits for.
- A contract estimate corrected: the proposal said about 120 more tests would run in the exported suite; the exported suite has 172 more tests, of which 53 are skipped (50 guarded and 3 skips the restored modules already had), so 119 more run.

## Refused first run and corrections before round 1

The first Verifier run (head `713fdd9`) was refused by `run_review.py` because the reviewer's answer did not end with the Outcome line (it appended two sentences after `Outcome: BLOCKED`); nothing was committed, so no round is recorded for it. The refused answer is kept outside the repository. It raised five findings, each checked here before round 1 was run again on the corrected head (this is disclosed so the Change Owner can see that round 1 below reviews a head that already answers them):

| Finding of the refused run | Check | Disposition |
|---|---|---|
| The pack's and the dispositions' split of the 53 extra exported skips was wrong | the three modules skip once in the private tree (the symlink test); `test_reference_suite_v2.py` skips two more tests in the exported tree only, where the pinned revision is not a commit | FIXED in the pack (AC1): 50 guards, 1 skip that already exists in the private tree, 2 that happen only in the exported tree. The dispositions' implementation record is superseded by this row |
| The dispositions said two file-removal mutations were killed by the old pin "rather than" the new test | the mutations were re-run with all failures printed: each committed file removal fails the existing pin and the new test | FIXED in the pack (e3) and superseded here: the new test kills every committed mutation of a guarded file |
| The class guard's reason said the environment profile is not in a published copy; the changelog listed it too | the environment profile is published; the suite and the three unqualified records are not | FIXED: the reason and the CHANGELOG name `suite-v1.json` and the records `profiles/unqualified/*-unavailable.json` |
| Five guarded tests open the three unqualified records, which neither the guard nor the pin named | the records are under an excluded directory | FIXED: the class guard waits for them and the pin lists them (and a removed record is a ninth mutation, killed) |
| The pack said five changed test files | the diff has four | FIXED in the pack |

The dry run after these corrections: the same counts (exported suite 560 tests, OK, skipped=75; private suite unchanged at 783, skipped=21).

## Verifier round 1 (reviewed head `79a012a`, report `verification/restore-excluded-tests-verifier-report.md`, Outcome: PASS_WITH_ADVISORIES)

The Verifier confirmed AC1 to AC6 and every row of the corrections table above. One finding:

| Finding | Disposition | What was done |
|---|---|---|
| F1 (Informational, rank 1, record text, no blocking exception met): the implementation record's fourth bullet still says two file-removal mutations were killed by the old pin "rather than" the new test and that the environment profile is the one file only the new test waits for; both clauses are false on the reviewed head (the new test also fails those two mutations, and removing an unqualified record also fails only the new test) | ACCEPTED, recorded here, no edit | the file is append-only after review; the corrections table above and pack e3 already state the correct results. Read the implementation record's fourth bullet as superseded: every committed removal or rename of a file a guard waits for fails the new test, and the existing pin additionally fails for files that are also on the exclusion list. Round 2 is not needed and is not run. |
