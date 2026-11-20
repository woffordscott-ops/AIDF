---
owner: framework-maintainer
load_when: preparing the brief for a Verifier or Security Reviewer round
max_length: 1 page
last_verified: 2026-10-31
---

# Review Brief

Fill the fields, delete the guidance in italics, and give the result to the reviewer as its prompt. A brief is a template to fill; nothing generates its round-specific checks. `python verification/run_review.py` (run by the human, never by the Implementer's session) adds the computed header, runs the preflight, starts the reviewer with a reduced environment and commits the answer verbatim; this file is the round-specific part it takes as `--brief`. Before the first round run `python verification/preflight.py --contract <contract.json> --evidence <pack.json>` and attach its output. Fix what it reports before the round starts.

**Before the first run of the tool** (the same note ends `python verification/run_review.py --help`): a reviewer CLI that is not on PATH is named with `--reviewer-executable` and its full path (on Windows `cursor-agent` is a `.cmd` launcher in the user's local application directory); the report path must be named by an entry of the contract's `declared_scope`, a path or a pattern, before the run; `--out` must be a new or empty directory, and a refused start leaves its log there, so clear it before the next start; the tool refuses to start the reviewer when the head holds files that can steer it (`AGENTS.md`, `CLAUDE.md`, `.cursor`, `.agents`, `.claude`, `.codex`, `.grok`, symbolic links, names with a control character), and `--allow-steering-files` starts it anyway and the log records that; the reviewer's ruff, mypy, Python and pytest caches are pointed into `<out>/reviewer-cache`, and any other file it leaves in the checkout makes the run invalid; an answer with an Outcome line anywhere but its last line is not committed and is kept as `<out>/answer.rejected`; the tool commits the report alone on top of the pinned HEAD, moves the branch you are on to it (on a detached HEAD only HEAD moves), and never pushes.

- **Role and layer:** independent Verifier | Security Reviewer, round N of the declared budget. *Name the Change Owner's recorded reason for any round past the budget.* You did not write this change and you are a fresh session.
- **Reviewed head:** the full commit SHA, in a read-only checkout at that commit. *For round 2 and later also give the previous reviewed head and the delta command `git diff <previous> HEAD`; confirmation rounds cover the delta only (`core/05-review.md` §6).*
- **Shell:** run the commands you are given, and say plainly at the top of the report whether your shell worked. Do not report a check as passed that you did not run. Read-only commands only; write only to a new empty directory outside the checkout.
- **Inputs:** the Task Contract, the evidence pack and the dispositions file are claims to test, not evidence. *List the paths. Attach the preflight output.*
- **Record text:** apply `core/05-review.md` §4. A finding only about narrative, a count or history in the pack or dispositions is advisory unless it meets one of the four exceptions, which you name.
- **What to do:** *the numbered checks for this round, each with the command to run.*
- **Each finding:** file and line, severity (Critical, High, Medium, Low, Informational; `core/05-review.md` §4), evidence rank and a failure scenario.
- **One pass:** list every finding you can establish and the routes you tried and found closed. Non-blocking findings: at most N. Recorded Change Owner acceptances are accepted; do not raise them as defects. An acceptance never waives required evidence and never accepts a rank-1 behavior defect that has a reproducing case (`core/05-review.md` §5).
- **Outcome line:** `Outcome: PASS`, `Outcome: PASS_WITH_ADVISORIES` or `Outcome: BLOCKED`, no other words. Print the complete report as your final reply.
