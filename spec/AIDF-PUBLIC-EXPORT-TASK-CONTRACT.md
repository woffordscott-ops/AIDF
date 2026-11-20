---
owner: framework-maintainer
load_when: reviewing or changing the public-tree export (verification/export_public_tree.py)
max_length: 1 screen
last_verified: 2026-10-28
---

# Task Contract: public-tree export

Written after the first build and after Verifier round 1 (BLOCKED, finding PE-003: no Task Contract). It records what was asked and approved on 2026-10-27; it is not a plan made before the work.

## Part A

- **Intended outcome:** a command that builds a public copy of this repository without the committed evidence archives and without files that contain the maintainer's workstation path or the private host name, and that fails rather than write a tree that still contains either string.
- **Acceptance criteria:**
  1. AC1. The manifest lists the left-out directories and files; the export copies every other tracked file unchanged and leaves out whole files only.
  2. AC2. The scan reads the file name and the raw bytes of every committed file it would publish (also with NULs removed, to catch UTF-16, and with whitespace, quotes and plus signs removed, to catch a simple concatenation), and the export scans every file it wrote, including the generated notes file, and fails if either scan finds a pattern.
  3. AC3. The export tool, its manifest and its test are not part of the public tree, because the manifest names the strings searched for.
  4. AC4. With `--run-tests` the export compiles the exported scripts and runs the exported tree's own test suite, reports each result, and says which CI jobs were not run; the checks run on a disposable copy with a minimal environment (no inherited tokens or proxy variables), never in the output directory, and the output is verified byte-identical afterwards.
  5. AC5. Tests that read left-out files skip with a stated reason; no assertion changes.
  6. AC6. The project name and the maintainer's name and email are accepted as they are; git history is not changed.
  7. AC7. Outcome records: `verification/aidf-public-export-verifier-report-round*.md` and `verification/aidf-public-export-security-report-round*.md`.
  8. AC8. The export takes the committed files of HEAD, not the working tree; it refuses a dirty tracked tree, a symbolic link or submodule entry, an output directory inside the repository, an empty or invalid pattern list and a manifest with duplicate keys.
  Spec Confidence: Clear via `strategy/AIDF-PUBLIC-EXPORT-PROPOSAL.md` (approved 2026-10-27).
- **Declared scope:** `verification/export_public_tree.py`, `verification/public-export-manifest.json`, `verification/tests/test_export_public_tree.py`, the skip decorator in `verification/tests/test_phase8_qualification_check.py`, this contract, `strategy/AIDF-PUBLIC-EXPORT-PROPOSAL.md`, the review reports.

## Part B

- **Approach:** exclusion only, by manifest; scan before and after writing; self-check of the written tree.
- **Invariants touched:** no committed file is rewritten; no digest changes; git history is not touched.
- **Evidence strategy:** unit tests for exclusion, byte scanning (including UTF-16), scanning the written tree (a seeded identifier in the generated notes file), and the exported-tree checks; a run of the export on this repository with `--run-tests`.
- **Recovery:** revert the commit. The export writes only to an empty or absent directory (not a link or junction) and changes nothing in the repository.

## Status

- **State:** Approved (approval recorded after the build, as noted above)
- **Established by:** Claude (Implementer)
- **Approved by:** Scott Wofford, Change Owner and Architect, 2026-10-27 ("I will follow your recommendations on these": build as T2 with one review; publish as a fresh repository)
- **Class:** T3. Decided by the Change Owner on 2026-10-28 ("Treat as T3") after Verifier round 1 (PE-004) argued that `KERNEL.md` trip-wire 4 applies. Review: Verifier round 2 and a distinct Security Reviewer (Codex), both authorized by the Change Owner the same day.
- **Spec Confidence at intake:** Clear

## Decisions of the Change Owner, 2026-10-28 (after the Security Reviewer's round 1; "I will follow your suggestions on these 4")

1. The scan's guarantee stays literal-plus-normalised (file names and bytes: raw, UTF-16, simple concatenation); a closed allowlist of published files is not built. The documents state the limit.
2. The checks are not network-isolated; the minimal environment, the disposable copy and the byte-identical output check are the controls. The documents state this.
3. The other operational identifiers named in the Security Reviewer's finding SR-10 (the project-group paths of the private host and its CI pin records, a Cursor service host name, the accepted project name) are accepted as they are.
4. PE-010 (the CI statement names no jobs) is accepted as built: the public tree has no pipeline, and the tool says so.
5. A Verifier round on the final head (beyond the two rounds of `core/05-review.md` section 5, authorized by the Change Owner) and then a fresh Security Review are to be run before merge.

## Decision of the Change Owner, 2026-10-29 (after the Security Reviewer's round 2)

6. The fixes for SR2-01 to SR2-06 are made as proposed (no manifest option; contained output paths; bounded blob reader; documents corrected for the Windows executable bit and the late-writer limit), and a re-review is authorized.
7. SR3-01 is accepted as outside the boundary (Security Reviewer round 3, 2026-10-29): code that imports `verification/export_public_tree.py` into its own Python process can set `MANIFEST` and call `main()`, and so can replace any function in the module. The boundary is the command line, the environment and the files next to the script, none of which can replace the committed manifest. The tool's docstring says so. Fixes for SR3-02 to SR3-05 are made, and a narrowly scoped re-review of SR3-02, SR3-03 and the manifest tests is authorized.

## Decision of the Change Owner, 2026-10-30 (after the Security Reviewer's round 5)

8. After five Security Review rounds the Change Owner accepts the following and asks that no further security pass be run before merge: (a) round 5 returned BLOCKED only because a document said a refused kill of git was handled; the documents and the error message were corrected in `011e3fa`, and no path that publishes an identifier or writes outside the output was found in rounds 4 or 5; (b) the residual in SR5-01, that a read blocked in a pipe stays blocked until git exits if the system refuses to kill it; (c) the absence of a Verifier review after the round 3 fix for PE-011, which the Change Owner authorized going without. The accepted residuals of decisions 1 to 7 stand.
