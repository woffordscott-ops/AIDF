The shell worked. Python 3.14.7 and git 2.55.0.windows.3 both ran. The preflight’s pinned git version was not what this shell reported, and git itself was usable. Caches and `PYTHONDONTWRITEBYTECODE` were pointed at `<scratch>` before the first tool. `GIT_CONFIG_GLOBAL` was a file in `<scratch>`. At the end, `git status --ignored --short` in `<checkout>` was empty. No process was left running.

Independent Verifier, round 2 of 2. Fresh session; I did not write this change. Model: Grok 4.7. Reviewed head `80c9bca288554ca8bd48c1d7249378ca8969b7e9`, previous head `b0a911a673ee1bff1ae2b11e9f93bd79826d7ab3`, base `2d44ecb9b37281795f5df958857af55091a6b685`. No merge-request id was in the inputs. Started 2026-11-09T19:25:00Z, completed 2026-11-09T20:06:00Z. Inputs: the task contract (Markdown and JSON), the evidence pack, the dispositions, the round 1 report, and the delta `b0a911a673ee1bff1ae2b11e9f93bd79826d7ab3..HEAD`. One blocking finding. One non-blocking finding. This round raises one blocking finding and it is not yet adjudicated, so blocking precision is unknown.

F1 is fixed for the spellings that round 1 wrote inside the input folder. `check_output` no longer treats a `ValueError` from `os.path.commonpath` as “not inside”. `plain_path` removes the extended-length prefix of a drive path, refuses another prefixed form, and normalises case, and the drive test is outside the comparison. A new file inside the input folder, and the existing planning file with `--force`, are refused for a normal path, the extended-length prefix with backslashes, the slash spelling of that prefix, the device prefix with backslashes and with slashes, a different case, forward slashes, a short (8.3) name, a trailing dot or space on the file or on a directory component, a relative path while the current directory is the input folder, a substituted drive aimed at the input folder, and a junction whose target is inside the input folder. Each of those was tried with and without `--force`. The refusal text was the inside-folder refusal, and the input folder’s files were unchanged.

## B1 — A stream on the input directory is written

- File: `verification/spec_mapper.py:455` (the write is `verification/spec_mapper.py:474`)
- Severity: Medium
- Evidence rank: 1
- Affects AC5, the inside-folder refusal

`check_output` decides “inside” by comparing the plain path of the input folder with the plain path of the output’s parent plus the output’s final component. A path whose final component is the input directory’s name, a colon, and a stream name has the parent of the input folder as its directory. Those two plain paths do not share the input folder as their common path, so the check allows the write. `open` then stores the draft in that stream. The planning file’s bytes stay as they were, and a directory listing does not grow a new name, so a later rule does not quote the stream. The input folder still holds the draft.

Reproduced, with and without the extended-length prefix on that same directory path:

- The first call exits as a successful write. The stream’s bytes begin with the draft heading. The planning file is unchanged. The directory listing is unchanged.
- A second call without `--force` is refused because that stream exists.
- A call with `--force` after the stream exists writes again.
- The same shape on the planning file itself (`plan.md` plus a stream, `plan.md::$DATA`, and the short name of that file plus a stream) is refused as inside.

Failure scenario: a caller passes `--out` as the input directory’s path plus a colon and a stream name, with or without the extended-length prefix. The containment check allows it. The tool writes the draft onto the input directory and returns success. The tests never pass a stream, so they stay green. The pack’s AC5 sentence says an output inside the input folder is refused in any spelling and that nothing is written. That sentence is wider than the tests, and this spelling writes.

## A1 — `--force` through a hard link replaces the planning file

- File: `verification/spec_mapper.py:457-461` (the link test is `verification/spec_mapper.py:206-208`; the write is `verification/spec_mapper.py:474`)
- Severity: Low
- Evidence rank: 1
- Affects the output-link refusal

`is_link` is true for a symbolic link or a reparse point. A hard link is a regular file, so with `--force` the existing-file branch allows the replacement. The output path is outside the input folder, and the containment check allows it. The hard link and the planning file are the same file, so the planning file’s bytes become the draft.

Reproduced: a hard link outside the input folder, aimed at the planning file, is refused without `--force`. With `--force`, the call writes, and the planning file’s bytes then begin with the draft heading.

Failure scenario: the output path is a hard link to a planning file and the caller passes `--force`. The tool replaces that planning file. Creating the link already takes access to the file, and `--force` is specified to replace an existing regular file, so this does not block. Round 1 recorded that a hard link read as a source is a regular file. This is the output path, which that round did not try. The pack’s e5 does not list it.

## Routes tried and closed

Reads and writes for the shapes below stayed on the path the check had already classified, or the call was refused before `open`.

- Extended-length prefix, slash spelling, device prefix, case, short names, trailing dots and spaces, relative paths, a substituted drive of the input folder, and a direct junction into the input folder or into a subdirectory of it: refused, input unchanged, with and without `--force`. A sibling directory is still written.
- A junction plus `..` with no extended-length prefix, and the same shape with the device prefix or the slash spelling, writes the lexically collapsed file outside the input folder. The input folder is unchanged. The same shape with the extended-length prefix raises `OSError` (invalid argument) from `open`. Nothing is written. `main` catches `Refused` only, so that path is an uncaught error rather than exit code 2.
- An extended-length path whose lexical `..` lands inside the input folder is refused. `normpath` collapses `..` before the comparison.
- `plan.md::$DATA` and a stream on the planning file are refused as inside.
- A stream on a file outside the input folder is written as that named output. The input folder is unchanged.
- A UNC output on the loopback address, share absent, is refused in about two seconds because the folder does not exist. Nothing is written. The module does not import a socket, a subprocess, or an URL library. I did not leave that call running.
- Every `except` in `verification/spec_mapper.py` refuses (bad JSON or non-UTF-8) or turns `Refused` into exit code 2. None of them sets a safety check to the allow state. The `ValueError` handler from F1 is gone.
- The delta adds no import. There is still one text-mode write.

I did not repeat round 1’s timing probes. The delta does not change the matchers, the size caps, or the import list.

## Acceptance criteria

AC1–AC4 and AC6–AC10 are unchanged in code by this delta. The private suite, which includes those tests and the guide pins, passed at this head. Section 8 of `instantiation/spec-tools.md` still has the command and says a draft is not an approval, not a classification, and not evidence. The dispositions’ account of the guide sentences and the added scope entries matches the text I read. AC5 holds for the F1 spellings and is open for B1. AC9: the round-2 diff is the five files in the commands section. Nothing in it is under `core/`, `KERNEL.md`, `templates/`, the preflight, `verification/run_review.py`, or the export tool.

## Mutations

On a clone under `<scratch>`, `python -m unittest verification.tests.test_spec_mapper`: baseline 53 tests, OK (skipped=2). Each edit was restored. The clone matched the original again at the end.

Killed:

- Removing the extended-length strip. The spelling test fails. The question-mark test still refuses that path with “not supported”, so the draft is not written. The assertion wants the inside-folder words.
- Removing the strip and the question-mark test together. The spelling test fails with `Refused` not raised: the draft is written. The unknown-form test also fails.
- Inverting the containment comparison. Twelve failures and ten errors.
- Replacing the unknown-key refusal with `pass`. `Refused` is not raised.
- Changing the Status state from Established. Four failures.

Survived, and equivalent to the checks the pack names:

- A leading slash, a backslash, and a colon in a pattern still fail the segment class.
- An empty segment still fails the one-or-more segment pattern. `.` and `..` are in that class, so only the empty-string arm was removed.
- The byte-count check after the read still refuses an oversized file when the stat check is removed.
- `len(supplied)` equals the copied-part count. Every filled target is one of the seventeen parts.

Survived, without reopening a write inside the input folder on the paths I ran:

- Removing only the question-mark test. Prefixed paths that are not a drive letter are already refused by the drive-form test.
- Removing `normcase`. `realpath` already returns the filesystem’s casing of existing directories, so the upper-case spelling is still refused.
- Removing the drive conjunct. Same-drive paths behave as before. I had no second physical drive. A substituted drive of the input folder still resolved to the input folder and was refused.
- Restoring “`ValueError` means not inside” while `plain_path` stays. No tested path raises after that normalisation, so the handler does not run and the F1 spellings are still refused.

## Commands

- `python -m unittest discover -s verification/tests`: Ran 836 tests, OK (skipped=23).
- `python -m unittest verification.tests.test_spec_mapper` on the clone: Ran 53 tests, OK (skipped=2).
- `python -m ruff check verification --no-cache`: all checks passed.
- `python verification/pack_facts.py --evidence verification/spec-mapper-evidence-pack.json`: PASS.
- `python verification/export_public_tree.py --scan-only`: tracked 3451, excluded 3080, exported 371; no private identifier.
- Full export with `--run-tests` into an empty directory under `<scratch>`, after removing credential-like environment names (none were set): exported 371, compile of 68 Python files PASS, Ran 613 tests, OK (skipped=77), scan PASS, byte-identical PASS.

The pack’s 836, 23, 53, 2, 371, 68, 613, and 77 match this head. A `ResourceWarning` during the private suite and the exported suite said a subprocess was still running. That process was gone afterward. The suite printed a dry-run plan that names cursor-agent. I did not start cursor-agent or `verification/run_review.py`.

Credential, certificate, and crypto rules: I read the round-2 delta for hardcoded secrets, PEM certificates, certificate loads, and banned or legacy algorithms, because that delta is what this round adds to a tree that will be published. It is a path check, two tests, pack counts, and disposition text. It contains none of those, so there was nothing to rotate, reissue, or replace.

## Not read

The round-2 delta was read in full: `verification/spec_mapper.py`, `verification/tests/test_spec_mapper.py`, the pack, the dispositions, and the round 1 report. `verification/spec_mapper.py` was read in full, including every `try` and `except`. I did not re-read the fixture bodies or the four expected drafts in the diff from the base. The delta does not touch them. I did not re-read every pre-delta test in `verification/tests/test_spec_mapper.py` line by line. I read the helpers, the start of the schema tests, and the output tests, including the two new ones.

Outcome: BLOCKED
