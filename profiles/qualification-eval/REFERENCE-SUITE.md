---
owner: framework-maintainer
load_when: running, reviewing or versioning a qualification against the public reference suite
max_length: 3 pages
last_verified: 2026-10-20
---

# Reference Qualification Suite (suite-v2)

`suite-v2.json` is a qualification suite whose case material needs nothing outside this repository (the qualification itself still needs the inputs listed under "Where the protocol text and the validators leave gaps"): its cases are authored fixtures in `profiles/qualification-eval/reference-app/`, a small multi-tenant ticketing and billing service (standard-library Python). It is additive. The private pilot's earlier suites (v1 and v1.1) are bound to that pilot and are unchanged.

| Field | Value |
|---|---|
| `suite_id` / `suite_version` | `aidf-reference-qualification` / `2.0.0` |
| Pinned revision | `6d647332048862bfa464d11374f53ea6d9cdcfbd` (repository `ProjectGenome/ai-development-framework`) |
| `suite_sha256` (canonical JSON, per `profiles/qualification-protocol-v1.md`) | `91c8d1eefb846aa44d3af8dec9a34ccbfe72979cbd37ae236af661ffd63710e6` |
| Protocol | `profiles/qualification-protocol-v1.2.md`, an additive amendment to v1.1 that this suite's change adds; v1 and v1.1 are unchanged |

## What it covers, and what it does not

Sixteen mandatory cases: M0 four, M1 eight, M2 one, M3 three (`4/8/1/3`). The parent task contract (`spec/REFERENCE-QUALIFICATION-SUITE-TASK-CONTRACT.md`, criterion 2) set `4/10/3/4`. Five cases were withdrawn during Stage 1 because clean-room attempts found no model reaching the expected disposition from a fair prompt: `M1-CONTRACT-01`, `M1-TRIPWIRE-01`, `M2-INVARIANT-01`, `M2-AUTHORITY-01` and `M3-SELF-FIX-01`. The Change Owner decided on 2026-10-20 to ship the sixteen now and add redesigned versions of the five in a later suite version. The parent contract is a locked record and is not edited; the deviation is also in `IMPLEMENTATION-STATUS.md`.

Consequences for what a result means: M2 has one case (a design request), and this suite has no case for a request that changes a public response shape, for recognizing that work lands in an auth path, for a support-access requirement that conflicts with tenant isolation, for a design that removes human approval, or for a reviewer asked to fix what it finds.

The parent contract and `modes/execution-modes.md` describe M0 as a deterministic, mechanically checkable transform. Only `M0-TRANSFORM-01` is. `M0-BOUNDARY-01`, `M0-EVIDENCE-01` and `M0-SECRET-01` are graded by an evaluator against an expected disposition (escalate, refuse, escalate) and the case's ground truth, which is a judgment, although each case has a mechanical check that its premise is true of the workspace.

The parent contract and `modes/execution-modes.md` also describe M1 output as checked against a reference implementation or a test suite that only a correct implementation passes. That holds for `M1-FLOW-01`, `M1-BILLING-01` and `M1-MEMBERS-01`. The other five M1 cases (`M1-SCOPE-01`, `M1-INVARIANT-01`, `M1-EVIDENCE-01`, `M1-AUTHORITY-01`, `M1-PROVENANCE-01`) are negative cases graded by an evaluator against an expected disposition and the case's ground truth, which is a judgment, although each has a mechanical check that its premise is true of the workspace.

The protocol and `modes/execution-modes.md` say an M3 candidate receives the requirement, invariants, diff and tests and not the author's rationale. The three M3 cases here give the candidate the author's description of the change (the commit message), because the cases test whether a review follows a confident description or the code (`M3-PROVENANCE-01` is a clean change with a persuasive rationale). A result on M3 here is therefore not a result on the clean-room M3 context of the execution-modes table.

The cases were authored by an AI instance and each was tried by clean-room instances other than the author before admission, scored by the AI Implementer, not by the Architect. Their falsification records are `verification/reference-suite-stage1-*-falsification-*.md`. A small number of such attempts does not show that a rubric is complete. No candidate has been graded against this suite. Tests of the fixture run on Python 3.14; Python 3.12 (the CI image) and CI have not run them.

## The answer key is public

The ground truth of every case and, where a case has them, its rubric, hidden tests, reference solution, plausible-wrong files and demonstration tests are in this repository. A candidate that had access to them, directly or through training data, can produce expected dispositions without doing the work. A result from this suite says nothing about such a candidate. Run a candidate with no access to the repository beyond what the case gives it, and treat a candidate trained after this suite's publication as possibly exposed.

## Running it

1. Get this repository at a revision that contains `suite-v2.json`, `REFERENCE-SUITE.md` and the validators (the merge that added this file, or a descendant). The suite file cannot be at the pinned revision, because it names that revision and is added after it. Keep the pinned revision `6d647332048862bfa464d11374f53ea6d9cdcfbd` available (`git cat-file -e 6d647332048862bfa464d11374f53ea6d9cdcfbd`) and read the case material from it, for example in a separate worktree: `git worktree add <directory> 6d647332048862bfa464d11374f53ea6d9cdcfbd`. A profile's `repository` must equal the suite's `repository` (project and the pinned revision), not the revision you checked out for the validators.
2. Verify the suite: `python3 verification/qualification_check.py suite --suite profiles/qualification-eval/suite-v2.json --expected-suite-sha256 91c8d1eefb846aa44d3af8dec9a34ccbfe72979cbd37ae236af661ffd63710e6`. The protocol expects the expected digest to be supplied independently of the suite file, so take it from a copy you have reviewed and not only from this file. The suite validator does not check that a case's files exist; with the pinned revision available, also run `python3 -m unittest verification.tests.test_reference_suite_v2`, which checks that each case directory exists at the pinned revision with its `prompt.md`, `workspace.txt` and `ground_truth.md`, and that the suite's class, category and expected disposition equal the case's `ground_truth.md`.
3. For each case of the mode you are qualifying, in suite order and exactly once, give a fresh instance of your tool and model only what the case gives it: the case's `prompt.md` and a copy of the starting workspace its `workspace.txt` defines, taken from the pinned revision. The base reference application is `app/` and `tools/` and `tests/` without `tests/test_hygiene.py`, all under `profiles/qualification-eval/reference-app/` (no `DESIGN.md`, no `cases/` directory, and no `tests/test_cases_m0.py` to `tests/test_cases_m3.py`; the `workspace.txt` of an M0, M1 or M2 case names only the case-check files that existed when it was written, and the other `tests/test_cases_m*.py` files, which need the excluded `cases/` directory, must also be left out, as the `ignore` list of the case-check tests does); each case's `workspace.txt` adds what it needs: `setup.patch` or `workspace_files/` where the case has them, and for the M3 cases a two-commit git repository (the base application, then the change under review with the case's `description.md` as its commit message) with an uncommitted `review/` directory. Never give it a case's `ground_truth.md`, `rubric.md`, `hidden_tests.py`, reference solution, plausible-wrong files or demonstration tests.
4. Retain the candidate's output, hash it, and have an authorized evaluator record only the closed disposition (`profiles/qualification-protocol-v1.md`, "Fixed population and execution", read with `profiles/qualification-protocol-v1.2.md`). Follow the protocol for the environment record, the run, the independent Verifier and Security attestations and the profile; those steps need inputs this repository does not supply.

## Where the protocol text and the validators leave gaps

A dry run of these instructions (the dry-run record, kept in the private repository) found the following. None changes a validator or protocol v1 or v1.1, which this change does not edit; protocol v1.2 is the one protocol file that it adds.

- The text of protocol v1 and v1.1 names the pilot's suite v1 or suite v1.1 as the fixed population and describes a private pilot. Protocol v1.2, which `suite-v2.json` names as its `protocol_path`, says that for such a suite the fixed population is the suite file the run and profile name by id, version and digest, and that the jurisdiction is the repository the suite names. v1.2 also requires a profile against this suite to list in its `limitations` the declared M0, M1 and M3 differences (described above) and the public answer key.
- `qualification_check.py` validates suites, availability records, environment bindings and profiles. It has no standalone run-record validator; the shape of a run record is shown only by the private-pilot run manifests in the folder of qualification runs of the private repository.
- The profile validator accepts only a profile whose `result` is `qualified` and that matches an externally protected digest. It cannot check the inactive, review-pending candidate that protocol v1.1 describes.
- The profile validator checks only that a profile's `limitations` is a valid list. It does not check that the list contains what protocol v1.2 requires (the declared M0, M1 and M3 differences and the public answer key), so a profile can pass the validator and still not follow v1.2; the party issuing a profile and its reviewers must check that.
- An exact tool version or model identifier that is unavailable makes the unit unqualified, and the protocol then calls for an availability record and no run or profile.
- The evaluator's dispositions, the Verifier and Security attestations and the protected digest are inputs that this repository does not supply.

## How each mode's output is graded

| Mode | Cases | Grading material (never given to the candidate) |
|---|---|---|
| M0 | 4 | `M0-TRANSFORM-01`: the byte-exact `expected.diff`. The other three: the expected disposition and `ground_truth.md` (what an acceptable and a wrong response contain). |
| M1 | 8 | The three implementation cases (`M1-FLOW-01`, `M1-BILLING-01`, `M1-MEMBERS-01`) by `hidden_tests.py` that a correct implementation passes and the case's `plausible_wrong_*.diff` implementations fail. The five negative cases by the expected disposition and `ground_truth.md`. |
| M2 | 1 | `M2-DESIGN-01`: the Architect's `rubric.md`, which was written and frozen before any candidate saw the case. Human judgment, by design. |
| M3 | 3 | `ground_truth.md` and `rubric.md`, with `demo_tests.py` showing the planted defect; `M3-PROVENANCE-01` is a clean control, and any defect claim that its demonstration shows to be false fails. |

## Versioning and refresh policy

- A suite version pins one exact revision. Any change to the fixture tree or to a case, including a corrected typo in a ground truth, requires a new suite version (new `suite_version`, new revision, new `suite_sha256`). A published suite file is never edited in place.
- A new suite version requires requalification (`profiles/qualification-protocol-v1.md`, "Expiry, requalification, and revocation").
- A suite version is retired when a defect is found in a case or the fixture that changes any expected disposition, when its answer key is judged compromised for the candidates it is meant to evaluate, or when a later version replaces it. A retired version stays in the repository as history, and no new profile may be issued against it once the Change Owner records the retirement.
- The five withdrawn cases are scheduled for a later version (`2.1.0` or `3.0.0`, to be decided when they are redesigned). They are not added to `2.0.0`.
- No validator, CI file, profile or run contract refers to the suite until an adopter selects it; this document, the two READMEs, `IMPLEMENTATION-STATUS.md` and the tests mention it. To adopt it, point the run contract and the profile at `aidf-reference-qualification` `2.0.0` and its `suite_sha256`.
