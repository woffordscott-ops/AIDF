**Outcome: BLOCKED.** I found six blocking defects, five of them reproduced. The most serious is that the tool cannot commit a report for this change, or for any recent review contract.

## Review record

- **Change:** review-run-review (no merge request identifier was given)
- **Reviewed head:** `68960360fd3c568e70057d8d687b4e62d8c00085`. Base `ab2ed741e8dd535ddc5b9790e03f04150a70ea0e`; the diff is `git diff ab2ed741… HEAD` (8 files, +1070/−1).
- **Role:** independent Verifier, round 1 of 2. This is a fresh Cursor agent session (Claude Opus 5.5) with no access to the Implementer's reasoning.
- **Times (UTC):** started 2026-11-02T15:27Z, finished about 15:52Z.
- **Inputs read:** `core/05-review.md`; the Task Contract in both forms (`.md` and `.json`); the tool, its tests, the evidence pack, the CHANGELOG and template diffs. I also read the dispositions file, which so far holds only the approval and budget records.
- **Mechanical checks:**
  - `test_run_review` ran 29 tests, OK.
  - The full `unittest discover` passed (skipped=3).
  - `ruff` passed, and `mypy --strict` passed on the new file.
  - `preflight.py` reported ALL OK at this head, with 5 advisory wording notes.
  - No protected file is in the diff.
  - I ran my probes only in temporary directories outside the checkout. My test runs created two `__pycache__` directories inside it, which I removed.

## Blocking findings

**V1. High, rank 1. The tool refuses every report path in this change's own contract.**
- `report_in_scope` only accepts `declared_scope` entries that contain `*`.
- The JSON contract lists the report paths literally, and so does every other `review-*` contract.
- Reproduction: `report_in_scope(contract, "verification/review-run-review-verifier-report.md")` returns `False`, and the same holds for the round-2 and security report paths.
- This breaks AC10 and AC14, and it rules out the Evidence strategy's real run on this change's first Verifier round.
- The tests pass only because their fixture uses a `*` pattern.
- Fix: also accept an exact match, and add a test with a scope list shaped like the real contracts.

**V2. Medium, rank 1. The report commit is not alone when a repository hook stages something.**
- The staged-path check runs before `git commit`, the commit runs hooks, and nothing checks the new commit's tree.
- Reproduction: a `pre-commit` hook that runs `git add extra.txt` produces a commit containing `extra.txt` and the report. The tool exits 0 and prints "committed".
- This breaks AC10 ("commits only that path") and falsifies the pack's own sentence "if it commits … more than the report … the change is wrong".

**V3. Medium, rank 1. The blob check runs after the commit.**
- `-c core.autocrlf=false` does not override `.gitattributes`, a global `core.attributesFile`, or a hook.
- Reproduction: with `.gitattributes` set to `*.md text eol=lf` and a CRLF answer, the tool commits, then refuses with exit 1. The branch is left with 2 commits, the top one non-verbatim.
- The approved AC10 says the tool commits *after* checking the blob.
- Fix for V2 and V3 together: build the commit without filters or hooks (`hash-object -w --no-filters`, a temporary index, `commit-tree`). Check that the tree difference is exactly the report, then `update-ref` with the expected old value.

**V4. Medium, rank 1. On POSIX the timeout neither kills the reviewer's children nor returns on time.**
- `process.kill()` kills only the direct child, and `communicate()` then waits for every pipe holder.
- Reproduction in WSL (Linux, Python 3.14): a reviewer whose child holds stdout, with timeout 2 s, returned after 25.0 s. A child that never exits would hang the tool for good.
- This breaks the JSON AC5 ("kills the reviewer and its children"). It matters because `cursor-agent --force` starts children, and the lab builds on a Mac.
- Fix: `start_new_session=True` plus `os.killpg`, a bounded `communicate()` after the kill, and a test with a grandchild process.

**V5. Medium, rank 1. The check that the origin repository is unchanged has no test.**
- I deleted the `snapshot(root) != before` lines in a copy of the tool, and all 29 tests still passed.
- `test_a_change_to_the_origin_repository_makes_the_run_invalid` calls `snapshot()` directly and never `run()`.
- This breaks AC12 ("a test that fails without it"). The pack's e4 entry for AC8 cites this test, and its list of 13 mutations leaves this control out.

**V6. Medium, rank 2. The JSON contract carries the approval but differs from the approved Markdown contract.**
- It was added in `00a4fbb`, after the approval commit (`5e5aae0`) and after the tool (`065170d`), and it rewrites criteria to fit the code:
  - **AC1:** "ancestor of HEAD" became "must be the current HEAD".
  - **AC2:** the tool does not show the preflight output when the preflight succeeds.
  - **AC11:** the approved text requires a duration field, and the log has none.
  - **AC4:** the JSON says every `GIT_` variable is dropped, but the code sets `GIT_TERMINAL_PROMPT=0` and the test exempts it.
- Fix: either change the code to match the approved text, or have the Change Owner approve the changes and record that in the dispositions.

## Advisory findings (the cap of five, the fifth grouping the excess)

- **A1. Low, rank 1. The tool can commit a report that does not qualify as an outcome record under §6(a).** A reply containing a NUL byte was committed; there is no 1 MiB cap; and `--accept-nonconforming` lets a non-UTF-8 reply through.
- **A2. Low, rank 1. A refused run still writes its log into the refused directory.** In my probe, a non-empty `--out` had its existing `review-run.json` overwritten. An `--out` inside the repository gets a log file written there.
- **A3. Low, rank 4. Any `*` entry in the scope list is accepted as a report pattern.** For example, `verification/tests/**` would be accepted, and `**` also matches `..` segments. The match should be limited to the report paths that AC14 declares.
- **A4. Low, rank 4. `--trust` with the working directory in the author's checkout lets the reviewed head configure its own reviewer.** The CLI trusts the workspace without asking, so project agent config in the head (rules, MCP servers, hooks) can steer the reviewer or run code in it. I'm passing this to the security-focused layer.
- **A5. Low, excess items:**
  - The pack's AC13 check sentence is garbled and names `98c1779` instead of the base.
  - `--model` defaults to `""`, so the default profile passes an empty `--model`.
  - On Python 3.11 or older under Windows, `shutil.which` searches the current directory first, and the tool sets no minimum Python version.

## Routes tried and found closed

- The clone has its own refs and no origin remote.
- A head that sits only on a detached HEAD, on no branch, clones and commits correctly.
- The reviewer gets an allowlist environment: tokens, `GIT_*` variables and `PYTHONPATH` do not arrive.
- Secret values stay out of the screen and the log.
- No shell is used, and arguments for a `.cmd` launcher are filtered for shell characters.
- A CRLF answer is committed byte for byte with `core.autocrlf=true`.
- An existing report is never overwritten.
- A failing preflight blocks the reviewer.
- A launcher committed in the current directory is not picked up on Python 3.14.
- The pack's replay claim holds: all three reports of review-guarantee-sentences are rejected.

**Not tried:** the other 12 mutations the pack lists; a real `.cmd` launch, including the trailing-dot `.cmd.` suffix variant; a real reviewer.

**Security rules:** I applied the credential, certificate and cryptography rules to the diff because the tool handles credential names and computes digests. The diff adds no credentials or certificates. The `tok-`/`key-12345678` strings are test fixtures, not credentials. The tool uses SHA-256 only for integrity, which those rules allow.

Outcome: BLOCKED
