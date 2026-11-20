---
owner: framework-maintainer
load_when: lifecycle stage 9, any T2/T3 change, or review calibration
max_length: 6 pages
last_verified: 2026-11-04
---

# 05 — Independent Review

Operational rules for locked V1.2.2 §11. Review is a supporting control under
the evidence ladder, not a substitute for executable evidence, architectural
judgment, or human risk acceptance.

## 1. When review is required

- T0: no independent review.
- T1: optional. Running any layer activates review-finding precision.
- T2: a Verifier distinct from the Implementer is mandatory.
- T3: Implementer, Verifier, and Security Reviewer are three distinct
  instances. At least one reviewer derives context independently.

At every team size, including one human, required separation is between
reasoning instances. A human wearing several role labels, author self-review,
strong tests, or a second pass by the same instance does not satisfy it.

## 2. Required ordering and inputs

The Implementer completes the class-required evidence before required review.
The Verifier performs this review. For T3, the Verifier must complete and its
findings must be dispositioned before the distinct Security Reviewer begins.
Security Review does not replace the Verifier and the Verifier does not
replace Security Review.

The initial clean-room Verifier receives:

1. requirement and executable acceptance criteria;
2. confirmed class and evidence boundary;
3. affected invariant and contract identifiers;
4. the exact diff and head SHA; and
5. the evidence pack and executing checks.

It does not receive the author's rationale before forming findings. A second
pass may read the Task Contract to detect contract-to-implementation drift.

The Security Reviewer receives the same final-SHA inputs plus the security
model, trust boundaries, data classification, dependency posture, recovery
model, the Verifier's findings, and their dispositions. Seeing the Verifier's
output does not permit adopting its conclusions without an independent
attack-path analysis.

### Complete findings in one pass

A review round reports every finding the reviewer can establish, not the first
blocking one, and lists the routes it tried and found closed. A later round
that raises a finding the earlier reviewer could have established dispositions
it with the note "late", and it is not a new defect class. The cap of section 4
on non-blocking findings still applies: a reviewer with more records the excess
as one finding that names each of them, so none is dropped silently.

### Review budget

The Task Contract declares a review budget: the number of Verifier rounds and,
at T3, Security rounds the change expects. The default is two Verifier rounds at
T2, and two Verifier and two Security rounds at T3. A contract that declares no
budget keeps the two-round maximum of section 5. A declared budget is at most
two rounds per layer; the human decision of section 5 follows it. A pre-check
(below) is not a round. Section 5 says what happens when the last budgeted round
does not pass.

The Change Owner may pre-authorise the decision of section 5 in the approved
Task Contract: up to two further rounds per layer, after the layer's last
budgeted round, naming the layer and the number (for a budget of two, four rounds
of that layer in all). A pre-authorisation is a human decision recorded in
advance, not a larger budget. The default and the maximum of a declared budget
stay at two rounds per layer, the cap of locked V1.2.2 section 11.3 stays, and a
contract without a pre-authorisation is unchanged. Section 5 gives the condition
each pre-authorised round must meet.

### Controls that enumerate

A control that detects by listing known-bad shapes (a static scan, a blocklist,
a pattern match over source) cannot be shown complete. Such a control is
accepted as evidence only if it is closed (it allows a fixed vocabulary and
refuses the rest), or if the property it protects is also enforced by a check
that does not depend on the list, such as an observed runtime property. A
reviewer-demonstrated bypass of an enumerating control is one finding against
the control's design. Its fix closes the class; adding the demonstrated shape
alone is not a fix, though the shape is kept as a regression test. A fix round
should be preceded by the Implementer's own attack on the control using
computed names, indirection, and introspection, so the reviewer does not
discover the next shape.

### Corrections and the pre-check

After any correction to a sentence of the evidence pack or the dispositions,
the Implementer searches the whole pack and the dispositions for every other
sentence on the same subject, including a sentence that points into text the
correction removed, and records in the dispositions what was searched. Section 6
governs which changes made after a review the review still covers: a corrected
pack sentence is not an outcome record, and the record of the sweep is an
append to the dispositions. No gate checks the sweep; a reviewer who finds a
surviving sentence on the same subject reports it as a finding.

Before a formal review round, a pre-check may be run: a separate instance with
no access to the Implementer's reasoning checks each sentence of the pack
against the test, file, command or report the sentence names, and lists the
sentences that are false, overbroad, dangling or in the future tense. The
pre-check is not a review layer, is not counted as a round, and never satisfies
section 7. An instance that ran a pre-check is not thereby a Verifier or a
Security Reviewer; if it later serves in either role, section 3 applies to it
as to any other instance. When a pre-check is run, an append to the dispositions
records that it was run and what the Implementer changed because of it.

## 3. Review identity and provenance

Each review record must contain:

- change and merge-request identifier;
- reviewed commit SHA and diff/base identity;
- role and distinct instance identifier;
- model/tool identity when available;
- review layer and round;
- start and completion timestamps in UTC;
- exact input-set references;
- findings digest and complete finding records; and
- outcome: `PASS`, `PASS_WITH_ADVISORIES`, or `BLOCKED`.

Repository records, instance labels, and prose are claims, not provenance. A
required gate must obtain the record from a non-author-controlled source or
corroborate it against protected external metadata. The Implementer must not be
able to manufacture, replace, reorder, or backdate a required review. Missing,
ambiguous, duplicate, malformed, stale-SHA, or unverifiable records fail closed.

When immutable history contains multiple otherwise-valid attestations for the
same required layer and round, remediation must preserve that history. Use a
fresh MR carrying the unchanged reviewed commit, or another protected mechanism
that produces one unambiguous attestation set and links the superseded record.
Editing or deleting review notes to make a verifier pass is prohibited.

## 4. Findings and severity

A finding names one affected requirement, invariant, contract, or trust
boundary and one falsifiable basis. Findings are ranked by evidence:

1. reproducible failing case;
2. cited invariant or contract violation;
3. cited standard or convention;
4. reasoned opinion.

Severity is separate from evidence rank:

- **Critical:** credible path to severe compromise, irrecoverable effect, or
  uncontrolled high-consequence behavior.
- **High:** requirement, invariant, contract, recovery, or material security
  failure.
- **Medium:** concrete defect or evidence gap with bounded impact.
- **Low:** bounded improvement.
- **Informational:** observation with no requested revision.

Adjectives, confidence, model reputation, and severity alone do not make a
finding falsifiable. Rank 1 wins automatically. Rank 2 wins unless the cited
record is proven inapplicable. Only rank-1 and rank-2 findings may block. Rank-3
and rank-4 findings are advisory by definition regardless of severity; at T2+
an unresolved advisory finding escalates to the Change Owner. Each review is
limited to five non-blocking findings unless the approved Task Contract sets a
lower cap. Blocking findings are never omitted to meet that cap.

### Findings about record text

A finding whose only subject is narrative, a count or history in an evidence
pack or a dispositions file is advisory, whatever its rank. It is not dropped:
it is dispositioned by an append to the dispositions file that names the
sentence and the correct fact, and it does not start a new round. The append is
made before merge. The pack sentence stays as reviewed, because a corrected pack
sentence is not an outcome record (section 6). The append settles the
finding without a new round only if the contract declares outcome records
(section 6); otherwise the append changes the head and section 7 applies. Four kinds of
record finding still block: a sentence that overstates a guarantee a consumer
relies on; a required artifact, rehearsal or acceptance that is missing; a
SHA, digest or hash that a gate or a consumer uses and that is wrong; and a
record that contradicts the code or tests it describes. A hash, SHA or named
test that `verification/pack_facts.py` verifies is not argued in
review. The rule narrows nothing for code, tests or security posture.

## 5. Disposition and false positives

Every finding retains its identifier and history and receives exactly one final
disposition:

- `CONFIRMED_FIXED` — evidence shows the defect and its correction;
- `CONFIRMED_ACCEPTED_RISK` — a human with applicable authority accepts a
  named, scoped residual risk and records the reason; at T3 the record names
  the residual and its scope. This never waives required evidence and never
  accepts a rank-1 behavior defect that has a reproducing case. Accepting a
  named residual is not a waiver of a control (`core/02-authority.md` section 1);
- `FALSE_POSITIVE` — cited evidence demonstrates the finding did not apply;
- `DUPLICATE` — points to the canonical finding;
- `WITHDRAWN` — reviewer retracts it with rationale;
- `SUPERSEDED` — a later finding replaces it without erasing history; or
- `UNRESOLVED` — remains blocking where its severity/evidence requires.

Author disagreement is not a false-positive disposition. The Verifier proposes
rank-1/2 disposition after examining evidence; unresolved rank-3/4 judgment at
T2+ escalates to the Change Owner. A Security Reviewer may block a T3 change
unconditionally.

When the last budgeted round (section 2) does not pass, unresolved matters
escalate to the Change Owner, who chooses one of the following and records it
in the dispositions with the date: merge with the listed advisories; accept a
named residual (above); split the change; stop; or allow one more round. One
more round is allowed only if the last round found a rank-1 finding in code,
tests or security posture. A contract without a declared budget has a budget
of two rounds. After an extra round the menu repeats only on the same
condition: another round needs a new rank-1 finding in code, tests or security
posture.

A pre-authorisation (section 2) stands for the Change Owner's choice "allow one
more round" for up to two further rounds of the layer it names. A pre-authorised
round starts only if the round before it, of the same layer, did not pass and
found a rank-1 finding in code, tests or security posture. Before the round starts, the dispositions record the
pre-authorisation (contract and criterion), the finding that meets the condition
and the date. If no such finding exists the round is not started and the menu
above applies. After the last pre-authorised round the menu repeats only on the
same condition. A pre-authorisation applies to the reviews of the change whose
contract carries it; it does not carry to another layer or to another change, and
a rebase or a merge-base refresh of the change does not end it.

## 6. Re-review triggers

Re-review is required after a change to behavior, acceptance criteria,
contract, invariant, architecture, tests or test intent, security posture,
dependency/license, recovery evidence, or finding-relevant code. A reviewer may
scope re-review to the affected findings and interactions but must bind the
outcome to the new complete head SHA (for outcome records, as the paragraphs
below provide).

A confirmation round after a fix names the delta it covers, re-runs the
mechanical checks, and re-attacks only the affected findings and interactions.
It is a valid re-review under this section; it does not repeat unchanged areas.

**Review-outcome records (opt-in).** This paragraph applies only when the approved
Task Contract has an acceptance criterion that declares the outcome-record
paths: the report path patterns and the dispositions file. The evidence pack and
the Task Contract are those of the change. Without that declaration a review
binds only a head that nothing changes afterward, and nothing below applies. A
declaration may narrow the classes below; it cannot widen them.

An outcome record is exactly one of the following, and nothing else is one:

- (a) A review report: a file added (not modified) at a path that matches a
  declared report pattern, where `*` matches within one path segment and
  matching is case-sensitive. It is a regular file (mode 100644), UTF-8 text
  without a NUL byte, not empty, and at most 1 MiB. A path that exists in the
  reviewed head is not an outcome record.
- (b) A security-evidence fill: a change to `status`, `artifact`,
  `artifact_sha256` and `coverage_boundary` of the evidence pack's
  `security_evidence` object, and to no other part of the pack, where `status`
  is `passed`, `artifact` is a Security Review report added under (a) between
  the reviewed head and the final head, `artifact_sha256` is the SHA-256 of
  that committed file, and `coverage_boundary` is not empty.
- (c) A dispositions append: the declared dispositions file at the final head
  begins with the file at the reviewed head byte for byte, the earlier file is
  empty or ends with a newline, and the added bytes are UTF-8 text without a
  NUL byte. Inserting, changing, or deleting any earlier byte is not an append.
- (d) A scope addition: entries added to the contract's `declared_scope` list,
  each exactly the path of a report added under (a), with no other change to
  the contract.

A mode change, a rename, a type change, a deleted file, and a file outside these
classes are not outcome records. The evidence pack and the contract are
compared by parsed value after the strict JSON loading of `aidf_check.py`
(a duplicate key, a non-finite number, or a parse error is a difference), so
formatting that does not change a parsed value is not a difference. The evidence
pack must not describe the outcome of a review that has not been committed.

A review's reviewed content head R is the head it examined. The review covers
the final head H if and only if R is an ancestor of H and a deterministic
comparison of R and H finds only outcome records. The comparison reads the raw
tree difference (`git diff-tree -r -z --no-renames --raw R H`, which gives each
path's status, modes, and blob ids), reads the blobs that difference names, and
applies the classes above. `verification/review_head_binding_evidence.py`
implements it as `compare()`; the merger may run that function or an equivalent
one. Any other difference (a code or test change, a changed pack sentence, a
changed contract criterion, an extra file) invalidates the review exactly as an
unexplained diff does. The protected gate or the merger runs the comparison for
each required review and records its commands and output.

The comparison establishes the shape of a change, not who wrote a report. Section
3 still applies in full: a report counts only if it comes from a distinct
instance and is corroborated by a source the author does not control.

A formatting-only edit or merge-base refresh does not require a new substantive
round when a deterministic comparison proves the reviewed semantic diff is
unchanged. It still requires final-SHA binding. Any unexplained diff invalidates
the prior review.

Class escalation immediately adds the higher class's review and evidence
requirements. De-escalation never removes a review already required without
the authority of the class being left.

## 7. Completion and anti-substitution

Review is complete only when:

- every required role is represented by a valid distinct instance;
- required ordering is proven;
- every review covers the final head SHA and declared input set (directly,
  or through section 6 outcome records where the approved Task Contract
  declares them);
- every blocking finding has a valid non-`UNRESOLVED` disposition;
- all triggered re-reviews are complete;
- the evidence pack reflects revisions and residual risk;
- required human decisions are recorded once under applicable roles; and
- protected gates for the exact commit pass.

The following never satisfy or substitute for completion: author self-approval;
tests alone; an automated rule-based scan alone; the Verifier alone at T3;
Security Review without a prior completed Verifier pass; a human approval
without required AI separation; a review of an older SHA, except as section 6 outcome records allow where the approved Task Contract declares them; a summary without
findings; or branch-authored self-attestation without external provenance.

## 8. Precision and calibration

Every review layer records blocking findings raised and the subset adjudicated
`CONFIRMED_FIXED` or `CONFIRMED_ACCEPTED_RISK`. Blocking precision is:

`confirmed blocking findings / blocking findings raised`

Report numerator, denominator, and ratio by layer. A zero denominator is
`not applicable`, not 100%. Missing adjudication is `unknown`, not false or
zero. Also record disagreement count, findings causing substantive revision,
false positives, re-review rounds, escalations, and time to disposition.

Small samples are reported as counts and `insufficient sample`; no threshold is
invented. Low precision in an optional layer permits retirement. A
class-required layer is re-specified—narrow its remit, improve framing, or
change the instance—but is never removed unilaterally.

Controlled STOP/DECLARE/ESCALATE exercises are labeled simulations and excluded
from product finding precision. Precision measures review yield; it never lowers
task class, evidence, separation, or approval requirements.
