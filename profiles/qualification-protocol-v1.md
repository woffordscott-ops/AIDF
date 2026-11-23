---
owner: framework-maintainer
load_when: assigning or running a Layer 2 model/tool qualification
max_length: 4 pages
last_verified: 2026-10-06
---

# Qualification Protocol v1

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

The private pilot's first suite file (suite version 1) is the fixed population. Its
SHA-256 is calculated over strict canonical JSON (UTF-8, sorted keys, compact
separators, Unicode preserved) and supplied independently to the validator.
This retains semantic identity across Git line-ending conversion. Cases are
derived from the private pilot's own immutable outcomes and controlled failures. A run must
execute every case marked mandatory for its requested mode, exactly once, in
suite order. Environment records use the same canonical digest rule.

Each case runs from a clean task instance with only the context allowed by its
mode. Candidate output is retained outside the profile and represented by an
immutable SHA-256 evidence reference. An authorized evaluator compares the
output with the case's closed expected disposition and records only that
enumerated disposition. Free-form model output never becomes validator input.

M3 cases receive the requirement, invariants, diff, and tests without author
rationale. M3 produces findings only. For a T2/T3 source change, an instance
identifier used as M1 Implementer must differ from the M3 Verifier identifier.

## Result semantics

There is no score. A mode qualifies only when:

- the suite, run, and profile schemas are exact and complete;
- repository, suite, model/tool, environment, and evidence digests match;
- every mandatory case for the mode appears exactly once and has the exact
  expected disposition;
- no prohibited action is recorded;
- required role separation holds;
- ordered Verifier and Security reviewer bindings cover the exact run and
  profile digests with zero unresolved findings and exactly match a separately
  supplied attestation document whose canonical digest is protected by the
caller; and
- the profile has a finite UTC expiry later than both the run completion and
  the validator's current UTC evaluation time.

Otherwise the result is `unqualified`. Missing evidence is never a skipped or
partial pass. An unavailable runtime uses an availability record and does not
create a run or profile.

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
append-only; historical evidence is not rewritten.

## Security and privacy boundary

Inputs are strict UTF-8 JSON regular files beneath the repository root, capped
at 256 KiB. Unknown fields, duplicate keys, non-finite numbers, unsafe paths,
unbounded strings/lists, non-lowercase SHA-256 values, non-UTC timestamps, and
ambiguous identities, missing protected review attestations, and expired
profiles fail closed. The validator has no network, subprocess,
credential, certificate, native-deserialization, or dependency behavior.

Fixtures may name credential/certificate boundary conditions but must not
contain real secrets, private keys, tokens, or certificates. Vendor execution
that transfers repository data, emits telemetry, permits training use, or
requires new terms remains blocked until Legal and Security disposition.
