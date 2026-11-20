---
owner: framework-maintainer
load_when: implementing Phase 5 after its Task Contract is approved
max_length: 3 pages
last_verified: 2026-08-24
---

# Phase 5 Implementation Brief — Review Control and T2/T3 Pilot

**Authority:** Approved by Scott Wofford, Change Owner and Architect, on
2026-08-24. Work is authorized only within
`spec/PHASE5-TASK-CONTRACT.md`.

## Governing sources

Locked `spec/AIDF-v1.2.2-design-proposal.md`, especially §§7, 8, 10, 11, 13,
and 17; accepted Phase 1/2 artifacts; the closed private Phase 3/4 evidence;
`spec/PHASE5-PREREQUISITE-INTAKE.md`; and the approved Task Contract. The locked
specification wins over this brief.

## Delivery order

1. Implement `core/05-review.md` before any T2/T3 pilot implementation.
2. Make the review-finding template operational and activate precision metrics.
3. Run CodeGuard, local verification, and a separated Bugbot review for that
   T2 framework change; do not claim CI enforcement yet.
4. In a separate T3 change, test GitLab 17.3 least-privilege metadata access,
   then implement external review attestations and the protected provenance
   gate. Stop if the test fails and no non-author-controlled alternative is
   approved.
5. Rehearse stale-policy rejection and current-policy reapplication before the
   immutable consumer pin is rotated.
6. Run the four T2 consumer changes in their fixed order, each with its own Task
   Contract, E0-E6 evidence, separated Bugbot/Verifier, human approval points,
   and protected pipeline.
7. Exercise STOP, DECLARE, and ESCALATE if they have not occurred naturally.
8. Calibrate review precision and classification, then reconcile exact commits,
   jobs, approvals, recovery evidence, and unknowns at closure.

## Review implementation constraints

- Clean-room review begins from requirement, invariants/contracts, diff, and
  evidence boundary—not the author's rationale.
- Bugbot acts as the Verifier layer. At T3, a distinct Security Reviewer follows
  Bugbot and independently evaluates trust boundaries and attack paths.
- Every required review names its role and instance, reviewed head SHA, input
  set, start/completion time, findings digest, and outcome.
- Review artifacts are untrusted until a non-author-controlled source or
  protected corroboration establishes provenance.
- A substantive change to behavior, contract, tests, architecture, security
  posture, acceptance criteria, dependencies, or recovery evidence triggers
  re-review. Mechanical merge-base refreshes require re-binding to the final SHA
  but need not create a new substantive round when the reviewed diff is proven
  identical.
- No finding disappears. Every finding reaches an explicit disposition and
  preserves its history.
- Review completion is a gate result, not an adjective or summary.

## Security and supply-chain constraints

- No credential, token, private key, certificate, or reviewer secret enters a
  repository, artifact, fixture, URL, or log.
- Use `CI_JOB_TOKEN` only if the required read-only metadata is available with
  least privilege. Never weaken the project allowlist to bypass a failed check.
- Treat MR notes, names, timestamps, identifiers, and finding content as
  untrusted input: bound size, parse strictly, reject duplicates/ambiguity, and
  sanitize diagnostics.
- Pin and integrity-check images, tools, engines, rulesets, and PCAP corpora.
  New dependencies and licenses require human approval.
- Never represent image scanning, signature matching, or a successful review as
  proof of product security efficacy.

## Pilot product boundary

The T2 changes may define and simulate stateful IPv4/IPv6 firewalling, NAT, and
detect/prevent IPS contracts. They may compare Suricata and Snort offline. They
may not attach to live interfaces, deploy Kubernetes resources, mutate host
networking, process production traffic, or claim 10-Gbit/s fitness.

Suricata is the first adapter/evaluation target; Snort remains the comparator.
That preference is conditional on license approval and later Kubernetes/virtual
performance evidence. Missing performance or licensing evidence is `unknown`,
not a failing or passing value.

## Acceptance evidence

- Relevant local tests and static/security checks actually run and pass.
- The complete diff is reviewed against applicable CodeGuard rules.
- Required separated reviews are completed in order and bound to the final SHA.
- Protected pipelines prove the applicable gates for the exact reviewed commit.
- Every skipped or unavailable check and every retained unknown is named.
- Phase 3/4 paths remain unchanged.
