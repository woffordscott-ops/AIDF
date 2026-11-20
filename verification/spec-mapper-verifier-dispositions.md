# Dispositions: spec-mapper

Append-only record of the Implementer's dispositions of Verifier findings and of the implementation. Task Contract: `spec/AIDF-SPEC-MAPPER-STAGES-0-1-TASK-CONTRACT.md` (T2, approved by the Change Owner on 2026-11-06).

## Implementation record

- Base `2d44ecb` (main after MR !77). The branch was rebased onto it before the work.
- The change: `verification/spec_mapper.py`; four mappings under `instantiation/mappings/`; fixtures under `verification/spec-mapper-fixtures/` (the real OpenSpec and Spec Kit outputs of the reading test copied as inputs, a synthetic Kiro-style folder labelled as such, a markdown-sections example, and four expected drafts); `verification/tests/test_spec_mapper.py` (51 tests); section 8 of `instantiation/spec-tools.md`; CHANGELOG entry.
- Expected drafts: the contract called them hand-made. They were made by a separate script that does not import the tool (it finds headings by plain string tests) and each was compared with the tool's output; the first comparison differed because of a defect in the script (a checklist prefix slice), which was fixed. A misreading of the template shared by both would not be caught (stated in the pack's e5).
- Hostile and malformed inputs: the contract listed a malformed and a hostile folder among the fixtures. They are built by the tests at run time in a temporary directory, because a link cannot be committed portably. The two tests that need a link to a file skip on an account without that right (here); link detection is also tested through a stub.
- Contract deviations, disclosed for the Change Owner: (1) the guide's introduction said "Nothing in AIDF reads a tool's files" and its section 7 said "None is offered here"; both contradict section 8, so both sentences were edited and their pins in `verification/tests/test_spec_tools_guide.py` updated; (2) that test file was added to the contract's declared scope (JSON and Markdown). The approved criterion AC7 (a short section) is otherwise unchanged.
- Checks at `abec600`: private suite 834 tests OK (skipped=23; base 783, skipped=21); the dry run `python verification/export_public_tree.py --out <directory> --run-tests` exported 368 files, compile of 68 Python files PASS, exported suite 611 tests OK (skipped=77; base 560, skipped=75), scan PASS, byte identity PASS, manifest unchanged; the module also passes over a CRLF copy of the fixtures.
- Mutations: 69 applied, 63 killed. The first run killed 54 of 67; the survivors led to new tests. The 6 survivors are equivalent (shadowed by another check), listed in pack e3.

- Preflight corrections: the first preflight run failed two checks, both fixed before review: the pack's AC4 check used the word TODO in a way the evidence check reads as incomplete (reworded), and the approved proposal `strategy/AIDF-SPEC-MAPPER-PROPOSAL.md`, committed on this branch, was missing from the declared scope (added to the JSON and the Markdown; a third scope clarification for the Change Owner).

## Verifier round 1 (reviewed head `b0a911a`, report `verification/spec-mapper-verifier-report.md`, Outcome: BLOCKED)

| Finding | Disposition | What was done |
|---|---|---|
| F1 (High, rank 1): `check_output` treated a `ValueError` from `os.path.commonpath` as "not inside the input folder"; a path in the Windows extended-length spelling (`\\?\` or `//?/`) of a place inside the input folder raised it, so the tool wrote the draft there, and with `--force` replaced an existing planning file | FIXED in code | `check_output` now compares plain forms of the two paths (`plain_path`: the real path, the extended-length prefix of a drive path removed, any other prefixed form refused, case normalised) and compares drives itself instead of catching the error, so no exception can turn the check off. A new test refuses the prefixed spellings, the slash spelling, upper case and the `--force` overwrite of a planning file and shows nothing was written; another shows that a sibling folder is still allowed and an unknown path form is refused. Mutation of the prefix removal killed. Private suite 836 tests OK (skipped=23); exported suite 613 tests OK (skipped=77); the pack's counts and e3 are updated |

Routes the Verifier closed (junctions at any level, short names, case, trailing dots, control characters, regex timing, size limits, imports) need no action. Round 2, a confirmation of the delta `b0a911a..7f6a39c`, is within the declared budget of two.

## Verifier round 2 (reviewed head `80c9bca`, report `verification/spec-mapper-verifier-report-round2.md`, Outcome: BLOCKED)

F1 of round 1 is confirmed fixed for every spelling tried (prefixes, case, short names, trailing dots, relative, subst drive, junction). Two findings:

| Finding | Disposition | What was done |
|---|---|---|
| B1 (Medium, rank 1, blocking): an output path made of the input directory's path, a colon and a stream name was not seen as inside the input folder, and the draft was written into that stream | FIXED in code | on Windows `check_output` refuses any ':' after the drive in the output path (a stream), before it looks at containment; a test refuses four spellings (the folder plus a stream, the planning file plus a stream, `::$DATA`, with the extended-length prefix) and shows nothing was written and the planning file is unchanged. Skipped on a system without streams |
| A1 (Low, rank 1, advisory): with `--force`, an output path that is a hard link to a planning file replaced that file | FIXED in code | an existing output with more than one name is refused even with `--force`; a test links a planning file and shows it is unchanged |

Checks after the fixes: private suite 838 tests OK (skipped=23), exported suite 615 tests OK (skipped=77), 372 files exported, the pack's counts and AC5 and e3 sentences updated, e5 states that other aliases of a place inside the input folder are covered only as far as the real path shows them.

Budget: the contract declares two Verifier rounds; both are used and the second ended BLOCKED, so the Change Owner chooses and records (core/05-review.md section 5): approve a third round on the delta `80c9bca..HEAD`, accept the residual shapes, or stop. This append is made before that decision.

## Approval of a third Verifier round

The Change Owner approved a third Verifier round on 2026-11-09 ("3rd round approved"), outside the declared budget of two (core/05-review.md section 5), as a confirmation of the delta `80c9bca..` (B1 and A1 fixes, pack and dispositions). Recorded before the round starts.

## Verifier round 3 (reviewed head `4f005dd`, report `verification/spec-mapper-verifier-report-round3.md`, Outcome: PASS)

No findings. The round was run after the merge of the change, on main's head, as the confirmation the Change Owner approved on 2026-11-09. B1 and A1 are confirmed fixed and F1 of round 1 still fixed; the mutations of the two fixes were killed. The first attempt at this round was refused by the tool as invalid, with nothing committed, because the repository changed while it ran (the author pushed in the shared checkout); it was re-run in a separate worktree. No code change follows from this round.
