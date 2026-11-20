---
owner: framework-maintainer
load_when: assigning or running a Layer 2 model/tool qualification
max_length: 4 pages
last_verified: 2026-10-06
---

# Qualification Protocol v1.1

## Jurisdiction and identity

This protocol measures whether one exact tool/model combination produces the
required bounded behavior for one execution mode on the private pilot's
repository revision and fixed suite digest recorded by the run. It does not establish a
permanent model identity, another mode, another repository, architecture
fitness, legal approval, risk acceptance, merge authority, production access,
cost effectiveness, performance, or security efficacy.

The immutable evaluation unit is:

`repository project + repository revision + tool vendor + tool name + exact
tool version + exact model identifier + mode + suite version + suite SHA-256 +
environment SHA-256`.

Any unavailable element makes the unit unqualified. Aliases such as “latest,”
product family names, or inferred backend versions are not exact identifiers.
The environment record contains a structured observed candidate identity; a
profile must match all four identity fields exactly. A null or `unknown`
observed identity cannot support a profile.

## Fixed population and execution

`profiles/qualification-eval/suite-v1.1.json` is the fixed population. Its
SHA-256 is calculated over strict canonical JSON (UTF-8, sorted keys, compact
separators, Unicode preserved) and supplied independently to the validator.
This retains semantic identity across Git line-ending conversion. Cases are
derived from the private pilot's own immutable outcomes and controlled failures. A run must
execute every case marked mandatory for its requested mode, exactly once, in
suite order. Environment records use the same canonical digest rule.
Schema-version 1 environment records remain valid for historical local or
unavailable-runtime evidence. Schema-version 2 records separate
`execution_transport` (`local` or `hosted`) from `candidate_network_access`
(`disabled` or `not_used`). Hosted transport requires candidate network access
to be `disabled`.

Each case runs from a clean task instance with only the context allowed by its
mode. Candidate output is retained outside the profile and represented by an
immutable SHA-256 evidence reference. An authorized evaluator compares the
output with the case's closed expected disposition and records only that
enumerated disposition. Free-form model output never becomes validator input.

Qualification-profile schema version 1 remains valid for historical runs that
used one candidate instance for a complete mode. Schema version 2 removes the
run-level candidate instance and records one unique `candidate_instance_id` on
every case result. Review separation for schema version 2 is checked against
the complete set of those case-level identities. Moving, omitting, duplicating,
or substituting an identity fails closed.

Schema version 3 retains the schema-version 2 candidate-instance model and
adds explicit provenance for accepted Claude substitute reviews. Its ordered
bindings are named `correctness` and `security`, not Bugbot or Codex Security
Review. Each binding records the substitute type, review role, Anthropic
provider, exact Claude model, skill or disclosed methodology, session identity,
and independently initialized context. A binding uses exactly one provenance
form: an existing Claude web session identity paired with its canonical URL, or
a canonical Claude CLI session UUID paired with the lowercase SHA-256 of the
complete review report's exact file bytes. Mixed, missing, malformed, reused,
or mismatched provenance fails closed. CLI report digests are protected through
the exact review-attestation binding and do not substitute for independent
initialization, ordering, or reviewer-instance separation. The centralized
approved substitute-review
model set for this protocol revision is `claude-sonnet-5`; changing that set
requires a reviewed protocol and validator amendment. Schema-version 1 and 2
profiles retain their historical native `bugbot` and `security` binding format
unchanged.

Before supplying a CLI review attestation, the protected operator independently
hashes the saved report's exact file bytes and verifies that the result equals
the binding's `report_sha256`. For a findings-only report, `findings_sha256`
binds those same complete report bytes. The separately stored attestation
document must exactly equal the candidate's ordered review bindings; partial,
mixed, mismatched, or duplicate review provenance fails closed.

M3 cases receive the requirement, invariants, diff, and tests without author
rationale. M3 produces findings only. For a T2/T3 source change, an instance
identifier used as M1 Implementer must differ from the M3 Verifier identifier.
When an immutable historical T2/T3 source artifact has no AI M1 implementer,
the run uses the reserved identifier `historical-source-no-ai-implementer` and
the governed evidence records that provenance. A symbolic human identity must
not be substituted for an AI instance identifier.

## Result semantics

There is no score. A completed run and its inactive profile candidate use
`pass_pending_ordered_review_and_protected_integration` until every remaining
review and protected-integration condition below is satisfied. That pending
result covers both the pre-review state with explicitly empty bindings and the
reviews-complete state with exact ordered bindings and matching attestations.
Completing reviews does not authorize, activate, or make the candidate eligible
for use. An inactive candidate must not claim `qualified` while its review
bindings or attestations remain empty, incomplete, mismatched, or not yet bound
by protected integration.

The canonical run evidence pack remains an immutable pre-review snapshot. Its
recorded empty-binding status is historical; the candidate and its separately
stored, exactly matching attestation document carry the later reviewed-pending
transition without changing the evidence or profile-payload digests reviewed.

A mode qualifies only when:

- the suite, run, and profile schemas are exact and complete;
- repository, suite, model/tool, environment, and evidence digests match;
- every mandatory case for the mode appears exactly once and has the exact
  expected disposition;
- no prohibited action is recorded;
- required role separation holds;
- ordered correctness and Security reviewer bindings cover the exact run and
  profile digests with zero unresolved findings and exactly match a separately
  supplied attestation document whose canonical digest is protected by the
  caller; schema-version 3 bindings additionally disclose accepted-substitute
  provenance and must not claim to be unavailable Codex reviewer attestations;
  and
- the profile has a finite UTC expiry later than both the run completion and
  the validator's current UTC evaluation time.

After activation validation, failure of any condition makes the result
`unqualified`. Before activation, the pending result is neither qualified nor
eligible for use. Missing evidence is never a skipped or partial pass. An
unavailable runtime uses an availability record and does not create a run or
profile.

The validator also requires the canonical digest of the complete profile to
match `AIDF_PROTECTED_PROFILE_SHA256`, an external value supplied only by the
protected integration environment after independent verification. It is not a
command-line argument or repository value and is absent while no run is
qualified. Before setting it, the protected operator must independently verify
the referenced evidence artifacts and authenticated MR, pipeline, reviewer,
and outcome records. Keeping this trust value outside the reviewed commit
avoids an exact-final-head self-reference.

## Expiry, requalification, and revocation

There is no default expiry duration. The run contract must contain a finite
explicit `expires_at` value approved for that run. Expiry immediately removes
assignment eligibility while preserving historical evidence.

Requalification is mandatory on any exact tool version or model identifier
change; suite version or digest change; repository compatibility-boundary
change; material environment change; M0–M3 contract change; expiration;
security or provenance defect; or revocation. A new run and profile are
append-only; historical evidence is not rewritten. Every replacement run binds
the exact immediately preceding eligible run, increments its run ordinal by
one, and records the replacement basis. Earlier failed, ineligible, and
superseded runs remain non-qualifying history.

## Security and privacy boundary

Inputs are strict UTF-8 JSON regular files beneath the repository root, capped
at 256 KiB. Unknown fields, duplicate keys, non-finite numbers, unsafe paths,
unbounded strings/lists, non-lowercase SHA-256 values, non-UTC timestamps, and
ambiguous identities, missing protected review attestations, and expired
profiles fail closed. The validator has no network, subprocess,
credential, certificate, native-deserialization, or dependency behavior. A
schema-version 2 `hosted` transport records only the approved invocation path
between the exact client and hosted candidate. It grants no candidate web,
dependency-download, external-service, or arbitrary network authority within a
case. Unknown transport values, mixed schema fields, and hosted transport
without disabled candidate network access fail closed.

Fixtures may name credential/certificate boundary conditions but must not
contain real secrets, private keys, tokens, or certificates. Vendor execution
that transfers repository data, emits telemetry, permits training use, or
requires new terms remains blocked until Legal and Security disposition.
