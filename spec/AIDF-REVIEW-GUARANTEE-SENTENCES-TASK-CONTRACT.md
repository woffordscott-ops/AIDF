---
owner: framework-maintainer
load_when: deciding or implementing the guarantee-sentence rule for evidence packs, the enumerating-check checklist item and the CI-like preflight run
max_length: 1 screen
last_verified: 2026-10-31
---

# Task Contract: Guarantee Sentences in Evidence Packs, Enumerating Checks, CI-like Preflight, Preflight Follow-ups

`core/01-lifecycle.md` §4. Class T2 (see Classification); Approved status required from a human under Architect authority before implementation begins. **Status: Approved by the Change Owner on 2026-11-01 (see Status). It builds on `review-preflight`, merged to main as 98c1779.**

## Why (the evidence)

`review-preflight` was blocked in its last round by one finding (B7): a sentence the Implementer wrote in the evidence pack in a *fix* commit, "a policy that attests files by another mechanism fails the lookup closed", was false for four mechanisms. Round 3 of that change, and an extra round before it, existed because of this class:

1. **A new guarantee sentence was written after a finding and not tested.** The fix for A6 (round 2) closed one shape; the same commit wrote a sentence about the whole class. `templates/evidence-pack.md` already says a universal word is used only with the set it covers, but "another mechanism" is an open set without a universal word, and nothing checks it. This repeats the pattern in `strategy/AIDF-REVIEW-EFFICIENCY-PROPOSAL.md`: each fix adds prose for the next round to fault.
2. **An enumerating check was fixed by instance.** `core/05-review.md` §2 ("controls that enumerate") says to close the class or back it by a runtime property. Round 2 reported A6 with two reproducing shapes; the fix closed one, which §2 says is not a fix.
3. **A CI-only failure came after the reviews.** The pipeline job `checker-fixtures` failed on the head of `review-preflight` after three rounds: six tests fetched a temporary policy repository by local path and the pipeline image's git has no `git-upload-pack`. This machine's git has it, so neither the preflight nor the suite nor any reviewer's run showed it. Running the tests with local-path fetching disabled (`protocol.file.allow=never`) reproduced the same six failures here. That cost a fourth round.
4. **All three were avoidable by the Implementer** with rules the project already has; what was missing is a mechanical prompt at the moment of the fix. The same two causes appear in earlier changes (`review-efficiency-core` rounds 2 and 3; base app rounds 15 to 27).

## Part A: Minimal

- **Intended outcome:** A fix commit cannot add a guarantee sentence to an evidence pack without a test that falsifies it, and a finding about a check that enumerates is fixed for its class or stated as a limit, so these two findings stop costing a round. No control on code, tests or security posture is weakened; this adds prompts and a warning.
- **Acceptance criteria:**
  1. **Pack template rule.** `templates/evidence-pack.md` content rules gain: a sentence that guarantees behaviour over an open set ("fails closed", "cannot", "never", "always", "every other", "any other") names the test that fails when the guarantee is false; if no such test exists the sentence is written as a limit ("passes silently for X") or removed.
  2. **Checklist item.** `templates/task-contract.md`, in the "New rule or checker" checklist (added by `review-preflight`), gains: when a reviewer reproduces one shape of a check that enumerates, close the class (parse, do not pattern-match) or state in the pack the shapes that still pass, and write no guarantee about the class; closing one reported shape is not a fix (`core/05-review.md` §2).
  3. **Preflight warning.** `verification/preflight.py` gains a step `pack wording` that reads the evidence pack and prints a note for each sentence containing a guarantee word (fails closed, cannot, never, always, every, all, any other, none) that does not cite a `test_` name or a command in the same sentence. It never fails the preflight (false positives are expected), and it prints how many sentences it examined.
  4. **CI-like run.** `verification/preflight.py --ci-like` runs the unit-test step (the policy's `unittest discover` command) with an environment that removes what the pipeline image lacks: no user or system git configuration (`GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` pointing at an empty file, `GIT_CONFIG_NOSYSTEM=1`), local-path fetching disabled (`protocol.file.allow=never`), no inherited token or proxy variables, and a fixed `HOME` in an empty temporary directory. It prints the environment it used and what it cannot reproduce (the image's tool versions and the missing programs). It does not claim parity with the pipeline.
  5. **Tests.** The warning fires on the B7 sentence of `review-preflight` (read from its committed pack at the head that was blocked) and on a synthetic sentence, stays quiet on a sentence that cites a test, and counts examined sentences; presence tests for the two template lines; with `--ci-like` the preflight's own tests that depend on local-path fetching fail on the head of `review-preflight` before its fix `4abe5ff` (run in a scratch export) and pass after it, and the environment passed to the step contains the settings above. `mypy --strict` and `ruff` pass. `CHANGELOG.md` records the change as additive.
  6. **Replay.** Run the warning over the committed evidence packs (20 files named *evidence-pack*.json at the time of writing) and report how many sentences it flags and how many of the flagged sentences were later the subject of a blocking finding in the finding table (`verification/review-finding-table.csv`); report the result without adjusting the word list to fit it.
  7. **Scope.** No change to `core/05-review.md`, `verification/aidf_check.py`, `verification/phase2-task-contract.json`, `.gitlab-ci.yml`, `KERNEL.md`, trip-wires or `core/02-authority.md`.
  8. Outcome records (core/05-review.md section 6): the review report patterns are `verification/review-guarantee-sentences-verifier-report*.md`; the dispositions file is `verification/review-guarantee-sentences-verifier-dispositions.md`.

  9. **Record check by parse (follow-up A6 of `review-preflight`).** `attested_records` reads the policy job's embedded Python with `ast` instead of matching text: it fails closed unless `records` and `selected_records` are each bound exactly once (any other binding of either name, by assignment, augmented assignment, walrus, loop or `with` target, import, definition, argument, `global` or `nonlocal`, fails), `records` is a tuple of two-element tuples of a string constant and a name, and a single top-level `for` over `records + selected_records` has no `break` or `continue`. The shapes that still pass are stated as limits in the evidence pack: the body of that loop and the function it calls are not examined.
  10. **Pin of the policy ref (A13).** A test with a two-commit policy fixture shows `--policy-ref <sha of the first commit>` reads that commit's template and not the later one, and fails if the ref is ignored.
  11. **Fetch success path (A14).** A test fetches a temporary policy repository through `file://` and passes; it is skipped, with the reason printed, when the git transport is unavailable (as in the pipeline image). The failure path stays tested.

  Spec Confidence: Clear at intake.

- **Declared scope:** `templates/evidence-pack.md`, `templates/task-contract.md`, `verification/preflight.py` and `verification/tests/test_preflight.py`, `CHANGELOG.md`, this contract, `verification/review-guarantee-sentences-task-contract.json`, `verification/review-guarantee-sentences-evidence-pack.json`, `verification/review-guarantee-sentences-verifier-dispositions.md`, and the reports `verification/review-guarantee-sentences-verifier-report*.md`. **Excluded:** everything named in criterion 7; automatic rejection of a pack (a warning only); 5b (`run_review.py`).

## Part B: Plan

- **Approach:** Two template lines, one warning step in the preflight with a small word list, tests, replay over the committed packs; criteria 9 to 11 are the three follow-ups the Change Owner approved with this contract (A6, A13, A14 of `review-preflight`).
- **Invariants touched:** none of the stable surface. The warning changes no review rule and blocks nothing.
- **Evidence strategy:** counterfactual tests as in criterion 4; the replay of criterion 5 states the warning's precision on the old data and is reported as it comes out.
- **Review budget (this change):** one preflight run and two Verifier rounds. A third round needs the Change Owner's recorded reason and a rank-1 finding in code, tests or security posture. Accepted limits stated before review: a word list cannot find every guarantee; the warning is advisory; the template lines are checked by presence only.
- **Protected files touched:** none.
- **Recovery / reversal approach:** `git revert`.

## Classification

Proposed **T2**: it edits two templates and a verification tool, no trip-wire. It could be argued T1 (templates and a warning), but templates are framework rules with project-wide reach, so T2.

## Decisions for the Change Owner

1. Approve as T2, after `review-preflight` merges? **Answered 2026-11-01: approved (see Status).**
2. Is a warning (never a failure) the right strength for criterion 3? **Answered: approved as drafted, a warning only.**

## Status

- **State:** Approved
- **Established by:** Claude Sonnet 5.5 (Anthropic), under Implementer role, 2026-10-31
- **Approved by:** Scott Wofford (Change Owner and Architect), 2026-11-01, by his message "As for follow-ups, I approve those 3", given in answer to the three items offered after `review-preflight` round 4: this contract (T2, including `--ci-like`), the `ast`-based fix for A6, and the A13 and A14 tests. Criteria 9 to 11 were added to this contract on the same day to carry the last two items; the Implementer's reading is that the approval covers them. Scott may correct this reading.
- **Class:** T2 (as proposed)
- **Spec Confidence at intake:** Clear
