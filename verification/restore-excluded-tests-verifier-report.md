The shell worked. Python 3.14.7 and git 2.55.0.windows.3 both ran. Caches and the export went to `<scratch>`. At the end, `git status --ignored --short` in `<checkout>` was empty.

## Review identity

- Change: restore-excluded-tests. No merge-request id was in the inputs.
- Head `79a012af90aa9bbac02b409c4d73ea826bf55e4c`. Base `55f59dbf7e0717f220fccffa9eeba2b18405f8f2`.
- Role: independent Verifier, round 1 of 2. Fresh session. Model: Grok 4.7.
- Started 2026-11-09T16:30:00Z. Measurements finished 2026-11-09T16:56:29Z.
- Inputs: `spec/AIDF-RESTORE-EXCLUDED-TESTS-TASK-CONTRACT.md`, `verification/restore-excluded-tests-task-contract.json`, `verification/restore-excluded-tests-evidence-pack.json`, `verification/restore-excluded-tests-verifier-dispositions.md`, the diff of the base against the head, and `core/05-review.md`.

The diff adds no credentials, certificates, or cryptographic algorithms. Those checks were applied by reading the diff; there was nothing to flag.

## Result

The seven acceptance criteria hold on this head. One informational record finding is below. It does not meet a blocking exception.

## AC1 — guards

The three modules contain 172 tests. Fifty are guarded, and those fifty are the ones that open a file the public tree leaves out.

- `verification/tests/test_qualification_check.py`: the class guard covers all 42 tests of `QualificationCheckTest`. In the private tree every one of them opens `profiles/qualification-eval/suite-v1.json` from `setUp`. Five also open records under `profiles/unqualified/`: `test_unavailable_records_are_explicitly_unqualified` opens all three, and `test_availability_rejects_inferred_version_or_partial_success`, `test_environment_digest_and_identity_are_exactly_bound`, `test_environment_v2_separates_hosted_transport_from_candidate_network`, and `test_environment_v2_rejects_unknown_or_mislabeled_transport` open `codex-unavailable.json`. The guard waits for the suite, the published environment profile, and the three unqualified records. The reason names `profiles/qualification-eval/suite-v1.json` and `profiles/unqualified/*-unavailable.json`.
- `verification/tests/test_aidf_check.py`: these seven, and only these seven, open `verification/fixtures/positive/automation-policy-expanded-streamlined.json`, and each carries the guard whose reason names that file: `test_automation_policy_accepts_expanded_streamlined_pilot`, `test_automation_policy_rejects_unknown_fields_and_loosening_override`, `test_automation_policy_requires_project_and_digest_binding`, `test_automation_task_override_tightens_every_axis`, `test_automation_task_override_unhashable_enums_fail_safe`, `test_automation_task_override_null_on_every_axis_fails_safe`, `test_automation_policy_cli_accepts_strict_base64`.
- `verification/tests/test_reference_suite_v2.py`: only `test_the_suite_has_its_own_identity_and_the_v1_files_have_their_pinned_digests` opens `suite-v1.json` and `suite-v1.1.json`. Its reason names both.

In the exported tree the three modules exited 0: qualification 42 skipped with that reason; the aidf module 118 tests, 8 skipped (the seven guards plus the pre-existing symlink skip); the reference module 12 tests, 3 skipped (the v1 guard, plus the two pinned-revision skips). No guarded test failed to name its left-out file. No unguarded test in these modules failed for lack of a left-out file.

## AC2 and AC3 — private suite and the pin

`python -m unittest discover -s verification/tests` at the head: 783 tests, OK, skipped=21. The fifty guards ran. The new test is the one added method (`def test_` counts 788 at the base and 789 at the head). The recorded base of 782 and 21 skips was not re-executed.

`test_the_three_restored_tests_are_published_and_every_file_their_guards_wait_for_exists` passes on the clean tree. The paths the three guards wait for are exactly the seven paths that test lists. None is missing from the pin, and the pin lists no extra path.

## Mutations

Killed:

- Each of the three test files put back into `exclude_files`: `test_the_committed_exclusions_are_exactly_the_approved_set` and the new test fail. The old existence pin stays green.
- `suite-v1.json` renamed, `suite-v1.1.json` renamed, and the gate-checker fixture removed: the old existence pin and the new test both fail.
- `profiles/unqualified/claude-code-unavailable.json` removed, and `profiles/environments/phase7-local-windows.json` removed: only the new test fails.
- Class guard removed, then the module run in the exported tree: 42 errors.
- One aidf guard removed, then that module run in the exported tree: 1 error (the other six guards and the symlink skip remain).
- The reference-suite guard removed, then that module run in the exported tree: 1 error (the two revision skips remain).

Surviving, and already stated in the pack's e5: a class guard rewritten to wait for `suite-v1-typo.json` skips all 42 qualification tests in the private tree, and all three pin tests stay green. The pin lists paths by hand. It does not read the guard expressions. Every path a current guard waits for is on that list.

## AC4 and AC5 — manifest and the dry run

The manifest diff removes only `verification/tests/test_qualification_check.py`, `verification/tests/test_aidf_check.py`, and `verification/tests/test_reference_suite_v2.py` from `exclude_files`, and changes only the `exclude_files` notes sentence. JSON keys, directories, prefixes, and scan patterns are unchanged. The notes pin in `verification/tests/test_export_public_tree.py` carries the same sentence. The new test asserts the three files are published.

`python verification/export_public_tree.py --out <scratch> --run-tests` at the reviewed head exited 0: tracked 3417, excluded 3080, exported 337, compile of 66 Python files PASS, exported suite 560 tests OK (skipped=75) PASS, scan PASS, byte identity PASS. The written tree has 338 files (337 plus the notes file). No excluded path is in it. The three restored tests are present. The two v1 suites, the unqualified record, the gate-checker fixture, the agent-routing test, the export tool, and the manifest are absent. The environment profile and `suite-v2.json` are present.

560 − 388 = 172 and 75 − 22 = 53. Of those 53, 50 are the guards, 1 is the symlink skip that the restored aidf module already has in the private tree, and 2 are the revision skips that occur only in the export. 172 − 53 = 119 more tests run. That is the recorded correction of the “about 120” estimate.

The pack’s “335 files” matches the implementation commit `45efbaf`, which scan-only reports as exported 335. The reviewed head exports 337 because the evidence pack and the dispositions file were added after that commit and are published. The later dispositions sentence repeats the test counts, which match this head, and does not repeat 335.

## AC6 — scope and the tool

`git diff` of `verification/export_public_tree.py` against the base is empty. The ten changed paths are the four test files, the manifest, `CHANGELOG.md`, and this change’s four records. No core, template, preflight, or `run_review.py` change. The public-tree scan at this head printed PASS.

## Regression and the pack’s other sentences

`ruff check verification --no-cache` passed. `pack_facts.py` on the evidence pack passed. `py_compile` on the four changed test files passed. The supplied preflight was ALL OK; governance was not re-run here.

Pack sentences that state the diff or a run match what was reproduced, including e3’s nine mutations (42 errors and 1 error) and e5’s surviving wrong-path shape. The implementation-record paragraph checked below is the exception, and the later table plus e3 already state the mutation results the tests show.

## Dispositions table

Checked against this head:

- The 53 extra export skips split as 50 guards, 1 private symlink skip, and 2 export-only revision skips. Holds.
- Renaming `suite-v1.json` and removing the fixture each fail the old existence pin and the new test. Holds for those two. The new test also fails removal of the environment profile, removal of one unqualified record, and a rename of `suite-v1.1.json`.
- The class-guard reason and the changelog name `suite-v1.json` and the unqualified records. The environment profile is in the published tree. Holds.
- Five tests open the unqualified records; the guard and the pin name them. Holds.
- The pack’s “four changed test files” matches the diff. Holds.

## Finding

`verification/restore-excluded-tests-verifier-dispositions.md:10`. Severity: Informational. Evidence rank: 1. The implementation record still says the two file-removal mutations were killed by `test_every_excluded_path_exists_in_the_repository` rather than by the new test, and that the environment profile is the one file only the new test waits for. Both clauses are false on this head: the new test fails those two mutations as well, and removing `profiles/unqualified/claude-code-unavailable.json` also fails only the new test. A reader who stops at that paragraph will treat the new pin as blind to a deleted `suite-v1.json` or a deleted fixture. The table in the same file marks that paragraph superseded, and pack e3 states the results the mutations show. This is record text. It does not overstate a guarantee, omit an artifact, or cite a wrong gate hash, and the correction in the same file matches the tests, so exception 4 is not met. No code change follows from it.

## Routes closed

- An unguarded test that needs a left-out file. Two aidf tests open `.gitlab-ci.yml` when the private root is scanned; both passed in the export, where that file is absent.
- A guarded test that opens no left-out file. None of the 50.
- A current guard path absent from the pin. The sets are equal.
- A wrong-path guard. It survives, and e5 already says so.
- The class guard also waits for the published environment profile and for unqualified records that not every test opens. Every guarded qualification test still opens the left-out suite file, which is the contract’s class guard.
- A second copy of the exclusion list left the three files excluded. The pinned list and the manifest both dropped them.
- The diff of the export tool, files outside the declared scope, and a left-out file in the written tree.

The diff was read in full (10 files, 236 insertions, 9 deletions). Unchanged bodies of the three test modules were not read line by line; their opens were traced. `verification/export_public_tree.py` was read only for exclusion, scan, and the test runner; its diff is empty. The base suite and the base export were not re-executed.

Outcome: PASS_WITH_ADVISORIES
