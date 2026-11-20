The shell worked. Python 3.14.7 and git 2.55.0.windows.3 both ran; the preflight’s pinned git version was skipped, and git itself was usable. Caches and `PYTHONDONTWRITEBYTECODE` were pointed at `<scratch>` before the tools ran. `GIT_CONFIG_GLOBAL` was a file in `<scratch>`. After every command, `git status --ignored --short` in `<checkout>` was empty. No process was left running.

Independent Verifier, round 1 of 2. Fresh session; I did not write this change. Model: Grok 4.7. Reviewed head `b0a911a673ee1bff1ae2b11e9f93bd79826d7ab3`, base `2d44ecb9b37281795f5df958857af55091a6b685`. No merge-request id was in the inputs. Started 2026-11-09T18:27:00Z, completed 2026-11-09T19:02:59Z. Inputs: the task contract (Markdown and JSON), the evidence pack, the dispositions, and the full diff. One blocking finding. No non-blocking findings.

## F1 — Output path inside the input folder is written

- File: `verification/spec_mapper.py:442-445` (the write is `verification/spec_mapper.py:463`)
- Severity: High
- Evidence rank: 1
- Affects AC5 and the intended outcome that the tool refuse an output path inside the input folder

`check_output` treats a `ValueError` from `os.path.commonpath` as “not inside” and then `make_draft` opens the caller’s path. On this host, `commonpath` raises `ValueError` with “Paths don't have the same drive” when the output path uses the Win32 extended-length prefix. `os.path.abspath` rewrites the slash spelling of that prefix into the same form, so that spelling takes the same path.

Reproduced:

- A normal path of a new file inside the input folder is refused, and the folder is unchanged.
- The same new file, spelled with the extended-length prefix, is created inside the input folder. Exit is a successful write. The same happened for the slash spelling.
- An existing source file inside the input folder, spelled with that prefix, is refused without `--force` because `lexists` still sees it.
- The same existing source file with `--force` is replaced. After the call, that file’s contents were the draft, beginning with the draft heading.

Failure scenario: a caller passes `--out` as a path inside the input folder using the extended-length prefix (or the slash spelling that abspath turns into it). The containment check fails open. Without `--force` a new draft file appears among the planning files, where a later rule can quote it as a source. With `--force` an existing planning file is overwritten by the draft.

The tests kill a mutant that deletes the inside-folder refusal. They never pass a prefixed path, so they do not lock the fail-open branch.

## Routes tried and closed

Reads stay inside the named folder for the shapes below.

- A real directory junction as a matched path, as a glob segment, and as the input folder (including the extended-length spelling of that folder) is refused. `lstat` shows a reparse point, `S_ISLNK` is false, and `is_link` is true. The outside canary was not drafted.
- A path whose final component is a real subdirectory reached through a parent junction drafts that subdirectory’s own file.
- A file symbolic link and a mapping-file symbolic link could not be created on this account (privilege not held). The pack states those two tests skip. The stub still treats both a symlink mode and a reparse point as links; mutants that drop either check are killed.
- A hard link inside the folder is a regular file. `is_link` is false, and the draft quotes that entry. The same account created the link. The contract’s control is a symbolic link or a junction.
- Short names: the input folder’s short path as `--out` is refused. `listdir` returns the long name. A pattern cannot contain the short-name tilde; the segment class rejects it. Expanding the short name finds nothing.
- Case: a lower-case glob and a lower-case exact name leave `Other.MD` unread. The exact-case name is read.
- Trailing dots and spaces collapse to the existing name. An output whose name has a trailing dot or space is refused without `--force` when the collapsed file exists. A directory entry named with three dots could not be created; the joined path resolved to the input folder and was not listed, so the walk did not leave the folder.
- `relative()` accepts a dot-dot relative string when called on a sibling path. The walk did not produce such a path in these probes.
- Form feed, vertical tab, and NEL are replaced and are absent from the draft. U+2028 and U+2029 stay on a physical line that still begins with the quotation prefix. `splitlines()` then yields an unquoted status-shaped line. The pack’s e5 states that characters above U+009F are kept. That limit is accepted and is not re-raised. A bidirectional control is kept under the same sentence.
- A file name with a backtick or U+2028 is refused. A null in a name is rejected by the platform before the tool runs.
- Output through a junction whose target is the input folder is refused. A sibling directory whose name shares the input folder’s prefix is allowed. A relative `--out` while the current directory is the input folder is refused. The device-namespace prefix is normalized by `realpath` and refused.
- The module’s imports are the listed standard library. There is one text-mode write. No `eval`, `exec`, subprocess, or socket call. I did not pass a network path.
- A heading, checkbox, or fence line of about 200,000 characters matches in under 0.02 seconds. `fnmatch` patterns of 8, 12, and 16 stars return immediately. A source file of 262,144 bytes is read; one more byte is refused. A mapping past its byte cap is refused. A truncated nested JSON value within the cap is refused by the schema.
- The reserved device-name open was not completed.

## Acceptance criteria

AC1. The closed schema refuses an unknown key, a missing key, a wrong type, a bool used as a number, a duplicate key, a non-finite number, and a path with an empty segment, `..`, a leading slash, a backslash, a colon, `**`, or a character class. The refusal text names the key. The suite covers this, and the unknown-key mutant is killed.

AC2. `file`, `section`, `blocks`, and `checklist` match the fixtures I read: whole-heading match, first section only, fenced headings ignored, block prefix, nested blocks not repeated, checkbox lines only. Mutants of the first-match rule and of the fence check are killed.

AC3. For all four mappings, every quoted passage I checked is text from the named source file, under the operation that mapping names. OpenSpec copies Why, Capabilities, What Changes, Impact, the Decisions section, the whole design file, requirement blocks, and the task checkboxes. Spec Kit copies the three user-story blocks, Requirements, Success Criteria, Summary, Technical Context, and the task checkboxes. The Assumptions section and the files the Spec Kit mapping does not name (research, data model, quickstart, contract, checklist) stay out of the draft. The markdown-sections Notes section stays out. The Kiro mapping’s prefix `Requirement` also matches the level-1 heading `Requirements Document`, so the acceptance-criteria quotation is that whole file; the expected draft records that, and the text is from the source. Checklist lines are joined across gaps in the source, so they are not one contiguous substring; each line is in the source.

AC4. Status is Established, the approver value is none, the class is `TODO(AIDF)`, and copied lines sit under a source line in a quotation. The markdown-sections header is 6 of 17. Imitation lines that use ordinary newlines stay quoted. The State, class, and quotation mutants are killed.

AC5. Closed for links, size, named files, case, short names, and trailing dots, as above. Open for F1.

AC6. The reversed-listing mutant is killed. The suite’s determinism test passed.

AC7. Section 8 of `instantiation/spec-tools.md` has the exact command and says a draft is not an approval, not a classification, and not evidence. The introduction and section 7 now point at section 8. The dispositions describe those two sentence edits, the guide-test pins, and the added scope entries, including the proposal file. That account matches the diff.

AC8. Fifteen semantic mutants of `verification/spec_mapper.py` in `<scratch>` were killed by `verification.tests.test_spec_mapper` (51 tests, 2 skipped). The six pack e3 mutants survived and are equivalent: a leading slash, a backslash, and a colon also fail the segment class; an empty segment also fails the one-or-more segment pattern; the size check on the bytes read repeats the stat check for a stable file; every filled target is one of the seventeen parts, so `len(supplied)` equals the copied-part count. An earlier unknown-key edit that deleted the loop body died on `IndentationError` and is not counted. The fair mutant replaces that refusal with `pass` and is killed.

AC9. `git diff` names only the declared scope. Nothing under `core/`, `KERNEL.md`, `templates/`, the preflight, `verification/run_review.py`, or the export tool.

AC10. The contract declares `verification/spec-mapper-verifier-report*.md` and `verification/spec-mapper-verifier-dispositions.md`. This review did not write into the tree.

## Commands

- `python -m unittest discover -s verification/tests`: Ran 834 tests, OK (skipped=23).
- `python -m unittest verification.tests.test_spec_mapper` on the clone: Ran 51 tests, OK (skipped=2) on the unmutated file.
- `python -m ruff check verification --no-cache`: all checks passed.
- `python verification/pack_facts.py --evidence verification/spec-mapper-evidence-pack.json`: PASS.
- `python verification/export_public_tree.py --scan-only`: tracked 3450, excluded 3080, exported 370; no private identifier.
- Full export with `--run-tests` into an empty directory under `<scratch>`, after removing credential-like environment names (none were set): exported 370, compile of 68 Python files PASS, Ran 611 tests, OK (skipped=77), scan PASS, byte-identical PASS.

The pack’s 611, 77, 68, 834, 23, and 51 match this head. Its 368 is the figure it gives for the head before the records; the dispositions name that earlier commit. This head exports 370. I did not export that earlier commit, so I do not treat 368 as a false sentence.

The required suite’s probe log names cursor-agent. I did not start `verification/run_review.py` or an agent myself. A ResourceWarning during the exported suite said a subprocess was still running; that process was gone afterward.

Credential, certificate, and crypto rules: I read the new Python, JSON, and Markdown for hardcoded secrets, PEM certificates, certificate loads, and banned or legacy algorithms. The change is a local drafter over files the caller names. It contains none of those, so there was nothing to rotate, reissue, or replace.

The diff was read in full.

Outcome: BLOCKED
