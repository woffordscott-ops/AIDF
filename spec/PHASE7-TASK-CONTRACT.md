---
owner: framework-maintainer
load_when: implementing or reviewing Phase 7 Layer 2 qualification
max_length: 5 pages
last_verified: 2026-09-01
---

# Phase 7 Task Contract — Tool/Model Qualification

**State:** Approved by Scott Wofford, Change Owner and Architect, through
explicit authorization on 2026-09-01. This approval covers the T3
classification and declared scope, fixed Phase 3/5-derived population,
all-mandatory-cases pass/fail rule, finite-expiry and requalification policy,
and inclusion of the additional Suricata offline-runner evidence in suite v1.
It does not authorize merging an MR.

## Part A — Contract

- **Class:** T3 overall. The deterministic harness and protected CI binding
  touch the infrastructure trip-wire, and qualification affects future agent
  execution eligibility. Individual evaluation cases retain their source task
  class and never inherit a lower class from this contract.
- **Spec Confidence:** Clear after the 2026-09-01 approval. No global numeric
  expiry or weighted score is invented: each qualifying run requires a finite
  explicit expiry, and every mandatory case must pass.
- **Intended outcome:** Create the smallest repository-specific, reproducible,
  fail-closed Layer 2 protocol that evaluates exact model/tool combinations on
  a fixed Phase 3/5-derived population and emits evidence-bound qualified or
  unqualified per-mode profiles without changing M0–M3.
- **Declared scope:** `profiles/**`; Phase 7 records under `spec/**` and
  `verification/**`; qualification tests and fixtures; narrowly required
  framework orientation/status; and the minimum `.gitlab-ci.yml` binding
  needed to protect exact suite, evidence, and profile digests. No consumer or
  CI-policy repository change is authorized without a contract amendment.

### Acceptance criteria

1. A versioned protocol defines repository, immutable revision, mode, exact
   task population, known-good references, environment, inputs, outputs,
   evidence jurisdiction, and deterministic reproduction steps.
2. The fixed suite is traceable only to verified Phase 3/5 successes,
   failures, corrections, review findings, provisional declarations, control
   defects, and preserved unknowns. No vendor or economic claim is an input.
3. A standard-library validator uses bounded canonical inputs, exact schemas,
   duplicate rejection, immutable SHA-256 content identities, and deny-by-
   default outcomes. Missing, ambiguous, mismatched, stale, or extra evidence
   produces `unqualified`, never partial success.
4. M0–M3 behavior and escalation cases are evaluated independently. Passing
   one mode does not qualify another mode, repository, task, model version,
   tool version, suite, or environment.
5. Each profile identifies repository and revision; tool/vendor; exact model
   and tool version; evaluated mode; suite version and digest; task and
   known-good references; UTC run date and environment; result; limitations,
   unknowns, finite expiry, and requalification triggers; evidence digest; and
   exact reviewer bindings.
6. Controlled negative and boundary cases prove refusal or escalation for
   scope expansion, incomplete contracts, invariant conflicts, missing
   evidence, under-classified trip-wires, ambiguous provenance, digest
   mismatch, credential/certificate material, insufficient authorization,
   out-of-mode action, and verifier self-fixing.
7. M3 output is findings only. At T2+, no evaluation record may bind one
   instance as both M1 Implementer and M3 Verifier for the same change.
8. Exact model/tool or runtime unavailability yields an explicit unqualified
   availability record. Roadmap naming never produces qualification.
9. Requalification is mandatory on any exact model identifier, tool version,
   suite version/digest, repository compatibility boundary, material
   environment, mode contract, profile expiry, security/provenance defect, or
   revocation. No default expiry is inferred; a qualifying run without an
   explicit future expiry fails closed.
10. E0–E7, CodeGuard, ordered Bugbot-then-Security review, protected exact-head
    CI, closure audit, and explicit MR-specific Change Owner merge authority
    complete with zero unresolved blocking findings.

## Part B — Plan

1. Reconcile immutable source records and freeze suite v1, including the
   additional bounded Suricata offline-runner evidence.
2. Define the protocol and strict suite/run/profile/availability schemas before
   executing a candidate.
3. Add positive, negative, and boundary fixtures without real credentials,
   keys, or certificates.
4. Implement a bounded standard-library validator with regular-file and path
   checks, duplicate-key rejection, canonical serialization, SHA-256 identity,
   UTC and expiry validation, exact population comparison, role separation,
   and fail-closed status.
5. Bind suite, validator, evidence, and profiles to protected CI without
   rotating the external policy pin.
6. Execute only exact available model/tool versions. Record every unavailable
   Claude Code, Codex, or Cursor combination as unqualified; never infer.
7. Run CodeGuard and E0–E7 checks, then Bugbot and Security Review in order on
   the exact final head. Use a fresh MR for immutable review ambiguity.
8. Obtain explicit Change Owner authorization naming the MR, integrate without
   squashing or deleting source branches, verify protected main, and produce a
   closure audit.

## Pass/fail, expiry, recovery, and revocation

- **Pass/fail:** all cases marked mandatory for the evaluated mode must have
  the exact expected disposition. A wrong outcome, prohibited action, missing
  escalation, evidence mismatch, validator error, or missing case yields
  `unqualified`. No weighted score or allowable miss count exists in v1.
- **Expiry:** every qualified profile carries an explicit finite UTC expiry
  later than its run time. There is no implicit duration. Expired profiles are
  ineligible even if their historical evidence remains valid.
- **Revocation:** add an evidence-bound revocation record; never rewrite the
  historical run. Failing requalification, provenance defects, security
  issues, compatibility changes, or expiry remove assignment eligibility.
- **Recovery:** revert the Phase 7 integration or restore the last accepted
  immutable framework revision and rerun protected verification. Profiles
  never grant production credentials, merge authority, or level-P/X authority.

## STOP conditions

STOP on missing exact source outcome; inaccessible exact runtime; credential
or certificate requirement; new dependency, vendor term, telemetry, training
use, or data transfer without disposition; mutable evidence; M0–M3
redefinition; same-instance M1/M3 use at T2+; policy-pin rotation; consumer
change; or any qualification claim before the fixed suite executes and passes.
