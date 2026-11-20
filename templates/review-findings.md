---
owner: framework-maintainer
load_when: lifecycle stage 9, required at T2+ and optional at T1
max_length: ranked bounded finding set plus dispositions
last_verified: 2026-10-14
---

# Review Findings

Use with `core/05-review.md`. The initial Verifier pass receives the requirement,
invariants/contracts, exact diff/head SHA, evidence boundary, and evidence pack;
it does not receive the author's rationale.

## Review identity

- **Change / MR:**
- **Reviewed head SHA / base or diff identity:**
- **Role:** Verifier | Security Reviewer
- **Layer:** Verifier | Security Review | approved optional layer
- **Instance identity:**
- **Model / tool identity:**
- **Round:** 1 | 2 (final)
- **Started / completed (UTC):**
- **Input references:**
- **Findings digest:** immutable digest over the complete finding records
- **Non-blocking finding cap:** 5, or lower value from the approved Task Contract
- **Provenance source:** non-author-controlled record or protected corroboration
- **Outcome:** PASS | PASS_WITH_ADVISORIES | BLOCKED
- **Findings complete for this round:** yes | no, with the reason

## Findings

Rank most severe first. Record at most five non-blocking findings unless the
approved Task Contract sets a lower cap. Never omit a blocking finding to meet
the cap. Preserve every identifier through disposition and re-review.

| ID | Severity | Evidence rank | Requirement / invariant / contract / boundary | Falsifying input, failing check, or citation | Blocking? |
|---|---|---:|---|---|---|
| REV-001 | | 1-4 | | | yes only for rank 1-2 / no |

## Routes tried and found closed

List the attack paths, inputs, and checks tried that did not produce a finding.
A reviewer that reports only what failed leaves the next round to repeat it.

## Dispositions

| Finding ID | Disposition | Evidence / canonical finding | Decided by role | Revision SHA | Re-review required? |
|---|---|---|---|---|---|
| REV-001 | CONFIRMED_FIXED / CONFIRMED_ACCEPTED_RISK / FALSE_POSITIVE / DUPLICATE / WITHDRAWN / SUPERSEDED / UNRESOLVED | | | | yes / no |

Author disagreement is not evidence of a false positive. Required human risk
acceptance names the authority and rationale and cannot waive a trip-wire or
class-required evidence.

## Re-review and metrics

- **Metric population / included review records:**
- **Immutable metric source references:**
- **Collector / collected at (UTC):**
- **Substantive revision count:**
- **Re-reviewed final SHA:**
- **Blocking findings raised:**
- **Confirmed blocking findings:**
- **False positives:**
- **Disagreements:**
- **Findings causing substantive revision:**
- **Escalations and outcomes:**
- **Time to disposition:**
- **Missing values:** `unknown`, never zero

If an MR's immutable history contains more than one otherwise-valid
attestation for the same required layer and round, do not edit or delete notes.
Close or supersede the ambiguous MR and use a fresh MR carrying the unchanged
reviewed commit, or another protected mechanism that yields one unambiguous
attestation set. Bind the replacement record to both MR identities.

## Records the Implementer writes

None of these records describes what a list, a diff or a report contains.

- **Authorization:** the date, the Change Owner's reply quoted verbatim, and a
  plain list of what the reply authorizes (for example a fix, or a numbered
  review round). A proposal the Implementer made is labelled as a proposal.
- **Disposition:** the columns of the Dispositions table above: finding ID,
  one disposition from `core/05-review.md` section 5, evidence, decided by role,
  revision SHA, and whether re-review is required.
- **Correction:** the statement being withdrawn, named by the section it is in
  and its opening words. A correction does not say what a list, a diff or a
  report contains; to restate a fact it points to the object that holds it.
- **Sweep:** the subject, and the search terms and files searched.
