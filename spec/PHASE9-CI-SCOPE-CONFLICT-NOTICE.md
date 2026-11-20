---
owner: framework-maintainer
load_when: resolving the Phase 9 agent-routing MR's scope/tripwire/dependency conflict
max_length: 1 page
last_verified: 2026-09-30
---

# Conflict Notice — Phase 9 routing MR vs. CI-governance scope/class rules

Filed 2026-09-30 during formal accepted-substitute review of MR !22. Work on
`spec/AGENT-ROUTING-TASK-CONTRACT.md` STOPPED here rather than forcing a fix
past a real mechanical rule conflict.

- **Invariant / contract in conflict:** `verification/aidf_check.py`'s
  `check_tripwires` — any changed file matching a `tripwire_paths` pattern
  (`verification/policy.json` maps `.gitlab-ci.yml` to id `infrastructure`,
  the same blunt, deliberate rule that already makes
  `verification/phase8-ci-governance-task-contract.json` a standing T3
  contract) mechanically forces the governing Task Contract to class T3.
  `check_scope` separately requires every file in a diff to match some
  pattern in the *same* contract's `declared_scope` — there is no
  cross-contract "governed elsewhere" exemption in the code as written.
- **What the task requires:** `spec/AGENT-ROUTING-TASK-CONTRACT.md` (T2)
  needed `.gitlab-ci.yml` and `phase8-ci-governance-task-contract.json`
  edited to wire `agent_routing_check.py` into the existing mypy/py_compile
  CI gates — explicitly authorized by Scott Wofford, Change Owner
  ("1 & 3, unblock the gates"), and bundled into the same branch/MR as the
  rest of the T2 routing work at his direction.
- **Why they are incompatible:** Declaring those two files in scope (required
  for `check_scope` to pass) triggers the `infrastructure` tripwire, which
  mechanically requires class T3 — but the routing contract is T2 and
  satisfies none of T3's requirements (no genuinely distinct third Security
  Reviewer instance has reviewed this work; no E7 recovery evidence; no
  `security_evidence` block with a pinned artifact digest). `check_dependencies`
  additionally requires the routing contract to independently re-approve all
  five of `.gitlab-ci.yml`'s pinned dependencies in its own
  `dependency_changes`. Verified by actually running `aidf_check.py
  scope/tripwires/dependencies` locally against the real MR diff
  (`c6fa9bd..73eab30`), not asserted.
- **Options:**
  1. **Split.** Move the `.gitlab-ci.yml` / CI-governance-contract edits off
     this branch into their own small change governed solely by
     `phase8-ci-governance-task-contract.json` (already T3, already scoped
     for exactly this file — it exists for precisely this purpose). The
     routing contract stays T2; its own scope/tripwire/dependency checks
     never need to touch CI files. Cost: git-history surgery to separate an
     already-committed, already-reviewed change; requires a fresh review
     round on the split-out state.
  2. **Escalate.** Add the two files to the routing contract's scope and
     `dependency_changes`, reclassify T2 → T3, and complete the outstanding
     T3 requirements. Cost: substantial new work (a genuine separate
     Security Reviewer instance, E7, pinned security evidence) disproportionate
     to routing's actual risk profile — none of T3's real triggers
     (auth/crypto/destructive-data/irreversibility) apply to the routing
     logic itself, only the incidental CI touch does. Risk: sets precedent
     that any future low-class contract touching CI wiring even trivially
     inherits T3, diluting what T3 is meant to signal.
  3. **Unresolved, open for review:** is there a cleaner mechanism this
     tooling doesn't yet have — e.g., running `scope`/`tripwires`/
     `dependencies` per contract against a *subset* of a shared MR diff,
     rather than requiring one contract to cover 100% of it? No such
     mechanism exists in `aidf_check.py` as written (`check_scope` iterates
     the full `changed_files` argument unconditionally). If one should
     exist, that changes the calculus and is itself a design question, not
     a quick fix.
- **Recommendation (mine, not yet independently checked):** Option 1 —
  `phase8-ci-governance-task-contract.json` exists specifically to isolate
  CI-enforcement-layer risk from unrelated feature work, and this is exactly
  that case. But I both implemented the CI change and diagnosed this
  conflict, which is the self-review problem this framework exists to avoid
  — hence filing this rather than resolving it myself.
- **Escalated to:** Architect / Change Owner (Scott Wofford), explicitly
  requesting independent cross-model consensus before deciding.
- **Resolution:** Split (Option 1), with a correction to the initial framing from independent cross-model review (Codex, Cursor's Grok): the extracted CI change gets its **own** new, dedicated T3 Task Contract — `phase8-ci-governance-task-contract.json` is a closed historical record (`phase8-ci-governance-scope-fix-v1`, approved 2026-09-02) and was not a valid reuse target. Splitting narrows the T3 obligation to the CI edit itself; it does not discharge it — genuine T3 evidence (a real Security Reviewer pass, recovery evidence, pinned security evidence) is still required for that separate change. Executed: `.gitlab-ci.yml` and `verification/phase8-ci-governance-task-contract.json` reverted to their pre-Item-1 content on `codex/phase9-governance-records`, leaving all reviewed routing code byte-identical; `aidf_check.py scope/tripwires/dependencies/secrets` all verified passing against the real post-revert diff. The routing Task Contract stays T2 and no longer references either file. See `spec/AGENT-ROUTING-TASK-CONTRACT.md`'s Status, "Item 1 retracted and split out, 2026-09-30."
- **Date opened:** 2026-09-30. **Date resolved:** 2026-09-30.

Silence is not consent. Implementation does not resume, and does not
degrade to "best effort," until this is resolved.
