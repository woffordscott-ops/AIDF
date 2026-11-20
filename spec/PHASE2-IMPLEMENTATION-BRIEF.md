---
owner: framework-maintainer
load_when: implementing Phase 2 after its Task Contract is explicitly approved
max_length: concise implementation assignment
last_verified: 2026-08-20
---

# Phase 2 Implementation Brief — Verification Spine

**Authority:** Approved by Scott Wofford, Change Owner, on 2026-08-19; immutable-policy fail-closed recovery semantics amended and approved on 2026-08-20. Work is authorized only within the boundary and stop conditions below.

## Governing sources

Locked `spec/AIDF-v1.2.2-design-proposal.md`, especially §§10, 13, 15, and 17; accepted Phase 1 artifacts; `spec/PHASE2-PREREQUISITE-INTAKE.md`; and `spec/PHASE2-TASK-CONTRACT.md`. The locked specification wins over this brief.

## Concrete implementation boundary

Phase 2 builds only:

1. `core/04-verification.md`, including evidence jurisdiction, E0–E7, counterfactual mechanisms and exemptions, test-integrity rules, class-aware evidence packs, and all three §10.4.1 recovery forms.
2. Operational updates to the existing evidence-pack and exemption templates without adding evidence fields above a class's required level.
3. `metrics/definitions.md` for the six base metrics plus conditional review-finding precision, with crude collection methods, ownership, and cadence.
4. `metrics/classification-audit.md` for the 3-of-20 audit and separate Phase 3 calibration audit.
5. GitLab-compatible mechanical checks for:
   - counterfactual-evidence record completeness;
   - declared scope against the Task Contract;
   - trip-wire detection and forced T3 declaration;
   - dependency additions/changes and approval evidence;
   - secret scanning;
   - assertion/coverage delta as an inspection trigger only.
6. Automated positive/negative fixtures for every checker, pipeline enforcement evidence, and a rehearsed Git revert path.
7. Minimal status/orientation updates needed to state what is implemented versus operationally enforced.

Phase 2 does **not** build architecture/invariant lint, the architecture/context pack, pattern ratification, cross-agent review, dashboards, model/tool qualification, generalized project onboarding, production deployment controls, or general long-running agent autonomy. It does not run the Phase 3 8–12-change pilot.

## Design constraints

- Prefer repository-native, deterministic checks with no network dependency. Pin and integrity-check any unavoidable CI dependency.
- Never store credentials, private keys, certificates, tokens, or real secret samples in the repository. CI credentials are repository-scoped, masked/protected, and unavailable to untrusted jobs.
- No checker may treat green tests as proof of intent, architecture quality, or acceptable risk.
- A repository with no product suite records E2 as unavailable/narrow; it must not manufacture a passing E2 signal.
- Every blocking rule must identify the exact failed condition and the remediation path. Advisory checks must not masquerade as gates.
- Enforcement logic must fail safely on malformed or missing governance input. It must not silently downgrade a task class or evidence requirement.
- Agent jobs may be bounded and unattended; any human gate pauses safely. General checkpoint/resume orchestration remains out of scope.
- NIST CSF/SSDF references may annotate security intent, but Phase 2 makes no certification claim.

## Delivery order

1. Verify and record GitLab repository, runner, branch-protection, required-check, and revert capability.
2. Finalize schemas and verification semantics.
3. Implement local checkers with falsifying fixtures.
4. Add GitLab pipeline jobs with least privilege and deterministic dependencies.
5. Prove each gate blocks its negative fixture and accepts its positive fixture.
6. Exercise a thin integration branch against the approved pilot without beginning Phase 3 work.
7. Rehearse revert/reapply and update the implementation-status ledger with evidence-backed enforcement status.

## Acceptance evidence

- Relevant local tests and static/security checks pass.
- Each CI control has a captured failing case and corrected passing case.
- Required checks actually block a test merge request.
- Direct-to-protected-branch behavior matches the recorded policy.
- The active external-policy rollback produces the approved observable prior-policy behavior, including fail-closed rejection when immutable trust records are incompatible, and reapplication restores the current mechanical and security checks.
- Full resulting diff is reviewed against CodeGuard hardcoded-credential, certificate, cryptography, CI/CD, supply-chain, and authorization/least-privilege rules.
- Any skipped check, unsupported GitLab feature, or residual gap is named; no unsupported feature is described as operational.

## Stop conditions

Stop and escalate if the locked spec conflicts with implementable GitLab behavior; required-check enforcement is unavailable; the runner would require production credentials or broad cloud authority; a check cannot be made falsifiable; the pilot would require production impact; or implementation would cross the declared boundary.
