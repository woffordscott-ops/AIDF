---
owner: framework-maintainer
load_when: assigning, running, or reviewing a tool/model qualification
max_length: 2 pages
last_verified: 2026-10-20
---

# Layer 2 — Tool/Model Qualification

**Published copy:** the example profiles described below (`qualified/`, `qualification-candidates/`, `unqualified/`) and the earlier suites (the pilot's suite v1 and suite v1.1) belong to the private project the framework was first used on. A published copy of this repository does not contain them, so the paragraphs below that mention those files describe the original repository. The protocol, the validators and the public reference suite (`qualification-eval/suite-v2.json`) are in the copy.

**Status: the protocol, suites and validators are active; the only qualified
profiles have expired.** `codex-cli 0.151.0-alpha.7.2` / `gpt-5.6-sol` was
qualified for M0–M3 until its per-mode expiries of 2026-10-09 (see "Current
mapping"; requalification is required), having executed every mandatory case for each mode, passed the
fail-closed validator, completed ordered review, and reached protected
integration at framework protected main `c6fa9bdd06680cefcb36e2cd0280d9ee9f4dcd1f`
(protected pipeline #1113, jobs `phase8-qualified-profile-m0` through `m3`).

## Artifacts

- `qualification-protocol-v1.md` defines identity, execution, all-mandatory-
  case semantics, evidence jurisdiction, expiry, requalification, revocation,
  and the security/privacy boundary. `qualification-protocol-v1.1.md` is an
  additive amendment, not a replacement — it adds later schema versions
  (environment transport detail, per-case candidate-instance identity, accepted
  Claude substitute-reviewer provenance) and the trigger table cited below,
  without changing anything v1 already defined. Both apply; v1.1 is the one
  to check for anything added after v1 shipped.
- `qualification-protocol-v1.2.md` is an additive amendment to v1.1 for a suite that is not the private
  pilot's: it restates the jurisdiction and fixed population, and requires a profile to list a suite's declared
  differences and public answer key. `suite-v2.json` names it.
- `qualification-eval/suite-v2.json` is the public reference suite: sixteen authored cases (M0 4, M1 8, M2 1, M3 3)
  over the fixture in `qualification-eval/reference-app/`. To run it: it pins repository
  `ProjectGenome/ai-development-framework` at revision `6d647332048862bfa464d11374f53ea6d9cdcfbd` and has
  `suite_sha256` `91c8d1eefb846aa44d3af8dec9a34ccbfe72979cbd37ae236af661ffd63710e6`. That revision is in the
  project's private history. A published copy of this repository starts at one commit that does not contain it, and
  re-pinning the suite to that commit would change the suite digest, so it is not done here. In a published copy, read
  the case material (`qualification-eval/reference-app/cases/`) and the suite file and validators from the commit you
  checked out, and record that commit and the digest in your profile. Where the private history is available, the pinned
  revision is still the one to read the case material from (for example `git worktree add <directory> 6d647332048862bfa464d11374f53ea6d9cdcfbd`). Give a fresh instance of your tool and
  model only each case's `prompt.md` and the starting workspace its `workspace.txt` defines; never its
  `ground_truth.md`, `rubric.md`, hidden tests, reference solution, plausible-wrong files or demonstration
  tests. Grading: M0 `M0-TRANSFORM-01` byte-exactly against an expected diff, and the other three M0 cases by an evaluator
  against an expected disposition and ground truth; M1 `M1-FLOW-01`, `M1-BILLING-01` and `M1-MEMBERS-01` by hidden
  tests that the plausible-wrong implementations fail, and the five other M1 cases by expected disposition against
  ground truth; M2 by the Architect's frozen rubric; M3 by ground truth and rubric. The answer key is public, so a result says nothing about a
  candidate that had access to it. `qualification-eval/REFERENCE-SUITE.md` has the full procedure, what the
  suite does not cover and its versioning policy.
- The pilot's suite v1 (not in a published copy) fixes the private-pilot-derived
  population and known-good dispositions for M0–M3.
- `environments/` binds observed execution environments.
- `unqualified/` records named combinations that could not execute because an
  exact tool/model identity or runtime was unavailable. These records are not
  profiles and confer no eligibility.
- A `qualified/` record is accepted only by
  `verification/qualification_check.py` with exact canonical-suite digest and
  ordered external reviewer bindings that match a separately supplied
  attestation document and caller-protected canonical digest, plus an exact
  complete-profile digest supplied by the external protected-integration
  environment.

## Assignment rule

Qualification is repository-, revision-, tool-, exact-version-, model-, mode-,
suite-, and environment-specific. Task assignment may select a candidate only
when an unexpired qualified profile matches every dimension and no revocation
or requalification trigger is active. Passing one dimension never qualifies
another.

Profiles narrow neither M0–M3 nor human gates. They grant no merge, production,
credential, legal, architecture, Security, Change Owner, or level-P/X
authority. At T2+, the same instance may not be both M1 Implementer and M3
Verifier on the same change.

## Current mapping

`codex-cli 0.151.0-alpha.7.2` / `gpt-5.6-sol` was **qualified and active** for
M0–M3 for the private pilot project at revision
`87fedca3995125fc9042787395fc981a95b12eb1`, against the pilot's qualification suite v1.1, environment
`phase8-codex-gpt-5-6-sol-windows`. Per-mode expiry (earliest first): M2
2026-10-09T16:41:53Z, M0 2026-10-09T16:44:40Z, M1 2026-10-09T16:47:55Z, M3
2026-10-09T16:49:26Z. All four expiries have passed (checked 2026-10-20), so
these profiles no longer make the combination eligible and requalification is
required; it is also required sooner on any trigger in
`qualification-protocol-v1.1.md`.

Claude Code and Cursor remain explicitly **unqualified** for the pilot's suite
v1 in the observed local environment because exact reproducible tool and
backend model identifiers were unavailable and the suite was not executed
against them. Roadmap naming and current-session availability do not
substitute for evidence.

## Specialty dimension and automatic routing

`verification/agent_routing_check.py` (`spec/AGENT-ROUTING-TASK-CONTRACT.md`,
T2) implements automatic, cost-aware routing among qualified candidates.
`profiles/specialty/*.json` records a per-domain (`security_review`,
`correctness_review`, `ci_infrastructure`, `implementation`) empirical
qualification, linked to (never merged into) a `qualified/*.json`
record by `profile_id` — a separate record rather than an added field,
because `profile_payload_sha256` is computed over the entire profile record
and every protected `review_bindings.*.profile_payload_sha256` cross-check
is pinned to that exact digest; adding a field would invalidate every
existing attestation.

Only `security_review` and `correctness_review` currently have a supported
evidence type (`DOMAIN_TO_REVIEW_LAYER` maps them to real review-layer
figures; `evidence_source.type` is closed to `"review_precision"`). A
specialty claim for `ci_infrastructure` or `implementation` will always fail
content verification under the code as written, by design — they are
declared in `DOMAINS` for forward compatibility, but no evidence type
exists yet that could back them. Disclosed, non-blocking (round-2 formal
review, R2-F4); building that evidence type is future work, not a silent
gap.

Neither a profile nor a specialty claim is ever trusted from the data that
proposes using it. A routing candidate declaration carries only `profile_id`,
`instance_id`, cost, access, and claimed specialty domains — no digest, no
evidence path. Every value that establishes trust is looked up from a
separately supplied `authorization` mapping (`resolve_candidate()`'s
`authorization` argument), itself loaded and digest-verified against a
caller-protected `--expected-authorization-sha256`, populated out of band by
the Change Owner or by CI reading its own protected variables:
`authorization["profiles"][profile_id]` supplies the protected profile
digest and review-attestations file `qualification_check.validate_profile()`
requires (this repository's own activation gate, reused rather than reimplemented);
`authorization["specialty"][profile_id][domain]` supplies the specialty
record's own protected digest. A specialty record additionally must pass
binding verification (cited evidence file exists, digest matches) and
content/attribution verification (claimed `precision`/`sample_size`
recomputed from the cited file's own structured per-layer figures, whose
recorded `model_identifier` must equal the resolved profile's own
`tool.model_identifier`). No self-reported, vendor-asserted, or merely
digest-self-consistent specialty value is ever accepted.

**Revocation and compatibility.** This repository has no `revoked: true`
field anywhere, by design — `qualification-protocol-v1.1.md`'s own model is
that the protected operator (human, or CI reading `AIDF_PROTECTED_PROFILE_
SHA256_M0..M3`) simply stops vouching for a profile to revoke or
requalify it. The routing `authorization` mapping generalizes that exact
model: a `profile_id` absent from `authorization["profiles"]` is never
routable, full stop, regardless of what a real file on disk claims.
Revocation is authorization absence, not a field the router tracks
independently. `select_candidate()` treats `required_repository_revision`
and `required_environment_sha256` as mandatory, exactly-matched dimensions
alongside repository/suite/environment_id — every candidate considered for
one task must describe the same real context. `required_tool_version` and
`required_model_identifier` stay optional, caller-declared pins: routing
exists to choose among tools and models, so those two are opt-in, not
automatically inferred.

As of 2026-10-05, one specialty record exists:
`profiles/specialty/phase8-codex-gpt-5-6-sol-security-review.json`, citing
`metrics/observations/phase9-ci-policy-security-r1.json`
(`review_finding_precision` 1/1, security layer, from
`aidf-ci-policy` MR !57 — a different repository than the
qualified profile's own private pilot project; the
specialty attribution check recomputes `precision`/`sample_size` and checks
`model_identifier`, but does not itself compare the observation's source
project or revision against the profile's — disclosed, non-blocking, a
Change Owner decision whether to add that cross-check) for the qualified
profile `phase8-codex-gpt-5-6-sol-m3-rerun-3-20260909`. The precision figure
is retrospective: the observation's own `basis` records that the
2026-10-02 report, at the time it was written, showed "0
adjudicated-confirmed / 1 raised, adjudication unknown," and the 1/1 credit
was assigned on 2026-10-04 relying partly on a human "accepted admission"
for the provenance component — not a same-day, first-pass 1/1. Both
`specialty`/`route` CLI checks were run locally against a representative
(uncommitted) `authorization` mapping and passed; this is an author
statement, not something this repository alone can reproduce, since that
mapping was never committed (see below).

There are two distinct gaps here, and only one is closed. **Closed:** the
qualified profile itself had never performed a review; it now has one,
attributed by a human-attested `model_identifier` binding — Scott Wofford,
Change Owner, confirmed directly (not inferred, and not self-reported by
Codex's own tooling, which does not expose its backend model identity) that
the reviewing sessions ran on `gpt-5.6-sol`, the qualified profile's own
tool identity. **Still open:** the entity whose review track record this
repository's own evidence commits actually show — Claude Sonnet 5, acting
as an `accepted_substitute` reviewer per
`qualification_check.APPROVED_SUBSTITUTE_REVIEW_MODELS` (unchanged by this
specialty record) — still has no Layer 2 qualified profile of its own.
"Accepted substitute reviewer" and "Layer 2 qualified candidate" remain
distinct, not-yet-unified concepts; bridging them is still future work.

**The out-of-band `authorization` mapping is deliberately not pre-built.**
A representative mapping was constructed once, locally, to exercise and
prove the `specialty`/`route` mechanism end to end (2026-10-04) — it was
never committed, since `profiles/authorization/**` mechanically forces T3
(`verification/policy.json`'s path-based tripwire, the same rule that
forces T3 for the CI configuration file), correctly: a real trust mapping is
genuinely security-relevant and earns its own T3 review, not a technicality
to route around for a demonstration. The Change Owner's decision, 2026-10-05:
build the real mapping fresh, with its own T3 Task Contract and review, at
the time of an actual T2+ task assignment — not pre-emptively.
