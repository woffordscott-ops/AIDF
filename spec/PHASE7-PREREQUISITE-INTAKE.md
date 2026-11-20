---
owner: framework-maintainer
load_when: deciding whether Phase 7 tool/model qualification may begin
max_length: 5 pages
last_verified: 2026-09-01
---

# Phase 7 Prerequisite Intake — Qualification Candidate

**Status:** Entry evidence verified where repository objects are sufficient;
implementation is blocked pending human approval of the Phase 7 Task Contract.
This record authorizes no model/tool qualification claim.

## Verified facts

- Framework protected `main` resolves to Phase 6 closure merge
  `c59da1cc1f8e683962bef0051e6fc324fd607485`.
- Phase 6 implementation merge
  `07fec47f1d0fc2af62486cc19b7b6e0ea14463a5`, reviewed implementation head
  `bc701a6892e779d34cf3e4429dbeae7d37fa01e0`, and reviewed closure head
  `7cef5aafe23e37ebd923091764e8f823b08c0847` resolve in the fetched framework
  repository. Remote branches `codex/phase6-framework-revision` and
  `codex/phase6-closure-reconciliation` resolve to the two reviewed heads.
- The fetched framework CI-policy `main` resolves to the supplied immutable
  policy commit `1f7d8cd4758372cffa59002ae5104c20dd318948`.
- The Phase 6 Task Contract, trusted evidence pack, and closure audit hash to,
  respectively, `9717ad98e1c4d77e413c452e71125c3018e5160ef080593b3d06714a7e524eeb`,
  `a4cdddf8edf18ec45c85090e581c93738110b2524997b588938fa88297b8f681`,
  and `a8482831206c2e8520e20bbc66f74bc52bf71ea813fe92fce7f9b3611de4fc9f`.
- The closure audit records implementation MR !13, closure MR !14, ordered
  Bugbot-then-Security attestations, explicit merge authority, protected-main
  pipelines #615 and #620, and preservation of source commits and branches.
  These GitLab facts are repository-record facts in this intake; they were not
  independently re-read from the GitLab API during this pass.
- The workspace root was on the older Phase 5 closure branch. Phase 7 work is
  isolated in the preserved framework worktree on branch
  `codex/phase7-tool-model-qualification`, based on the verified protected-main
  closure merge. Existing Phase 3, Phase 5, and Phase 6 work directories were
  not modified or removed.

## Repository-derived requirements

Locked specification §§6.2, 13.4, and 17 and the stable
`modes/execution-modes.md` contract require all of the following:

1. Qualification is repository-specific, exact model/tool-version-specific,
   mode-specific, and assigned per task. It is not a permanent model identity.
2. The evaluation is a fixed population of representative tasks with
   known-good outcomes and is rerun on model or tool version change.
3. Phase 3 and Phase 5 pilot evidence supplies the population. Vendor claims,
   reputation, price, speed, and subjective impressions are not evidence.
4. M0 through M3 retain their existing envelopes. Layer 2 may map tools to
   modes but may not redefine a mode or allow project automation profiles to
   widen one.
5. At T2+, the same instance may not be both M1 Implementer and M3 Verifier on
   the same change. M3 produces findings only and never fixes its findings.
6. Missing measurements remain `unknown`; a zero denominator is not success;
   small samples remain counts and do not justify an invented rate threshold.
7. Evidence settles falsifiable correctness only. Architecture decisions,
   human risk acceptance, legal disposition, protected integration, and
   level-P/X actions retain their existing authorities.
8. The harness and profiles must fail closed on absent, malformed, ambiguous,
   stale, mismatched, or incompletely reviewed evidence.

## Evidence-grounded candidate population

The following is the smallest source inventory from which a fixed suite can be
approved. Inclusion in this inventory is not yet inclusion in an executable
suite and is not a qualification result.

### Phase 3 candidates

- Ten fixed T1 architecture-only changes: controlled vocabulary; flow-owner
  invariant; policy snapshot and verdict contract; fast-path/userspace
  boundary; flow-state transitions; inspection-plugin contract;
  deployment-form invariants; overload and failure dispositions; verdict
  receipt and privacy boundary; and exit synthesis.
- Known outcomes: Changes 1–9 have exact merge and protected pipeline records
  in `aidf/phase3/change-ledger.md`; all recorded substantive-revision counts
  are zero, active human minutes are unknown, and eight known CI durations form
  a bounded population only. The later Phase 4 prerequisite record reconciles
  Change 10 through protected consumer `main` merge
  `be9f3346c9c01688cd39d59bb5f7fd802408b3d9` and passed pipeline #265; its
  reviewed source head is `0e3c2e28e76a87a0b795f1c1b4ea4e4458214870`.
- Boundary evidence: the Phase 3 calibration selected Change 5 randomly and
  Changes 4 and 9 by boundary weighting. M3 and Change Owner adjudication found
  0 of 3 under-classifications. This is an insufficient sample, not a stable
  success rate.
- Preserved unknowns include runtime implementation, deployment, performance,
  privacy efficacy, isolation, recovery, and security efficacy. Evaluation
  tasks must not manufacture answers to those unknowns.

### Phase 5 candidates

- T2 review-control change: exact framework outcome
  `cf397f604d602153285653086cfb0911116cd123`, protected-main pipeline #368.
- T3 protected review-provenance control: exact policy outcome
  `89776b1aecfa38f8b2466d8b1f35b224471aec69`, with MR #330 and main #331.
- Four fixed T2 consumer outcomes: firewall/NAT contract at
  `084e6aae764352fce400b18b0b106553b10f2b7c`; policy compiler/simulator at
  `83dfa4453efcb254bf2dcef10b3e6bd40e2c5a22`; engine-neutral IPS adapter at
  `26ba342e22468eec1b6410041919dbd460dd8926`; and Suricata/Snort evaluation at
  `eaa92d2cd9dc8902d766a51e17b7c1d00bc7f28b`.
- Additional bounded evidence: the Suricata offline runner at
  `526de28a54f56d51f211a5cb42aafb6d6e68bc28` is explicitly outside the Phase 5
  fixed four-change population and may only be included in Phase 7 through an
  explicit population decision.
- Confirmed failure/correction material: MR !16 retained non-conforming review
  rounds 3 and 4 because the protected verifier accepted any positive round;
  the later guardrail restricts rounds to 1–2. Ambiguous immutable review
  history was recovered through fresh MRs rather than deletion. Both are
  required falsification cases.
- Review precision, disagreement count, finding-driven revisions, false
  positives, disposition time, human minutes, and model/tool cost are unknown.
  They cannot supply qualification thresholds.
- Product, deployment, 10-Gbit/s, security-efficacy, ruleset, and final GTM
  license conclusions remain outside the known-good outcome boundary.

## Required controlled negative and boundary behaviors

Every approved mode suite must test the cases applicable to that mode: scope
expansion; incomplete Task Contract; invariant conflict; absent evidence;
under-classified trip-wire; ambiguous provenance; digest or immutable-evidence
mismatch; credential, private-key, or certificate material; insufficient
authorization; attempted action outside the assigned mode; and an M3 verifier
attempting to fix its own finding. Expected behavior is refusal, bounded
finding, or STOP → DECLARE → ESCALATE as defined by the stable mode and
authority contracts—never silent continuation.

## Unresolved questions

1. The locked material defines a fixed known-good evaluation but does not
   specify a numerical score, allowable miss count, expiry duration, or minimum
   number of tasks per mode. These values remain `unknown`.
2. Complete immutable source bindings for each selected task, including its
   Task Contract, input set, expected output, and reviewed evidence digest,
   must be reconciled before suite lock.
3. The available records do not identify exact Claude Code, Codex, or Cursor
   model/tool versions that can be executed in a reproducible environment.
4. No approved retention or disclosure decision yet covers third-party model
   prompts, outputs, telemetry, training use, or vendor data transfer for the
   qualification runs. Any such transfer triggers legal and security review.
5. It is not yet decided whether the additional offline-runner task belongs in
   version 1 of the fixed population.

## Decisions requiring human authorization

- Architect and Change Owner approval of the Phase 7 T3 Task Contract,
  including the fixed population, pass/fail semantics, expiry, and
  requalification rules, before harness or profile implementation.
- Legal and Security disposition before sending repository content to any new
  vendor service or accepting third-party evaluation content or terms.
- Approval of any new dependency, image, license, protected-policy change, or
  external runtime credential.
- Explicit Change Owner authorization naming the eventual Phase 7 MR before
  integration. No approval in this intake authorizes a merge.
