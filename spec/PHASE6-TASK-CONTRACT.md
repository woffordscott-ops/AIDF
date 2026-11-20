---
owner: framework-maintainer
load_when: implementing, reviewing, or closing the approved Phase 6 revision
max_length: 6 pages
last_verified: 2026-09-01
---

# Phase 6 Task Contract — Evidence-Grounded Framework Revision

## Contract

- **Status:** Approved.
- **Class:** T3.
- **Declared trip-wire:** `infrastructure` because the protected governance job
  changes its contract/evidence inputs. No runner, image, network, IAM, or
  deployment setting changes.
- **Spec Confidence:** Clear.
- **Version:** AIDF framework `v1.3.0`; locked V1.2.2 remains the immutable
  historical specification baseline.
- **Human-involvement profile:** `checkpointed`. Mandatory legal, security,
  provenance, architecture, Task Contract, and T3 merge gates remain intact;
  T3 is never eligible for automatic merge.
- **Intended outcome:** Produce the smallest coherent framework revision
  supported by Phase 3 and Phase 5 evidence; simplify low-value ceremony
  without lowering assurance; re-baseline measurable metrics while preserving
  unknowns; and define compatibility, migration, and recovery boundaries.

## Acceptance criteria

1. Every retained, changed, or deleted behavior maps to pilot evidence, a
   locked requirement, or an explicit human architectural decision.
2. Gross and net reduction are reported. The 20–30% roadmap expectation is a
   hypothesis, not a quota that overrides safety or completeness.
3. Trip-wires, declared scope, T2/T3 approval, legal/dependency gates,
   Bugbot-before-Security ordering, exact-SHA provenance, immutable history,
   and fail-closed behavior remain at least as strong as the baseline.
4. Credential separation, least privilege, pinned-CA HTTPS, strict certificate
   validation, authorization, bounded parsing, immutable pins, and recovery
   evidence are unchanged or strengthened.
5. Phase 3/5 metrics name sources, denominators, populations, and unknowns.
   Claims remain within evidence jurisdiction.
6. A compatibility policy defines stable surfaces, breaking changes,
   migration, supported versions, deprecation, and rollback/reapplication.
7. Each invariant or gate change has an ADR. Any license, contribution,
   trademark, certification, distribution, commercial-claim, or third-party
   content decision receives legal disposition before inclusion.
8. E0–E7, applicable static/security checks, counterfactuals, negative and
   boundary fixtures, migration/recovery evidence, and CodeGuard review pass on
   the exact final head.
9. Bugbot completes first; Security Review starts afterward. Both bind the
   exact project, MR, base/head SHAs, round, pipeline, evidence digest, and zero
   unresolved findings.
10. Consumer or protected-policy changes require a separate approved scope and
    explicit merge authorization; they are not authorized by this contract.

## Exact declared scope

- `CHANGELOG.md`
- `.gitlab-ci.yml`
- `IMPLEMENTATION-STATUS.md`
- `KERNEL.md`
- `README.md`
- `core/01-lifecycle.md`
- `core/02-authority.md`
- `core/04-verification.md`
- `core/05-review.md`
- `metrics/README.md`
- `metrics/classification-audit.md`
- `metrics/definitions.md`
- `templates/evidence-pack.md`
- `templates/review-findings.md`
- `templates/task-contract.md`
- `verification/aidf_check.py`
- `verification/policy.json`
- `verification/tests/**`
- `verification/fixtures/**`
- `verification/phase6-friction-ledger.md`
- `verification/phase6-task-contract.json`
- `verification/phase6-evidence-pack.json`
- `verification/phase6-review-findings.md`
- `verification/phase6-closure-audit.md`
- `spec/PHASE6-PREREQUISITE-INTAKE.md`
- `spec/PHASE6-TASK-CONTRACT.md`
- `spec/PHASE6-COMPATIBILITY-POLICY.md`
- `spec/adr/phase6-*.md`

The locked `spec/AIDF-v1.2.2-design-proposal.md` is read-only. Consumer,
policy, deployment, runtime firewall/IPS, performance qualification, licensing,
and commercial launch are excluded.

## Ordered plan

1. Build a source-bound friction ledger and preserve missing data as unknown.
2. Propose each simplification with before/after control and evidence mapping.
3. Define compatibility, migration, deprecation, and recovery policy and ADRs.
4. Implement only approved, in-scope revisions with counterfactual fixtures.
5. Produce E0–E7 and complete CodeGuard review on the exact final head.
6. Run Bugbot, disposition its findings, then run Security Review.
7. Request explicit human merge authorization naming the Phase 6 MR.
8. Preserve commits and branch; verify protected `main`; reconcile closure.

## Stop conditions

Stop on a percentage-driven control deletion, unsupported conversion of unknown
to zero, weakened security/provenance/recovery behavior, unapproved legal or
dependency decision, scope expansion, immutable-history alteration, or more
than two review rounds. Escalate unresolved matters to the Change Owner.

## Approval record

- **Approved by:** Scott Wofford, human Change Owner and Architect
- **Approval date:** 2026-09-01
- **Approval reference:** user authorization in the originating Codex task
- **T3 merge approval:** separately required for the exact final MR
- **Pinned CI dependencies:** the existing Python, Git, Trivy, and Trivy DB
  digests remain unchanged; the Phase 6 authorization binds their exact values
  and the resulting `.gitlab-ci.yml` content digest recorded in the JSON Task
  Contract. No new dependency or license is introduced.
