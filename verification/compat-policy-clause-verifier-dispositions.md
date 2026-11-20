# Dispositions: compat-policy-clause

Append-only record of the Implementer's dispositions of Verifier findings and of the implementation. Task Contract: `spec/AIDF-COMPAT-POLICY-CLAUSE-TASK-CONTRACT.md` (T2, approved by the Change Owner on 2026-11-08).

## Implementation record

- Base `995b76b` (main after MR !75). Implementation commit `8b2955f`; contract AC4 amended at `c542413`.
- The change: one phrase of `spec/PHASE6-COMPATIBILITY-POLICY.md` line 37 now reads "the product contract of any project that consumes the framework"; the policy's entry is removed from the manifest's `exclude_files`; the export test's pin and a new test follow; CHANGELOG entry classified `compatible`.
- Dry run at `8b2955f`: `python verification/export_public_tree.py --out <directory> --run-tests` exited 0: 327 files exported (324 of the base, the policy, and this change's contract Markdown and JSON), compile of 63 Python files PASS, exported suite 388 tests OK (skipped=22) PASS, scan PASS, byte identity PASS. Private suite: 782 tests, OK (skipped=21).
- Four mutations of the pins were killed (name restored, name restored in lower case, policy excluded again, generic wording dropped).
- Contract note: the approved AC4 said the exported tree would have one more file than the base (325). The dry run showed 327 because the contract's own Markdown and JSON are published. AC4 now says that the tree holds the policy and, besides the base tree's files, only this change's own records that carry no scan pattern, and that the file and suite counts are recorded. This amends an approved criterion for a count the Implementer got wrong; it is disclosed to the Change Owner with the review request.

## Verifier round 1 (reviewed head `08c51a2`, report `verification/compat-policy-clause-verifier-report.md`, Outcome: PASS)

No finding. The Verifier confirmed AC1 to AC7: line 37 is the only changed line of the policy and the new phrase keeps the sentence's meaning; 14 mutations were killed and the survivors are the shapes the pack already lists; the exported tree is 329 files at the reviewed head (the base's 324, the policy, and this change's contract, JSON, pack and dispositions), the amended AC4 is true for it, the exported suite is 388 tests OK, the private suite 782 OK. Round 2 is not needed and is not run. The report adds one published file; it carries no scan pattern.
