The shell worked. Git worked (git version 2.55.0.windows.3). Python was 3.14.7. Commands ran in `<checkout>`. Scratch files went to a new directory outside it, called `<scratch>` below. `GIT_CONFIG_GLOBAL` pointed at an empty file in `<scratch>`; no global git configuration was created or edited. The system git setting that enables CRLF conversion stayed in force, because hiding it made `git status` show line-ending-only differences on files this change does not touch. Before any checker ran, ruff, mypy, and Python bytecode caches were pointed at `<scratch>`, and Python bytecode writing was disabled. Credential-like environment names were checked before the export and none were set. At the end, `git status --ignored --short` in `<checkout>` was empty.

# Verifier report, round 1 of 2

- **Change:** compat-policy-clause. No merge-request identifier was in the inputs.
- **Reviewed head:** `08c51a276d6ef8204ed3bc6482035589f471fd5b`
- **Base:** `995b76baa1b0db535380772a72413e952257c9f4`
- **Role:** independent Verifier. This session. Model Grok 4.7.
- **Started:** 2026-11-09T13:25:00Z. **Completed:** 2026-11-09T14:03:10Z.
- **Inputs:** `spec/AIDF-COMPAT-POLICY-CLAUSE-TASK-CONTRACT.md`, `verification/compat-policy-clause-task-contract.json`, `verification/compat-policy-clause-evidence-pack.json`, `verification/compat-policy-clause-verifier-dispositions.md`, `core/05-review.md`, and `git diff 995b76baa1b0db535380772a72413e952257c9f4 HEAD`. The exporter was read where the attacks needed it. The earlier export contracts were used for the stated limits of the scan and the link reader.

The diff is eight paths: `CHANGELOG.md`, `spec/AIDF-COMPAT-POLICY-CLAUSE-TASK-CONTRACT.md`, `spec/PHASE6-COMPATIBILITY-POLICY.md`, `verification/compat-policy-clause-evidence-pack.json`, `verification/compat-policy-clause-task-contract.json`, `verification/compat-policy-clause-verifier-dispositions.md`, `verification/public-export-manifest.json`, `verification/tests/test_export_public_tree.py`. That is the declared scope. The report glob matches no file at this head.

## AC1 — the clause

The policy diff is one line. Line 37 is the only line that differs. The file stays 82 lines. Every other line is byte-identical to the base.

The stable-surfaces paragraph is unchanged. It names the Kernel principles and trip-wires; the T0–T3, M0–M3, and E0–E7 meanings; A/N/P/X authority; Task Contract and evidence semantics; required review ordering and provenance; published JSON schemas; and protected checker command behavior. Templates may change when their normative meaning and machine-readable fields stay compatible. Product contracts are not on that list.

The following sentence says what is outside the promise. At the base, the outside list named the pilot project's product contract by using `<NAME>` immediately before the words "product contract". At the head, that phrase is "the product contract of any project that consumes the framework". The rest of the sentence is the same: vendor/model qualification, private GitLab configuration, deployment topology, and commercial offering stay outside, and the sentence still ends by saying those things are not part of the framework compatibility promise.

That keeps the meaning. The pilot project consumes the framework, so its product contract stays outside. The positive list never included product contracts, so other consumers' product contracts were already outside the promise; the new phrase states that boundary for every consuming project. The sentence does not add a stable surface and does not remove one. It does not promise that a product contract will be preserved or governed by the framework. The classification `compatible`, wording only, matches that reading.

## AC2 and AC3 — manifest, pins, mutations

Parsed against the base, the manifest differs only by the removal of `spec/PHASE6-COMPATIBILITY-POLICY.md` from `exclude_files`. No key was added. No other exclusion list changed. The exporter blob is identical to the base.

`NAME_EXCLUDE_FILES` in `verification/tests/test_export_public_tree.py` no longer lists the policy. `test_the_compatibility_policy_is_published_and_carries_no_scan_pattern` (line 821) requires the path to be absent from `exclude_files`, present in the commit, not excluded, free of every scan pattern, and to contain the generic phrase.

Mutations were committed one at a time on a scratch clone of the reviewed head. Each ran the publication test, the published-name and link test, the exact-exclusion pin, and the committed-tree scan.

| Mutation | Result |
| --- | --- |
| Clean clone | All four passed |
| Mixed-case name put back in place of the generic phrase | Killed (publication, name scan, tree scan) |
| Lower-case name put back the same way | Killed (same three) |
| Upper-case name put back the same way | Killed (same three) |
| Policy path put back into `exclude_files` only | Killed (publication and exact pin) |
| Generic phrase replaced by a neutral phrase that does not carry the name | Killed (publication test only) |
| Policy path put back into the pinned name-exclusion list only | Killed (exact pin). The publication test still passed, so the file stayed published |
| Policy path put back into both the manifest and the pin list | Killed (publication test only). The exact pin passed because both lists moved together |
| A new `exclude_prefixes` entry equal to the policy path | Killed (publication and exact pin) |
| Name split across a line break, generic phrase kept | Killed (publication, name scan, tree scan) |
| Quoted concatenation of the two halves, generic phrase kept | Killed (same three) |
| UTF-16 encoding of the name appended, generic phrase kept | Killed (same three) |
| Name written into `CHANGELOG.md` only | Killed (name scan and tree scan) |
| New tracked file under `spec/` carrying the name | Killed (name scan and tree scan) |
| Name restored in the working tree and not committed | The four tests passed, because they read the committed blob. `export_public_tree.py --scan-only` exited 1 and printed that tracked files differ from HEAD. Nothing was published |

These survived, and each is a shape the pack already states still passes:

- A hyphen between the halves, generic phrase kept. The export test already records that this form is not a scan hit.
- A code point that is not whitespace, a quote, or a plus sign, inserted between the halves. The scan's join removes whitespace, quotes, and plus signs.
- The base64 encoding of the name, generic phrase kept.
- Another sentence of the policy edited while the generic phrase stayed. `e5` says other lines are not pinned. The real diff does not use that opening: every line but line 37 is byte-identical to the base.

Leaving the policy out while the new test remains is closed. Restoring the manifest entry, the pin, or a prefix fails that test or the exact pin. An uncommitted edit is refused by the exporter, which reads HEAD and stops when the work tree is dirty. Publishing the literal name, in any of the three cases tried, through a line break, through the quoted join, or through UTF-16, is closed by the existing scan. The surviving spellings are the denylist limit the Change Owner accepted and that `e5` and `residual_risk` already state. The code joins the forms it says it joins. I do not re-raise that limit.

The comments at `verification/tests/test_export_public_tree.py:365` and `:630` still say a later change never removes an entry. This change removes one entry from the name-exclusion list. That removal is what AC3 requires, and the publication test is the control that replaces the pin for this file. The comment is not an acceptance criterion. I do not raise it.

## AC4 — the export

Included committed files, using the manifest at each commit:

| Commit | Included |
| --- | --- |
| Base | 324 |
| Implementation `8b2955f` | 327 |
| AC4 amendment `c542413` | 327 |
| Reviewed head | 329 |

The tool's own `--scan-only` agrees: implementation and amendment print `exported 327` and PASS; the reviewed head prints `tracked 3412, excluded 3083, exported 329` and PASS.

Against the base, the implementation head adds exactly the policy and the two contract files. The reviewed head adds exactly these five, and removes none:

- `spec/PHASE6-COMPATIBILITY-POLICY.md`
- `spec/AIDF-COMPAT-POLICY-CLAUSE-TASK-CONTRACT.md`
- `verification/compat-policy-clause-task-contract.json`
- `verification/compat-policy-clause-evidence-pack.json`
- `verification/compat-policy-clause-verifier-dispositions.md`

No report file is in the tree. Those four records are this change's own records. The scan reports no hit on them, on the policy, on `CHANGELOG.md`, or on `core/06-context-and-cost.md`. The included Python files are the same 63 paths at the implementation head and at the reviewed head.

The amended AC4 text matches the diff of `c542413` and matches the dispositions. The old sentence said the tree would have one more file than the base (325). The base included set is 324, and the implementation export is 327 because the two contract files are published with the policy. The amendment is what the dispositions say. At the reviewed head the count is 329, which is those 327 plus the evidence pack and the dispositions. AC4's wording, which names those records and asks for the counts to be recorded, is true for this head.

`python verification/export_public_tree.py --out <scratch> --run-tests` printed `PASS: compile of 63 Python files` and `PASS: the exported tree's own test suite (disposable copy)`. The suite printed `Ran 388 tests` and `OK (skipped=22)`. The process then raised `ValueError` because the output directory was not empty, and exited 1. I had not created that directory. It already held 330 files: the notes file plus 329 files whose bytes matched HEAD, including the policy. The notes name this commit and say 329 files were exported. I do not count that process as a clean exit. The checks it printed did pass.

A separate run without `--run-tests`, into a fresh directory, printed `exported 329`, `PASS: no private identifier in any file written, including the notes file`, and `PASS: the written tree is byte-identical to the committed files (plus the notes file)`, and exited 0. `--scan-only` on `<checkout>` printed the same 329 and PASS.

The recorded 327, 63, and 388 at the implementation head match this head's compile and suite counts, and the Python set did not change between those commits. I did not run the four-minute suite a second time at `8b2955f`.

## AC5 — links

On every published `.md`, `.txt`, and `.rst` blob at the reviewed head, the export test's link reader found no target that is missing from the included set. Angle-bracket paths with a slash, the autolink form the reader skips, also had no dangling target. `core/06-context-and-cost.md:10` cites `spec/PHASE6-COMPATIBILITY-POLICY.md` by path in backticks. That file is in the included set and in the written tree. The same path is cited from `CHANGELOG.md`, the new contract, the new dispositions, three other published contracts, and three ADRs. Each of those files is published, and the target is published.

## AC6 and AC7 — tool, scope, changelog

`git diff` of `verification/export_public_tree.py` against the base is empty, and the blob ids match. No exclusion changed except the one policy path. The eight changed paths are the scope above. Nothing under `core/`, and nothing in `KERNEL.md`, `templates/`, `verification/preflight.py`, or `verification/run_review.py`.

`CHANGELOG.md:14` records the change under Unreleased, classifies it `` `compatible` ``, and says the change is wording only, with no stable-surface change. That matches AC1.

## Pack and dispositions

`python -m unittest discover -s verification/tests` printed `Ran 782 tests` and `OK (skipped=21)` in 287.9 seconds, exit 0. `python -m ruff check verification --no-cache` printed that all checks passed, exit 0. `python verification/pack_facts.py --evidence verification/compat-policy-clause-evidence-pack.json` printed PASS, exit 0.

The pack's counts that I re-ran match: 324 at the base, 327 at the implementation head, 63 Python files, 388 tests with 22 skipped in the exported suite, 782 with 21 skipped in the private suite. The four mutations named in `e3` were killed here. `e5` is no wider than the tests: the spellings and the unpinned policy lines that it says still pass did survive, and the forms it says the tests kill were killed.

The current policy's SHA-256 does not occur in the tree. The previous bytes' SHA-256 occurs on four lines, all under `verification/phase9-completeness-review-evidence/`, which `exclude_dirs` leaves out. Those lines are a historical snapshot of an older tree. No checker in `verification/` compares the live policy to a stored digest. The pack's statement that the current file's digest is not bound, and that citations are by path, holds.

`e6` calls the policy the one private file this change rewrites, and the next sentence lists the manifest, the export test, and `CHANGELOG.md` as the other edits. Read that way, the sentence matches the diff.

## Security rules applied to the diff

The hardcoded-credential rule was applied because the tree is treated as public. The diff was read for passwords, tokens, keys, and connection strings. None were introduced. The certificate rule was applied because certificate material has to be flagged when present. The diff has no PEM block and no certificate load. The cryptographic-algorithm rule was applied because new code must not select a broken algorithm. The diff adds no cryptographic code. The added test uses a fixed path, a committed blob, and assertions. It does not take external input, build a command, or parse untrusted XML, so the Python input-validation rules do not add a control on this diff.

## Findings

None.

## Routes closed

Literal name in lower, mixed, and upper case in the policy; the same name in the changelog or in a new published file; a line break, a quoted concatenation, and UTF-16; putting the policy back into `exclude_files`, into the pin list, into both, or under a new prefix; dropping the generic phrase; publishing from a dirty work tree. The hyphen, the unjoined code point, base64, and an edit to another policy line are the stated limits, reproduced and not raised.

## Not read

The diff of all eight paths was read, including the AC4 amendment at `c542413`. Of the unchanged exporter, the exclusion rule, the scan, the dirty-tree refusal, the notes writer, and the command entry were read. The blob-size limits and the Windows reserved-name table were not re-read line by line.

## Precision

Blocking findings raised: 0. Confirmed fixed or accepted: 0. Ratio: not applicable. Disagreement: 0. Substantive revisions from findings: 0. False positives: 0. Re-review rounds: 0. Escalations: 0. Time to disposition: not applicable. The sample is this round only and is insufficient for a rate.

Outcome: PASS
