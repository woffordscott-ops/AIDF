#!/usr/bin/env python3
"""Deterministic Phase 2 AIDF checks. Standard library only; no network access."""

from __future__ import annotations

import argparse
import base64
import binascii
import fnmatch
import hashlib
import hmac
import json
import math
import os
import re
import shlex
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, TypeGuard

MAX_JSON_BYTES = 256 * 1024
MAX_DIFF_BYTES = 10 * 1024 * 1024
MAX_LOCAL_CI_INCLUDES = 32
MAX_LOCAL_CI_INCLUDE_DEPTH = 8
MAX_LOCAL_CI_INCLUDE_BYTES = 2 * 1024 * 1024
CLASSES = ("T0", "T1", "T2", "T3")
E3_MECHANISMS = {
    "reversion test",
    "before/after reproduction",
    "failure reproduction",
    "mutation testing",
    "baseline comparison",
    "contract comparison",
    "performance benchmark",
    "architecture/invariant check",
    "other falsifiable mechanism",
}
CONTRACT_FIELDS = {
    "schema_version",
    "change_id",
    "class",
    "spec_confidence",
    "intended_outcome",
    "acceptance_criteria",
    "declared_scope",
    "tripwires",
    "approved_by",
    "approved_date",
    "dependency_changes",
}
EVIDENCE_FIELDS = {
    "schema_version",
    "change_id",
    "class",
    "falsification",
    "jurisdiction",
    "e0",
    "e1",
    "e2",
    "e3",
    "e4",
    "e5",
    "e6",
    "e7",
    "security_evidence",
    "residual_risk",
    "coverage_before",
    "coverage_after",
}
POLICY_FIELDS = {
    "schema_version",
    "exemptions_path",
    "dependency_manifests",
    "dependency_reference_rules",
    "dependency_content_lock",
    "tripwire_paths",
    "tripwire_content_terms",
    "tripwire_content_exclude",
}
AUTOMATION_POLICY_FIELDS = {
    "schema_version",
    "project_id",
    "risk_threshold",
    "human_involvement",
    "task_override_policy",
    "authorization",
}
AUTOMATION_ACTIONS = {
    "branch_create",
    "commit",
    "push",
    "merge_request_create",
    "ci_retry",
    "review_invoke",
    "remediation_apply",
    "merge",
}
AUTOMATION_CLASS_ORDER = {"none": -1, "T0": 0, "T1": 1, "T2": 2}
AUTOMATION_REMEDIATION_ORDER = {
    "none": 0,
    "mechanical_only": 1,
    "declared_scope": 2,
    "approved_task_contract": 3,
}
AUTOMATION_OVERRIDE_FIELDS = {
    "max_autonomous_class",
    "remediation_scope",
    "max_ci_retries",
    "checkpoint_actions",
    "notification_actions",
    "auto_merge_max_class",
}
AUTOMATION_RISK_PRESETS: dict[str, dict[str, Any]] = {
    "conservative": {
        "max_autonomous_class": "T0",
        "remediation_scope": "mechanical_only",
        "max_ci_retries": 1,
    },
    "standard": {
        "max_autonomous_class": "T1",
        "remediation_scope": "declared_scope",
        "max_ci_retries": 2,
    },
    "expanded": {
        "max_autonomous_class": "T2",
        "remediation_scope": "approved_task_contract",
        "max_ci_retries": 3,
    },
}
AUTOMATION_INVOLVEMENT_PRESETS: dict[str, dict[str, Any]] = {
    "guided": {
        "checkpoint_actions": [
            "commit",
            "push",
            "merge_request_create",
            "remediation_apply",
            "merge",
        ],
        "notification_actions": sorted(AUTOMATION_ACTIONS),
        "auto_merge_max_class": "none",
    },
    "checkpointed": {
        "checkpoint_actions": ["merge"],
        "notification_actions": [
            "merge_request_create",
            "remediation_apply",
            "ci_retry",
            "merge",
        ],
        "auto_merge_max_class": "none",
    },
    "streamlined": {
        "checkpoint_actions": [],
        "notification_actions": [
            "merge_request_create",
            "remediation_apply",
            "merge",
        ],
        "auto_merge_max_class": "T2",
    },
}
AUTOMATION_SAFE_FALLBACK: dict[str, Any] = {
    "risk_threshold": dict(AUTOMATION_RISK_PRESETS["conservative"]),
    "human_involvement": dict(AUTOMATION_INVOLVEMENT_PRESETS["guided"]),
    "effective_auto_merge_max_class": "none",
    "authorization_active": False,
}
SECURITY_EVIDENCE_FIELDS = {"status", "artifact", "artifact_sha256", "coverage_boundary"}
TRIPWIRE_FAMILIES = {
    "authentication-authorization-session-permissions",
    "cryptography-keys-secrets-tokens",
    "destructive-data-migrations",
    "regulated-data-privacy",
    "payments-billing-entitlements",
    "public-api-compatibility",
    "infrastructure",
    "production-configuration",
    "irreversibility",
}


@dataclass(frozen=True)
class Finding:
    check: str
    message: str


def _is_text(value: Any) -> TypeGuard[str]:
    return isinstance(value, str) and bool(value.strip())


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_repo_path(value: str, *, allow_glob: bool = False) -> bool:
    if (
        not _is_text(value)
        or "\\" in value
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        return False
    if value.startswith(("/", "~")) or re.match(r"^[A-Za-z]:", value):
        return False
    parts = PurePosixPath(value).parts
    if any(part in {"", ".", ".."} for part in parts):
        return False
    return allow_glob or not any(char in value for char in "*?[]")


def _resolve_input(root: Path, value: str) -> Path:
    if not _safe_repo_path(value):
        raise ValueError(f"input path must be a relative repository path: {value!r}")
    resolved = (root / value).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"input path escapes repository root: {value!r}") from exc
    return resolved


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for key, value in pairs:
        if key in parsed:
            raise ValueError(f"duplicate JSON object key {key!r}")
        parsed[key] = value
    return parsed


def _reject_nonfinite_json(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value!r} is not permitted")


def _parse_finite_json_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite JSON number {value!r} is not permitted")
    return parsed


def _strict_json_loads(value: str) -> Any:
    return json.loads(
        value,
        object_pairs_hook=_reject_duplicate_json_keys,
        parse_constant=_reject_nonfinite_json,
        parse_float=_parse_finite_json_float,
    )


def _is_schema_version_one(value: Any) -> bool:
    return type(value) is int and value == 1


def load_json(root: Path, value: str) -> dict[str, Any]:
    path = _resolve_input(root, value)
    size = path.stat().st_size
    if size > MAX_JSON_BYTES:
        raise ValueError(f"JSON input exceeds {MAX_JSON_BYTES} bytes: {value}")
    try:
        parsed = _strict_json_loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ValueError(f"cannot read strict JSON input {value}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise TypeError(f"JSON input must be an object: {value}")
    return parsed


def load_json_base64(value: str, name: str) -> dict[str, Any]:
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{name} is not valid strict base64: {exc}") from exc
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError(f"{name} exceeds {MAX_JSON_BYTES} decoded bytes")
    try:
        parsed = _strict_json_loads(raw.decode("utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ValueError(f"cannot decode strict JSON from {name}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise TypeError(f"{name} JSON must be an object")
    return parsed


def _unknown_fields(record: dict[str, Any], allowed: set[str], name: str) -> list[Finding]:
    return [
        Finding(name, f"unknown field {field!r}; correct or remove it")
        for field in sorted(set(record) - allowed)
    ]


def validate_contract(contract: dict[str, Any]) -> list[Finding]:
    findings = _unknown_fields(contract, CONTRACT_FIELDS, "contract")
    required = {
        "schema_version",
        "change_id",
        "class",
        "spec_confidence",
        "intended_outcome",
        "acceptance_criteria",
        "declared_scope",
        "tripwires",
        "dependency_changes",
    }
    for field in sorted(required - set(contract)):
        findings.append(Finding("contract", f"missing required field {field!r}"))
    if not _is_schema_version_one(contract.get("schema_version")):
        findings.append(Finding("contract", "schema_version must be 1"))
    task_class = contract.get("class")
    if task_class not in CLASSES:
        findings.append(Finding("contract", "class must be T0, T1, T2, or T3"))
    if contract.get("spec_confidence") != "Clear":
        findings.append(Finding("contract", "spec_confidence must be Clear before implementation"))
    for field in ("change_id", "intended_outcome"):
        if not _is_text(contract.get(field)):
            findings.append(Finding("contract", f"{field} must be non-empty text"))
    criteria = contract.get("acceptance_criteria")
    if not isinstance(criteria, list) or not criteria:
        findings.append(Finding("contract", "acceptance_criteria must be a non-empty list"))
    else:
        seen: set[str] = set()
        for index, criterion in enumerate(criteria):
            if not isinstance(criterion, dict) or set(criterion) != {"id", "text"}:
                findings.append(Finding("contract", f"acceptance_criteria[{index}] must contain only id and text"))
                continue
            criterion_id = criterion.get("id")
            if not _is_text(criterion_id) or not _is_text(criterion.get("text")):
                findings.append(Finding("contract", f"acceptance_criteria[{index}] id and text must be non-empty"))
            elif criterion_id in seen:
                findings.append(Finding("contract", f"duplicate acceptance criterion id {criterion_id!r}"))
            else:
                seen.add(criterion_id)
    scope = contract.get("declared_scope")
    if not isinstance(scope, list) or not scope:
        findings.append(Finding("contract", "declared_scope must be a non-empty list"))
    else:
        for pattern in scope:
            if not isinstance(pattern, str) or not _safe_repo_path(pattern, allow_glob=True):
                findings.append(Finding("contract", f"unsafe declared_scope pattern {pattern!r}"))
    tripwires = contract.get("tripwires")
    if not isinstance(tripwires, list) or any(not _is_text(item) for item in tripwires):
        findings.append(Finding("contract", "tripwires must be a list of non-empty identifiers"))
    elif unknown := set(tripwires) - TRIPWIRE_FAMILIES:
        findings.append(Finding("contract", f"unknown trip-wire identifiers {sorted(unknown)}"))
    if task_class in {"T2", "T3"}:
        if not _is_text(contract.get("approved_by")):
            findings.append(Finding("contract", "T2/T3 requires approved_by"))
        if not _valid_iso_date(contract.get("approved_date")):
            findings.append(Finding("contract", "T2/T3 requires approved_date in YYYY-MM-DD form"))
    dependency_changes = contract.get("dependency_changes")
    if not isinstance(dependency_changes, list):
        findings.append(Finding("contract", "dependency_changes must be a list"))
    else:
        for index, item in enumerate(dependency_changes):
            expected = {"path", "dependency", "pinned", "approved_by", "approval_reference"}
            if not isinstance(item, dict) or set(item) != expected:
                findings.append(Finding("contract", f"dependency_changes[{index}] must contain only {sorted(expected)}"))
                continue
            if not _safe_repo_path(item.get("path", "")):
                findings.append(Finding("contract", f"dependency_changes[{index}].path is unsafe"))
            if not _is_text(item.get("dependency")) or item.get("pinned") is not True:
                findings.append(Finding("contract", f"dependency_changes[{index}] requires a named, pinned dependency"))
            if not _is_text(item.get("approved_by")) or not _is_text(item.get("approval_reference")):
                findings.append(Finding("contract", f"dependency_changes[{index}] requires human approval and reference"))
    return findings


def _valid_iso_date(value: Any) -> TypeGuard[str]:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
        return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))
    except ValueError:
        return False


def _validate_result(evidence: dict[str, Any], level: str, findings: list[Finding]) -> None:
    value = evidence.get(level)
    expected = {"status", "artifact", "coverage_boundary"} if level == "e2" else {"status", "artifact"}
    if not isinstance(value, dict) or set(value) != expected:
        findings.append(Finding("evidence", f"{level} must contain only {', '.join(sorted(expected))}"))
        return
    allowed = {
        "e0": {"passed", "not applicable"},
        "e1": {"passed"},
        "e2": {"passed", "unavailable", "not applicable"},
    }[level]
    if value.get("status") not in allowed:
        findings.append(Finding("evidence", f"{level}.status must be one of {sorted(allowed)}"))
    if not _is_text(value.get("artifact")):
        findings.append(Finding("evidence", f"{level}.artifact must identify the command/result or gap reason"))
    if level == "e2" and not _is_text(value.get("coverage_boundary")):
        findings.append(Finding("evidence", "e2.coverage_boundary must be non-empty"))


def validate_evidence(
    evidence: dict[str, Any],
    contract: dict[str, Any],
    exemption_records: list[dict[str, Any]] | None = None,
) -> list[Finding]:
    findings = _unknown_fields(evidence, EVIDENCE_FIELDS, "evidence")
    task_class = contract.get("class")
    required = {"schema_version", "change_id", "class", "falsification", "jurisdiction", "e0", "e1", "e2", "residual_risk"}
    for field in sorted(required - set(evidence)):
        findings.append(Finding("evidence", f"missing required field {field!r}"))
    if not _is_schema_version_one(evidence.get("schema_version")):
        findings.append(Finding("evidence", "schema_version must be 1"))
    if evidence.get("change_id") != contract.get("change_id"):
        findings.append(Finding("evidence", "change_id must match the Task Contract"))
    if evidence.get("class") != task_class:
        findings.append(Finding("evidence", "class must match the Task Contract"))
    for field in ("falsification", "jurisdiction", "residual_risk"):
        if not _is_text(evidence.get(field)):
            findings.append(Finding("evidence", f"{field} must be non-empty text"))
    if _is_text(evidence.get("jurisdiction")) and "falsifiable correctness only" not in evidence["jurisdiction"].lower():
        findings.append(Finding("evidence", "jurisdiction must state that evidence covers falsifiable correctness only"))
    for level in ("e0", "e1", "e2"):
        _validate_result(evidence, level, findings)
    if task_class in {"T1", "T2", "T3"}:
        findings.extend(
            _validate_e3(
                evidence.get("e3"),
                task_class,
                contract.get("change_id"),
                exemption_records or [],
            )
        )
    for level in ("e4", "e5", "e6"):
        if task_class in {"T2", "T3"} and level not in evidence:
            findings.append(Finding("evidence", f"{task_class} requires {level}"))
    if task_class in {"T2", "T3"}:
        e4 = evidence.get("e4")
        criterion_ids = {item.get("id") for item in contract.get("acceptance_criteria", []) if isinstance(item, dict)}
        mapped = {item.get("criterion") for item in e4 if isinstance(item, dict)} if isinstance(e4, list) else set()
        if not isinstance(e4, list) or not e4 or mapped != criterion_ids:
            findings.append(Finding("evidence", "e4 must map every and only acceptance criterion id to a check"))
        else:
            for item in e4:
                expected = {"criterion", "check", "status", "artifact"}
                if set(item) != expected:
                    findings.append(Finding("evidence", f"each e4 item must contain only {sorted(expected)}"))
                    continue
                if item.get("status") != "passed":
                    findings.append(Finding("evidence", f"e4 criterion {item.get('criterion')!r} must have status 'passed'"))
                for field in ("check", "artifact"):
                    text = item.get(field)
                    if not _is_text(text):
                        findings.append(Finding("evidence", f"e4 criterion {item.get('criterion')!r} requires {field}"))
                    elif re.search(r"\b(?:pending|todo|not yet|after this|requires? final)\b", text, re.IGNORECASE):
                        findings.append(Finding("evidence", f"e4 criterion {item.get('criterion')!r} contains incomplete {field}"))
        for level in ("e5", "e6"):
            if not _is_text(evidence.get(level)):
                findings.append(Finding("evidence", f"{level} must be non-empty text"))
    if task_class == "T3":
        findings.extend(_validate_e7(evidence.get("e7")))
        security = evidence.get("security_evidence")
        if not isinstance(security, dict) or set(security) != SECURITY_EVIDENCE_FIELDS:
            findings.append(Finding("evidence", f"T3 security_evidence must contain only {sorted(SECURITY_EVIDENCE_FIELDS)}"))
        else:
            if security.get("status") != "passed":
                findings.append(Finding("evidence", "T3 security_evidence.status must be 'passed'"))
            for field in ("artifact", "coverage_boundary"):
                if not _is_text(security.get(field)):
                    findings.append(Finding("evidence", f"T3 security_evidence.{field} must be non-empty"))
            if not re.fullmatch(r"[0-9a-f]{64}", str(security.get("artifact_sha256", ""))):
                findings.append(Finding("evidence", "T3 security_evidence.artifact_sha256 must be a lowercase SHA-256"))
    return findings


def _validate_e3(
    value: Any,
    task_class: str,
    change_id: Any,
    exemption_records: list[dict[str, Any]],
) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(value, dict):
        return [Finding("evidence", f"{task_class} requires an e3 object")]
    status = value.get("status")
    if status == "satisfied":
        if set(value) != {"status", "mechanism", "artifact", "counterfactual"}:
            findings.append(Finding("evidence", "satisfied e3 must contain only status, mechanism, artifact, and counterfactual"))
        if value.get("mechanism") not in E3_MECHANISMS:
            findings.append(Finding("evidence", "e3 mechanism is not recognized"))
        for field in ("artifact", "counterfactual"):
            if not _is_text(value.get(field)):
                findings.append(Finding("evidence", f"e3.{field} must be non-empty"))
        return findings
    if status != "exempted":
        return [Finding("evidence", "e3.status must be satisfied or exempted")]
    if task_class == "T3":
        return [Finding("evidence", "T3 has no E3 exemption")]
    expected = {"status", "exemption_id"}
    if set(value) != expected:
        findings.append(Finding("evidence", f"{task_class} exempted e3 must contain only {sorted(expected)}"))
    exemption_id = value.get("exemption_id")
    if not _is_text(exemption_id):
        findings.append(Finding("evidence", "e3.exemption_id must be non-empty"))
        return findings
    matches = [record for record in exemption_records if record.get("exemption_id") == exemption_id]
    if len(matches) != 1:
        findings.append(Finding("evidence", f"e3 exemption {exemption_id!r} must resolve to exactly one registry record"))
        return findings
    record = matches[0]
    if record.get("status") != "Open":
        findings.append(Finding("evidence", f"e3 exemption {exemption_id!r} is not Open"))
    if record.get("class") != task_class or record.get("change_id") != change_id:
        findings.append(Finding("evidence", f"e3 exemption {exemption_id!r} must match the evidence class and change_id"))
    expiry = record.get("expiry")
    if not _valid_iso_date(expiry) or date.fromisoformat(expiry) < datetime.now(timezone.utc).date():
        findings.append(Finding("evidence", f"e3 exemption {exemption_id!r} is expired or invalid"))
    return findings


def _validate_e7(value: Any) -> list[Finding]:
    if not isinstance(value, dict):
        return [Finding("evidence", "T3 requires an e7 object")]
    findings: list[Finding] = []
    operation = value.get("operation")
    operational = {
        "operation",
        "status",
        "artifact",
        "operational_behavior",
        "failure_observability",
        "kill_switch",
        "unrecoverable_effects",
    }
    expected_by_operation = {
        "reversible": set(operational),
        "destructive but recoverable": {
            *operational,
            "representative_dataset",
            "measured_recovery_time",
        },
        "truly irreversible": {
            *operational,
            "recovery_point",
            "restore_path",
            "irrecoverable_effects",
            "human_acceptance",
        },
    }
    expected = expected_by_operation.get(operation) if isinstance(operation, str) else None
    if expected is None:
        findings.append(Finding("evidence", "e7.operation is invalid"))
        return findings
    if set(value) != expected:
        findings.append(Finding("evidence", f"e7 for {operation!r} must contain only {sorted(expected)}"))
    if value.get("status") != "passed":
        findings.append(Finding("evidence", "e7.status must be 'passed'"))
    if not _is_text(value.get("artifact")):
        findings.append(Finding("evidence", "e7.artifact must identify executed recovery evidence"))
    for field in expected - {"operation", "status"}:
        if not _is_text(value.get(field)):
            findings.append(Finding("evidence", f"e7.{field} must be non-empty"))
    return findings


def validate_policy(policy: dict[str, Any]) -> list[Finding]:
    findings = _unknown_fields(policy, POLICY_FIELDS, "policy")
    if not _is_schema_version_one(policy.get("schema_version")):
        findings.append(Finding("policy", "schema_version must be 1"))
    if not _safe_repo_path(policy.get("exemptions_path", "")):
        findings.append(Finding("policy", "exemptions_path must be a safe relative repository path"))
    for field in ("dependency_manifests", "dependency_reference_rules", "dependency_content_lock", "tripwire_paths", "tripwire_content_terms", "tripwire_content_exclude"):
        if not isinstance(policy.get(field), list):
            findings.append(Finding("policy", f"{field} must be a list"))
    dependency_manifests = _as_list(policy.get("dependency_manifests"))
    dependency_reference_rules = _as_list(policy.get("dependency_reference_rules"))
    dependency_content_lock = _as_list(policy.get("dependency_content_lock"))
    tripwire_paths = _as_list(policy.get("tripwire_paths"))
    tripwire_content_terms = _as_list(policy.get("tripwire_content_terms"))
    tripwire_content_exclude = _as_list(policy.get("tripwire_content_exclude"))
    for pattern in dependency_manifests:
        if not isinstance(pattern, str) or not _safe_repo_path(pattern, allow_glob=True):
            findings.append(Finding("policy", f"unsafe dependency manifest pattern {pattern!r}"))
    for item in dependency_reference_rules:
        if not isinstance(item, dict) or set(item) != {"pattern", "term"}:
            findings.append(Finding("policy", "dependency_reference_rules entries require only pattern and term"))
        elif not _safe_repo_path(item["pattern"], allow_glob=True) or not _is_text(item["term"]) or len(item["term"]) > 100:
            findings.append(Finding("policy", f"invalid dependency reference entry {item!r}"))
    for pattern in dependency_content_lock:
        if not isinstance(pattern, str) or not _safe_repo_path(pattern, allow_glob=True):
            findings.append(Finding("policy", f"unsafe dependency content-lock pattern {pattern!r}"))
    for item in tripwire_paths:
        if not isinstance(item, dict) or set(item) != {"id", "pattern"}:
            findings.append(Finding("policy", "tripwire_paths entries require only id and pattern"))
        elif not _is_text(item["id"]) or not _safe_repo_path(item["pattern"], allow_glob=True):
            findings.append(Finding("policy", f"invalid tripwire path entry {item!r}"))
    for item in tripwire_content_terms:
        if not isinstance(item, dict) or set(item) != {"id", "term"}:
            findings.append(Finding("policy", "tripwire_content_terms entries require only id and term"))
        elif not _is_text(item["id"]) or not _is_text(item["term"]) or len(item["term"]) > 100:
            findings.append(Finding("policy", f"invalid tripwire content entry {item!r}"))
    for pattern in tripwire_content_exclude:
        if not isinstance(pattern, str) or not _safe_repo_path(pattern, allow_glob=True):
            findings.append(Finding("policy", f"unsafe tripwire content exclusion {pattern!r}"))
    represented: set[str] = set()
    for items in (tripwire_paths, tripwire_content_terms):
        for item in items:
            if isinstance(item, dict) and _is_text(identifier := item.get("id")):
                represented.add(identifier)
    missing_families = TRIPWIRE_FAMILIES - represented
    if missing_families:
        findings.append(Finding("policy", f"trip-wire policy omits locked families {sorted(missing_families)}"))
    unknown_families = represented - TRIPWIRE_FAMILIES
    if unknown_families:
        findings.append(Finding("policy", f"trip-wire policy has unknown families {sorted(unknown_families)}"))
    return findings


def _bounded_policy_text(value: Any, limit: int) -> bool:
    return (
        _is_text(value)
        and len(value) <= limit
        and not any(ord(character) < 32 or ord(character) == 127 for character in value)
    )


def _automation_date(value: Any, field: str, findings: list[Finding]) -> date | None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        findings.append(Finding("automation-policy", f"authorization.{field} must be YYYY-MM-DD"))
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        findings.append(Finding("automation-policy", f"authorization.{field} is not a valid date"))
        return None


def _validate_action_set(value: Any, field: str) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(value, list) or len(value) > len(AUTOMATION_ACTIONS):
        return [Finding("automation-policy", f"human_involvement.{field} must be a bounded list")]
    if any(not isinstance(item, str) or item not in AUTOMATION_ACTIONS for item in value):
        findings.append(Finding("automation-policy", f"human_involvement.{field} has an unknown action"))
    string_actions = [item for item in value if isinstance(item, str)]
    if len(string_actions) != len(set(string_actions)):
        findings.append(Finding("automation-policy", f"human_involvement.{field} contains duplicates"))
    return findings


def validate_automation_policy(policy: dict[str, Any], *, today: date | None = None) -> list[Finding]:
    """Validate project automation policy without granting any human authority."""

    if not isinstance(policy, dict):
        return [Finding("automation-policy", "policy must be an object")]
    findings = _unknown_fields(policy, AUTOMATION_POLICY_FIELDS, "automation-policy")
    required = set(AUTOMATION_POLICY_FIELDS)
    for field in sorted(required - set(policy)):
        findings.append(Finding("automation-policy", f"missing required field {field!r}"))
    if not _is_schema_version_one(policy.get("schema_version")):
        findings.append(Finding("automation-policy", "schema_version must be 1"))
    project_id = policy.get("project_id")
    if (
        not isinstance(project_id, str)
        or len(project_id) > 128
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*", project_id)
    ):
        findings.append(Finding("automation-policy", "project_id must be a bounded project slug without traversal"))
    if policy.get("task_override_policy") != "tighten_only":
        findings.append(Finding("automation-policy", "task_override_policy must be 'tighten_only'"))

    risk = policy.get("risk_threshold")
    if not isinstance(risk, dict):
        findings.append(Finding("automation-policy", "risk_threshold must be an object"))
    elif risk.get("type") == "preset":
        findings.extend(_unknown_fields(risk, {"type", "preset"}, "automation-policy.risk_threshold"))
        if set(risk) != {"type", "preset"} or risk.get("preset") not in AUTOMATION_RISK_PRESETS:
            findings.append(Finding("automation-policy", "risk_threshold preset is invalid"))
    elif risk.get("type") == "custom":
        risk_fields = {"type", "max_autonomous_class", "remediation_scope", "max_ci_retries"}
        findings.extend(_unknown_fields(risk, risk_fields, "automation-policy.risk_threshold"))
        if set(risk) != risk_fields:
            findings.append(Finding("automation-policy", "custom risk_threshold is incomplete"))
        maximum_class = risk.get("max_autonomous_class")
        remediation = risk.get("remediation_scope")
        retries = risk.get("max_ci_retries")
        if maximum_class not in {"T0", "T1", "T2"}:
            findings.append(Finding("automation-policy", "custom max_autonomous_class must be T0, T1, or T2"))
        remediation_by_class = {
            "T0": {"none", "mechanical_only"},
            "T1": {"none", "mechanical_only", "declared_scope"},
            "T2": {"none", "mechanical_only", "declared_scope", "approved_task_contract"},
        }
        if maximum_class in remediation_by_class and remediation not in remediation_by_class[maximum_class]:
            findings.append(Finding("automation-policy", "custom remediation_scope exceeds its class ceiling"))
        if type(retries) is not int or not 0 <= retries <= 3:
            findings.append(Finding("automation-policy", "custom max_ci_retries must be an integer from 0 through 3"))
    else:
        findings.append(Finding("automation-policy", "risk_threshold.type must be 'preset' or 'custom'"))

    involvement = policy.get("human_involvement")
    if not isinstance(involvement, dict):
        findings.append(Finding("automation-policy", "human_involvement must be an object"))
    elif involvement.get("type") == "preset":
        findings.extend(_unknown_fields(involvement, {"type", "preset"}, "automation-policy.human_involvement"))
        if set(involvement) != {"type", "preset"} or involvement.get("preset") not in AUTOMATION_INVOLVEMENT_PRESETS:
            findings.append(Finding("automation-policy", "human_involvement preset is invalid"))
    elif involvement.get("type") == "custom":
        involvement_fields = {"type", "checkpoint_actions", "notification_actions", "auto_merge_max_class"}
        findings.extend(_unknown_fields(involvement, involvement_fields, "automation-policy.human_involvement"))
        if set(involvement) != involvement_fields:
            findings.append(Finding("automation-policy", "custom human_involvement is incomplete"))
        findings.extend(_validate_action_set(involvement.get("checkpoint_actions"), "checkpoint_actions"))
        findings.extend(_validate_action_set(involvement.get("notification_actions"), "notification_actions"))
        if involvement.get("auto_merge_max_class") not in AUTOMATION_CLASS_ORDER:
            findings.append(Finding("automation-policy", "custom auto_merge_max_class must be none, T0, T1, or T2"))
    else:
        findings.append(Finding("automation-policy", "human_involvement.type must be 'preset' or 'custom'"))

    authorization = policy.get("authorization")
    authorization_fields = {"grantor", "recorded_roles", "approval_reference", "granted_on", "expires_on", "status"}
    if not isinstance(authorization, dict):
        findings.append(Finding("automation-policy", "authorization must be an object"))
    else:
        findings.extend(_unknown_fields(authorization, authorization_fields, "automation-policy.authorization"))
        if set(authorization) != authorization_fields:
            findings.append(Finding("automation-policy", "authorization is incomplete"))
        if not _bounded_policy_text(authorization.get("grantor"), 128):
            findings.append(Finding("automation-policy", "authorization.grantor must be bounded text"))
        if not _bounded_policy_text(authorization.get("approval_reference"), 256):
            findings.append(Finding("automation-policy", "authorization.approval_reference must be bounded text"))
        roles = authorization.get("recorded_roles")
        if (
            not isinstance(roles, list)
            or len(roles) != 2
            or any(not isinstance(role, str) for role in roles)
            or set(roles) != {"Change Owner", "Architect"}
        ):
            findings.append(Finding("automation-policy", "authorization.recorded_roles must contain Change Owner and Architect"))
        granted = _automation_date(authorization.get("granted_on"), "granted_on", findings)
        expires = _automation_date(authorization.get("expires_on"), "expires_on", findings)
        check_date = today or datetime.now(timezone.utc).date()
        if granted and expires and granted > expires:
            findings.append(Finding("automation-policy", "authorization expires before it is granted"))
        if granted and granted > check_date:
            findings.append(Finding("automation-policy", "authorization is not yet effective"))
        if expires and expires < check_date:
            findings.append(Finding("automation-policy", "authorization is expired"))
        if authorization.get("status") != "active":
            findings.append(Finding("automation-policy", "authorization.status must be 'active' for autonomous use"))
    return findings


def _safe_automation_profile() -> dict[str, Any]:
    return {
        "risk_threshold": dict(AUTOMATION_SAFE_FALLBACK["risk_threshold"]),
        "human_involvement": {
            "checkpoint_actions": list(AUTOMATION_SAFE_FALLBACK["human_involvement"]["checkpoint_actions"]),
            "notification_actions": list(AUTOMATION_SAFE_FALLBACK["human_involvement"]["notification_actions"]),
            "auto_merge_max_class": "none",
        },
        "effective_auto_merge_max_class": "none",
        "authorization_active": False,
        "task_override_applied": False,
    }


def automation_policy_sha256(policy: Any) -> str:
    """Return the stable semantic digest that protected policy must bind."""

    canonical = json.dumps(
        policy,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_automation_override(override: Any, active_profile: dict[str, Any]) -> list[Finding]:
    """Reject any task-local override that is not a strict or equal tightening."""

    if not isinstance(override, dict) or not override:
        return [Finding("automation-override", "task override must be a non-empty object")]
    findings = _unknown_fields(override, AUTOMATION_OVERRIDE_FIELDS, "automation-override")
    risk = active_profile["risk_threshold"]
    involvement = active_profile["human_involvement"]
    maximum_class = override.get("max_autonomous_class")
    if "max_autonomous_class" in override and (
        not isinstance(maximum_class, str)
        or maximum_class not in AUTOMATION_CLASS_ORDER
        or maximum_class == "none"
        or AUTOMATION_CLASS_ORDER[maximum_class] > AUTOMATION_CLASS_ORDER[risk["max_autonomous_class"]]
    ):
        findings.append(Finding("automation-override", "max_autonomous_class must not exceed the project ceiling"))
    remediation = override.get("remediation_scope")
    if "remediation_scope" in override and (
        not isinstance(remediation, str)
        or remediation not in AUTOMATION_REMEDIATION_ORDER
        or AUTOMATION_REMEDIATION_ORDER[remediation] > AUTOMATION_REMEDIATION_ORDER[risk["remediation_scope"]]
    ):
        findings.append(Finding("automation-override", "remediation_scope must not exceed the project ceiling"))
    retries = override.get("max_ci_retries")
    if "max_ci_retries" in override and (type(retries) is not int or not 0 <= retries <= risk["max_ci_retries"]):
        findings.append(Finding("automation-override", "max_ci_retries must not exceed the project ceiling"))
    for field in ("checkpoint_actions", "notification_actions"):
        if field in override:
            findings.extend(_validate_action_set(override[field], field))
            if (
                isinstance(override[field], list)
                and all(isinstance(item, str) for item in override[field])
                and not set(involvement[field]).issubset(set(override[field]))
            ):
                findings.append(Finding("automation-override", f"{field} may add but not remove project actions"))
    merge_class = override.get("auto_merge_max_class")
    if "auto_merge_max_class" in override and (
        not isinstance(merge_class, str)
        or merge_class not in AUTOMATION_CLASS_ORDER
        or AUTOMATION_CLASS_ORDER[merge_class] > AUTOMATION_CLASS_ORDER[involvement["auto_merge_max_class"]]
    ):
        findings.append(Finding("automation-override", "auto_merge_max_class must not exceed the project ceiling"))
    effective_class = maximum_class if isinstance(maximum_class, str) else risk["max_autonomous_class"]
    effective_remediation = remediation if isinstance(remediation, str) else risk["remediation_scope"]
    remediation_by_class = {
        "T0": {"none", "mechanical_only"},
        "T1": {"none", "mechanical_only", "declared_scope"},
        "T2": set(AUTOMATION_REMEDIATION_ORDER),
    }
    if effective_class in remediation_by_class and effective_remediation not in remediation_by_class[effective_class]:
        findings.append(Finding("automation-override", "remediation_scope exceeds the override class ceiling"))
    return findings


def resolve_automation_policy(
    policy: dict[str, Any],
    *,
    expected_project_id: str,
    expected_policy_sha256: str,
    task_override: dict[str, Any] | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Return a project-bound normalized profile or the immutable safe fallback."""

    try:
        invalid_policy = validate_automation_policy(policy, today=today)
        actual_digest = automation_policy_sha256(policy)
    except (TypeError, ValueError):
        return _safe_automation_profile()
    if (
        invalid_policy
        or not isinstance(expected_project_id, str)
        or policy.get("project_id") != expected_project_id
        or not isinstance(expected_policy_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", expected_policy_sha256)
        or not hmac.compare_digest(actual_digest, expected_policy_sha256)
    ):
        return _safe_automation_profile()
    risk_value = policy["risk_threshold"]
    risk: dict[str, Any] = (
        dict(AUTOMATION_RISK_PRESETS[risk_value["preset"]])
        if risk_value["type"] == "preset"
        else {field: risk_value[field] for field in ("max_autonomous_class", "remediation_scope", "max_ci_retries")}
    )
    involvement_value = policy["human_involvement"]
    source: dict[str, Any] = (
        AUTOMATION_INVOLVEMENT_PRESETS[involvement_value["preset"]]
        if involvement_value["type"] == "preset"
        else involvement_value
    )
    involvement: dict[str, Any] = {
        "checkpoint_actions": list(source["checkpoint_actions"]),
        "notification_actions": list(source["notification_actions"]),
        "auto_merge_max_class": source["auto_merge_max_class"],
    }
    active_profile = {"risk_threshold": risk, "human_involvement": involvement}
    if task_override is not None:
        try:
            override_findings = validate_automation_override(task_override, active_profile)
            if override_findings:
                return _safe_automation_profile()
            if "max_autonomous_class" in task_override:
                risk["max_autonomous_class"] = task_override["max_autonomous_class"]
            if "remediation_scope" in task_override:
                risk["remediation_scope"] = task_override["remediation_scope"]
            if "max_ci_retries" in task_override:
                risk["max_ci_retries"] = task_override["max_ci_retries"]
            for field in ("checkpoint_actions", "notification_actions", "auto_merge_max_class"):
                if field in task_override:
                    involvement[field] = list(task_override[field]) if field.endswith("_actions") else task_override[field]
        except (KeyError, TypeError, ValueError):
            return _safe_automation_profile()
    try:
        merge_ceiling = min(
            AUTOMATION_CLASS_ORDER[risk["max_autonomous_class"]],
            AUTOMATION_CLASS_ORDER[involvement["auto_merge_max_class"]],
        )
        effective_merge = next(name for name, order in AUTOMATION_CLASS_ORDER.items() if order == merge_ceiling)
    except (KeyError, TypeError, ValueError, StopIteration):
        return _safe_automation_profile()
    return {
        "risk_threshold": risk,
        "human_involvement": involvement,
        "effective_auto_merge_max_class": effective_merge,
        "authorization_active": True,
        "task_override_applied": task_override is not None,
    }


def validate_exemptions(records: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    open_count = 0
    common = {
        "schema_version",
        "exemption_id",
        "change_id",
        "class",
        "mechanisms_attempted",
        "approved_by",
        "expiry",
        "status",
        "retirement_evidence",
    }
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            findings.append(Finding("exemptions", f"record {index} must be an object"))
            continue
        task_class = record.get("class")
        expected = set(common)
        if task_class == "T2":
            expected |= {"verifier_recommendation", "residual_risk"}
        if set(record) != expected:
            findings.append(Finding("exemptions", f"record {index} must contain only {sorted(expected)}"))
        if not _is_schema_version_one(record.get("schema_version")) or task_class not in {"T1", "T2"}:
            findings.append(Finding("exemptions", f"record {index} requires schema_version 1 and class T1 or T2"))
        for field in expected - {"schema_version", "status", "retirement_evidence", "expiry"}:
            if not _is_text(record.get(field)):
                findings.append(Finding("exemptions", f"record {index}.{field} must be non-empty"))
        status = record.get("status")
        if status not in {"Open", "Retired", "Expired"}:
            findings.append(Finding("exemptions", f"record {index}.status must be Open, Retired, or Expired"))
        if not _valid_iso_date(record.get("expiry")):
            findings.append(Finding("exemptions", f"record {index}.expiry must be YYYY-MM-DD"))
        elif status == "Open" and date.fromisoformat(record["expiry"]) < datetime.now(timezone.utc).date():
            findings.append(Finding("exemptions", f"record {index} is expired but still marked Open"))
        if status == "Open":
            open_count += 1
        if status == "Retired" and not _is_text(record.get("retirement_evidence")):
            findings.append(Finding("exemptions", f"record {index} requires retirement_evidence"))
    if open_count > 5:
        findings.append(Finding("exemptions", f"{open_count} exemptions are open; the hard cap is 5"))
    return findings


def load_exemption_records(root: Path, policy: dict[str, Any]) -> tuple[list[dict[str, Any]], list[Finding]]:
    value = policy.get("exemptions_path")
    if not isinstance(value, str):
        return [], [Finding("exemptions", "policy does not define a valid exemptions_path")]
    directory = _resolve_input(root, value)
    if not directory.exists():
        return [], []
    if not directory.is_dir():
        return [], [Finding("exemptions", f"{value} must be a directory")]
    files = sorted(directory.glob("*.json"))
    if len(files) > 100:
        return [], [Finding("exemptions", "more than 100 exemption files found; archive retired records or split the registry")]
    records: list[dict[str, Any]] = []
    for path in files:
        try:
            relative = path.resolve().relative_to(root).as_posix()
        except ValueError:
            return [], [Finding("exemptions", f"exemption path escapes repository root: {path}")]
        try:
            records.append(load_json(root, relative))
        except ValueError as exc:
            return [], [Finding("exemptions", str(exc))]
    return records, validate_exemptions(records)


def check_exemption_directory(root: Path, policy: dict[str, Any]) -> list[Finding]:
    _, findings = load_exemption_records(root, policy)
    return findings


def _matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern) or (pattern.startswith("**/") and fnmatch.fnmatchcase(path, pattern[3:]))


def check_scope(changed_files: Iterable[str], contract: dict[str, Any]) -> list[Finding]:
    patterns = contract.get("declared_scope", [])
    findings: list[Finding] = []
    for path in changed_files:
        if not _safe_repo_path(path):
            findings.append(Finding("scope", f"unsafe changed path {path!r}"))
        elif not any(_matches(path, pattern) for pattern in patterns):
            findings.append(Finding("scope", f"{path} is outside declared scope; re-declare or split the change"))
    return findings


@dataclass(frozen=True)
class ParsedDiff:
    added: tuple[tuple[str, str], ...]
    removed: tuple[tuple[str, str], ...]
    touched: frozenset[str]


def _header_path(value: str, expected_prefix: str) -> str | None:
    if value == "/dev/null":
        return None
    if not value.startswith(expected_prefix):
        raise ValueError(f"malformed unified-diff path header {value!r}")
    path = value[len(expected_prefix):]
    if not _safe_repo_path(path):
        raise ValueError(f"unsafe unified-diff path {path!r}")
    return path


def parse_unified_diff(diff_text: str) -> ParsedDiff:
    """Parse Git's zero-context unified diff without confusing hunk data for headers."""
    added: list[tuple[str, str]] = []
    removed: list[tuple[str, str]] = []
    touched: set[str] = set()
    diff_old_path: str | None = None
    diff_new_path: str | None = None
    old_path: str | None = None
    new_path: str | None = None
    current_path: str | None = None
    saw_old_header = False
    saw_new_header = False
    is_new_file = False
    is_deleted_file = False
    in_hunk = False
    saw_diff_header = False
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            try:
                parts = shlex.split(line)
            except ValueError as exc:
                raise ValueError(f"malformed diff header: {exc}") from exc
            if len(parts) != 4 or parts[:2] != ["diff", "--git"]:
                raise ValueError("malformed diff --git header")
            diff_old_path = _header_path(parts[2], "a/")
            diff_new_path = _header_path(parts[3], "b/")
            if diff_old_path != diff_new_path:
                raise ValueError("cross-path diff sections are not permitted when diff generation disables renames")
            if diff_old_path:
                touched.add(diff_old_path)
            if diff_new_path:
                touched.add(diff_new_path)
            old_path = new_path = current_path = None
            saw_old_header = saw_new_header = False
            is_new_file = is_deleted_file = False
            in_hunk = False
            saw_diff_header = True
            continue
        if not saw_diff_header:
            if line:
                raise ValueError("unified diff must begin with a diff --git header")
            continue
        if not in_hunk and line.startswith("--- "):
            if saw_old_header:
                raise ValueError("duplicate unified-diff old file header")
            old_path = _header_path(line[4:], "a/")
            if old_path is None and not is_new_file:
                raise ValueError("/dev/null old file header requires new file mode")
            if is_new_file and old_path is not None:
                raise ValueError("new file mode requires /dev/null old file header")
            if old_path is not None and old_path != diff_old_path:
                raise ValueError(
                    f"unified-diff old file header {old_path!r} disagrees with diff --git path {diff_old_path!r}"
                )
            saw_old_header = True
            continue
        if not in_hunk and line.startswith("+++ "):
            if saw_new_header:
                raise ValueError("duplicate unified-diff new file header")
            new_path = _header_path(line[4:], "b/")
            if new_path is None and not is_deleted_file:
                raise ValueError("/dev/null new file header requires deleted file mode")
            if is_deleted_file and new_path is not None:
                raise ValueError("deleted file mode requires /dev/null new file header")
            if new_path is not None and new_path != diff_new_path:
                raise ValueError(
                    f"unified-diff new file header {new_path!r} disagrees with diff --git path {diff_new_path!r}"
                )
            saw_new_header = True
            continue
        if line.startswith("@@ "):
            if not saw_old_header or not saw_new_header:
                raise ValueError("diff hunk is missing file headers")
            current_path = new_path or old_path
            in_hunk = True
            continue
        if in_hunk and line.startswith("+"):
            if new_path is not None:
                added.append((new_path, line[1:]))
            continue
        if in_hunk and line.startswith("-"):
            if old_path is not None:
                removed.append((old_path, line[1:]))
            continue
        if in_hunk and (line.startswith(" ") or line == r"\ No newline at end of file"):
            continue
        if not in_hunk and line.startswith("new file mode "):
            if is_deleted_file:
                raise ValueError("diff cannot be both a new and deleted file")
            if saw_old_header or saw_new_header:
                raise ValueError("new file mode must precede unified-diff file headers")
            is_new_file = True
            continue
        if not in_hunk and line.startswith("deleted file mode "):
            if is_new_file:
                raise ValueError("diff cannot be both a new and deleted file")
            if saw_old_header or saw_new_header:
                raise ValueError("deleted file mode must precede unified-diff file headers")
            is_deleted_file = True
            continue
        if not in_hunk and line.startswith(("rename from ", "rename to ")):
            raise ValueError("rename metadata is not permitted when diff generation disables renames")
        if line.startswith(("index ", "old mode ", "new mode ", "similarity index ", "dissimilarity index ", "Binary files ")):
            continue
        if line:
            raise ValueError(f"unsupported or malformed unified-diff line for {current_path or 'header'}")
    return ParsedDiff(tuple(added), tuple(removed), frozenset(touched))


def added_lines(diff_text: str) -> list[tuple[str, str]]:
    return list(parse_unified_diff(diff_text).added)


def removed_lines(diff_text: str) -> list[tuple[str, str]]:
    return list(parse_unified_diff(diff_text).removed)


def check_diff_consistency(changed_files: Iterable[str], diff_text: str) -> list[Finding]:
    changed = set(changed_files)
    parsed = parse_unified_diff(diff_text)
    if parsed.touched != changed:
        return [Finding("diff", f"changed-file artifact and diff disagree: names={sorted(changed)!r}, diff={sorted(parsed.touched)!r}")]
    return []


def detect_tripwires(changed_files: Iterable[str], diff_text: str, policy: dict[str, Any]) -> set[str]:
    signals: set[str] = set()
    tripwire_paths = _as_list(policy.get("tripwire_paths"))
    for path in changed_files:
        for rule in tripwire_paths:
            if (
                isinstance(rule, dict)
                and _is_text(rule.get("id"))
                and _is_text(rule.get("pattern"))
                and _matches(path, rule["pattern"])
            ):
                signals.add(rule["id"])
    exclusions_value = policy.get("tripwire_content_exclude")
    exclusions = [item for item in exclusions_value if isinstance(item, str)] if isinstance(exclusions_value, list) else []
    lowered_lines = [
        line.lower()
        for path, line in added_lines(diff_text)
        if not any(_matches(path, pattern) for pattern in exclusions)
    ]
    content_rules = _as_list(policy.get("tripwire_content_terms"))
    for rule in content_rules:
        if not isinstance(rule, dict) or not _is_text(rule.get("id")) or not _is_text(rule.get("term")):
            continue
        term = rule["term"].lower()
        if any(term in line for line in lowered_lines):
            signals.add(rule["id"])
    return signals


def check_tripwires(changed_files: Iterable[str], diff_text: str, policy: dict[str, Any], contract: dict[str, Any]) -> list[Finding]:
    signals = detect_tripwires(changed_files, diff_text, policy)
    findings: list[Finding] = []
    declared = {item for item in _as_list(contract.get("tripwires")) if isinstance(item, str)}
    if (signals or declared) and contract.get("class") != "T3":
        identifiers = signals | declared
        findings.append(Finding("tripwires", f"signals or declarations {sorted(identifiers)} force T3; update and approve the Task Contract"))
    missing = signals - declared
    if missing:
        findings.append(Finding("tripwires", f"declare detected trip-wire identifiers {sorted(missing)} in the Task Contract"))
    return findings


def _content_dependency(root: Path | None, path: str) -> str:
    if root is None:
        return "unresolved-manifest-content"
    candidate = root / path
    if candidate.is_symlink():
        return "unresolved-manifest-symlink"
    try:
        target = _resolve_input(root, path)
    except ValueError:
        return "unresolved-manifest-content"
    if not target.exists():
        return "manifest-removal"
    if not target.is_file() or target.stat().st_size > MAX_JSON_BYTES:
        return "unresolved-manifest-content"
    try:
        text = target.read_bytes().decode("utf-8", errors="strict")
    except UnicodeError:
        return "unresolved-manifest-content"
    canonical = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return f"content-sha256:{hashlib.sha256(canonical).hexdigest()}"


def _yaml_key_pattern(key: str) -> str:
    escaped = re.escape(key)
    return rf'(?:{escaped}|"{escaped}"|\'{escaped}\')'


def _decode_yaml_double_quoted_scalar(token: str) -> str | None:
    escapes = {
        "0": "\0", "a": "\a", "b": "\b", "t": "\t", "n": "\n", "v": "\v", "f": "\f",
        "r": "\r", "e": "\x1b", " ": " ", '"': '"', "/": "/", "\\": "\\", "N": "\x85",
        "_": "\xa0", "L": "\u2028", "P": "\u2029",
    }
    inner = token[1:-1]
    decoded: list[str] = []
    index = 0
    while index < len(inner):
        if inner[index] != "\\":
            decoded.append(inner[index])
            index += 1
            continue
        index += 1
        if index >= len(inner):
            return None
        marker = inner[index]
        if marker in escapes:
            decoded.append(escapes[marker])
            index += 1
            continue
        widths = {"x": 2, "u": 4, "U": 8}
        width = widths.get(marker)
        if width is None or index + width >= len(inner):
            return None
        digits = inner[index + 1:index + 1 + width]
        if not re.fullmatch(rf"[0-9A-Fa-f]{{{width}}}", digits):
            return None
        try:
            decoded.append(chr(int(digits, 16)))
        except ValueError:
            return None
        index += width + 1
    return "".join(decoded)


def _normalize_yaml_key(line: str, key: str) -> str:
    quoted_key = re.compile(
        r'(?P<prefix>^|[\s,{{\[\-])'
        r'(?P<token>"(?:\\.|[^"\\])*"|\'(?:\'\'|[^\'])*\')(?P<suffix>\s*:)',
    )

    def replace(match: re.Match[str]) -> str:
        token = match.group("token")
        decoded = (
            _decode_yaml_double_quoted_scalar(token)
            if token.startswith('"')
            else token[1:-1].replace("''", "'")
        )
        if decoded != key:
            return match.group(0)
        return f'{match.group("prefix")}{key}{match.group("suffix")}'

    return quoted_key.sub(replace, line)


def _yaml_structural_key_colons(line: str, key: str) -> list[int]:
    """Locate mapping-key colons outside comments, quotes, and scalar text."""
    if not line.strip() or line.lstrip().startswith("#"):
        return []
    candidates: set[int] = set()
    leading = len(line) - len(line.lstrip(" "))
    block_start = leading
    sequence = re.match(r"-\s+", line[leading:])
    if sequence is not None:
        block_start += sequence.end()
    candidates.add(block_start)
    block_key = r'(?:"(?:\\.|[^"\\])*"|\'(?:\'\'|[^\'])*\'|[^\s?:,\[\]{}#]+)'

    quote: str | None = None
    escaped = False
    flow_depth = 0
    index = 0
    while index < len(line):
        character = line[index]
        if escaped:
            escaped = False
            index += 1
            continue
        if quote == '"' and character == "\\":
            escaped = True
            index += 1
            continue
        if quote is not None:
            if character == quote:
                if quote == "'" and index + 1 < len(line) and line[index + 1] == "'":
                    index += 2
                    continue
                quote = None
            index += 1
            continue
        if character in "'\"":
            quote = character
            index += 1
            continue
        if character == "#" and (index == 0 or line[index - 1].isspace()):
            break
        previous_nonspace = index - 1
        while previous_nonspace >= 0 and line[previous_nonspace].isspace():
            previous_nonspace -= 1
        block_value_prefix = re.fullmatch(
            rf"{block_key}\s*:\s+[\[\s,]*",
            line[block_start:index],
        )
        flow_mapping_start = character == "{" and (
            index == block_start
            or previous_nonspace < 0
            or block_value_prefix is not None
            or (flow_depth > 0 and line[previous_nonspace] in "[,:")
        )
        if flow_mapping_start:
            flow_depth += 1
            candidates.add(index + 1)
        elif character == "}":
            flow_depth = max(0, flow_depth - 1)
        elif character == "," and flow_depth:
            candidates.add(index + 1)
        index += 1

    colons: list[int] = []
    for candidate in sorted(candidates):
        cursor = candidate
        while cursor < len(line) and line[cursor].isspace():
            cursor += 1
        if cursor >= len(line) or line[cursor] in "?&*!":
            continue
        if line[cursor] in "'\"":
            delimiter = line[cursor]
            token_start = cursor
            cursor += 1
            escaped = False
            while cursor < len(line):
                character = line[cursor]
                if delimiter == '"' and not escaped and character == "\\":
                    escaped = True
                    cursor += 1
                    continue
                if character == delimiter and not escaped:
                    if delimiter == "'" and cursor + 1 < len(line) and line[cursor + 1] == "'":
                        cursor += 2
                        continue
                    cursor += 1
                    break
                escaped = False
                cursor += 1
            token = line[token_start:cursor]
            decoded = (
                _decode_yaml_double_quoted_scalar(token)
                if delimiter == '"'
                else token[1:-1].replace("''", "'")
            )
        else:
            token_start = cursor
            while cursor < len(line) and not line[cursor].isspace() and line[cursor] not in ":,{}[]#":
                cursor += 1
            decoded = line[token_start:cursor]
        while cursor < len(line) and line[cursor].isspace():
            cursor += 1
        if decoded == key and cursor < len(line) and line[cursor] == ":":
            colons.append(cursor)
    return colons


def _yaml_key_values(line: str, key: str) -> list[str]:
    """Extract simple YAML scalar values for a key, including quoted keys.

    The CI dependency gate intentionally supports only the scalar forms it can
    validate without executing a general YAML loader. Unsupported constructs
    yield no value and therefore fall through to the manifest content lock.
    """
    scalar = r'(?P<token>"(?:\\.|[^"\\])*"|\'(?:\'\'|[^\'])*\'|[^\s,}\]#]+)'
    values: list[str] = []
    for colon in _yaml_structural_key_colons(line, key):
        match = re.match(rf"\s*{scalar}", line[colon + 1:])
        if match is None:
            continue
        token = match.group("token")
        if token.startswith('"'):
            value = _decode_yaml_double_quoted_scalar(token)
        elif token.startswith("'"):
            value = token[1:-1].replace("''", "'")
        else:
            value = token
        if value:
            values.append(value)
    return values


def _yaml_has_key(line: str, key: str) -> bool:
    return bool(_yaml_structural_key_colons(line, key))


def _yaml_has_explicit_key(line: str, key: str) -> bool:
    """Recognize YAML's explicit ``? key`` mapping-key form."""
    match = re.fullmatch(
        r'\s*(?:-\s*)?\?\s*'
        r'(?P<token>"(?:\\.|[^"\\])*"|\'(?:\'\'|[^\'])*\'|[^\s#]+)'
        r'\s*(?:#.*)?',
        line,
    )
    if match is None:
        return False
    token = match.group("token")
    if token.startswith('"'):
        decoded = _decode_yaml_double_quoted_scalar(token)
    elif token.startswith("'"):
        decoded = token[1:-1].replace("''", "'")
    else:
        decoded = token
    return decoded == key


CI_SUPPORTED_EXPLICIT_KEYS = frozenset({
    "image", "name", "TRIVY_DB_REPOSITORY", "include", "project", "ref", "file",
    "remote", "component", "template", "local",
})


def _yaml_has_unsupported_explicit_key(line: str) -> bool:
    if re.match(r"\s*(?:-\s*)?\?", line) is None and re.search(r"[{,]\s*\?", line) is None:
        return False
    return not any(_yaml_has_explicit_key(line, key) for key in CI_SUPPORTED_EXPLICIT_KEYS)


def _yaml_has_unsupported_key_syntax(line: str) -> bool:
    """Reject key syntaxes the deterministic CI parser cannot safely bind."""
    if _yaml_has_unsupported_explicit_key(line):
        return True
    key_start = r"(?:^\s*(?:-\s*)?|[{,]\s*)"
    node_property_key = rf"{key_start}(?:(?:!{{1,2}}|&)\S+\s+\S+\s*:|\*\S+\s*:)"
    return re.search(node_property_key, line) is not None


def _yaml_values_at(material: Sequence[str], index: int, key: str) -> tuple[bool, list[str]]:
    """Return presence and scalar values for ordinary or explicit YAML keys.

    Unsupported or incomplete forms report the key as present without a value,
    which makes the dependency gate fail closed.
    """
    line = material[index]
    values = _yaml_key_values(line, key)
    if _yaml_has_key(line, key):
        return True, values
    if not _yaml_has_explicit_key(line, key):
        return False, []
    for nearby in material[index + 1:index + 6]:
        stripped = nearby.strip()
        if not stripped or stripped.startswith("#"):
            continue
        value_line = re.fullmatch(r"\s*:\s*(?P<value>.*)", nearby)
        if value_line is None:
            return True, []
        return True, _yaml_key_values(f"{key}: {value_line.group('value')}", key)
    return True, []


def _yaml_mapping_value_at(material: Sequence[str], index: int, key: str) -> tuple[bool, str | None]:
    """Return the unparsed value text for an ordinary or explicit mapping key."""
    colons = _yaml_structural_key_colons(material[index], key)
    if colons:
        return True, material[index][colons[0] + 1:].strip()
    if not _yaml_has_explicit_key(material[index], key):
        return False, None
    for nearby in material[index + 1:index + 6]:
        stripped = nearby.strip()
        if not stripped or stripped.startswith("#"):
            continue
        value_line = re.fullmatch(r"\s*:\s*(?P<value>.*)", nearby)
        return True, value_line.group("value").strip() if value_line is not None else None
    return True, None


def _yaml_mapping_position(line: str) -> tuple[int, int | None]:
    """Return a mapping key's structural column and enclosing sequence column."""
    leading = len(line) - len(line.lstrip(" "))
    remainder = line[leading:]
    sequence = re.match(r"-\s+", remainder)
    if sequence is None:
        return leading, None
    return leading + sequence.end(), leading


def _yaml_sibling_values(
    material: Sequence[str],
    index: int,
    key: str,
) -> tuple[bool, list[str]]:
    """Read a key only from the same YAML mapping as the source at index."""
    source_column, sequence_column = _yaml_mapping_position(material[index])
    for nearby_index in range(index + 1, len(material)):
        nearby = material[nearby_index]
        stripped = nearby.strip()
        if not stripped or stripped.startswith("#"):
            continue
        nearby_leading = len(nearby) - len(nearby.lstrip(" "))
        if (
            sequence_column is not None
            and nearby_leading == sequence_column
            and re.match(r"-\s+", nearby[nearby_leading:]) is not None
        ):
            break
        nearby_column, _ = _yaml_mapping_position(nearby)
        if nearby_column < source_column:
            break
        if nearby_column != source_column:
            continue
        present, values = _yaml_values_at(material, nearby_index, key)
        if present:
            return True, values
    return False, []


def _yaml_is_top_level_key(line: str, key: str) -> bool:
    """Recognize a key only at the root mapping, never in comments or scalars."""
    if not line or line[0].isspace() or line.lstrip().startswith("#"):
        return False
    if line.lstrip().startswith("{"):
        return bool(_yaml_structural_key_colons(line, key))
    normalized = _normalize_yaml_key(line, key).strip()
    pattern = _yaml_key_pattern(key)
    return re.match(rf"^(?:{pattern}\s*:|\?\s*{pattern}(?:\s|$)|\{{\s*{pattern}\s*:)", normalized) is not None


def _yaml_block_scalar_body_indexes(material: Sequence[str]) -> set[int]:
    """Identify literal/folded scalar bodies so payload text is never parsed as YAML."""
    bodies: set[int] = set()
    parent_column: int | None = None
    key_token = r'(?:(?:"(?:\\.|[^"\\])*")|(?:\'(?:\'\'|[^\'])*\')|(?:[^\s?:,\[\]{}#]+))'
    opener = re.compile(
        rf"^\s*(?:-\s+)?{key_token}\s*:\s*[|>][1-9+\-]{{0,2}}\s*(?:#.*)?$",
    )
    for index, line in enumerate(material):
        stripped = line.strip()
        if parent_column is not None:
            if not stripped:
                bodies.add(index)
                continue
            indentation = len(line) - len(line.lstrip(" "))
            if indentation > parent_column:
                bodies.add(index)
                continue
            parent_column = None
        if stripped and not line.lstrip().startswith("#") and opener.fullmatch(line):
            parent_column, _ = _yaml_mapping_position(line)
    return bodies


def _ci_include_candidate_indexes(material: Sequence[str]) -> set[int]:
    """Return only structural lines belonging directly to root include entries."""
    candidates: set[int] = set()
    for index, line in enumerate(material):
        if not _yaml_is_top_level_key(line, "include"):
            continue
        candidates.add(index)
        _, value_text = _yaml_mapping_value_at(material, index, "include")
        if value_text:
            continue
        direct_indentation: int | None = None
        item_column: int | None = None
        for nearby_index in range(index + 1, len(material)):
            nearby = material[nearby_index]
            stripped = nearby.strip()
            if not stripped or stripped.startswith("#"):
                continue
            leading = len(nearby) - len(nearby.lstrip(" "))
            if leading == 0:
                break
            if direct_indentation is None:
                direct_indentation = leading
            if leading < direct_indentation:
                break
            column, sequence_column = _yaml_mapping_position(nearby)
            if sequence_column == direct_indentation:
                item_column = column
                candidates.add(nearby_index)
                continue
            if item_column is not None:
                if column == item_column:
                    candidates.add(nearby_index)
                continue
            if column == direct_indentation:
                candidates.add(nearby_index)
    return candidates


def _yaml_scalar(token: str) -> str | None:
    """Decode one bounded YAML scalar without interpreting tags, aliases, or code."""
    token = token.strip()
    if not token or token[0] in "!&*{}[]":
        return None
    if token.startswith('"'):
        if len(token) < 2 or not token.endswith('"'):
            return None
        return _decode_yaml_double_quoted_scalar(token)
    if token.startswith("'"):
        if len(token) < 2 or not token.endswith("'"):
            return None
        return token[1:-1].replace("''", "'")
    value = token.split(" #", 1)[0].strip()
    return value if value and not any(character.isspace() for character in value) else None


def _yaml_flow_scalars(value: str) -> list[str] | None:
    """Parse a simple YAML flow sequence of scalar include sources."""
    value = value.strip()
    if len(value) < 2 or value[0] != "[" or value[-1] != "]":
        return None
    tokens: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False
    for character in value[1:-1]:
        if escaped:
            current.append(character)
            escaped = False
            continue
        if quote == '"' and character == "\\":
            current.append(character)
            escaped = True
            continue
        if quote is not None:
            current.append(character)
            if character == quote:
                quote = None
            continue
        if character in "'\"":
            current.append(character)
            quote = character
            continue
        if character == ",":
            token = _yaml_scalar("".join(current))
            if token is None:
                return None
            tokens.append(token)
            current = []
            continue
        if character in "{}[]":
            return None
        current.append(character)
    if quote is not None or escaped:
        return None
    tail = "".join(current).strip()
    if tail:
        token = _yaml_scalar(tail)
        if token is None:
            return None
        tokens.append(token)
    return tokens


def _normalize_local_ci_include(value: str) -> str | None:
    """Canonicalize one GitLab local include and reject dynamic or glob syntax."""
    value = value.strip().removeprefix("/")
    if not value or "$" in value or any(character in value for character in "*?[]{}"):
        return None
    return PurePosixPath(value).as_posix() if _safe_repo_path(value) else None


def _classify_ci_include_scalar(
    value: str,
    references: set[tuple[str, str]],
    local_includes: set[str],
) -> None:
    """Classify GitLab's scalar include shorthand without fetching anything."""
    if re.fullmatch(r"https?://[^\s]+", value, re.IGNORECASE):
        references.add((f"remote:{value}", "ci-remote-include"))
        return
    local = _normalize_local_ci_include(value)
    if local is None:
        references.add(("unresolved-include-scalar", "ci-local-include"))
    else:
        local_includes.add(local)


def _ci_include_shorthand(
    lines: Sequence[str],
) -> tuple[set[tuple[str, str]], set[str]]:
    """Extract documented scalar, sequence, and flow-sequence include shorthands."""
    references: set[tuple[str, str]] = set()
    local_includes: set[str] = set()
    for index, line in enumerate(lines):
        if not _yaml_is_top_level_key(line, "include"):
            continue
        present, value_text = _yaml_mapping_value_at(lines, index, "include")
        if not present:
            continue
        if value_text:
            if value_text.startswith("["):
                values = _yaml_flow_scalars(value_text)
                if values is None:
                    references.add(("unresolved-include-flow", "ci-local-include"))
                for value in values or []:
                    _classify_ci_include_scalar(value, references, local_includes)
            elif value_text.startswith("{"):
                # Flow mappings are handled by the explicit source-key scan.
                if not any(_yaml_has_key(line, key) for key in ("remote", "project", "component", "template", "local")):
                    references.add(("unresolved-include-flow", "ci-local-include"))
            else:
                scalar = _yaml_scalar(value_text)
                if scalar is None:
                    references.add(("unresolved-include-scalar", "ci-local-include"))
                else:
                    _classify_ci_include_scalar(scalar, references, local_includes)
            continue

        indentation = len(line) - len(line.lstrip(" "))
        recognized_block_item = False
        sequence_indentation: int | None = None
        for nearby in lines[index + 1:]:
            if not nearby.strip() or nearby.lstrip().startswith("#"):
                continue
            nearby_indentation = len(nearby) - len(nearby.lstrip(" "))
            if nearby_indentation <= indentation:
                break
            item = re.fullmatch(r"\s*-\s*(?P<value>.+?)\s*", nearby)
            if item is None:
                continue
            if sequence_indentation is None:
                sequence_indentation = nearby_indentation
            elif nearby_indentation != sequence_indentation:
                continue
            payload = item.group("value")
            if any(_yaml_has_key(payload, key) for key in ("remote", "project", "component", "template", "local")):
                recognized_block_item = True
                continue
            if payload.startswith("{"):
                references.add(("unresolved-include-flow", "ci-local-include"))
                continue
            scalar = _yaml_scalar(payload)
            if scalar is None:
                references.add(("unresolved-include-scalar", "ci-local-include"))
            else:
                _classify_ci_include_scalar(scalar, references, local_includes)
            recognized_block_item = True
        if not recognized_block_item:
            source_found = any(
                any(_yaml_values_at(lines, nearby_index, key)[0] for key in ("remote", "project", "component", "template", "local"))
                for nearby_index in range(index + 1, min(index + 10, len(lines)))
            )
            if not source_found:
                references.add(("unresolved-include-block", "ci-local-include"))
    return references, local_includes


def _ci_external_references(lines: Iterable[str]) -> tuple[set[tuple[str, str]], set[str]]:
    """Extract external and repository-local CI include sources."""
    references: set[tuple[str, str]] = set()
    material = list(lines)
    shorthand_references, local_includes = _ci_include_shorthand(material)
    references.update(shorthand_references)
    for index in sorted(_ci_include_candidate_indexes(material)):
        remote_present, remote_values = _yaml_values_at(material, index, "remote")
        for remote in remote_values:
            references.add((f"remote:{remote}", "ci-remote-include"))
        if remote_present and not remote_values:
            references.add(("unresolved-remote-include", "ci-remote-include"))
        project_present, project_values = _yaml_values_at(material, index, "project")
        for project in project_values:
            ref = "unresolved-ref"
            _, inline_refs = _yaml_values_at(material, index, "ref")
            if len(inline_refs) == 1:
                ref = inline_refs[0]
            if ref == "unresolved-ref":
                sibling_present, sibling_refs = _yaml_sibling_values(material, index, "ref")
                if sibling_present and len(sibling_refs) == 1:
                    ref = sibling_refs[0]
            references.add((f"gitlab-project:{project}@{ref}", "ci-project-include"))
        if project_present and not project_values:
            references.add(("unresolved-project-include", "ci-project-include"))
        component_present, component_values = _yaml_values_at(material, index, "component")
        for component in component_values:
            references.add((f"component:{component}", "ci-component-include"))
        if component_present and not component_values:
            references.add(("unresolved-component-include", "ci-component-include"))
        template_present, template_values = _yaml_values_at(material, index, "template")
        for template in template_values:
            references.add((f"template:{template}", "ci-template-include"))
        if template_present and not template_values:
            references.add(("unresolved-template-include", "ci-template-include"))
        local_present, local_values = _yaml_values_at(material, index, "local")
        for local_value in local_values:
            local = _normalize_local_ci_include(local_value)
            if local is None:
                references.add(("unresolved-local-include", "ci-local-include"))
            else:
                local_includes.add(local)
        if local_present and not local_values:
            references.add(("unresolved-local-include", "ci-local-include"))
    return references, local_includes


def _manifest_symlinks(root: Path, patterns: Iterable[Any]) -> list[str]:
    """Return configured dependency manifests that are symbolic links."""
    found: list[str] = []
    for directory, directories, files in os.walk(root, followlinks=False):
        base = Path(directory)
        directories[:] = [
            name for name in directories
            if name != ".git" and not (base / name).is_symlink()
        ]
        for name in files:
            candidate = base / name
            if not candidate.is_symlink():
                continue
            relative = candidate.relative_to(root).as_posix()
            if any(isinstance(pattern, str) and _matches(relative, pattern) for pattern in patterns):
                found.append(relative)
    return sorted(found)


def _repo_path_has_symlink(root: Path, path: str) -> bool:
    """Reject a symlink in any component of a repository-relative path."""
    candidate = root
    for part in PurePosixPath(path).parts:
        candidate = candidate / part
        if candidate.is_symlink():
            return True
    return False


def _read_local_ci_include(root: Path, path: str) -> tuple[list[str] | None, str | None, int]:
    """Read one local CI include with path, symlink, encoding, and size bounds."""
    if _repo_path_has_symlink(root, path):
        return None, "unresolved-local-include-symlink", 0
    try:
        target = _resolve_input(root, path)
        if not target.is_file():
            return None, "manifest-removal", 0
        size = target.stat().st_size
        if size > MAX_JSON_BYTES:
            return None, "unresolved-local-include-size", size
        return target.read_text(encoding="utf-8", errors="strict").splitlines(), None, size
    except (OSError, UnicodeError, ValueError):
        return None, "unresolved-local-include-content", 0


def _ci_dependency_values(lines: Sequence[str]) -> set[tuple[str, str]]:
    """Inventory executable CI dependencies in one current-commit YAML file."""
    references, _ = _ci_external_references(lines)
    scalar_bodies = _yaml_block_scalar_body_indexes(lines)
    for index, line in enumerate(lines):
        if index in scalar_bodies:
            continue
        if _yaml_has_unsupported_key_syntax(line):
            references.add(("unresolved-yaml-key-syntax", "image"))
        for key in ("image", "TRIVY_DB_REPOSITORY"):
            present, direct = _yaml_values_at(lines, index, key)
            if direct:
                for dependency in direct:
                    references.add((dependency, "image"))
                continue
            if not present:
                continue
            nested_found = False
            if key == "image":
                for nested_line in lines[index + 1:index + 4]:
                    if not nested_line.strip():
                        continue
                    for dependency in _yaml_key_values(nested_line, "name"):
                        references.add((dependency, "image"))
                        nested_found = True
                    break
            if not nested_found:
                references.add((f"unresolved-yaml-scalar:{key}", "image"))
    return references


def _ci_local_include_graph(
    root: Path,
) -> tuple[
    dict[str, list[str] | None],
    dict[str, set[str]],
    dict[str, set[tuple[str, str]]],
]:
    """Build a bounded, no-network graph of repository-local GitLab CI includes."""
    files: dict[str, list[str] | None] = {}
    edges: dict[str, set[str]] = {}
    errors: dict[str, set[tuple[str, str]]] = {}
    active: set[str] = set()
    total_bytes = 0

    def visit(path: str, depth: int) -> None:
        nonlocal total_bytes
        if path in active:
            errors.setdefault(path, set()).add(("unresolved-local-include-cycle", "ci-local-include"))
            return
        if path in files:
            return
        if depth > MAX_LOCAL_CI_INCLUDE_DEPTH or len(files) >= MAX_LOCAL_CI_INCLUDES:
            files[path] = None
            errors.setdefault(path, set()).add(("unresolved-local-include-limit", "ci-local-include"))
            return
        lines, error, size = _read_local_ci_include(root, path)
        files[path] = lines
        if error is not None:
            errors.setdefault(path, set()).add((error, "ci-local-include"))
            return
        total_bytes += size
        if total_bytes > MAX_LOCAL_CI_INCLUDE_BYTES:
            errors.setdefault(path, set()).add(("unresolved-local-include-total-size", "ci-local-include"))
            return
        assert lines is not None
        active.add(path)
        include_references, local_includes = _ci_external_references(lines)
        errors.setdefault(path, set()).update(
            reference for reference in include_references
            if reference[0].startswith("unresolved-")
        )
        edges[path] = set(local_includes)
        for child in sorted(local_includes):
            if child in active:
                errors.setdefault(path, set()).add(("unresolved-local-include-cycle", "ci-local-include"))
                continue
            visit(child, depth + 1)
        active.remove(path)

    visit(".gitlab-ci.yml", 0)
    return files, edges, errors


def _descendant_paths(starts: Iterable[str], edges: dict[str, set[str]]) -> set[str]:
    selected: set[str] = set()
    pending = list(starts)
    while pending:
        path = pending.pop()
        if path in selected:
            continue
        selected.add(path)
        pending.extend(edges.get(path, set()))
    return selected


def _dependency_references(
    changed_files: Iterable[str],
    diff_text: str,
    policy: dict[str, Any],
    root: Path | None,
) -> dict[str, set[tuple[str, str]]]:
    manifest_patterns = _as_list(policy.get("dependency_manifests"))
    manifests = {
        path
        for path in changed_files
        if any(
            isinstance(pattern, str) and _matches(path, pattern)
            for pattern in manifest_patterns
        )
    }
    references: dict[str, set[tuple[str, str]]] = {path: set() for path in manifests}
    content_lock_patterns = _as_list(policy.get("dependency_content_lock"))
    if root is not None:
        for path in manifests:
            if any(isinstance(pattern, str) and _matches(path, pattern) for pattern in content_lock_patterns):
                references[path].add((_content_dependency(root, path), "content"))
    reference_rules = _as_list(policy.get("dependency_reference_rules"))
    additions = added_lines(diff_text)
    addition_lines: dict[str, list[str]] = {}
    for addition_path, addition_line in additions:
        addition_lines.setdefault(addition_path, []).append(addition_line)
    scalar_bodies = {
        path: _yaml_block_scalar_body_indexes(lines)
        for path, lines in addition_lines.items()
    }
    addition_offsets: dict[str, int] = {}
    for addition_index, (path, line) in enumerate(additions):
        path_offset = addition_offsets.get(path, 0)
        addition_offsets[path] = path_offset + 1
        window = [line]
        for nearby_path, nearby_line in additions[addition_index + 1:addition_index + 6]:
            if nearby_path != path:
                break
            window.append(nearby_line)
        gitlink = re.fullmatch(r"Subproject commit ([0-9a-fA-F]{40}|[0-9a-fA-F]{64})", line.strip())
        if gitlink:
            references.setdefault(path, set()).add((f"git-oid:{gitlink.group(1).lower()}", "gitlink"))
        current_ci_inventory = root is not None and path == ".gitlab-ci.yml" and (root / path).is_file()
        in_scalar_body = path_offset in scalar_bodies.get(path, set())
        if (
            path == ".gitlab-ci.yml"
            and not current_ci_inventory
            and not in_scalar_body
            and _yaml_has_unsupported_key_syntax(line)
        ):
            references.setdefault(path, set()).add(("unresolved-yaml-key-syntax", "image"))
        for rule in reference_rules:
            if not isinstance(rule, dict) or not _is_text(rule.get("pattern")) or not _is_text(rule.get("term")):
                continue
            if current_ci_inventory or in_scalar_body:
                continue
            term = rule["term"]
            key_match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):", term)
            present, values = _yaml_values_at(window, 0, key_match.group(1)) if key_match else (False, [])
            if _matches(path, rule["pattern"]) and values:
                for dependency in values:
                    references.setdefault(path, set()).add((dependency, "image"))
            elif _matches(path, rule["pattern"]) and key_match and present:
                nested_found = False
                for nested_line in window[1:4]:
                    if not nested_line.strip():
                        continue
                    if term.lower() == "image:":
                        nested_values = _yaml_key_values(nested_line, "name")
                        for dependency in nested_values:
                            references.setdefault(path, set()).add((dependency, "image"))
                            nested_found = True
                    break
                if not nested_found:
                    references.setdefault(path, set()).add((f"unresolved-yaml-scalar:{key_match.group(1)}", "image"))
        if any(_matches(path, pattern) for pattern in ("requirements*.txt", "**/requirements*.txt")):
            dependency = line.strip()
            if dependency and not dependency.startswith(("#", "-r", "--requirement")):
                references.setdefault(path, set()).add((dependency, "python-requirement"))
    if root is not None and (root / ".gitlab-ci.yml").exists():
        files, edges, graph_errors = _ci_local_include_graph(root)
        changed = set(changed_files)
        graph_paths = set(files) | {child for children in edges.values() for child in children}
        starts = graph_paths & changed
        if ".gitlab-ci.yml" in changed:
            starts.add(".gitlab-ci.yml")
        selected = _descendant_paths(starts, edges)
        unresolved_graph = any(graph_errors.values())
        if unresolved_graph and any(path.endswith((".yml", ".yaml")) for path in changed):
            selected.add(".gitlab-ci.yml")
        for path in sorted(selected):
            references.setdefault(path, set()).add((_content_dependency(root, path), "content"))
            references[path].update(graph_errors.get(path, set()))
            lines = files.get(path)
            if lines is not None:
                references[path].update(_ci_dependency_values(lines))
    for path, dependencies in references.items():
        if not dependencies:
            dependencies.add((_content_dependency(root, path), "content"))
    return references


def _is_exactly_pinned(dependency: str, kind: str) -> bool:
    if kind == "image":
        return bool(re.fullmatch(r"[^\s@]+(?::[^\s@]+)?@sha256:[0-9a-fA-F]{64}", dependency))
    if kind == "python-requirement":
        requirement = dependency.split(";", 1)[0].strip()
        return bool(re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[A-Za-z0-9_,.-]+\])?==[A-Za-z0-9][A-Za-z0-9._+-]*"
            r"(?:\s+--hash=sha256:[0-9a-f]{64})*",
            requirement,
        ))
    if kind == "gitlink":
        return bool(re.fullmatch(r"git-oid:(?:[0-9a-f]{40}|[0-9a-f]{64})", dependency))
    if kind == "ci-project-include":
        return bool(re.fullmatch(r"gitlab-project:[^\s@]+@(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", dependency))
    if kind == "ci-component-include":
        return bool(re.fullmatch(r"component:[^\s@]+@(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", dependency))
    if kind in {"ci-remote-include", "ci-template-include", "ci-local-include"}:
        return False
    return bool(re.fullmatch(r"content-sha256:[0-9a-f]{64}|manifest-removal", dependency))


def check_dependencies(
    changed_files: Iterable[str],
    diff_text: str,
    policy: dict[str, Any],
    contract: dict[str, Any],
    *,
    root: Path | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    if root is not None:
        for path in _manifest_symlinks(root, _as_list(policy.get("dependency_manifests"))):
            findings.append(Finding("dependencies", f"{path} must be a regular, non-symlink dependency manifest"))
    if findings:
        return findings
    references = _dependency_references(changed_files, diff_text, policy, root)
    if not references:
        return findings
    approvals = {
        (item.get("path"), item.get("dependency"))
        for item in contract.get("dependency_changes", [])
        if isinstance(item, dict) and item.get("pinned") is True
    }
    for path in sorted(references):
        for dependency, kind in sorted(references[path]):
            if not _is_exactly_pinned(dependency, kind):
                findings.append(Finding("dependencies", f"{path} adds unpinned or unresolved dependency {dependency!r}"))
            if (path, dependency) not in approvals:
                findings.append(Finding("dependencies", f"{path} dependency {dependency!r} lacks an exact pinned approval"))
    return findings


SECRET_PATTERNS = (
    ("AWS access key", re.compile(r"\b(?:AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    (
        "GitLab token",
        re.compile(
            r"\b(?:glpat|gloas|gldt|glrt|glrtr|glcbt|glptt|glft|glimt|glagent|glwt|glsoat|glffct)-"
            r"[A-Za-z0-9_.-]{16,}\b",
        ),
    ),
    ("GitLab session cookie", re.compile(r"\b_gitlab_session=[A-Za-z0-9%_.-]{16,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("private key block", re.compile(r"-{5}BEGIN (?:(?:ENCRYPTED|RSA|EC|DSA|OPENSSH) )?PRIVATE KEY-{5}")),
    ("PEM certificate block", re.compile(r"-{5}BEGIN (?:(?:TRUSTED|X509) )?CERTIFICATE-{5}")),
    ("credential assignment", re.compile(r"(?i)\b(?:password|passwd|api[_-]?key|secret|access[_-]?token)\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"]")),
    ("credential-bearing URI", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/:]+:[^\s/@]+@", re.IGNORECASE)),
    ("AIDF test canary", re.compile(r"AIDF_TEST_CANARY_SECRET_DO_NOT_USE_[A-Z0-9]{10,}")),
)


def check_secrets(diff_text: str) -> list[Finding]:
    findings: list[Finding] = []
    for path, line in added_lines(diff_text):
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(Finding("secrets", f"possible {label} in added content at {path}; remove it and rotate if real"))
    return findings


ASSERTION_PATTERN = re.compile(r"\b(?:assert|expect|should)\b|\bassert[A-Z]\w*\s*\(")


def inspect_test_delta(diff_text: str, coverage_before: float | None = None, coverage_after: float | None = None) -> list[str]:
    added = removed = 0
    for line in diff_text.splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line.startswith("+") and ASSERTION_PATTERN.search(line[1:]):
            added += 1
        elif line.startswith("-") and ASSERTION_PATTERN.search(line[1:]):
            removed += 1
    notices: list[str] = []
    if removed > added:
        notices.append(f"assertion-like lines declined ({added} added, {removed} removed); inspect test intent")
    if coverage_before is not None and coverage_after is not None and coverage_after < coverage_before:
        notices.append(f"coverage declined ({coverage_before:g} -> {coverage_after:g}); inspect the reason")
    return notices


def _git_output(root: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-c", f"safe.directory={root.as_posix()}", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=30,
        )
    except (OSError, UnicodeError, subprocess.SubprocessError) as exc:
        raise ValueError(f"Git inspection failed safely: {exc}") from exc
    if len(result.stdout.encode("utf-8")) > MAX_DIFF_BYTES:
        raise ValueError("Git output exceeds the 10 MiB inspection limit; split the change")
    return result.stdout


def _valid_git_revision(value: str | None) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9A-Fa-f]{7,64}", value))


def _read_bounded(root: Path, value: str, limit: int) -> str:
    path = _resolve_input(root, value)
    if path.stat().st_size > limit:
        raise ValueError(f"input exceeds {limit} bytes: {value}")
    return path.read_text(encoding="utf-8")


def _read_bounded_bytes(root: Path, value: str, limit: int) -> bytes:
    path = _resolve_input(root, value)
    if path.stat().st_size > limit:
        raise ValueError(f"input exceeds {limit} bytes: {value}")
    return path.read_bytes()


def _changed_files(args: argparse.Namespace, root: Path) -> list[str]:
    if args.changed_files:
        raw = _read_bounded_bytes(root, args.changed_files, MAX_JSON_BYTES)
        if args.changed_files_nul:
            values = raw.split(b"\x00")
        else:
            if b"\r" in raw.replace(b"\r\n", b""):
                raise ValueError("changed-file artifact contains a lone or embedded carriage return")
            values = raw.replace(b"\r\n", b"\n").split(b"\n")
        try:
            paths = [value.decode("utf-8", errors="strict").replace("\\", "/") for value in values if value]
        except UnicodeError as exc:
            raise ValueError(f"changed-file artifact is not strict UTF-8: {exc}") from exc
    else:
        if not _valid_git_revision(args.base) or not _valid_git_revision(args.head):
            raise ValueError("supply --changed-files or hexadecimal --base and --head revisions")
        content = _git_output(root, ["diff", "--name-only", "--no-renames", "--no-ext-diff", args.base, args.head, "--"])
        paths = [line.strip().replace("\\", "/") for line in content.splitlines() if line.strip()]
    if len(paths) > 5000:
        raise ValueError("changed-file count exceeds 5000; split the change")
    unsafe = [path for path in paths if not _safe_repo_path(path)]
    if unsafe:
        raise ValueError(f"changed-file artifact contains unsafe paths: {unsafe!r}")
    if len(set(paths)) != len(paths):
        raise ValueError("changed-file artifact contains duplicate paths")
    return paths


def _diff_text(args: argparse.Namespace, root: Path) -> str:
    if args.diff_file:
        return _read_bounded(root, args.diff_file, MAX_DIFF_BYTES)
    if not _valid_git_revision(args.base) or not _valid_git_revision(args.head):
        raise ValueError("supply --diff-file or hexadecimal --base and --head revisions")
    return _git_output(root, ["diff", "--unified=0", "--no-renames", "--no-ext-diff", "--no-textconv", args.base, args.head, "--"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("all", "contract", "evidence", "exemptions", "scope", "tripwires", "dependencies", "secrets", "test-delta", "automation-policy"))
    parser.add_argument("--root", default=".")
    parser.add_argument("--contract")
    parser.add_argument("--evidence")
    parser.add_argument("--policy")
    parser.add_argument("--policy-b64")
    parser.add_argument("--automation-policy")
    parser.add_argument("--automation-policy-b64")
    parser.add_argument("--expected-project-id")
    parser.add_argument("--expected-policy-sha256")
    parser.add_argument("--task-override")
    parser.add_argument("--task-override-b64")
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--changed-files")
    parser.add_argument("--changed-files-nul", action="store_true")
    parser.add_argument("--diff-file")
    parser.add_argument("--coverage-before", type=float)
    parser.add_argument("--coverage-after", type=float)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    findings: list[Finding] = []
    notices: list[str] = []
    try:
        contract = load_json(root, args.contract) if args.contract else {}
        evidence = load_json(root, args.evidence) if args.evidence else {}
        if args.policy and args.policy_b64:
            raise ValueError("supply only one of --policy or --policy-b64")
        policy = load_json(root, args.policy) if args.policy else load_json_base64(args.policy_b64, "--policy-b64") if args.policy_b64 else {}
        if args.automation_policy and args.automation_policy_b64:
            raise ValueError("supply only one of --automation-policy or --automation-policy-b64")
        automation_policy = (
            load_json(root, args.automation_policy)
            if args.automation_policy
            else load_json_base64(args.automation_policy_b64, "--automation-policy-b64")
            if args.automation_policy_b64
            else {}
        )
        if args.task_override and args.task_override_b64:
            raise ValueError("supply only one of --task-override or --task-override-b64")
        task_override = (
            load_json(root, args.task_override)
            if args.task_override
            else load_json_base64(args.task_override_b64, "--task-override-b64")
            if args.task_override_b64
            else None
        )
        commands = {args.command} if args.command != "all" else {"contract", "evidence", "exemptions", "scope", "tripwires", "dependencies", "secrets", "test-delta"}
        if args.command == "all" and automation_policy:
            commands.add("automation-policy")
        if "automation-policy" in commands:
            if not automation_policy:
                findings.append(Finding("automation-policy", "--automation-policy is required"))
            else:
                automation_findings = validate_automation_policy(automation_policy)
                findings.extend(automation_findings)
                if not args.expected_project_id:
                    findings.append(Finding("automation-policy", "--expected-project-id is required"))
                elif automation_policy.get("project_id") != args.expected_project_id:
                    findings.append(Finding("automation-policy", "policy project_id does not match protected project identity"))
                if not args.expected_policy_sha256:
                    findings.append(Finding("automation-policy", "--expected-policy-sha256 is required"))
                elif not re.fullmatch(r"[0-9a-f]{64}", args.expected_policy_sha256):
                    findings.append(Finding("automation-policy", "--expected-policy-sha256 must be lowercase SHA-256"))
                elif not automation_findings and not hmac.compare_digest(
                    automation_policy_sha256(automation_policy), args.expected_policy_sha256
                ):
                    findings.append(Finding("automation-policy", "policy digest does not match protected approval binding"))
                elif not automation_findings and task_override is not None:
                    active_profile = resolve_automation_policy(
                        automation_policy,
                        expected_project_id=args.expected_project_id,
                        expected_policy_sha256=args.expected_policy_sha256,
                    )
                    findings.extend(validate_automation_override(task_override, active_profile))
        needs_exemption_registry = "exemptions" in commands or (
            "evidence" in commands
            and isinstance(evidence.get("e3"), dict)
            and evidence["e3"].get("status") == "exempted"
        )
        policy_required = bool(commands & {"tripwires", "dependencies", "exemptions"}) or needs_exemption_registry
        policy_valid = False
        contract_valid = False
        exemption_records: list[dict[str, Any]] = []
        if policy_required and not policy:
            findings.append(Finding("policy", "--policy is required"))
        elif policy:
            policy_findings = validate_policy(policy)
            findings.extend(policy_findings)
            policy_valid = not policy_findings
        if needs_exemption_registry:
            if not policy:
                findings.append(Finding("exemptions", "--policy is required to resolve an E3 exemption"))
            elif policy_valid:
                exemption_records, exemption_findings = load_exemption_records(root, policy)
                findings.extend(exemption_findings)
        contract_required = bool(commands & {"contract", "evidence", "scope", "tripwires", "dependencies"})
        if contract_required:
            if not contract:
                findings.append(Finding("contract", "--contract is required"))
            else:
                contract_findings = validate_contract(contract)
                findings.extend(contract_findings)
                contract_valid = not contract_findings
        if "evidence" in commands:
            if not contract or not evidence:
                findings.append(Finding("evidence", "--contract and --evidence are required"))
            elif contract_valid:
                findings.extend(validate_evidence(evidence, contract, exemption_records))
        if commands & {"scope", "tripwires", "dependencies", "secrets", "test-delta"}:
            changed = _changed_files(args, root)
            diff_text = _diff_text(args, root)
            findings.extend(check_diff_consistency(changed, diff_text))
        else:
            changed, diff_text = [], ""
        if "scope" in commands and contract_valid:
            findings.extend(check_scope(changed, contract))
        if "tripwires" in commands and policy_valid and contract_valid:
            findings.extend(check_tripwires(changed, diff_text, policy, contract))
        if "dependencies" in commands and policy_valid and contract_valid:
            findings.extend(check_dependencies(changed, diff_text, policy, contract, root=root))
        if "secrets" in commands:
            findings.extend(check_secrets(diff_text))
        if "test-delta" in commands:
            coverage_before = args.coverage_before if args.coverage_before is not None else evidence.get("coverage_before")
            coverage_after = args.coverage_after if args.coverage_after is not None else evidence.get("coverage_after")
            notices.extend(inspect_test_delta(diff_text, coverage_before, coverage_after))
    except (KeyError, OSError, TypeError, UnicodeError, ValueError) as exc:
        findings.append(Finding("input", str(exc)))
    for finding in findings:
        print(f"FAIL [{finding.check}] {finding.message}")
    for notice in notices:
        print(f"NOTICE [test-delta] {notice}; this is an inspection trigger, not evidence")
    if findings:
        return 1
    print("PASS: requested AIDF checks completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
