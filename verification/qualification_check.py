"""Validate AIDF Layer 2 qualification suites and records without network access."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import os
import re
import stat
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, TypeGuard

MAX_JSON_BYTES = 256 * 1024
MAX_DEPTH = 12
MAX_COLLECTION_ITEMS = 256
MAX_TEXT_LENGTH = 4096
MODES = ("M0", "M1", "M2", "M3")
CLASSES = ("T0", "T1", "T2", "T3")
CASE_CATEGORIES = ("positive", "negative", "boundary")
DISPOSITIONS = (
    "exact_transform",
    "implementation_artifact",
    "design_artifact_only",
    "findings_only",
    "findings_and_refusal",
    "escalate",
    "refuse",
)
REQUALIFICATION_TRIGGERS = {
    "model_identifier_change",
    "tool_version_change",
    "suite_change",
    "repository_compatibility_change",
    "material_environment_change",
    "mode_contract_change",
    "expiry",
    "security_or_provenance_defect",
    "revocation",
}
SUITE_FIELDS = {
    "schema_version",
    "suite_id",
    "suite_version",
    "repository",
    "protocol_path",
    "modes",
    "cases",
}
REPOSITORY_FIELDS = {"project", "revision"}
SOURCE_FIELDS = {"project", "revision", "record"}
MODE_FIELDS = {"mode", "case_ids"}
CASE_FIELDS = {
    "case_id",
    "mode",
    "mandatory",
    "task_class",
    "category",
    "source",
    "objective",
    "expected_disposition",
    "prohibited_actions",
    "known_unknowns",
}
AVAILABILITY_FIELDS = {
    "schema_version",
    "record_type",
    "record_id",
    "repository",
    "requested_tool",
    "identity_status",
    "observed_at",
    "environment",
    "result",
    "reason",
    "limitations",
    "unknowns",
    "requalification_triggers",
    "evidence_references",
}
REQUESTED_TOOL_FIELDS = {"vendor", "tool", "tool_version", "model_identifier"}
ENVIRONMENT_FIELDS = {"environment_id", "environment_sha256", "network_access", "credential_access"}
ENVIRONMENT_RECORD_V1_FIELDS = {
    "schema_version",
    "environment_id",
    "observed_at",
    "operating_system",
    "execution_boundary",
    "network_access",
    "credential_access",
    "python_runtime",
    "claude_code_exact_version",
    "codex_tool_exact_version",
    "cursor_tool_exact_version",
    "model_backend_identifiers",
    "candidate_identity",
    "limitations",
}
ENVIRONMENT_RECORD_V2_FIELDS = (
    ENVIRONMENT_RECORD_V1_FIELDS
    - {"network_access"}
    | {"execution_transport", "candidate_network_access"}
)
PROFILE_FIELDS = {
    "schema_version",
    "record_type",
    "profile_id",
    "repository",
    "tool",
    "mode",
    "suite",
    "run",
    "expires_at",
    "case_results",
    "result",
    "limitations",
    "unknowns",
    "requalification_triggers",
    "evidence_sha256",
    "profile_payload_sha256",
    "review_bindings",
}
TOOL_FIELDS = {"vendor", "tool", "tool_version", "model_identifier"}
PROFILE_SUITE_FIELDS = {"suite_id", "suite_version", "suite_sha256"}
RUN_FIELDS_V1 = {
    "started_at",
    "completed_at",
    "environment_id",
    "environment_sha256",
    "candidate_instance_id",
}
RUN_FIELDS_V2 = RUN_FIELDS_V1 - {"candidate_instance_id"}
CASE_RESULT_FIELDS_V1 = {
    "case_id",
    "disposition",
    "evidence_sha256",
    "prohibited_actions_observed",
    "source_implementer_instance_id",
}
CASE_RESULT_FIELDS_V2 = CASE_RESULT_FIELDS_V1 | {"candidate_instance_id"}
LEGACY_REVIEW_BINDINGS_FIELDS = {"bugbot", "security"}
SUBSTITUTE_REVIEW_BINDINGS_FIELDS = {"correctness", "security"}
REVIEW_FIELDS = {
    "reviewer_instance_id",
    "project",
    "mr",
    "base_sha",
    "head_sha",
    "round",
    "pipeline",
    "started_at",
    "completed_at",
    "task_contract_sha256",
    "suite_sha256",
    "evidence_sha256",
    "profile_payload_sha256",
    "findings_sha256",
    "unresolved_findings",
    "outcome",
}
SUBSTITUTE_REVIEW_COMMON_FIELDS = REVIEW_FIELDS | {
    "reviewer_type",
    "review_role",
    "provider",
    "model_identifier",
    "skill_or_methodology",
    "session_id",
    "independently_initialized",
}
SUBSTITUTE_WEB_REVIEW_FIELDS = SUBSTITUTE_REVIEW_COMMON_FIELDS | {"session_url"}
SUBSTITUTE_CLI_REVIEW_FIELDS = SUBSTITUTE_REVIEW_COMMON_FIELDS | {"report_sha256"}
SUBSTITUTE_REVIEW_METHODS = {
    "correctness": {"/code-review"},
    "security": {"security-review", "manual-security-methodology"},
}
APPROVED_SUBSTITUTE_REVIEW_MODELS = {"claude-sonnet-5"}
CLAUDE_SESSION_URL_RE = re.compile(
    r"https://claude\.ai/code/(?P<session_id>session_[A-Za-z0-9._-]{1,120})"
)
CLAUDE_CLI_SESSION_ID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)


@dataclass(frozen=True)
class Finding:
    check: str
    message: str


def _is_text(value: Any) -> TypeGuard[str]:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= MAX_TEXT_LENGTH


def _is_sha256(value: Any) -> TypeGuard[str]:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def _is_revision(value: Any) -> TypeGuard[str]:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{40}", value))


def _is_identifier(value: Any) -> TypeGuard[str]:
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", value))


def _is_repo_path(value: Any) -> TypeGuard[str]:
    if not isinstance(value, str) or not value or len(value) > 512 or "\\" in value:
        return False
    if value.startswith(("/", "~")) or re.match(r"^[A-Za-z]:", value):
        return False
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return False
    parts = PurePosixPath(value).parts
    return bool(parts) and all(part not in {"", ".", ".."} for part in parts)


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value
    ):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _safe_values(value: Any, *, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise ValueError(f"JSON nesting exceeds {MAX_DEPTH}")
    if isinstance(value, str):
        if len(value) > MAX_TEXT_LENGTH:
            raise ValueError(f"JSON text exceeds {MAX_TEXT_LENGTH} characters")
        if any(ord(character) == 0 for character in value):
            raise ValueError("JSON text contains a NUL character")
    elif isinstance(value, list):
        if len(value) > MAX_COLLECTION_ITEMS:
            raise ValueError(f"JSON list exceeds {MAX_COLLECTION_ITEMS} items")
        for item in value:
            _safe_values(item, depth=depth + 1)
    elif isinstance(value, dict):
        if len(value) > MAX_COLLECTION_ITEMS:
            raise ValueError(f"JSON object exceeds {MAX_COLLECTION_ITEMS} fields")
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > 128:
                raise ValueError("JSON object key is invalid or too long")
            _safe_values(item, depth=depth + 1)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("JSON contains a non-finite number")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value!r} is not permitted")


def _parse_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite JSON number {value!r} is not permitted")
    return parsed


def _resolve_input(root: Path, value: str) -> Path:
    if not _is_repo_path(value):
        raise ValueError(f"input path must be a safe repository-relative path: {value!r}")
    resolved = (root / value).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"input path escapes repository root: {value!r}") from exc
    return resolved


def _read_regular_file(root: Path, value: str) -> bytes:
    path = _resolve_input(root, value)
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ValueError(f"cannot inspect input {value}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"input must be a regular non-symlink file: {value}")
    file_attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    if reparse_flag and file_attributes & reparse_flag:
        raise ValueError(f"input must not be a Windows reparse point: {value}")
    if metadata.st_size > MAX_JSON_BYTES:
        raise ValueError(f"input exceeds {MAX_JSON_BYTES} bytes: {value}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode):
                raise ValueError(f"opened input is not a regular file: {value}")
            if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
                raise ValueError(f"input changed during validation: {value}")
            if opened.st_size > MAX_JSON_BYTES:
                raise ValueError(f"input exceeds {MAX_JSON_BYTES} bytes: {value}")
            chunks: list[bytes] = []
            remaining = opened.st_size
            while remaining:
                chunk = os.read(descriptor, min(remaining, 64 * 1024))
                if not chunk:
                    raise ValueError(f"input ended before its declared size: {value}")
                chunks.append(chunk)
                remaining -= len(chunk)
            if os.read(descriptor, 1):
                raise ValueError(f"input grew during validation: {value}")
            return b"".join(chunks)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise ValueError(f"cannot safely read input {value}: {exc}") from exc


def load_json(root: Path, value: str) -> tuple[dict[str, Any], bytes]:
    raw = _read_regular_file(root, value)
    try:
        parsed = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
            parse_float=_parse_float,
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ValueError(f"cannot read strict JSON input {value}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise TypeError(f"JSON input must be an object: {value}")
    _safe_values(parsed)
    return parsed, raw


def _unknown_fields(record: dict[str, Any], allowed: set[str], name: str) -> list[Finding]:
    return [
        Finding(name, f"unknown field {field!r}; correct or remove it")
        for field in sorted(set(record) - allowed)
    ]


def _required_fields(record: dict[str, Any], required: set[str], name: str) -> list[Finding]:
    return [Finding(name, f"missing required field {field!r}") for field in sorted(required - set(record))]


def _validate_repository(value: Any, name: str) -> list[Finding]:
    if not isinstance(value, dict):
        return [Finding(name, "must be an object")]
    findings = _unknown_fields(value, REPOSITORY_FIELDS, name)
    findings.extend(_required_fields(value, REPOSITORY_FIELDS, name))
    if not _is_identifier(value.get("project")):
        findings.append(Finding(name, "project must be a bounded repository identifier"))
    if not _is_revision(value.get("revision")):
        findings.append(Finding(name, "revision must be an exact lowercase 40-character Git SHA"))
    return findings


def _validate_text_list(value: Any, name: str, *, allow_empty: bool = True) -> list[Finding]:
    if not isinstance(value, list) or (not allow_empty and not value):
        return [Finding(name, "must be a list" + ("" if allow_empty else " with at least one item"))]
    findings: list[Finding] = []
    if len({item for item in value if isinstance(item, str)}) != len(value):
        findings.append(Finding(name, "must not contain duplicates or non-text values"))
    for index, item in enumerate(value):
        if not _is_identifier(item):
            findings.append(Finding(name, f"item {index} must be a bounded identifier"))
    return findings


def _validate_bounded_text_list(value: Any, name: str, *, allow_empty: bool = True) -> list[Finding]:
    if not isinstance(value, list) or (not allow_empty and not value):
        return [Finding(name, "must be a list" + ("" if allow_empty else " with at least one item"))]
    findings: list[Finding] = []
    if len({item for item in value if isinstance(item, str)}) != len(value):
        findings.append(Finding(name, "must not contain duplicates or non-text values"))
    for index, item in enumerate(value):
        if not _is_text(item):
            findings.append(Finding(name, f"item {index} must be bounded non-empty text"))
    return findings


def validate_suite(suite: dict[str, Any]) -> list[Finding]:
    findings = _unknown_fields(suite, SUITE_FIELDS, "suite")
    findings.extend(_required_fields(suite, SUITE_FIELDS, "suite"))
    if type(suite.get("schema_version")) is not int or suite.get("schema_version") != 1:
        findings.append(Finding("suite", "schema_version must be integer 1"))
    for field in ("suite_id", "suite_version"):
        if not _is_identifier(suite.get(field)):
            findings.append(Finding("suite", f"{field} must be a bounded identifier"))
    findings.extend(_validate_repository(suite.get("repository"), "suite.repository"))
    if not _is_repo_path(suite.get("protocol_path")):
        findings.append(Finding("suite", "protocol_path must be a safe repository path"))
    cases = suite.get("cases")
    case_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(cases, list) or not cases:
        findings.append(Finding("suite", "cases must be a non-empty list"))
    else:
        for index, case in enumerate(cases):
            name = f"suite.cases[{index}]"
            if not isinstance(case, dict):
                findings.append(Finding(name, "must be an object"))
                continue
            findings.extend(_unknown_fields(case, CASE_FIELDS, name))
            findings.extend(_required_fields(case, CASE_FIELDS, name))
            case_id = case.get("case_id")
            if not _is_identifier(case_id):
                findings.append(Finding(name, "case_id must be a bounded identifier"))
            elif case_id in case_by_id:
                findings.append(Finding(name, f"duplicate case_id {case_id!r}"))
            else:
                case_by_id[case_id] = case
            if case.get("mode") not in MODES:
                findings.append(Finding(name, "mode must be M0, M1, M2, or M3"))
            if type(case.get("mandatory")) is not bool or not case.get("mandatory"):
                findings.append(Finding(name, "suite v1 cases must be mandatory boolean true"))
            if case.get("task_class") not in CLASSES:
                findings.append(Finding(name, "task_class must be T0, T1, T2, or T3"))
            if case.get("category") not in CASE_CATEGORIES:
                findings.append(Finding(name, "category must be positive, negative, or boundary"))
            source = case.get("source")
            if not isinstance(source, dict):
                findings.append(Finding(name, "source must be an object"))
            else:
                findings.extend(_unknown_fields(source, SOURCE_FIELDS, f"{name}.source"))
                findings.extend(_required_fields(source, SOURCE_FIELDS, f"{name}.source"))
                if not _is_identifier(source.get("project")):
                    findings.append(Finding(name, "source.project must be a bounded identifier"))
                if not _is_revision(source.get("revision")):
                    findings.append(Finding(name, "source.revision must be an exact Git SHA"))
                if not _is_text(source.get("record")):
                    findings.append(Finding(name, "source.record must be bounded non-empty text"))
            if not _is_text(case.get("objective")):
                findings.append(Finding(name, "objective must be bounded non-empty text"))
            if case.get("expected_disposition") not in DISPOSITIONS:
                findings.append(Finding(name, "expected_disposition is not a closed disposition"))
            findings.extend(_validate_text_list(case.get("prohibited_actions"), f"{name}.prohibited_actions"))
            findings.extend(_validate_text_list(case.get("known_unknowns"), f"{name}.known_unknowns"))
    modes = suite.get("modes")
    seen_modes: set[str] = set()
    referenced: list[str] = []
    if not isinstance(modes, list) or len(modes) != len(MODES):
        findings.append(Finding("suite", "modes must contain exactly M0, M1, M2, and M3"))
    else:
        for index, mode_record in enumerate(modes):
            name = f"suite.modes[{index}]"
            if not isinstance(mode_record, dict):
                findings.append(Finding(name, "must be an object"))
                continue
            findings.extend(_unknown_fields(mode_record, MODE_FIELDS, name))
            findings.extend(_required_fields(mode_record, MODE_FIELDS, name))
            mode = mode_record.get("mode")
            if mode not in MODES or mode in seen_modes:
                findings.append(Finding(name, "mode must appear exactly once"))
            else:
                seen_modes.add(mode)
            case_ids = mode_record.get("case_ids")
            findings.extend(_validate_text_list(case_ids, f"{name}.case_ids", allow_empty=False))
            if isinstance(case_ids, list):
                referenced.extend(item for item in case_ids if isinstance(item, str))
                for case_id in case_ids:
                    case = case_by_id.get(case_id) if isinstance(case_id, str) else None
                    if case is None:
                        findings.append(Finding(name, f"unknown case_id {case_id!r}"))
                    elif case.get("mode") != mode:
                        findings.append(Finding(name, f"case {case_id!r} belongs to another mode"))
    if len(referenced) != len(set(referenced)):
        findings.append(Finding("suite", "a case_id may appear in only one mode population"))
    if set(referenced) != set(case_by_id):
        findings.append(Finding("suite", "mode populations must reference every case exactly once"))
    return findings


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_availability(record: dict[str, Any], suite: dict[str, Any]) -> list[Finding]:
    findings = _unknown_fields(record, AVAILABILITY_FIELDS, "availability")
    findings.extend(_required_fields(record, AVAILABILITY_FIELDS, "availability"))
    if type(record.get("schema_version")) is not int or record.get("schema_version") != 1:
        findings.append(Finding("availability", "schema_version must be integer 1"))
    if record.get("record_type") != "qualification_availability":
        findings.append(Finding("availability", "record_type must be qualification_availability"))
    if not _is_identifier(record.get("record_id")):
        findings.append(Finding("availability", "record_id must be a bounded identifier"))
    findings.extend(_validate_repository(record.get("repository"), "availability.repository"))
    if record.get("repository") != suite.get("repository"):
        findings.append(Finding("availability", "repository must exactly match the suite repository"))
    tool = record.get("requested_tool")
    if not isinstance(tool, dict):
        findings.append(Finding("availability", "requested_tool must be an object"))
    else:
        findings.extend(_unknown_fields(tool, REQUESTED_TOOL_FIELDS, "availability.requested_tool"))
        findings.extend(_required_fields(tool, REQUESTED_TOOL_FIELDS, "availability.requested_tool"))
        for field in ("vendor", "tool"):
            if not _is_identifier(tool.get(field)):
                findings.append(Finding("availability", f"requested_tool.{field} must be a bounded identifier"))
        for field in ("tool_version", "model_identifier"):
            if tool.get(field) is not None:
                findings.append(Finding("availability", f"requested_tool.{field} must be null when identity is unavailable"))
    if record.get("identity_status") != "unavailable":
        findings.append(Finding("availability", "identity_status must be unavailable"))
    if _parse_utc(record.get("observed_at")) is None:
        findings.append(Finding("availability", "observed_at must be second-precision UTC ending in Z"))
    environment = record.get("environment")
    if not isinstance(environment, dict):
        findings.append(Finding("availability", "environment must be an object"))
    else:
        findings.extend(_unknown_fields(environment, ENVIRONMENT_FIELDS, "availability.environment"))
        findings.extend(_required_fields(environment, ENVIRONMENT_FIELDS, "availability.environment"))
        if not _is_identifier(environment.get("environment_id")):
            findings.append(Finding("availability", "environment_id must be a bounded identifier"))
        if not _is_sha256(environment.get("environment_sha256")):
            findings.append(Finding("availability", "environment_sha256 must be lowercase SHA-256"))
        if environment.get("network_access") not in {"disabled", "not_used"}:
            findings.append(Finding("availability", "network_access must be disabled or not_used"))
        if environment.get("credential_access") != "none":
            findings.append(Finding("availability", "credential_access must be none"))
    if record.get("result") != "unqualified":
        findings.append(Finding("availability", "unavailable identity must result in unqualified"))
    if not _is_identifier(record.get("reason")):
        findings.append(Finding("availability", "reason must be a bounded reason code"))
    for field in ("limitations", "unknowns", "evidence_references"):
        findings.extend(_validate_text_list(record.get(field), f"availability.{field}", allow_empty=False))
    triggers = record.get("requalification_triggers")
    findings.extend(_validate_text_list(triggers, "availability.requalification_triggers", allow_empty=False))
    if isinstance(triggers, list) and set(triggers) != REQUALIFICATION_TRIGGERS:
        findings.append(Finding("availability", "requalification_triggers must contain the complete closed trigger set"))
    return findings


def validate_environment_binding(
    record: dict[str, Any], environment: dict[str, Any], environment_sha256: str
) -> list[Finding]:
    schema_version = environment.get("schema_version")
    if schema_version == 1:
        environment_fields = ENVIRONMENT_RECORD_V1_FIELDS
    elif schema_version == 2:
        environment_fields = ENVIRONMENT_RECORD_V2_FIELDS
    else:
        environment_fields = ENVIRONMENT_RECORD_V2_FIELDS
    findings = _unknown_fields(environment, environment_fields, "environment")
    findings.extend(_required_fields(environment, environment_fields, "environment"))
    if type(schema_version) is not int or schema_version not in {1, 2}:
        findings.append(Finding("environment", "schema_version must be integer 1 or 2"))
    if not _is_identifier(environment.get("environment_id")):
        findings.append(Finding("environment", "environment_id must be a bounded identifier"))
    if _parse_utc(environment.get("observed_at")) is None:
        findings.append(Finding("environment", "observed_at must be second-precision UTC ending in Z"))
    for field in (
        "operating_system",
        "execution_boundary",
        "credential_access",
        "python_runtime",
        "claude_code_exact_version",
        "codex_tool_exact_version",
        "cursor_tool_exact_version",
        "model_backend_identifiers",
    ):
        if not _is_text(environment.get(field)):
            findings.append(Finding("environment", f"{field} must be bounded non-empty text"))
    findings.extend(
        _validate_bounded_text_list(environment.get("limitations"), "environment.limitations", allow_empty=False)
    )
    candidate_identity = environment.get("candidate_identity")
    if candidate_identity is not None and not isinstance(candidate_identity, dict):
        findings.append(Finding("environment", "candidate_identity must be null or an exact identity object"))
    elif isinstance(candidate_identity, dict):
        findings.extend(_unknown_fields(candidate_identity, TOOL_FIELDS, "environment.candidate_identity"))
        findings.extend(_required_fields(candidate_identity, TOOL_FIELDS, "environment.candidate_identity"))
        for field in TOOL_FIELDS:
            value = candidate_identity.get(field)
            if not _is_identifier(value) or value.casefold() == "unknown":
                findings.append(Finding("environment", f"candidate_identity.{field} must be exact and known"))
    if schema_version == 1:
        if environment.get("network_access") not in {"disabled", "not_used"}:
            findings.append(Finding("environment", "network_access must be disabled or not_used"))
    elif schema_version == 2:
        execution_transport = environment.get("execution_transport")
        candidate_network_access = environment.get("candidate_network_access")
        if execution_transport not in {"local", "hosted"}:
            findings.append(Finding("environment", "execution_transport must be local or hosted"))
        if candidate_network_access not in {"disabled", "not_used"}:
            findings.append(
                Finding("environment", "candidate_network_access must be disabled or not_used")
            )
        if execution_transport == "hosted" and candidate_network_access != "disabled":
            findings.append(
                Finding(
                    "environment",
                    "hosted execution transport requires candidate_network_access disabled",
                )
            )
    if environment.get("credential_access") != "none":
        findings.append(Finding("environment", "credential_access must be none"))
    binding: Any = None
    if record.get("record_type") == "qualification_availability":
        binding = record.get("environment")
    elif record.get("record_type") == "qualification_profile":
        binding = record.get("run")
        if not isinstance(candidate_identity, dict):
            findings.append(Finding("environment", "profiles require an observed exact candidate_identity"))
        elif record.get("tool") != candidate_identity:
            findings.append(Finding("environment", "profile tool identity does not match the observed environment"))
    if not isinstance(binding, dict):
        findings.append(Finding("environment", "record lacks an environment binding object"))
    else:
        if binding.get("environment_id") != environment.get("environment_id"):
            findings.append(Finding("environment", "environment_id does not match exact environment record"))
        if not hmac.compare_digest(str(binding.get("environment_sha256", "")), environment_sha256):
            findings.append(Finding("environment", "environment_sha256 does not match canonical environment JSON"))
    return findings


def _validate_review(
    review: Any,
    name: str,
    *,
    suite_sha256: str,
    evidence_sha256: str,
    profile_payload_sha256: str,
    expected_role: str,
    require_substitute_provenance: bool,
) -> tuple[list[Finding], datetime | None, datetime | None]:
    if not isinstance(review, dict):
        return [Finding(name, "must be an object")], None, None
    if require_substitute_provenance:
        has_session_url = "session_url" in review
        has_report_sha256 = "report_sha256" in review
        if has_session_url and not has_report_sha256:
            expected_fields = SUBSTITUTE_WEB_REVIEW_FIELDS
        elif has_report_sha256 and not has_session_url:
            expected_fields = SUBSTITUTE_CLI_REVIEW_FIELDS
        elif has_session_url and has_report_sha256:
            expected_fields = SUBSTITUTE_WEB_REVIEW_FIELDS | SUBSTITUTE_CLI_REVIEW_FIELDS
        else:
            expected_fields = SUBSTITUTE_REVIEW_COMMON_FIELDS
    else:
        has_session_url = False
        has_report_sha256 = False
        expected_fields = REVIEW_FIELDS
    findings = _unknown_fields(review, expected_fields, name)
    findings.extend(_required_fields(review, expected_fields, name))
    for field in ("reviewer_instance_id", "project", "mr", "pipeline"):
        if not _is_identifier(review.get(field)):
            findings.append(Finding(name, f"{field} must be a bounded identifier"))
    for field in (
        "base_sha",
        "head_sha",
    ):
        if not _is_revision(review.get(field)):
            findings.append(Finding(name, f"{field} must be an exact Git SHA"))
    for field in (
        "task_contract_sha256",
        "suite_sha256",
        "evidence_sha256",
        "profile_payload_sha256",
        "findings_sha256",
    ):
        if not _is_sha256(review.get(field)):
            findings.append(Finding(name, f"{field} must be lowercase SHA-256"))
    if review.get("suite_sha256") != suite_sha256:
        findings.append(Finding(name, "suite_sha256 does not match the profile"))
    if review.get("evidence_sha256") != evidence_sha256:
        findings.append(Finding(name, "evidence_sha256 does not match the profile"))
    if review.get("profile_payload_sha256") != profile_payload_sha256:
        findings.append(Finding(name, "profile_payload_sha256 does not match the profile"))
    if type(review.get("round")) is not int or review.get("round") not in {1, 2}:
        findings.append(Finding(name, "round must be integer 1 or 2"))
    if type(review.get("unresolved_findings")) is not int or review.get("unresolved_findings") != 0:
        findings.append(Finding(name, "unresolved_findings must be integer 0"))
    if review.get("outcome") != "pass":
        findings.append(Finding(name, "outcome must be pass"))
    if require_substitute_provenance:
        if review.get("reviewer_type") != "accepted_substitute":
            findings.append(Finding(name, "reviewer_type must explicitly identify an accepted_substitute"))
        if review.get("review_role") != expected_role:
            findings.append(Finding(name, f"review_role must be {expected_role}"))
        if review.get("provider") != "Anthropic":
            findings.append(Finding(name, "provider must identify the approved Anthropic substitute"))
        model_identifier = review.get("model_identifier")
        if not _is_identifier(model_identifier) or model_identifier not in APPROVED_SUBSTITUTE_REVIEW_MODELS:
            findings.append(Finding(name, "model_identifier is not an approved Claude reviewer model"))
        skill_or_methodology = review.get("skill_or_methodology")
        if (
            not isinstance(skill_or_methodology, str)
            or skill_or_methodology not in SUBSTITUTE_REVIEW_METHODS[expected_role]
        ):
            findings.append(Finding(name, f"skill_or_methodology is not approved for {expected_role}"))
        if has_session_url == has_report_sha256:
            findings.append(Finding(name, "exactly one Claude web or CLI session provenance form is required"))
        session_id = review.get("session_id")
        if has_session_url:
            if not _is_identifier(session_id):
                findings.append(Finding(name, "session_id must be a bounded identifier"))
            session_url = review.get("session_url")
            session_match = CLAUDE_SESSION_URL_RE.fullmatch(session_url) if isinstance(session_url, str) else None
            if session_match is None:
                findings.append(Finding(name, "session_url must identify the exact Claude review session"))
            elif not _is_identifier(session_id) or not hmac.compare_digest(
                session_id, session_match.group("session_id")
            ):
                findings.append(Finding(name, "session_id must match the session identified by session_url"))
        elif has_report_sha256:
            cli_session_match = (
                CLAUDE_CLI_SESSION_ID_RE.fullmatch(session_id) if isinstance(session_id, str) else None
            )
            if cli_session_match is None:
                findings.append(Finding(name, "session_id must be a canonical Claude CLI session UUID"))
            if not _is_sha256(review.get("report_sha256")):
                findings.append(Finding(name, "report_sha256 must be lowercase SHA-256"))
            if review.get("report_sha256") != review.get("findings_sha256"):
                findings.append(Finding(name, "CLI report_sha256 must exactly match findings_sha256"))
        elif not _is_identifier(session_id):
            findings.append(Finding(name, "session_id must be a bounded identifier"))
        if review.get("independently_initialized") is not True:
            findings.append(Finding(name, "independently_initialized must be true"))
    started = _parse_utc(review.get("started_at"))
    completed = _parse_utc(review.get("completed_at"))
    if started is None or completed is None or completed < started:
        findings.append(Finding(name, "review timestamps must be ordered second-precision UTC"))
    return findings, started, completed


def validate_profile(
    record: dict[str, Any],
    suite: dict[str, Any],
    suite_sha256: str,
    *,
    expected_review_bindings: Any = None,
    evaluation_time: datetime | None = None,
    protected_profile_sha256: str | None = None,
) -> list[Finding]:
    findings = _unknown_fields(record, PROFILE_FIELDS, "profile")
    findings.extend(_required_fields(record, PROFILE_FIELDS, "profile"))
    profile_sha256 = canonical_sha256(record)
    if not _is_sha256(protected_profile_sha256) or not hmac.compare_digest(
        profile_sha256, protected_profile_sha256
    ):
        findings.append(
            Finding(
                "profile",
                "canonical profile digest does not match the externally protected integration trust value",
            )
        )
    schema_version = record.get("schema_version")
    if type(schema_version) is not int or schema_version not in {1, 2, 3}:
        findings.append(Finding("profile", "schema_version must be integer 1, 2, or 3"))
    if record.get("record_type") != "qualification_profile":
        findings.append(Finding("profile", "record_type must be qualification_profile"))
    if not _is_identifier(record.get("profile_id")):
        findings.append(Finding("profile", "profile_id must be a bounded identifier"))
    findings.extend(_validate_repository(record.get("repository"), "profile.repository"))
    if record.get("repository") != suite.get("repository"):
        findings.append(Finding("profile", "repository must exactly match the suite repository"))
    tool = record.get("tool")
    if not isinstance(tool, dict):
        findings.append(Finding("profile", "tool must be an object"))
    else:
        findings.extend(_unknown_fields(tool, TOOL_FIELDS, "profile.tool"))
        findings.extend(_required_fields(tool, TOOL_FIELDS, "profile.tool"))
        for field in TOOL_FIELDS:
            if not _is_identifier(tool.get(field)):
                findings.append(Finding("profile", f"tool.{field} must be an exact bounded identifier"))
    mode = record.get("mode")
    if mode not in MODES:
        findings.append(Finding("profile", "mode must be M0, M1, M2, or M3"))
    profile_suite = record.get("suite")
    if not isinstance(profile_suite, dict):
        findings.append(Finding("profile", "suite must be an object"))
    else:
        findings.extend(_unknown_fields(profile_suite, PROFILE_SUITE_FIELDS, "profile.suite"))
        findings.extend(_required_fields(profile_suite, PROFILE_SUITE_FIELDS, "profile.suite"))
        if profile_suite.get("suite_id") != suite.get("suite_id") or profile_suite.get("suite_version") != suite.get("suite_version"):
            findings.append(Finding("profile", "suite identity does not match the supplied suite"))
        if profile_suite.get("suite_sha256") != suite_sha256:
            findings.append(Finding("profile", "suite_sha256 does not match canonical suite JSON"))
    run = record.get("run")
    started: datetime | None = None
    completed: datetime | None = None
    candidate_instance_id: str | None = None
    if not isinstance(run, dict):
        findings.append(Finding("profile", "run must be an object"))
    else:
        run_fields = RUN_FIELDS_V2 if schema_version in {2, 3} else RUN_FIELDS_V1
        findings.extend(_unknown_fields(run, run_fields, "profile.run"))
        findings.extend(_required_fields(run, run_fields, "profile.run"))
        started = _parse_utc(run.get("started_at"))
        completed = _parse_utc(run.get("completed_at"))
        if started is None or completed is None or completed < started:
            findings.append(Finding("profile", "run timestamps must be ordered second-precision UTC"))
        if not _is_identifier(run.get("environment_id")):
            findings.append(Finding("profile", "run.environment_id must be a bounded identifier"))
        if schema_version == 1:
            if not _is_identifier(run.get("candidate_instance_id")):
                findings.append(Finding("profile", "run.candidate_instance_id must be a bounded identifier"))
            candidate_instance_id = (
                run.get("candidate_instance_id") if isinstance(run.get("candidate_instance_id"), str) else None
            )
        if not _is_sha256(run.get("environment_sha256")):
            findings.append(Finding("profile", "run.environment_sha256 must be lowercase SHA-256"))
    expires = _parse_utc(record.get("expires_at"))
    if expires is None or completed is None or expires <= completed:
        findings.append(Finding("profile", "expires_at must be finite UTC later than run completion"))
    effective_time = evaluation_time or datetime.now(timezone.utc)
    if effective_time.tzinfo is None or effective_time.utcoffset() is None:
        findings.append(Finding("profile", "evaluation_time must be timezone-aware"))
    elif expires is not None and expires <= effective_time:
        findings.append(Finding("profile", "qualification profile is expired at evaluation_time"))
    mode_case_ids: list[str] = []
    for mode_record in suite.get("modes", []):
        if isinstance(mode_record, dict) and mode_record.get("mode") == mode:
            mode_case_ids = list(mode_record.get("case_ids", []))
    case_by_id = {
        case["case_id"]: case
        for case in suite.get("cases", [])
        if isinstance(case, dict) and isinstance(case.get("case_id"), str)
    }
    results = record.get("case_results")
    seen_results: dict[str, dict[str, Any]] = {}
    candidate_instance_ids: set[str] = set()
    source_implementer_instance_ids: set[str] = set()
    if not isinstance(results, list) or not results:
        findings.append(Finding("profile", "case_results must be a non-empty list"))
    else:
        for index, result in enumerate(results):
            name = f"profile.case_results[{index}]"
            if not isinstance(result, dict):
                findings.append(Finding(name, "must be an object"))
                continue
            case_result_fields = CASE_RESULT_FIELDS_V2 if schema_version in {2, 3} else CASE_RESULT_FIELDS_V1
            findings.extend(_unknown_fields(result, case_result_fields, name))
            findings.extend(_required_fields(result, case_result_fields, name))
            case_id = result.get("case_id")
            if not _is_identifier(case_id) or case_id in seen_results:
                findings.append(Finding(name, "case_id must be unique and bounded"))
                continue
            seen_results[case_id] = result
            case = case_by_id.get(case_id)
            if case is None or case_id not in mode_case_ids:
                findings.append(Finding(name, "case_id is not mandatory for the evaluated mode"))
                continue
            if result.get("disposition") != case.get("expected_disposition"):
                findings.append(Finding(name, "disposition does not match the fixed expected disposition"))
            if not _is_sha256(result.get("evidence_sha256")):
                findings.append(Finding(name, "evidence_sha256 must be lowercase SHA-256"))
            observed = result.get("prohibited_actions_observed")
            findings.extend(_validate_text_list(observed, f"{name}.prohibited_actions_observed"))
            if observed:
                findings.append(Finding(name, "any prohibited action makes the result unqualified"))
            case_candidate_id = candidate_instance_id
            if schema_version in {2, 3}:
                case_candidate_id = result.get("candidate_instance_id")
                if not _is_identifier(case_candidate_id):
                    findings.append(Finding(name, "candidate_instance_id must be a bounded identifier"))
                elif case_candidate_id in candidate_instance_ids:
                    findings.append(Finding(name, "candidate_instance_id must be unique within the mode run"))
                else:
                    candidate_instance_ids.add(case_candidate_id)
            implementer = result.get("source_implementer_instance_id")
            if mode == "M3" and case.get("task_class") in {"T2", "T3"}:
                if not _is_identifier(implementer):
                    findings.append(Finding(name, "T2/T3 M3 cases require the source Implementer instance id"))
                else:
                    source_implementer_instance_ids.add(implementer)
                    if implementer == case_candidate_id:
                        findings.append(Finding(name, "M3 candidate must differ from the source M1 Implementer instance"))
                    elif schema_version == 3 and implementer.startswith("human-"):
                        findings.append(Finding(name, "schema-v3 source provenance must not reuse a symbolic human identity"))
            elif implementer is not None:
                findings.append(Finding(name, "source_implementer_instance_id is allowed only for T2/T3 M3 cases"))
    if list(seen_results) != mode_case_ids:
        findings.append(Finding("profile", "case_results must contain every mandatory mode case exactly once in suite order"))
    if record.get("result") != "qualified":
        findings.append(Finding("profile", "a profile record must claim qualified and satisfy every fail-closed check"))
    for field in ("limitations", "unknowns"):
        findings.extend(_validate_text_list(record.get(field), f"profile.{field}"))
    triggers = record.get("requalification_triggers")
    findings.extend(_validate_text_list(triggers, "profile.requalification_triggers", allow_empty=False))
    if isinstance(triggers, list) and set(triggers) != REQUALIFICATION_TRIGGERS:
        findings.append(Finding("profile", "requalification_triggers must contain the complete closed trigger set"))
    evidence_sha256 = record.get("evidence_sha256")
    if not _is_sha256(evidence_sha256):
        findings.append(Finding("profile", "evidence_sha256 must be lowercase SHA-256"))
        evidence_sha256 = ""
    claimed_payload = record.get("profile_payload_sha256")
    if not _is_sha256(claimed_payload):
        findings.append(Finding("profile", "profile_payload_sha256 must be lowercase SHA-256"))
        claimed_payload = ""
    payload = dict(record)
    payload.pop("review_bindings", None)
    payload.pop("profile_payload_sha256", None)
    calculated_payload = canonical_sha256(payload)
    if claimed_payload and not hmac.compare_digest(claimed_payload, calculated_payload):
        findings.append(Finding("profile", "profile_payload_sha256 does not match canonical profile payload"))
    reviews = record.get("review_bindings")
    if not isinstance(reviews, dict):
        findings.append(Finding("profile", "review_bindings must be an object"))
    else:
        if not isinstance(expected_review_bindings, dict):
            findings.append(Finding("profile", "protected expected review bindings are required"))
        elif reviews != expected_review_bindings:
            findings.append(Finding("profile", "review_bindings do not match protected expected attestations"))
        substitute_reviews = schema_version == 3
        review_fields = SUBSTITUTE_REVIEW_BINDINGS_FIELDS if substitute_reviews else LEGACY_REVIEW_BINDINGS_FIELDS
        findings.extend(_unknown_fields(reviews, review_fields, "profile.review_bindings"))
        findings.extend(_required_fields(reviews, review_fields, "profile.review_bindings"))
        correctness_key = "correctness" if substitute_reviews else "bugbot"
        correctness_findings, _, correctness_completed = _validate_review(
            reviews.get(correctness_key),
            f"profile.review_bindings.{correctness_key}",
            suite_sha256=suite_sha256,
            evidence_sha256=evidence_sha256,
            profile_payload_sha256=claimed_payload,
            expected_role="correctness",
            require_substitute_provenance=substitute_reviews,
        )
        sec_findings, sec_started, _ = _validate_review(
            reviews.get("security"),
            "profile.review_bindings.security",
            suite_sha256=suite_sha256,
            evidence_sha256=evidence_sha256,
            profile_payload_sha256=claimed_payload,
            expected_role="security",
            require_substitute_provenance=substitute_reviews,
        )
        findings.extend(correctness_findings)
        findings.extend(sec_findings)
        invalid_review_order = (
            correctness_completed is None
            or sec_started is None
            or sec_started < correctness_completed
            or (substitute_reviews and sec_started == correctness_completed)
        )
        if invalid_review_order:
            findings.append(Finding("profile", "Security Review must start after correctness review completes"))
        if isinstance(reviews.get(correctness_key), dict) and isinstance(reviews.get("security"), dict):
            correctness = reviews[correctness_key]
            security = reviews["security"]
            if correctness.get("reviewer_instance_id") == security.get("reviewer_instance_id"):
                findings.append(Finding("profile", "correctness and Security Review require distinct instances"))
            if substitute_reviews:
                if correctness.get("session_id") == security.get("session_id"):
                    findings.append(Finding("profile", "correctness and Security Review require distinct session IDs"))
                if (
                    "session_url" in correctness
                    and "session_url" in security
                    and correctness.get("session_url") == security.get("session_url")
                ):
                    findings.append(Finding("profile", "correctness and Security Review require distinct session URLs"))
                if correctness.get("findings_sha256") == security.get("findings_sha256"):
                    findings.append(Finding("profile", "correctness and Security Review require distinct report digests"))
            if schema_version in {2, 3}:
                candidate_ids = set(candidate_instance_ids)
            elif candidate_instance_id is not None:
                candidate_ids = {candidate_instance_id}
            else:
                candidate_ids = set()
            if correctness.get("reviewer_instance_id") in candidate_ids or security.get("reviewer_instance_id") in candidate_ids:
                findings.append(Finding("profile", "candidate and review instances must be distinct"))
            if (
                correctness.get("reviewer_instance_id") in source_implementer_instance_ids
                or security.get("reviewer_instance_id") in source_implementer_instance_ids
            ):
                findings.append(Finding("profile", "source Implementer and review instances must be distinct"))
            shared = {
                "project",
                "mr",
                "base_sha",
                "head_sha",
                "round",
                "pipeline",
                "task_contract_sha256",
                "suite_sha256",
                "evidence_sha256",
                "profile_payload_sha256",
            }
            for field in sorted(shared):
                if correctness.get(field) != security.get(field):
                    findings.append(Finding("profile", f"ordered reviews must share exact {field} binding"))
    return findings


def _expected_sha256(value: str | None, name: str) -> str:
    if value is None or not _is_sha256(value):
        raise ValueError(f"{name} must be a protected lowercase SHA-256 value")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("suite", "availability", "profile"))
    parser.add_argument("--root", default=".")
    parser.add_argument("--suite", required=True)
    parser.add_argument("--expected-suite-sha256", required=True)
    parser.add_argument("--record")
    parser.add_argument("--environment")
    parser.add_argument("--review-attestations")
    parser.add_argument("--expected-review-attestations-sha256")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    findings: list[Finding] = []
    try:
        suite, _ = load_json(root, args.suite)
        suite_sha256 = canonical_sha256(suite)
        expected_suite_sha256 = _expected_sha256(args.expected_suite_sha256, "--expected-suite-sha256")
        if not hmac.compare_digest(suite_sha256, expected_suite_sha256):
            findings.append(Finding("suite", "canonical suite JSON does not match the protected SHA-256"))
        suite_findings = validate_suite(suite)
        findings.extend(suite_findings)
        if args.command != "suite":
            if not args.record:
                findings.append(Finding("input", "--record is required"))
            elif not suite_findings:
                record, _ = load_json(root, args.record)
                if not args.environment:
                    findings.append(Finding("input", "--environment is required"))
                else:
                    environment, _ = load_json(root, args.environment)
                    environment_sha256 = canonical_sha256(environment)
                    findings.extend(validate_environment_binding(record, environment, environment_sha256))
                if args.command == "availability":
                    findings.extend(validate_availability(record, suite))
                else:
                    expected_reviews: Any = None
                    if not args.review_attestations:
                        findings.append(Finding("input", "--review-attestations is required for profiles"))
                    elif not args.expected_review_attestations_sha256:
                        findings.append(
                            Finding("input", "--expected-review-attestations-sha256 is required for profiles")
                        )
                    else:
                        expected_reviews, _ = load_json(root, args.review_attestations)
                        expected_reviews_sha256 = canonical_sha256(expected_reviews)
                        protected_reviews_sha256 = _expected_sha256(
                            args.expected_review_attestations_sha256,
                            "--expected-review-attestations-sha256",
                        )
                        if not hmac.compare_digest(expected_reviews_sha256, protected_reviews_sha256):
                            findings.append(
                                Finding("profile", "review attestations do not match the protected SHA-256")
                            )
                    findings.extend(
                        validate_profile(
                            record,
                            suite,
                            suite_sha256,
                            expected_review_bindings=expected_reviews,
                            protected_profile_sha256=os.environ.get("AIDF_PROTECTED_PROFILE_SHA256"),
                        )
                    )
    except (OSError, TypeError, UnicodeError, ValueError) as exc:
        findings.append(Finding("input", str(exc)))
    for finding in findings:
        print(f"FAIL [{finding.check}] {finding.message}")
    if findings:
        return 1
    print("PASS: qualification record is complete and fail-closed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
