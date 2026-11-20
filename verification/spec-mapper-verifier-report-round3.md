The shell worked. Python 3.14.7 and git 2.55.0.windows.3 both ran. The preflight’s pinned git version was not what this shell reported, and git itself was usable. Caches and `PYTHONDONTWRITEBYTECODE` were pointed at `<scratch>` before the first tool. `GIT_CONFIG_GLOBAL` was a file in `<scratch>`. At the end, `git status --ignored --short` in `<checkout>` was empty. No process was left running.

Independent Verifier, round 3. Fresh session; I did not write this change. Model: Grok 4.7. Reviewed head `4f005ddd7afc7a174d1026eab9584aa95bbbc753`, previous reviewed head `80c9bca288554ca8bd48c1d7249378ca8969b7e9`, change base `2d44ecb9b37281795f5df958857af55091a6b685`. The preflight’s origin base is the same commit as the reviewed head. No merge-request id was in the inputs. Started 2026-11-09T21:19:00Z, completed 2026-11-09T22:10:36Z. Inputs: the task contract (Markdown and JSON), the evidence pack, the dispositions, the round 1 and round 2 reports, and the delta `80c9bca288554ca8bd48c1d7249378ca8969b7e9..HEAD`. This round is the confirmation the Change Owner approved on 2026-11-09, outside the two-round budget. No findings. Blocking precision is not applicable.

B1 and A1 are fixed, and F1 of round 1 is still fixed. `check_output` refuses a colon that remains after the drive in the normalized output path, and it refuses an existing output whose link count is greater than one, with or without `--force`. The extended-length prefix is still stripped only for an ordinary drive path, and any other prefixed form is still refused. No exception in `verification/spec_mapper.py` turns a safety check into an allow. The `ValueError` handler from F1 is still gone.

## Routes tried and closed

Each of these was called with and without `--force`, except where a single clean call is named. The planning file’s bytes stayed as they were, and the input folder’s names stayed as they were, unless the line says a file outside was written.

Refused as inside the input folder: a normal path; the extended-length prefix with backslashes and with slashes; the device prefix with backslashes and with slashes; a different case; forward slashes; `..` collapsed into the folder; a trailing dot or space on the file or on a directory component; the extended-length form of a trailing dot; the extended-length form and the device form of the existing planning file; the short (8.3) name of the input folder and of the planning file; a relative path while the current directory is the input folder, and a relative path from the parent of that folder; a substituted drive aimed at the input folder, including the planning file and a stream on that spelling; a junction whose target is the input folder, including the extended-length spelling, the device spelling, and a trailing dot on the junction; a volume-guid path whose real path is the input folder.

Refused as a stream, with the planning file unchanged and no stream left on the folder or the file: the input folder plus a stream; the planning file plus a stream; the default data stream; the extended-length, device, and slash-extended spellings; a trailing dot on those stream spellings; a short name plus a stream or the default data stream; a relative stream and a relative default data stream; a one-dollar data suffix; an empty stream name; a stream name with a trailing space.

Refused as more than one name, planning file unchanged: a hard link to the planning file, with and without `--force`; a different case; a trailing dot, space, or run of dots; the extended-length prefix and the device prefix; the default data stream and a named stream on the link; the short name of the link; the link reached through a junction, including a trailing dot; the link reached through a substituted drive of the outside folder, including a trailing dot. Creating a file symbolic link failed on this account (privilege not held). The pack already says that test skips.

A colon followed by `..` is normalized away before the colon check. The tool then writes the collapsed file outside the input folder. A direct open of that shape does the same: the original file is unchanged and no stream is added. The check and the open agree. A hard-link path with a stream and `..` likewise writes the collapsed neighbor, and the planning file is unchanged. A junction followed by `..`, and the same shape with the device prefix, writes the collapsed file outside the input folder. The same shape with the extended-length prefix raises `OSError` from `open` and writes nothing. `main` still catches only `Refused`. That behavior is unchanged from round 2.

A sibling of the input folder is still written. A second call without `--force` is refused and leaves that file as it was. Reserved device names under the input folder, and a device name beside it, are refused. A fullwidth colon is an ordinary character: the tool writes a sibling file of that name and does not open a stream.

Every `except` in `verification/spec_mapper.py` refuses bad JSON or non-UTF-8 text, or turns `Refused` into exit code 2. The delta adds no import. There is still one text-mode write. The module does not import a socket, a subprocess, or an URL library.

## Acceptance criteria

AC5 holds for the F1 spellings, for B1, and for A1, on the routes above. AC1 to AC4 and AC6 to AC10 are unchanged in code by this delta. The private suite, which includes those tests and the guide pins, passed at this head. Section 8 of `instantiation/spec-tools.md` still has the command and says a draft is not an approval, not a classification, and not evidence. The dispositions’ account of the guide sentences and the added scope entries matches the text I read. AC9: the round-3 diff is the five files in the commands section. Nothing in it is under `core/`, `KERNEL.md`, `templates/`, the preflight, `verification/run_review.py`, or the export tool. The dispositions’ description of the two fixes matches the code and the runs above.

## Mutations

On a clone under `<scratch>`, `python -m unittest verification.tests.test_spec_mapper`: baseline 55 tests, OK (skipped=2). Each edit was restored. The clone matched the original again at the end.

Killed:

- Removing the colon check. One failure.
- Removing the link-count check. One failure.
- Raising the link-count threshold from one to two. One failure.
- Removing the extended-length strip. One failure. The question-mark guard is still there, so a prefixed path that is not a plain drive path is still refused; the spelling test wants the inside-folder words.
- Inverting the containment comparison. Thirteen failures and ten errors.
- Replacing the unknown-key refusal with `pass`. One failure.
- Changing the Status state from Established. Four failures.

Survived, and equivalent to the checks the pack names:

- A leading slash still produces an empty segment, which the segment walk refuses.
- A backslash and a colon in a pattern still fail the segment class.
- An empty segment still fails the one-or-more segment pattern. `.` and `..` stay in the explicit check.
- The byte-count check after the read still refuses an oversized file when the stat check is removed.
- `len(supplied)` equals the copied-part count. Every allowed target is one of the seventeen parts, and each target is stored once.

## Commands

- `python -m unittest discover -s verification/tests`: Ran 838 tests, OK (skipped=23).
- `python -m unittest verification.tests.test_spec_mapper` on the clone: Ran 55 tests, OK (skipped=2).
- `python -m ruff check verification --no-cache`: all checks passed.
- `python verification/pack_facts.py --evidence verification/spec-mapper-evidence-pack.json`: PASS.
- `python verification/export_public_tree.py --scan-only`: tracked 3452, excluded 3080, exported 372; no private identifier.
- Full export with `--run-tests` into an empty directory under `<scratch>`: exported 372, compile of 68 Python files PASS, Ran 615 tests, OK (skipped=77), scan PASS, byte-identical PASS. The only environment name that matched a credential-like pattern was a git configuration slot whose key is `core.quotePath`. It is not a credential, and removing it makes git exit 128, so it was left set. No password, token, or API key variable was set.

The pack’s 838, 23, 55, 2, 372, 68, 615, and 77 match this head. A `ResourceWarning` during the private suite and the exported suite said a subprocess was still running. That process was gone afterward. The suite printed a dry-run plan that names cursor-agent. I did not start cursor-agent or `verification/run_review.py`.

Credential, certificate, and crypto rules: I read the round-3 delta for hardcoded secrets, PEM certificates, certificate loads, and banned or legacy algorithms, because that delta is what this round adds to a tree that will be published. It is a path check, two tests, pack counts, the round 2 report, and disposition text. It contains none of those, so there was nothing to rotate, reissue, or replace.

## Not read

The round-3 delta was read in full: `verification/spec_mapper.py` (the four added lines, with `plain_path` and `check_output`), `verification/tests/test_spec_mapper.py` (the two new tests), the pack, the dispositions, and the round 2 report. `verification/spec_mapper.py` was read in full, including every `try` and `except`. I did not re-read the fixture bodies or the four expected drafts in the diff from the change base. The delta does not touch them. I did not re-read every pre-delta test in `verification/tests/test_spec_mapper.py` line by line. I read the helpers, the path-pattern test, and the output tests.

Outcome: PASS
