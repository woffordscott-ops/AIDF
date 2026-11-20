---
owner: framework-maintainer
load_when: implementing or reviewing the approved Phase 5 T2/T3 pilot
max_length: 4 pages
last_verified: 2026-08-24
---

# Phase 5 Task Contract — Review Control and T2/T3 Pilot

## Part A — Contract

- **Class:** T3 overall. The phase includes protected CI-policy and immutable
  pin changes. Each pilot change retains its own confirmed class.
- **Spec Confidence:** Clear.
- **Intended outcome:** Implement the locked V1.2.2 cross-agent review control,
  activate review-finding precision, and run four real structural T2 changes
  plus exactly one T3 review-provenance control in the private GitLab pilot.
- **Acceptance criteria:**
  1. `core/05-review.md` implements locked §§7, 8, 11, 13, and 17 without
     modifying the locked specification.
  2. T2 requires an Implementer and a distinct Verifier instance. T3 requires
     distinct Implementer, Verifier, and Security Reviewer instances.
  3. Bugbot acting as Verifier completes before Security Review starts; neither
     substitutes for the other.
  4. Findings are falsifiable, severity-ranked, dispositioned, bound to an
     exact head SHA, and invalidated by applicable substantive revision.
  5. Review-finding precision, disagreement, substantive revision,
     false-positive, re-review, and escalation outcomes are recorded without
     inferring missing values as zero.
  6. A protected non-author-controlled gate rejects missing, self-authored,
     reordered, stale-SHA, substituted, or unresolved required reviews.
  7. The pilot completes four approved T2 changes with E0-E6 and exactly one
     approved T3 change with E0-E7, recovery, and security evidence.
  8. STOP, DECLARE, and ESCALATE are exercised naturally or through controlled
     non-product fixtures that do not alter locked decisions or pollute review
     precision.
  9. Phase 3 and Phase 4 artifacts remain unchanged, and their invariants,
     contracts, and ratified patterns remain preserved.
- **Declared scope:** reusable review guidance and templates; review metrics;
  Phase 5 planning/evidence records; narrowly required framework orientation;
  the protected external review-provenance policy and consumer immutable pin;
  and the four approved consumer T2 changes.

## Part B — Plan

### Ordered change population

1. **T2 — Review control:** durable Phase 5 records, `core/05-review.md`, review
   findings/disposition schema, precision definitions, and orientation/status.
2. **T3 — Review provenance:** least-privilege GitLab metadata feasibility,
   non-author-controlled attestations, protected policy enforcement, immutable
   pin rotation, fail-closed recovery rehearsal, and security evidence. This is
   the phase's exactly-one T3 specimen.
3. **T2 — Stateful dual-stack firewall/NAT contract:** IPv4/IPv6 flow state,
   rule precedence, NAT tuple semantics, failure dispositions, and E6 contract
   evidence; no live enforcement.
4. **T2 — Deterministic policy compiler/simulator:** canonical rules,
   state/NAT simulation, conflict rejection, and counterfactual fixtures; no
   kernel or network mutation.
5. **T2 — Engine-neutral IPS adapter:** detect/prevent, request/verdict/event,
   overload/timeout/health, capability, and provenance contracts; no live
   engine process is required.
6. **T2 — Suricata/Snort evaluation and ADR:** digest-pinned offline inputs,
   a fixed PCAP corpus, comparable criteria, licensing/dependency analysis, and
   a bounded Suricata-first decision that retains deployment and performance
   unknowns.
7. **M3 — Calibration and closure:** review precision, disagreements,
   substantive revisions, escalation outcomes, classification calibration,
   exact protected evidence, and retained unknowns.

### Invariants and authority

- Locked AIDF V1.2.2 is authoritative and unmodified.
- Evidence, architectural judgment, and human risk acceptance retain separate
  jurisdiction.
- Green checks never approve scope, architecture, licensing, or risk.
- T2/T3 plans and contracts require human Architect approval before
  implementation; that approval was given on 2026-08-24.
- New dependencies and license decisions require separate human approval.
- T3 integration requires explicit human Change Owner approval after evidence
  and separated reviews.
- Infrastructure execution and immutable-pin changes retain their required
  human authority. Approval of this plan does not transfer credentials or
  execution identity to an agent.

### Evidence strategy

- T2 changes require E0-E6: build/static evidence within jurisdiction,
  existing suite, counterfactual evidence, criterion traceability, negative and
  boundary cases, contract diff, invariant checks, and explicit reasoning for
  prose-only invariants.
- The T3 policy change requires E0-E7 plus security evidence, including API
  denial/error cases, untrusted-note parsing, identity and ordering checks,
  stale-SHA rejection, observability, kill switch, and recovery evidence.
- Review evidence must be external to or independently corroborated against the
  author-controlled branch. Branch-authored role labels alone are circular.
- Prompt statements and conversation records establish intent and approval but
  do not prove a pipeline, review, test, performance, or deployment result.

### Recovery

The review-control and T2 artifacts are reversible through ordinary Git revert
before any product deployment exists. The T3 policy change uses the reversible
form: retain the last accepted policy SHA, demonstrate fail-closed rejection,
measure restoration/reapplication, expose a named failing job and reason, and
account explicitly for unrecoverable effects. No compatible-green stale-policy
result is required.

## Exclusions and stop conditions

Excluded from Phase 5: modifying Phase 3/4 artifacts; live packet enforcement;
eBPF attachment; host, CNI, IAM, or Kubernetes topology mutation; production
traffic; production NAT; a 10-Gbit/s qualification claim; formal compliance or
security-efficacy claims; and commercial distribution.

STOP and escalate on: unverifiable reviewer identity; unavailable
least-privilege metadata with no approved alternate issuer; ambiguous
state/NAT semantics; live or privileged networking; a new dependency or license
without approval; an affected invariant outside approved scope; evidence above
its jurisdiction; inability to recover the protected policy; or any attempt to
count work outside the fixed population.

## Status

- **State:** Approved
- **Approved by:** Scott Wofford, Change Owner and Architect
- **Approval date:** 2026-08-24
- **T3 merge approval:** still required after evidence and separated reviews
- **Implementation authority:** granted only within this contract
