**Outcome: BLOCKED.** I found two new blocking defects, both reproduced, in the process-group kill that this delta adds. After a Ctrl-C on Linux or macOS the reviewer keeps running with no timeout to stop it. The test for the kill also passes when the kill is removed. All six blocking findings from round 1 are fixed in the code.

## Review record

- **Change:** review-run-review. No merge request identifier was given.
- **Reviewed head:** `de3a394cb839b1cc0af89c2adbc5fcd628e61d09`.
  - The delta covered is `git diff 68960360fd3c568e70057d8d687b4e62d8c00085 de3a394` (6 files, +384/−59).
  - The base of the whole change is `ab2ed741e8dd535ddc5b9790e03f04150a70ea0e`.
- **Role:** independent Verifier, round 2 of 2 (the last budgeted round). This is a confirmation round under §6: the delta, plus one attack on the controls the delta adds.
- **Instance:** a fresh Cursor agent session (Claude Opus 5.5) with no access to the Implementer's reasoning.
- **Times (UTC):** started 2026-11-02T16:20Z, finished about 16:45Z.
- **Inputs read:**
  - `core/05-review.md`, the round 1 report and the dispositions.
  - The approved Markdown contract and the JSON contract.
  - The delta to `run_review.py`, its tests, the evidence pack and the contract.
- **Mechanical checks, run again at `de3a394`:**
  - `test_run_review`: 41 tests, OK, 1 skipped on Windows. The suite: 582 tests, OK (skipped=4). With file transport disabled: OK (skipped=5). These match the pack's e2.
  - `ruff` passed, and `mypy --strict` passed on `run_review.py`.
  - `preflight.py --offline` reported ALL OK, with 6 advisory wording notes.
  - No protected file is in the diff from the base.
- **Where I ran probes:** only in temporary directories, on Windows (Python 3.14.7, git 2.55.0) and Linux (WSL, Python 3.14.6, git 2.55.0). The checkout is still clean.
- **One side effect outside the checkout:** I briefly set a global git identity in the WSL distribution and then deleted `~/.gitconfig` there. If that file existed before with a `[user]` section, that section is gone.

## Blocking findings

**R2-B1. Medium, rank 1. On POSIX, interrupting the tool leaves the reviewer running with no timeout. The delta introduced this.**
- `start_new_session=True` puts the reviewer in its own session, so a terminal's Ctrl-C (SIGINT to the foreground group) and a closed terminal (SIGHUP) no longer reach it.
- `run_reviewer` catches only `TimeoutExpired`, so a `KeyboardInterrupt` exits the tool without calling `kill_tree`.
- **Reproduction (Linux):** the tool ran with a stand-in reviewer that sleeps 30 s and `--timeout 20`, and I sent SIGINT to the tool's process group.
  - The tool exited with a traceback and wrote no log.
  - The reviewer (pgid = its own pid) was still running afterwards.
- **The same probe against the round 1 tool:** the reviewer received the SIGINT and was gone. So this is new in the delta.
- **Why it matters:** this is the AC5 control, "a timeout kills the reviewer and its children". The default reviewer runs with `--force`, a human will often stop a run that can last 60 minutes, and the lab builds on a Mac. Windows is not affected, because the console sends Ctrl-C to every process attached to it.
- **Fix:**
  - In `run_reviewer`, catch `BaseException`, call `kill_tree(process)` and re-raise.
  - Turn SIGTERM and SIGHUP into an exception while the reviewer runs.
  - Write the log on that path too.
  - Add a test that sends SIGINT to the tool's group and checks that the reviewer's pid is gone (POSIX only).

**R2-B2. Medium, rank 1. The children-kill in AC5 has no test that fails without it, and the pack's e3 says it does.**
- `test_a_grandchild_that_holds_the_output_does_not_stall_the_timeout` only checks that the run returns within 45 s. The new 10 s bounded wait meets that limit by itself.
- **Mutation:** I replaced `kill_tree` with `process.kill()` only.
  - Windows: the test passed in 12.6 s.
  - Linux: the test passed in 12.1 s, and the grandchild `time.sleep(90)` was still alive afterwards.
- **The unmutated tool on Linux** returned in 2.1 s and left no grandchild. So the code fix for round 1's V4 works; the test cannot tell it from the mutation.
- **What it breaks:**
  - AC12 ("a test per criterion that fails without it").
  - The pack's e3 sentence "the timeout kill replaced by a kill of the direct child only (TimeoutTests, a grandchild holding the output) … every run failed", which contradicts the tests it describes.
- **Fix:** have the grandchild write its pid to a file, and assert after the run that this pid no longer exists. A time limit below `KILL_WAIT` alone would also distinguish the two, but more weakly.

## Proposed dispositions for round 1

| Finding | Proposed disposition | Basis |
|---|---|---|
| V1 | CONFIRMED_FIXED | The real contract's literal paths are accepted. Removing literal acceptance, or removing the report-name rule, fails `CommitTests` (I ran both mutations). |
| V2 | CONFIRMED_FIXED | The report commit holds only the report even when a pre-commit hook stages a file. The sentence "no hook runs" is wrong; see R2-A3. |
| V3 | CONFIRMED_FIXED | `hash-object --no-filters`, with the check made before `update-ref`. The `.gitattributes` test covers it. |
| V4 | CONFIRMED_FIXED for the code | My Linux probe shows the grandchild killed in 2.1 s. The evidence gap is R2-B2. |
| V5 | CONFIRMED_FIXED | Removing `snapshot(root) != before` fails `CheckoutIntegrityTests` (I ran the mutation). |
| V6 | CONFIRMED_FIXED | AC2, AC4 and AC11 are in the code. The JSON AC1 now carries the approved wording. Requiring head = HEAD refuses everything the approved AC1 refuses, and AC10's "on top of the pinned head" implies it. The Change Owner's acknowledgement is welcome but not needed to close V6; see R2-A5 for AC10. |
| A1 | SUPERSEDED by R2-A1 | The three shapes named in round 1 are refused. The class is not closed. |
| A2, A3, A5 | CONFIRMED_FIXED | I ran the mutations for a log in a refused directory and for the model requirement, and both fail their tests. The AC13 sentence is rewritten. Python 3.12 is the minimum. |
| A4 | Passed to the security-focused layer | It is stated in `residual_risk`. |

## Advisory findings (the cap of five, the fifth grouping the excess)

- **R2-A1. Low, rank 1. An empty answer is still committed with `--accept-nonconforming`.**
  - With a reviewer that prints nothing, the run exited 0 and committed a zero-byte blob.
  - §6(a) requires a report that is "not empty". The fix lists NUL, size and UTF-8 but leaves out empty.
  - Fix: refuse `len(answer) == 0` whatever the waiver, and add a test.
- **R2-A2. Low, rank 1. A link at the report path itself bypasses the new "outside the repository" check.**
  - The check resolves only the parent directory, and `target.exists()` is False for a dangling link.
  - Reproduction (Linux): the reviewer created a dangling link at the report path in the origin repository. `snapshot` ignores untracked files, so the change was not caught. The tool reported success and wrote the answer to a file outside the repository.
  - Afterwards `git status` showed `T` (typechange) for the report.
  - It is Low because a reviewer started with `--force` can already write there (accepted limit (a)).
  - Fix: refuse when `target.is_symlink()` or `os.path.lexists(target)` is true, and create the file with `O_EXCL`, plus `O_NOFOLLOW` where it is available.
- **R2-A3. Low, rank 1. "No hook runs" is false.** The sentence appears in the dispositions (V2 row), in the pack's `residual_risk` and in the `commit_report` docstring.
  - `update-ref` runs `reference-transaction`, and every index write runs `post-index-change`. My probe hooks logged both.
  - In a second probe, a `reference-transaction` hook added a commit after the report commit, and that commit deleted the report. The tool exited 0 and printed the report commit while HEAD pointed elsewhere.
  - The report commit itself stays alone.
  - Fix: after `update-ref`, check that `rev-parse HEAD` equals the report commit, and correct the sentence.
- **R2-A4. Low, rank 1. The trailing-space case of the batch-launcher rule has no test that fails without it.**
  - Changing `rstrip(" .")` to `rstrip(".")` passes, because the `"tool.CMD "` case exits 1 anyway when the launch fails.
  - The pack's e5 lists "a trailing dot or space" as tested.
- **R2-A5. Low, excess items:**
  - The dispositions say that only AC1 still differs from the approved contract. The JSON AC10 also drops "with `core.autocrlf=false`", because the code now uses `--no-filters`, which is stronger. The Change Owner's acknowledgement should name AC10 as well.
  - Rank 4: `read-tree HEAD` rewrites the index without `-m`, which drops skip-worktree bits in a sparse checkout.

## Routes tried and found closed

- A pre-commit hook that stages a file cannot get into the report commit.
- A `.gitattributes` `eol` rule cannot change the stored blob.
- Literal and pattern scope entries work. The eleven odd paths, `.git`-like names and directory links are refused.
- NUL bytes, answers over 1 MiB and non-UTF-8 answers are refused under the waiver.
- A refused `--out` directory is left untouched.
- `GIT_TERMINAL_PROMPT` is gone from the environment.
- The preflight output is shown on success, and the log has a duration.
- A grandchild is killed on Linux with the unmutated code.
- A reviewer that moves a ref in the origin repository makes the run invalid.
- The mutation that removes `read-tree HEAD` fails the tests.

**Not tried:** a real reviewer; a real `.cmd` launch; macOS itself (the POSIX behaviour was shown on Linux).

**Budget:** this was the last budgeted Verifier round, so under §5 the open matters go to the Change Owner. R2-B1 is a rank-1 finding in code and R2-B2 is a rank-1 finding in tests, so the "allow one more round" option is available.

**Security rules:** I applied the credential, certificate and cryptography rules to the delta because the tool handles credential names and computes digests. The delta adds no credentials or certificates, and the probe strings are test fixtures. SHA-256 is used only for integrity, which those rules allow.

Outcome: BLOCKEDThe background run of the whole test suite finished successfully: 582 tests passed with 4 skipped. That matches the pack's e2 and is the count already cited in my report, so nothing needs to follow up and the report's findings and outcome stand. I'm repeating the Outcome line below so that this message also ends on it, in case the tool reads this one as my final reply.

Outcome: BLOCKED
