---
owner: framework-maintainer
load_when: instantiating AIDF in a repository with existing code or governed history
max_length: 3 pages
last_verified: 2026-10-06
---

# Existing-project discovery

Outcome: a source-bound **project context pack**, not an approval of everything the repository already does. The sequence is generalized from a private pilot's own implementation experience. Product-specific pilot conclusions are not reusable precedent.

1. **Freeze entry:** identify project, exact Git source commit, protection state, active policy pin, current Task Contract, testing baseline, and owner. Confirm Spec Confidence and class. Stop on ambiguous source, missing authorization, credential need, or unapproved dependency. Do not modify historical pilot records.
2. **Generate inventory:** use a complete, non-shallow clone with the source commit present and reachable as an ancestor of the checked-out `HEAD`; shallow clones, unrelated branches, and rebased histories fail closed until the authoritative history and checkout are restored. Run `git ls-tree -r --name-only -z <source-commit>` from the project repository; record the exact commit, command and generated path list in the repository map. Do not infer a green test suite from an empty tree or stale CI badge. Declare unknown runner, deployment, runtime, and product properties.
3. **Discover the pack:** read only the paths and history needed to describe components/ownership, data flow, trust boundaries, interfaces, conventions, tests, and deployment/operational assumptions. Produce the common artifacts in `README.md`. Each durable document receives owner, load trigger, length cap, and verification date. The architecture overview is at most three pages.
4. **Separate fact from authority:** seed every incumbent pattern `PROVISIONAL`, with source evidence and scope. Record invariant enforcement truthfully (`PROSE-ONLY` when nothing runs), stable contract IDs, ADR history, and explicit context gaps. Existing code, repetition, and an expired standing authorization confer no precedent. Request Architect ratification or rejection as a distinct decision; do not self-ratify.
5. **Check and decide:** run `check_context_pack.py` on the manifest, compare generated inventory to the exact Git tree, and exercise positive/negative fixtures for every proposed mechanical rule. On Windows, use a canonical local drive-letter or canonical UNC path on a filesystem with stable file identities; substituted drives, mapped-drive aliases, unsupported volume namespaces, and unavailable identities fail closed. Protected Linux CI does not execute the Windows handle API, so record a local real-handle test run and disclose any unavailable reparse-point test before claiming Windows support. The checker proves only structural conditions. Human Architect review decides boundaries, invariant/contract commitments, pattern dispositions, and unresolved gaps. Class T3/protected-policy changes retain their separate approval and review gates.
6. **Integrate with recovery:** only after required approvals, evidence E0–E7, independent review, and protected checks are satisfied. Revert project changes through Git; rotate an immutable policy pin only under separate authority. Update context after any merge that invalidates it.

The manifest is strict JSON: `schema_version: 1`, `entry_path: "existing"`, project identifier, an exact lowercase `source_commit` whose 40- or 64-character length matches the repository's Git object format, a `repository_map` with the same commit and ordered path array, and exactly the artifact keys in `fixtures/existing-manifest.json`. The map document repeats the source commit and its inventory between `AIDF-TREE-BEGIN`/`AIDF-TREE-END` markers. Its exact inventory remains subject to the declared page cap and 128 KiB artifact limit. If the complete tree cannot fit, stop and request a governed segmented-inventory extension; truncation or summarization is forbidden. The pattern registry is a JSON table with `schema_version: 1` and bounded `entries`; `PROVISIONAL` entries have no ratifier/decision record, and `RATIFIED` entries name both. An approval record's existence is not proof of human authority.

Run locally: `python instantiation/check_context_pack.py --project-root <project-root> --manifest project-context-pack.json`. No file is generated or modified by this command. Its pass must not be described as a runtime, deployment, security-efficacy, or human-approval result.

Once the pack is in place: this playbook does not qualify any tool/model
for your project, and does not enable automatic routing. See
`instantiation/README.md`'s "After Layer 3" section for that separate,
project-specific setup.
