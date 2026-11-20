"""Fail-closed selection of a qualified agent for a governed sub-task.

Implements the T2 Task Contract at spec/AGENT-ROUTING-TASK-CONTRACT.md,
following the design in spec/SPIKE-AGENT-ROUTING-PROPOSAL.md. This is the
third rework. Round one found candidates were never checked against real
Layer 2 records; round two found the fix still stopped short of
qualification_check.validate_profile()'s real protected-digest gate; round
three found the deepest remaining flaw: the round-two fix read its
"protected" digests from the same declaration file that proposes the
candidate, which is not a trust boundary at all -- an author can modify a
profile, recompute its digest, and supply the recomputed value themselves.
The same defect applied to specialty evidence: an unsigned observation file
authored alongside a matching model_identifier label was still credited.

The trust chain is now:

1. A CandidateDeclaration expresses a proposal ONLY: profile_id, instance_id,
   cost, access, and which specialty domains are claimed. It carries no
   digests and no file paths for evidence -- none of that can be
   attacker-declared. resolve_candidate() looks up everything it needs to
   trust that profile_id from a separately supplied `authorization` mapping
   -- itself loaded and digest-verified against a caller-supplied
   `--expected-authorization-sha256`, the same pattern already used for the
   suite. The authorization mapping is populated out of band (by the Change
   Owner, or by CI reading its own protected variables) -- never derived
   from, or influenced by, the declarations file being routed.
2. For the profile itself: authorization["profiles"][profile_id] supplies
   the protected_profile_sha256 and the review-attestations path/digest,
   which feed qualification_check.validate_profile() -- the exact gate
   Phase 8's own activation uses.
3. For specialty evidence: authorization["specialty"][profile_id][domain]
   supplies the specialty-evidence file path and its own protected digest.
   That record must match, AND independently pass shape validation
   (validate_specialty_evidence), binding verification
   (verify_specialty_evidence_binding -- the cited observation file exists
   and matches digest), and content/attribution verification
   (verify_specialty_evidence_content -- the claimed precision/sample_size
   is recomputed from the cited observation's own structured per-layer
   figures, and that figure's recorded model_identifier must equal the
   resolved profile's own tool.model_identifier). A self-authored
   observation with a matching model label is no longer sufficient on its
   own -- the specialty record that cites it must itself be one the
   authorization mapping vouches for.
4. select_candidate() filters already-resolved Candidates by mode,
   repository AND repository_revision, suite (id + version), environment_id
   AND environment_sha256, unexpired, declared access, and a validated cost
   ceiling. Revision and environment digest are mandatory exact-match
   dimensions -- every candidate considered for one task must describe the
   same real context, not a caller's preference among candidates. When a
   caller additionally supplies them, tool_version / model_identifier are
   optional exact-match pins: routing exists to choose among tools and
   models, so those two stay opt-in. This module does not otherwise judge
   revision/environment "compatibility" beyond exact match, and tracks no
   revocation state of its own -- per qualification-protocol-v1.1.md's own
   design, a profile is trusted only as long as its authorization entry
   (step 1) remains present; the protected operator updates or removes
   that entry to requalify or revoke, the same way
   AIDF_PROTECTED_PROFILE_SHA256_M0..M3 already governs Phase 8 activation.
   Revocation is authorization absence, not a field this module tracks.
5. Apply the T2+ separation-of-duties exclusion as a final hard filter,
   after ranking, never blended into the score, operating on instance_id
   (the reasoning instance performing the work), never profile_id.
6. For any T2+ task, a selection is returned as "provisional_selection",
   never "selected".

Every input this module reads from a file is validated against a closed
field allowlist before use, and every nested boundary is isinstance-checked
before being indexed, so malformed input produces a Finding, never a raw
traceback. Numeric cost is bounded before float conversion so an
oversized-but-in-limits JSON integer cannot raise OverflowError.

This module has no independent parsing story: it reuses qualification_check's
bounded, duplicate-key-rejecting, TOCTOU-safe primitives rather than
reimplementing them, matching the existing precedent in
phase8_qualification_check.py.
"""

from __future__ import annotations

import argparse
import hmac
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from qualification_check import (
    CLASSES,
    MODES,
    Finding,
    _expected_sha256,
    _is_identifier,
    _is_revision,
    _is_sha256,
    _is_text,
    _parse_utc,
    _required_fields,
    _unknown_fields,
    canonical_sha256,
    load_json,
    validate_profile,
)

DOMAINS = frozenset(
    {"security_review", "correctness_review", "ci_infrastructure", "implementation"}
)
MIN_SPECIALTY_SAMPLE = 1
MIN_SPECIALTY_PRECISION = 1.0

QUALIFIED_PROFILES_DIR = "profiles/qualified"

# A sane bound on candidate cost, applied before any float conversion so an
# in-limits-but-absurd JSON integer (e.g. 10**400) cannot raise OverflowError
# converting to float.
MAX_COST_MAGNITUDE = 10**12

# review_precision evidence can only ever support a domain that corresponds
# to a real review layer this repository actually records outcomes for.
DOMAIN_TO_REVIEW_LAYER = {
    "security_review": "security",
    "correctness_review": "correctness",
}

SPECIALTY_EVIDENCE_FIELDS = {
    "schema_version",
    "record_type",
    "profile_id",
    "domain",
    "evidence_source",
    "precision",
    "sample_size",
    "qualified_at",
}
EVIDENCE_SOURCE_FIELDS = {"type", "observation_path", "observation_sha256"}

# A CandidateDeclaration expresses a proposal only -- it carries no digests
# and no evidence file paths. Anything that establishes trust is looked up
# from the separately supplied, independently protected `authorization`
# mapping, never accepted from the declaration itself.
DECLARATION_FIELDS = {
    "profile_id",
    "instance_id",
    "environment_access",
    "cost_per_unit",
    "specialty_domains",
}
DECLARATION_REQUIRED_FIELDS = {"profile_id", "instance_id", "cost_per_unit"}

PROFILE_AUTHORIZATION_FIELDS = {
    "protected_profile_sha256",
    "review_attestations_path",
    "protected_review_attestations_sha256",
}
SPECIALTY_AUTHORIZATION_FIELDS = {"specialty_evidence_path", "protected_specialty_evidence_sha256"}

REQUIREMENT_FIELDS = {
    "task_class",
    "required_mode",
    "required_domain",
    "required_repository",
    "required_suite_id",
    "required_suite_version",
    "required_environment_id",
    "required_environment_access",
    "required_tool_version",
    "required_model_identifier",
    "required_environment_sha256",
    "required_repository_revision",
    "cost_ceiling",
    "separation_exclusions",
}
REQUIREMENT_REQUIRED_FIELDS = {
    "task_class",
    "required_mode",
    "required_repository",
    "required_repository_revision",
    "required_suite_id",
    "required_suite_version",
    "required_environment_id",
    "required_environment_sha256",
}

# The role/context curation contract, generalizing core/05-review.md sec 2
# and modes/execution-modes.md's "Required context" column. Kernel is
# required context for every declared role, including review roles.
ROLE_CONTEXT_SPEC: dict[str, dict[str, Any]] = {
    "implementer": {
        "include": (
            "kernel",
            "established_task_contract",
            "touched_contracts",
            "tests",
            "conventions",
        ),
        "exclude": (),
    },
    "verifier": {
        "include": (
            "kernel",
            "requirement",
            "acceptance_criteria",
            "confirmed_class",
            "evidence_boundary",
            "invariants_touched",
            "contracts_touched",
            "exact_diff",
            "head_sha",
            "evidence_pack",
            "executing_checks",
        ),
        "exclude": ("author_rationale", "prior_review_narrative"),
    },
    "security_reviewer": {
        "include": (
            "kernel",
            "requirement",
            "acceptance_criteria",
            "confirmed_class",
            "evidence_boundary",
            "invariants_touched",
            "contracts_touched",
            "exact_diff",
            "head_sha",
            "evidence_pack",
            "executing_checks",
            "security_model",
            "trust_boundaries",
            "data_classification",
            "dependency_posture",
            "recovery_model",
            "verifier_findings",
            "verifier_dispositions",
        ),
        "exclude": ("author_rationale",),
    },
}

# Required context fields are typed: a "text" field must be a non-empty,
# non-whitespace-only string (so False or "" are rejected, not just None);
# a "collection" field must be an actual list or dict, but MAY legitimately
# be empty -- an empty list of touched contracts is honest, not missing.
_TEXT_CONTEXT_FIELDS = frozenset(
    {"kernel", "requirement", "confirmed_class", "evidence_boundary", "exact_diff", "head_sha", "data_classification"}
)
_COLLECTION_CONTEXT_FIELDS = frozenset(
    {
        "acceptance_criteria",
        "invariants_touched",
        "contracts_touched",
        "evidence_pack",
        "executing_checks",
        "security_model",
        "trust_boundaries",
        "dependency_posture",
        "recovery_model",
        "verifier_findings",
        "verifier_dispositions",
        "established_task_contract",
        "touched_contracts",
        "tests",
        "conventions",
    }
)


def _is_finite_number_in_unit_interval(value: Any) -> bool:
    """A precision value must be a real, non-boolean number in [0, 1].
    Bounded by magnitude before any float conversion, matching
    _is_finite_nonnegative_cost, so an in-limits-but-absurd JSON integer
    (e.g. 10**400) cannot raise OverflowError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    if isinstance(value, int) and abs(value) > MAX_COST_MAGNITUDE:
        return False
    return 0.0 <= float(value) <= 1.0


def _is_finite_nonnegative_cost(value: Any) -> bool:
    """A usable cost is a real, finite, non-negative, non-boolean number
    within a sane magnitude. `bool` is a subclass of `int` in Python, so it
    is excluded explicitly. An in-limits-but-absurd JSON integer (e.g.
    10**400) is rejected by magnitude before any float conversion, so it
    can never raise OverflowError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, int) and abs(value) > MAX_COST_MAGNITUDE:
        return False
    as_float = float(value)
    return math.isfinite(as_float) and as_float >= 0


@dataclass(frozen=True)
class CandidateDeclaration:
    """A routing proposal only -- profile_id, instance_id, cost, access, and
    which specialty domains are claimed. Carries no digests and no evidence
    paths: nothing here is trusted on its own. resolve_candidate() looks up
    everything that establishes trust from a separately supplied
    `authorization` mapping the declarant does not control."""

    profile_id: str
    instance_id: str
    environment_access: frozenset[str]
    cost_per_unit: Any
    specialty_domains: frozenset[str]


@dataclass(frozen=True)
class Candidate:
    """A routing-eligible candidate. Construct only via resolve_candidate() --
    every field below except environment_access/cost_per_unit/instance_id is
    read from a real, protected-digest-verified profiles/qualified/*.json
    record, never from caller-declared data."""

    profile_id: str
    instance_id: str
    repository: str
    repository_revision: str
    mode: str
    suite_id: str
    suite_version: str
    environment_id: str
    environment_sha256: str
    tool_vendor: str
    tool: str
    tool_version: str
    model_identifier: str
    expires_at: str
    environment_access: frozenset[str]
    cost_per_unit: float
    specialty: dict[str, tuple[float, int]]  # domain -> (precision, sample_size)


def _iter_repo_json_paths(root: Path, relative_dir: str) -> list[str]:
    """List *.json files under a repository-relative directory as sorted,
    root-relative POSIX paths. Listing is not a trust decision -- every path
    returned is still loaded through load_json's TOCTOU-safe primitives."""
    base = (root / relative_dir).resolve()
    try:
        base.relative_to(root)
    except ValueError:
        return []
    if not base.is_dir():
        return []
    paths: list[str] = []
    for entry in base.rglob("*.json"):
        try:
            rel = entry.resolve().relative_to(root)
        except (OSError, ValueError):
            continue
        paths.append(rel.as_posix())
    return sorted(paths)


def resolve_qualified_profile(root: Path, profile_id: str) -> tuple[dict[str, Any] | None, list[Finding]]:
    """Locate a claimed profile_id among real files under profiles/qualified/
    and confirm it is minimally well-shaped and claims result == 'qualified'.
    This is a locator and a fast, cheap pre-filter -- it is NOT the trust
    boundary. A file passing this still is not a Candidate until
    resolve_candidate() additionally runs it through
    qualification_check.validate_profile() using protected digests sourced
    from the authorization mapping, never from this file's own content."""
    if not _is_identifier(profile_id):
        return None, [Finding("qualification", "profile_id is not a valid identifier")]
    for rel_path in _iter_repo_json_paths(root, QUALIFIED_PROFILES_DIR):
        try:
            record, _ = load_json(root, rel_path)
        except (ValueError, TypeError):
            continue
        if not isinstance(record, dict) or record.get("profile_id") != profile_id:
            continue
        findings: list[Finding] = []
        if record.get("record_type") != "qualification_profile":
            findings.append(Finding("qualification", f"{rel_path}: record_type is not qualification_profile"))
        if record.get("result") != "qualified":
            findings.append(Finding("qualification", f"{rel_path}: result is not 'qualified'"))
        repository = record.get("repository")
        if not isinstance(repository, dict) or not _is_text(repository.get("project")):
            findings.append(Finding("qualification", f"{rel_path}: repository.project is missing or invalid"))
        tool = record.get("tool")
        if not isinstance(tool, dict) or not all(
            _is_identifier(tool.get(field)) for field in ("vendor", "tool", "tool_version", "model_identifier")
        ):
            findings.append(Finding("qualification", f"{rel_path}: tool fields are missing or invalid"))
        if record.get("mode") not in MODES:
            findings.append(Finding("qualification", f"{rel_path}: mode is not a valid mode"))
        suite = record.get("suite")
        if (
            not isinstance(suite, dict)
            or not _is_identifier(suite.get("suite_id"))
            or not _is_identifier(suite.get("suite_version"))
        ):
            findings.append(Finding("qualification", f"{rel_path}: suite identity is missing or invalid"))
        run = record.get("run")
        if not isinstance(run, dict) or not _is_identifier(run.get("environment_id")):
            findings.append(Finding("qualification", f"{rel_path}: run.environment_id is missing or invalid"))
        if _parse_utc(record.get("expires_at")) is None:
            findings.append(Finding("qualification", f"{rel_path}: expires_at is not a valid UTC timestamp"))
        if findings:
            return None, findings
        return record, []
    return None, [Finding("qualification", f"no qualified profile record found for profile_id {profile_id!r}")]


def validate_specialty_evidence(record: dict[str, Any]) -> list[Finding]:
    """Shape/range validation only. A record passing this check alone is not
    yet trustworthy: it must also be the exact file the authorization
    mapping's protected_specialty_evidence_sha256 vouches for, and pass
    verify_specialty_evidence_binding() and verify_specialty_evidence_content()."""
    findings: list[Finding] = []
    findings.extend(_unknown_fields(record, SPECIALTY_EVIDENCE_FIELDS, "specialty_evidence"))
    for field in SPECIALTY_EVIDENCE_FIELDS:
        if field not in record:
            findings.append(Finding("specialty_evidence", f"missing required field {field!r}"))
    if findings:
        return findings

    if record.get("schema_version") != 1:
        findings.append(Finding("specialty_evidence", "unsupported schema_version"))
    if record.get("record_type") != "specialty_evidence":
        findings.append(Finding("specialty_evidence", "record_type must be 'specialty_evidence'"))
    if not _is_identifier(record.get("profile_id")):
        findings.append(Finding("specialty_evidence", "profile_id is not a valid identifier"))
    if record.get("domain") not in DOMAINS:
        findings.append(
            Finding("specialty_evidence", f"domain must be one of {sorted(DOMAINS)}")
        )

    source = record.get("evidence_source")
    if not isinstance(source, dict):
        findings.append(Finding("specialty_evidence", "evidence_source must be an object"))
    else:
        findings.extend(_unknown_fields(source, EVIDENCE_SOURCE_FIELDS, "evidence_source"))
        if source.get("type") != "review_precision":
            findings.append(
                Finding("evidence_source", "type must be 'review_precision' in this version")
            )
        if not _is_text(source.get("observation_path")):
            findings.append(Finding("evidence_source", "observation_path is not valid text"))
        if not _is_sha256(source.get("observation_sha256")):
            findings.append(Finding("evidence_source", "observation_sha256 is not a valid digest"))

    precision = record.get("precision")
    sample_size = record.get("sample_size")
    if not _is_finite_number_in_unit_interval(precision):
        findings.append(Finding("specialty_evidence", "precision must be a number in [0, 1]"))
    if not isinstance(sample_size, int) or isinstance(sample_size, bool) or sample_size < 1:
        findings.append(Finding("specialty_evidence", "sample_size must be a positive integer"))
    if _parse_utc(record.get("qualified_at")) is None:
        findings.append(Finding("specialty_evidence", "qualified_at is not a valid UTC timestamp"))
    return findings


def verify_specialty_evidence_binding(root: Path, record: dict[str, Any]) -> list[Finding]:
    """Confirm the cited observation file exists, is well-formed, and its
    digest matches exactly -- the claim must resolve, not just be shaped
    correctly."""
    source = record.get("evidence_source")
    if not isinstance(source, dict):
        return [Finding("evidence_source", "evidence_source must be an object to verify binding")]
    path = source.get("observation_path")
    expected_digest = source.get("observation_sha256")
    if not isinstance(path, str) or not isinstance(expected_digest, str):
        return [Finding("evidence_source", "cannot verify binding without path and digest")]
    try:
        parsed, _ = load_json(root, path)
    except (ValueError, TypeError) as exc:
        return [Finding("evidence_source", f"cannot load cited observation: {exc}")]
    actual_digest = canonical_sha256(parsed)
    if actual_digest != expected_digest:
        return [
            Finding(
                "evidence_source",
                f"observation digest mismatch: expected {expected_digest}, found {actual_digest}",
            )
        ]
    return []


def verify_specialty_evidence_content(root: Path, record: dict[str, Any]) -> list[Finding]:
    """Checks a digest match alone cannot make: (1) profile_id resolves to a
    real, currently qualified Layer 2 profile; (2) for review_precision
    evidence, the claimed precision and sample_size are recomputed from the
    cited observation's own structured per-layer numerator/denominator and
    must match exactly; (3) the cited layer's recorded model_identifier
    must equal the resolved profile's own tool.model_identifier -- numerical
    agreement alone does not prove the candidate performed the cited
    review. This function does not by itself prove the record is one the
    authorization mapping vouches for; resolve_candidate() checks that
    separately, before this function is ever called on untrusted input."""
    findings: list[Finding] = []

    profile_id = record.get("profile_id")
    profile: dict[str, Any] | None = None
    if isinstance(profile_id, str):
        profile, profile_findings = resolve_qualified_profile(root, profile_id)
        if profile is None:
            findings.append(
                Finding(
                    "specialty_evidence",
                    f"profile_id {profile_id!r} does not resolve to a currently qualified Layer 2 profile",
                )
            )
            del profile_findings

    source = record.get("evidence_source")
    domain = record.get("domain")
    if isinstance(source, dict) and source.get("type") == "review_precision":
        layer = DOMAIN_TO_REVIEW_LAYER.get(domain) if isinstance(domain, str) else None
        if layer is None:
            findings.append(
                Finding(
                    "specialty_evidence",
                    f"domain {domain!r} has no review-layer mapping for review_precision evidence",
                )
            )
        else:
            path = source.get("observation_path")
            if not isinstance(path, str):
                return findings + [Finding("evidence_source", "observation_path is not valid text")]
            try:
                observation, _ = load_json(root, path)
            except (ValueError, TypeError) as exc:
                return findings + [Finding("evidence_source", f"cannot load cited observation: {exc}")]
            if not isinstance(observation, dict):
                return findings + [Finding("evidence_source", "cited observation is not an object")]
            metrics_obj = observation.get("metrics")
            metric = metrics_obj.get("review_finding_precision") if isinstance(metrics_obj, dict) else None
            if not isinstance(metric, dict) or metric.get("status") != "measured":
                findings.append(
                    Finding("specialty_evidence", "cited observation's review_finding_precision is not status=measured")
                )
            else:
                by_layer = metric.get("value")
                layer_data = by_layer.get(layer) if isinstance(by_layer, dict) else None
                if not isinstance(layer_data, dict):
                    findings.append(
                        Finding("specialty_evidence", f"cited observation has no per-layer figure for {layer!r}")
                    )
                else:
                    numerator = layer_data.get("numerator")
                    denominator = layer_data.get("denominator")
                    observed_model_identifier = layer_data.get("model_identifier")
                    if (
                        not isinstance(numerator, (int, float))
                        or isinstance(numerator, bool)
                        or not isinstance(denominator, (int, float))
                        or isinstance(denominator, bool)
                        or denominator <= 0
                        or (isinstance(numerator, int) and abs(numerator) > MAX_COST_MAGNITUDE)
                        or (isinstance(denominator, int) and abs(denominator) > MAX_COST_MAGNITUDE)
                    ):
                        findings.append(
                            Finding("specialty_evidence", "cited observation's per-layer numerator/denominator are not usable")
                        )
                    else:
                        expected_precision = numerator / denominator
                        claimed_precision = record.get("precision")
                        precision_mismatch = True
                        if isinstance(claimed_precision, (int, float)) and not isinstance(claimed_precision, bool):
                            precision_mismatch = not _is_finite_number_in_unit_interval(
                                claimed_precision
                            ) or abs(expected_precision - float(claimed_precision)) > 1e-9
                        if precision_mismatch:
                            findings.append(
                                Finding(
                                    "specialty_evidence",
                                    f"claimed precision does not match cited observation's {layer} figure ({numerator}/{denominator})",
                                )
                            )
                        claimed_sample_size = record.get("sample_size")
                        if int(denominator) != claimed_sample_size:
                            findings.append(
                                Finding(
                                    "specialty_evidence",
                                    f"claimed sample_size does not match cited observation's {layer} denominator ({denominator})",
                                )
                            )
                    if not isinstance(observed_model_identifier, str):
                        findings.append(
                            Finding(
                                "specialty_evidence",
                                f"cited observation's {layer} figure has no recorded model_identifier -- "
                                "numerical agreement alone does not attribute the review to a candidate",
                            )
                        )
                    elif profile is not None:
                        tool = profile.get("tool")
                        profile_model_identifier = tool.get("model_identifier") if isinstance(tool, dict) else None
                        if profile_model_identifier != observed_model_identifier:
                            findings.append(
                                Finding(
                                    "specialty_evidence",
                                    f"profile_id {profile_id!r} is model {profile_model_identifier!r}; the cited "
                                    f"{layer} figure attributes the review to {observed_model_identifier!r}, not "
                                    "this candidate",
                                )
                            )
    return findings


def resolve_candidate(
    root: Path,
    declaration: CandidateDeclaration,
    *,
    suite: dict[str, Any],
    suite_sha256: str,
    authorization: dict[str, Any],
    now: datetime,
) -> tuple[Candidate | None, list[Finding]]:
    """Resolve a caller's declaration into a trustworthy Candidate. Every
    trust-establishing value -- the profile's protected digest, its review
    attestations and their protected digest, and each claimed specialty
    domain's evidence file and protected digest -- is looked up from
    `authorization`, keyed by profile_id, never accepted from `declaration`
    itself. `authorization` must already have been loaded and digest-
    verified by the caller (see _load_and_verify_authorization) from a
    source the candidate declarant does not control."""
    if not _is_identifier(declaration.instance_id):
        return None, [Finding("qualification", "instance_id is not a valid identifier")]
    if not _is_finite_nonnegative_cost(declaration.cost_per_unit):
        return None, [Finding("qualification", "cost_per_unit must be a finite non-negative, non-boolean number")]
    if not isinstance(declaration.specialty_domains, frozenset) or not all(
        isinstance(domain, str) for domain in declaration.specialty_domains
    ):
        return None, [Finding("qualification", "specialty_domains must be a set of strings")]

    profiles_auth = authorization.get("profiles")
    profile_auth = profiles_auth.get(declaration.profile_id) if isinstance(profiles_auth, dict) else None
    if not isinstance(profile_auth, dict):
        return None, [
            Finding("qualification", f"no protected authorization entry exists for profile_id {declaration.profile_id!r}")
        ]
    auth_findings = _unknown_fields(profile_auth, PROFILE_AUTHORIZATION_FIELDS, "authorization.profiles")
    auth_findings.extend(_required_fields(profile_auth, PROFILE_AUTHORIZATION_FIELDS, "authorization.profiles"))
    protected_profile_sha256 = profile_auth.get("protected_profile_sha256")
    review_attestations_path = profile_auth.get("review_attestations_path")
    protected_review_attestations_sha256 = profile_auth.get("protected_review_attestations_sha256")
    if not _is_sha256(protected_profile_sha256):
        auth_findings.append(Finding("qualification", "authorization protected_profile_sha256 is not a valid digest"))
    if not _is_text(review_attestations_path):
        auth_findings.append(Finding("qualification", "authorization review_attestations_path is not valid text"))
    if not _is_sha256(protected_review_attestations_sha256):
        auth_findings.append(
            Finding("qualification", "authorization protected_review_attestations_sha256 is not a valid digest")
        )
    if auth_findings:
        return None, auth_findings
    assert isinstance(protected_profile_sha256, str)
    assert isinstance(review_attestations_path, str)
    assert isinstance(protected_review_attestations_sha256, str)

    record, findings = resolve_qualified_profile(root, declaration.profile_id)
    if record is None:
        return None, findings

    try:
        expected_review_bindings, _ = load_json(root, review_attestations_path)
    except (ValueError, TypeError) as exc:
        return None, findings + [Finding("qualification", f"cannot load review attestations: {exc}")]
    attestations_sha256 = canonical_sha256(expected_review_bindings)
    if not hmac.compare_digest(attestations_sha256, protected_review_attestations_sha256):
        return None, findings + [
            Finding("qualification", "review attestations do not match the protected authorization digest")
        ]

    protection_findings = validate_profile(
        record,
        suite,
        suite_sha256,
        expected_review_bindings=expected_review_bindings,
        evaluation_time=now,
        protected_profile_sha256=protected_profile_sha256,
    )
    if protection_findings:
        return None, findings + [
            Finding("qualification", f"protected qualification validation failed: {f.message}")
            for f in protection_findings
        ]

    specialty_auth_root = authorization.get("specialty")
    profile_specialty_auth: dict[str, Any] = {}
    if isinstance(specialty_auth_root, dict):
        candidate_specialty_auth = specialty_auth_root.get(declaration.profile_id)
        if isinstance(candidate_specialty_auth, dict):
            profile_specialty_auth = candidate_specialty_auth
    specialty: dict[str, tuple[float, int]] = {}
    for domain in declaration.specialty_domains:
        entry = profile_specialty_auth.get(domain)
        if not isinstance(entry, dict):
            findings.append(
                Finding(
                    "specialty_evidence",
                    f"no protected authorization entry exists for profile_id {declaration.profile_id!r} domain {domain!r}",
                )
            )
            continue
        entry_findings = _unknown_fields(entry, SPECIALTY_AUTHORIZATION_FIELDS, "authorization.specialty")
        entry_findings.extend(_required_fields(entry, SPECIALTY_AUTHORIZATION_FIELDS, "authorization.specialty"))
        record_path = entry.get("specialty_evidence_path")
        expected_specialty_sha256 = entry.get("protected_specialty_evidence_sha256")
        if not _is_text(record_path):
            entry_findings.append(Finding("specialty_evidence", "authorization specialty_evidence_path is not valid text"))
        if not _is_sha256(expected_specialty_sha256):
            entry_findings.append(
                Finding("specialty_evidence", "authorization protected_specialty_evidence_sha256 is not a valid digest")
            )
        if entry_findings:
            findings.extend(entry_findings)
            continue
        assert isinstance(record_path, str)
        assert isinstance(expected_specialty_sha256, str)
        try:
            specialty_record, _ = load_json(root, record_path)
        except (ValueError, TypeError) as exc:
            findings.append(Finding("specialty_evidence", f"{record_path}: cannot load: {exc}"))
            continue
        actual_specialty_digest = canonical_sha256(specialty_record)
        if not hmac.compare_digest(actual_specialty_digest, expected_specialty_sha256):
            findings.append(
                Finding(
                    "specialty_evidence",
                    f"{record_path}: does not match the protected authorization digest for "
                    f"{declaration.profile_id!r} domain {domain!r}",
                )
            )
            continue
        domain_findings = validate_specialty_evidence(specialty_record)
        if not domain_findings:
            domain_findings = verify_specialty_evidence_binding(root, specialty_record)
        if not domain_findings:
            domain_findings = verify_specialty_evidence_content(root, specialty_record)
        if domain_findings:
            findings.extend(domain_findings)
            continue
        if specialty_record.get("profile_id") != declaration.profile_id:
            findings.append(
                Finding(
                    "specialty_evidence",
                    f"{record_path}: bound to profile_id {specialty_record.get('profile_id')!r}, "
                    f"not candidate {declaration.profile_id!r}",
                )
            )
            continue
        if specialty_record.get("domain") != domain:
            findings.append(
                Finding(
                    "specialty_evidence",
                    f"{record_path}: record domain {specialty_record.get('domain')!r} does not match "
                    f"declared domain {domain!r}",
                )
            )
            continue
        specialty[domain] = (float(specialty_record["precision"]), int(specialty_record["sample_size"]))

    candidate = Candidate(
        profile_id=record["profile_id"],
        instance_id=declaration.instance_id,
        repository=record["repository"]["project"],
        repository_revision=record["repository"]["revision"],
        mode=record["mode"],
        suite_id=record["suite"]["suite_id"],
        suite_version=record["suite"]["suite_version"],
        environment_id=record["run"]["environment_id"],
        environment_sha256=record["run"]["environment_sha256"],
        tool_vendor=record["tool"]["vendor"],
        tool=record["tool"]["tool"],
        tool_version=record["tool"]["tool_version"],
        model_identifier=record["tool"]["model_identifier"],
        expires_at=record["expires_at"],
        environment_access=declaration.environment_access,
        cost_per_unit=declaration.cost_per_unit,
        specialty=specialty,
    )
    return candidate, findings


def select_candidate(
    candidates: list[Candidate],
    *,
    task_class: str,
    required_mode: str,
    required_domain: str | None,
    required_repository: str,
    required_repository_revision: str,
    required_suite_id: str,
    required_suite_version: str,
    required_environment_id: str,
    required_environment_sha256: str,
    required_environment_access: frozenset[str],
    cost_ceiling: float | None,
    now: Any,
    separation_exclusions: frozenset[str],
    required_tool_version: str | None = None,
    required_model_identifier: str | None = None,
) -> dict[str, Any]:
    """The routing decision over already-resolved Candidates (see
    resolve_candidate). Fail closed at every step; never silently downgrade
    a requirement, widen a dimension match, or override an exclusion to
    produce a result.

    required_repository_revision and required_environment_sha256 are
    mandatory, exactly-matched dimensions like repository/suite/
    environment_id -- they describe the task's actual context, which every
    candidate considered for the same task must match, not which candidate
    to pick. required_tool_version/required_model_identifier stay optional:
    routing exists to choose among tools/models, so pinning them is an
    opt-in exact constraint a caller supplies only when they specifically
    need one.

    This module does not otherwise judge repository-revision or
    environment "compatibility" beyond exact match, and performs no
    revocation check of its own. Per qualification-protocol-v1.1.md's own
    design, that judgment belongs to whoever maintains the `authorization`
    mapping resolve_candidate() consults (the Change Owner, or CI reading
    its protected variables) -- a profile drifts out of eligibility the
    moment its authorization entry is updated or removed, the same way
    AIDF_PROTECTED_PROFILE_SHA256_M0..M3 already governs Phase 8
    activation. Revocation is authorization absence, not a field this
    module tracks independently."""
    if task_class not in CLASSES:
        return {"result": "unavailable", "reason": f"unknown task_class {task_class!r}"}
    if required_mode not in MODES:
        return {"result": "unavailable", "reason": f"unknown required_mode {required_mode!r}"}
    if required_domain is not None and required_domain not in DOMAINS:
        return {"result": "unavailable", "reason": f"unknown required_domain {required_domain!r}"}
    if not _is_text(required_repository):
        return {"result": "unavailable", "reason": "required_repository is not valid text"}
    if not _is_revision(required_repository_revision):
        return {"result": "unavailable", "reason": "required_repository_revision is not valid"}
    if not _is_identifier(required_suite_id) or not _is_identifier(required_suite_version):
        return {"result": "unavailable", "reason": "required suite identity is not valid"}
    if not _is_identifier(required_environment_id):
        return {"result": "unavailable", "reason": "required_environment_id is not valid"}
    if not _is_sha256(required_environment_sha256):
        return {"result": "unavailable", "reason": "required_environment_sha256 is not valid"}
    if cost_ceiling is not None and not _is_finite_nonnegative_cost(cost_ceiling):
        return {"result": "unavailable", "reason": "cost_ceiling must be a finite non-negative, non-boolean number"}
    if required_tool_version is not None and not _is_identifier(required_tool_version):
        return {"result": "unavailable", "reason": "required_tool_version is not valid"}
    if required_model_identifier is not None and not _is_identifier(required_model_identifier):
        return {"result": "unavailable", "reason": "required_model_identifier is not valid"}

    eligible = [
        c
        for c in candidates
        if c.mode == required_mode
        and c.repository == required_repository
        and c.repository_revision == required_repository_revision
        and c.suite_id == required_suite_id
        and c.suite_version == required_suite_version
        and c.environment_id == required_environment_id
        and c.environment_sha256 == required_environment_sha256
        and _parse_utc(c.expires_at) is not None
        and _parse_utc(c.expires_at) > now
        and required_environment_access.issubset(c.environment_access)
        and _is_finite_nonnegative_cost(c.cost_per_unit)
        and (cost_ceiling is None or c.cost_per_unit <= cost_ceiling)
        and (required_tool_version is None or c.tool_version == required_tool_version)
        and (required_model_identifier is None or c.model_identifier == required_model_identifier)
    ]
    if not eligible:
        return {
            "result": "unavailable",
            "reason": "no candidate matches assignment dimensions, expiry, environment, cost, or declared pins",
        }

    if required_domain is not None:
        eligible = [
            c
            for c in eligible
            if required_domain in c.specialty
            and c.specialty[required_domain][0] >= MIN_SPECIALTY_PRECISION
            and c.specialty[required_domain][1] >= MIN_SPECIALTY_SAMPLE
        ]
        if not eligible:
            return {
                "result": "unavailable",
                "reason": f"no candidate has qualified specialty evidence for domain {required_domain!r}",
            }

    def sort_key(candidate: Candidate) -> tuple[float, float]:
        precision = (
            -candidate.specialty[required_domain][0] if required_domain else 0.0
        )
        return (precision, candidate.cost_per_unit)

    ranked = sorted(eligible, key=sort_key)

    excluded_for_separation = [c.instance_id for c in ranked if c.instance_id in separation_exclusions]
    survivors = [c for c in ranked if c.instance_id not in separation_exclusions]
    if not survivors:
        return {
            "result": "unavailable",
            "reason": "every eligible candidate is excluded by separation of duties",
            "excluded_for_separation": excluded_for_separation,
        }

    selected = survivors[0]
    provisional = task_class in ("T2", "T3")
    return {
        "result": "provisional_selection" if provisional else "selected",
        "selected_profile_id": selected.profile_id,
        "selected_instance_id": selected.instance_id,
        "requires_architect_confirmation": provisional,
        "eligible_count": len(survivors),
        "excluded_for_separation": excluded_for_separation,
    }


def _find_excluded_key(value: Any, excluded: tuple[str, ...]) -> str | None:
    """Recursively search for any excluded field name at any depth -- an
    included field (e.g. evidence_pack) can itself carry a nested excluded
    key, which a top-level-only check would miss."""
    if isinstance(value, dict):
        for key, sub_value in value.items():
            if isinstance(key, str) and key in excluded:
                return key
            found = _find_excluded_key(sub_value, excluded)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_excluded_key(item, excluded)
            if found is not None:
                return found
    return None


def _context_value_invalid(key: str, value: Any) -> bool:
    if value is None:
        return True
    if key in _TEXT_CONTEXT_FIELDS:
        return not (isinstance(value, str) and value.strip())
    if key in _COLLECTION_CONTEXT_FIELDS:
        return not isinstance(value, (list, dict))
    return False


def generate_handoff_package(role: str, full_context: dict[str, Any]) -> dict[str, Any]:
    """Construct the curated context slice for a role. Fails closed: raises
    if any field the role's contract declares required is absent, null, or
    of the wrong kind for its content type -- a "text" field (e.g. kernel,
    head_sha) must be a non-empty, non-whitespace-only string, so False or
    "" are rejected exactly like None; a "collection" field (e.g.
    evidence_pack, tests) must be an actual list or dict, but may
    legitimately be empty. Excluded fields are checked absent at every
    depth in the assembled package, not only at the top level."""
    spec = ROLE_CONTEXT_SPEC.get(role)
    if spec is None:
        raise ValueError(f"unknown role {role!r}; must be one of {sorted(ROLE_CONTEXT_SPEC)}")
    invalid = [key for key in spec["include"] if _context_value_invalid(key, full_context.get(key))]
    if invalid:
        raise ValueError(f"cannot build {role} handoff package: missing or invalid required context {invalid}")
    package = {key: full_context[key] for key in spec["include"]}
    leaked = _find_excluded_key(package, spec["exclude"])
    if leaked is not None:
        raise AssertionError(f"excluded field {leaked!r} leaked into {role} package")
    return package


def _validate_against_fields(
    payload: dict[str, Any], allowed: set[str], required: set[str], name: str
) -> list[Finding]:
    findings = _unknown_fields(payload, allowed, name)
    findings.extend(_required_fields(payload, required, name))
    return findings


def _string_list_or_finding(value: Any, name: str) -> tuple[frozenset[str] | None, Finding | None]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None, Finding(name, f"{name} must be an array of strings")
    return frozenset(value), None


def _load_and_verify_suite(root: Path, suite_path: str, expected_suite_sha256_arg: str) -> tuple[dict[str, Any], str] | None:
    suite, _ = load_json(root, suite_path)
    suite_sha256 = canonical_sha256(suite)
    try:
        expected_suite_sha256 = _expected_sha256(expected_suite_sha256_arg, "--expected-suite-sha256")
    except ValueError as exc:
        print(f"FAIL [input] {exc}")
        return None
    if not hmac.compare_digest(suite_sha256, expected_suite_sha256):
        print("FAIL [suite] canonical suite JSON does not match the protected SHA-256")
        return None
    return suite, suite_sha256


def _load_and_verify_authorization(
    root: Path, authorization_path: str, expected_authorization_sha256_arg: str
) -> dict[str, Any] | None:
    """Load the authorization mapping and confirm it matches an
    independently protected digest supplied by the caller -- exactly the
    suite's own pattern. This file is the ONLY source of the digests that
    establish trust for a profile_id or a specialty claim; it must be
    supplied and protected separately from the declarations file naming
    candidates."""
    authorization, _ = load_json(root, authorization_path)
    authorization_sha256 = canonical_sha256(authorization)
    try:
        expected_authorization_sha256 = _expected_sha256(
            expected_authorization_sha256_arg, "--expected-authorization-sha256"
        )
    except ValueError as exc:
        print(f"FAIL [input] {exc}")
        return None
    if not hmac.compare_digest(authorization_sha256, expected_authorization_sha256):
        print("FAIL [authorization] canonical authorization JSON does not match the protected SHA-256")
        return None
    if not isinstance(authorization, dict) or _unknown_fields(authorization, {"profiles", "specialty"}, "authorization") != []:
        print("FAIL [authorization] authorization document has unknown top-level fields")
        return None
    return authorization


def _run_route(root: Path, args: argparse.Namespace) -> int:
    now = _parse_utc(args.now)
    if now is None:
        print("FAIL [input] --now must be an exact UTC timestamp")
        return 1

    loaded_suite = _load_and_verify_suite(root, args.suite, args.expected_suite_sha256)
    if loaded_suite is None:
        return 1
    suite, suite_sha256 = loaded_suite

    authorization = _load_and_verify_authorization(root, args.authorization, args.expected_authorization_sha256)
    if authorization is None:
        return 1

    declarations_doc, _ = load_json(root, args.declarations)
    requirement, _ = load_json(root, args.requirement)

    requirement_findings = _validate_against_fields(
        requirement, REQUIREMENT_FIELDS, REQUIREMENT_REQUIRED_FIELDS, "requirement"
    )
    if requirement_findings:
        for finding in requirement_findings:
            print(f"FAIL [{finding.check}] {finding.message}")
        return 1

    required_environment_access, access_finding = _string_list_or_finding(
        requirement.get("required_environment_access", []), "requirement.required_environment_access"
    )
    if access_finding is not None:
        print(f"FAIL [{access_finding.check}] {access_finding.message}")
        return 1
    separation_exclusions, exclusions_finding = _string_list_or_finding(
        requirement.get("separation_exclusions", []), "requirement.separation_exclusions"
    )
    if exclusions_finding is not None:
        print(f"FAIL [{exclusions_finding.check}] {exclusions_finding.message}")
        return 1

    raw_declarations = declarations_doc.get("declarations")
    if not isinstance(raw_declarations, list):
        print("FAIL [declarations] declarations file must contain a 'declarations' array")
        return 1

    candidates: list[Candidate] = []
    for index, raw in enumerate(raw_declarations):
        if not isinstance(raw, dict):
            print(f"REJECTED [declarations] declarations[{index}] must be an object")
            continue
        declaration_findings = _validate_against_fields(
            raw, DECLARATION_FIELDS, DECLARATION_REQUIRED_FIELDS, f"declarations[{index}]"
        )
        if declaration_findings:
            for finding in declaration_findings:
                print(f"REJECTED [{finding.check}] {finding.message}")
            continue
        environment_access, env_finding = _string_list_or_finding(
            raw.get("environment_access", []), f"declarations[{index}].environment_access"
        )
        if env_finding is not None:
            print(f"REJECTED [{env_finding.check}] {env_finding.message}")
            continue
        specialty_domains, domains_finding = _string_list_or_finding(
            raw.get("specialty_domains", []), f"declarations[{index}].specialty_domains"
        )
        if domains_finding is not None:
            print(f"REJECTED [{domains_finding.check}] {domains_finding.message}")
            continue
        declaration = CandidateDeclaration(
            profile_id=raw.get("profile_id", ""),
            instance_id=raw.get("instance_id", ""),
            environment_access=environment_access if environment_access is not None else frozenset(),
            cost_per_unit=raw.get("cost_per_unit"),
            specialty_domains=specialty_domains if specialty_domains is not None else frozenset(),
        )
        resolved, resolution_findings = resolve_candidate(
            root, declaration, suite=suite, suite_sha256=suite_sha256, authorization=authorization, now=now
        )
        for finding in resolution_findings:
            print(f"REJECTED [declarations[{index}].{finding.check}] {finding.message}")
        if resolved is not None:
            candidates.append(resolved)

    decision = select_candidate(
        candidates,
        task_class=requirement.get("task_class", ""),
        required_mode=requirement.get("required_mode", ""),
        required_domain=requirement.get("required_domain"),
        required_repository=requirement.get("required_repository", ""),
        required_repository_revision=requirement.get("required_repository_revision", ""),
        required_suite_id=requirement.get("required_suite_id", ""),
        required_suite_version=requirement.get("required_suite_version", ""),
        required_environment_id=requirement.get("required_environment_id", ""),
        required_environment_sha256=requirement.get("required_environment_sha256", ""),
        required_environment_access=required_environment_access or frozenset(),
        required_tool_version=requirement.get("required_tool_version"),
        required_model_identifier=requirement.get("required_model_identifier"),
        cost_ceiling=requirement.get("cost_ceiling"),
        now=now,
        separation_exclusions=separation_exclusions or frozenset(),
    )
    print(json.dumps(decision, sort_keys=True))
    return 0 if decision.get("result") != "unavailable" else 1


def _run_specialty(root: Path, args: argparse.Namespace) -> int:
    """Validate a specialty_evidence record end to end, including that it is
    the exact record the authorization mapping vouches for and that its
    named profile passes full protected qualification -- a PASS here means
    genuinely protected qualification, not merely a well-shaped file."""
    now = _parse_utc(args.now)
    if now is None:
        print("FAIL [input] --now must be an exact UTC timestamp")
        return 1
    loaded_suite = _load_and_verify_suite(root, args.suite, args.expected_suite_sha256)
    if loaded_suite is None:
        return 1
    suite, suite_sha256 = loaded_suite
    authorization = _load_and_verify_authorization(root, args.authorization, args.expected_authorization_sha256)
    if authorization is None:
        return 1

    record, _ = load_json(root, args.record)
    findings = validate_specialty_evidence(record)
    if not findings:
        findings = verify_specialty_evidence_binding(root, record)
    if not findings:
        findings = verify_specialty_evidence_content(root, record)
    if findings:
        for finding in findings:
            print(f"FAIL [{finding.check}] {finding.message}")
        return 1

    profile_id = record["profile_id"]
    domain = record["domain"]
    declaration = CandidateDeclaration(
        profile_id=profile_id,
        instance_id="specialty-command-probe",
        environment_access=frozenset(),
        cost_per_unit=0.0,
        specialty_domains=frozenset({domain}),
    )
    resolved, resolution_findings = resolve_candidate(
        root, declaration, suite=suite, suite_sha256=suite_sha256, authorization=authorization, now=now
    )
    if resolved is None or domain not in resolved.specialty:
        for finding in resolution_findings:
            print(f"FAIL [{finding.check}] {finding.message}")
        if not resolution_findings:
            print(f"FAIL [specialty_evidence] {profile_id!r} domain {domain!r} did not resolve under authorization")
        return 1

    # The submitted record must itself be the authorized one, not merely an
    # equivalent-looking record for the same profile_id/domain.
    specialty_auth_root = authorization.get("specialty")
    profile_specialty_auth = specialty_auth_root.get(profile_id) if isinstance(specialty_auth_root, dict) else None
    entry = profile_specialty_auth.get(domain) if isinstance(profile_specialty_auth, dict) else None
    expected_digest = entry.get("protected_specialty_evidence_sha256") if isinstance(entry, dict) else None
    if not isinstance(expected_digest, str) or not hmac.compare_digest(canonical_sha256(record), expected_digest):
        print("FAIL [specialty_evidence] submitted record does not match the protected authorization digest")
        return 1

    print("PASS: specialty evidence is protected-authorized end to end")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    specialty_parser = subparsers.add_parser(
        "specialty",
        help="validate a specialty_evidence record against protected authorization end to end",
    )
    specialty_parser.add_argument("--record", required=True)
    specialty_parser.add_argument("--suite", required=True)
    specialty_parser.add_argument("--expected-suite-sha256", required=True)
    specialty_parser.add_argument("--authorization", required=True)
    specialty_parser.add_argument("--expected-authorization-sha256", required=True)
    specialty_parser.add_argument("--now", required=True)
    specialty_parser.add_argument("--root", default=".")

    route_parser = subparsers.add_parser(
        "route", help="resolve declared candidates against protected authorization and select one"
    )
    route_parser.add_argument("--declarations", required=True)
    route_parser.add_argument("--requirement", required=True)
    route_parser.add_argument("--suite", required=True)
    route_parser.add_argument("--expected-suite-sha256", required=True)
    route_parser.add_argument("--authorization", required=True)
    route_parser.add_argument("--expected-authorization-sha256", required=True)
    route_parser.add_argument("--now", required=True)
    route_parser.add_argument("--root", default=".")

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    try:
        if args.command == "specialty":
            return _run_specialty(root, args)
        if args.command == "route":
            return _run_route(root, args)
        print(f"FAIL [input] unknown command: {args.command}")
        return 1
    except (OSError, TypeError, UnicodeError, ValueError) as exc:
        print(f"FAIL [input] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
