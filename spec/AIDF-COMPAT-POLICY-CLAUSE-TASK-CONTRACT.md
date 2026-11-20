---
owner: framework-maintainer
load_when: deciding or implementing the return of the compatibility policy to the public export
max_length: an approver's opening, then 1 screen
last_verified: 2026-11-08
---

# Task Contract: return the compatibility policy to the public export

`core/01-lifecycle.md` §4. Class T2 (decision 1). **Status: Approved by the Change Owner on 2026-11-08 (see Status).** Follow-up F3 of the change that removed the pilot project's name from the public export (T3, merged as MR !75; Verifier round 1 finding F3).

## Approver's opening

- **Read this first:** This asks you to approve one changed phrase in `spec/PHASE6-COMPATIBILITY-POLICY.md` and the removal of that file from the export's left-out list, so that the first GitHub publication contains the framework's compatibility and versioning policy. Your approval is on the whole contract, not on this opening alone. Nothing is pushed to GitHub by this change.
- **Problem:** The policy is left out of the public copy because one phrase in it names the pilot project. It is the only compatibility and versioning policy of the framework, so a reader who is upgrading, pinning or publishing cannot read it from the published copy, and `core/06-context-and-cost.md`, which is published, cites it.
- **The change:** In the sentence that says what is outside the compatibility promise, "<NAME> product contract" becomes "the product contract of any project that consumes the framework". Nothing else in the policy changes. The manifest stops excluding the file, the export test's pins follow, and the CHANGELOG records the change as `compatible`. BREAKING: none. The scan's pattern for the name stays and guards the file.
- **Technical details:** (1) `spec/PHASE6-COMPATIBILITY-POLICY.md` line 37, that one phrase. (2) `verification/public-export-manifest.json`: remove `spec/PHASE6-COMPATIBILITY-POLICY.md` from `exclude_files`; no other member changes. (3) `verification/tests/test_export_public_tree.py`: remove the entry from the pinned name-exclusion list and add a test that the policy is published and that the manifest's patterns do not match it. (4) `CHANGELOG.md` entry. No digest of the policy is bound anywhere (a search of the tree for its sha256 found none); the files that cite it do so by path.
- **What you need to decide:** Assumptions: the new wording keeps the sentence's meaning (a consuming project's product contract is outside the framework's compatibility promise). Out of scope: the other left-out files (the pilot profiles and the three dependent tests), any other wording in the policy, the push to GitHub. Class: T2 (a wording change to a live policy and a publication-boundary manifest entry that the scan guards). Main risk: the new wording changes the meaning of the promise; the Verifier reads the sentence against the stable-surfaces paragraph.

## Part A: Minimal

- **Intended outcome:** The published copy contains the compatibility policy, with the phrase that named the pilot project replaced by a generic one and its meaning unchanged, and the export's checks still pass.

- **Acceptance criteria** (identical to `verification/compat-policy-clause-task-contract.json`):
  1. **The clause.** The only difference between the policy at the base and at the head is that phrase of line 37; the rest of the file is byte-identical.
  2. **Published.** `spec/PHASE6-COMPATIBILITY-POLICY.md` is not in the manifest's `exclude_files`; the exported tree contains it; the manifest is otherwise unchanged.
  3. **Pins.** The export test no longer lists the file as excluded, asserts that the exported tree contains it and that no scan pattern matches it; a mutation that restores the name to the file and one that restores the exclusion are each failed by a test.
  4. **The export passes.** `python verification/export_public_tree.py --out <empty directory outside the repository> --run-tests` reports compile, exported suite, scan and byte identity as PASS; the exported tree holds the policy and, besides the files of the base tree, only this change's own records that carry no scan pattern (its contract, evidence pack, dispositions and reports); the file count and the suite count are recorded.
  5. **Links.** No published document links to a file that is not published; `core/06-context-and-cost.md`'s citation of the policy resolves in the exported tree.
  6. **No code change.** `verification/export_public_tree.py` is byte-identical to the base; no other exclusion changes.
  7. **Scope.** No change to `core/`, `KERNEL.md`, `templates/`, the preflight or `verification/run_review.py`; the CHANGELOG entry classifies the change `compatible` under the policy (wording only, no stable surface changes).
  8. **Outcome records.** Report patterns `verification/compat-policy-clause-verifier-report*.md`; dispositions file `verification/compat-policy-clause-verifier-dispositions.md`.

- **Scope:** `spec/PHASE6-COMPATIBILITY-POLICY.md`, `verification/public-export-manifest.json`, `verification/tests/test_export_public_tree.py`, `CHANGELOG.md` and this change's own records (the contract, its JSON, the evidence pack, the dispositions and the reports).

## Part B: Plan

- **Approach:** edit the phrase; remove the manifest entry; update the pins and add the publication test; run the export dry run and the existing suite; mutation-test the pins in a scratch clone; write the pack and the CHANGELOG entry.
- **Invariants touched:** the export only excludes and never rewrites a file; the scan covers every published file; the policy's stable-surfaces paragraph.
- **Evidence strategy:** the dry run with `--run-tests`; the pin test and its two mutations; a byte diff of the policy against the base showing the one phrase; the link check; the existing suite and `preflight.py --ci-like`.
- **Protected files touched:** to be confirmed with the preflight; expected none.
- **Recovery / reversal:** `git revert`; nothing is published by this change.
- **Review budget:** one preflight run and two Verifier rounds; no security layer. Accepted limit stated before review: the scan is a denylist over one spelling family, as in the export contracts.

## Classification

Proposed **T2**: one phrase in a live policy and one manifest entry that makes the file published, a file the scan guards. It cannot publish a file that carries the name.

## Decisions for the Change Owner

1. **Class.** T2 with Verifier rounds [recommended] or T3. Decided 2026-11-08: T2.
2. **Wording.** "the product contract of any project that consumes the framework". Decided 2026-11-08: approved.

## Status

- **State:** Approved
- **Established by** (author): Claude Sonnet 5.5 (Anthropic), under Implementer role, 2026-11-08
- **Approved by** (human, T2/T3 only — role: Architect): Scott Wofford (Change Owner and Architect), 2026-11-08, by his message "approved" to the proposal of class T2, two Verifier rounds and the wording above.
- **Date:** 2026-11-08
- **Class:** T2
- **Spec Confidence at intake:** Clear
