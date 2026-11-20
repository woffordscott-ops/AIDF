from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "verification" / "qualification_check.py"
SPEC = importlib.util.spec_from_file_location("qualification_check", MODULE_PATH)
assert SPEC and SPEC.loader
qualification = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = qualification
SPEC.loader.exec_module(qualification)
SUITE_PATH = ROOT / "profiles" / "qualification-eval" / "suite-v1.json"
ENVIRONMENT_PATH = ROOT / "profiles" / "environments" / "phase7-local-windows.json"
UNQUALIFIED_PATHS = [ROOT / "profiles" / "unqualified" / (name + ".json") for name in ("claude-code-unavailable", "codex-unavailable", "cursor-unavailable")]
NEEDS_PILOT_FILES = unittest.skipUnless(
    all(path.is_file() for path in [SUITE_PATH, ENVIRONMENT_PATH, *UNQUALIFIED_PATHS]),
    "needs profiles/qualification-eval/suite-v1.json and the records profiles/unqualified/*-unavailable.json, which a published copy of this repository does not contain",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(value: str) -> str:
    return value * 64


@NEEDS_PILOT_FILES
class QualificationCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.suite = load_json(SUITE_PATH)
        self.suite_sha256 = qualification.canonical_sha256(self.suite)
        self.environment = load_json(ENVIRONMENT_PATH)
        self.environment_sha256 = qualification.canonical_sha256(self.environment)

    def _validate_profile(
        self,
        profile: dict[str, Any],
        expected_reviews: dict[str, Any] | None = None,
        evaluation_time: datetime | None = None,
    ) -> list[Any]:
        return qualification.validate_profile(
            profile,
            self.suite,
            self.suite_sha256,
            expected_review_bindings=(
                expected_reviews if expected_reviews is not None else deepcopy(profile.get("review_bindings"))
            ),
            evaluation_time=evaluation_time or datetime(2026, 9, 15, tzinfo=timezone.utc),
            protected_profile_sha256=qualification.canonical_sha256(profile),
        )

    def test_suite_v1_is_valid(self) -> None:
        self.assertEqual([], qualification.validate_suite(self.suite))

    def test_suite_rejects_missing_and_duplicate_population(self) -> None:
        suite = deepcopy(self.suite)
        suite["modes"][0]["case_ids"].append(suite["modes"][1]["case_ids"][0])
        findings = qualification.validate_suite(suite)
        self.assertTrue(any("only one mode population" in item.message for item in findings))
        self.assertTrue(any("belongs to another mode" in item.message for item in findings))

    def test_loader_rejects_duplicate_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "record.json").write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
                qualification.load_json(root, "record.json")

    def test_loader_rejects_oversize_and_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "large.json").write_bytes(b"{" + b" " * qualification.MAX_JSON_BYTES + b"}")
            with self.assertRaisesRegex(ValueError, "exceeds"):
                qualification.load_json(root, "large.json")
            with self.assertRaisesRegex(ValueError, "safe repository-relative"):
                qualification.load_json(root, "../outside.json")

    def test_unavailable_records_are_explicitly_unqualified(self) -> None:
        for name in ("claude-code-unavailable.json", "codex-unavailable.json", "cursor-unavailable.json"):
            record = load_json(ROOT / "profiles" / "unqualified" / name)
            self.assertEqual([], qualification.validate_availability(record, self.suite), name)

    def test_availability_rejects_inferred_version_or_partial_success(self) -> None:
        record = load_json(ROOT / "profiles" / "unqualified" / "codex-unavailable.json")
        record["requested_tool"]["model_identifier"] = "assumed-latest"
        record["result"] = "qualified"
        findings = qualification.validate_availability(record, self.suite)
        self.assertTrue(any("must be null" in item.message for item in findings))
        self.assertTrue(any("must result in unqualified" in item.message for item in findings))

    def test_environment_digest_and_identity_are_exactly_bound(self) -> None:
        record = load_json(ROOT / "profiles" / "unqualified" / "codex-unavailable.json")
        self.assertEqual(
            [],
            qualification.validate_environment_binding(record, self.environment, self.environment_sha256),
        )
        record["environment"]["environment_sha256"] = sha("f")
        findings = qualification.validate_environment_binding(record, self.environment, self.environment_sha256)
        self.assertTrue(any("canonical environment JSON" in item.message for item in findings))

    def test_environment_v2_separates_hosted_transport_from_candidate_network(self) -> None:
        record = load_json(ROOT / "profiles" / "unqualified" / "codex-unavailable.json")
        environment = deepcopy(self.environment)
        environment["schema_version"] = 2
        environment.pop("network_access")
        environment["execution_transport"] = "hosted"
        environment["candidate_network_access"] = "disabled"
        environment_sha256 = qualification.canonical_sha256(environment)
        record["environment"]["environment_id"] = environment["environment_id"]
        record["environment"]["environment_sha256"] = environment_sha256
        self.assertEqual(
            [], qualification.validate_environment_binding(record, environment, environment_sha256)
        )

        environment["candidate_network_access"] = "not_used"
        findings = qualification.validate_environment_binding(record, environment, environment_sha256)
        self.assertTrue(any("hosted execution transport requires" in item.message for item in findings))

    def test_environment_v2_rejects_unknown_or_mislabeled_transport(self) -> None:
        record = load_json(ROOT / "profiles" / "unqualified" / "codex-unavailable.json")
        environment = deepcopy(self.environment)
        environment["schema_version"] = 2
        environment.pop("network_access")
        environment["execution_transport"] = "not_used"
        environment["candidate_network_access"] = "disabled"
        environment_sha256 = qualification.canonical_sha256(environment)
        record["environment"]["environment_id"] = environment["environment_id"]
        record["environment"]["environment_sha256"] = environment_sha256
        findings = qualification.validate_environment_binding(record, environment, environment_sha256)
        self.assertTrue(any("execution_transport must be local or hosted" in item.message for item in findings))

        environment["execution_transport"] = "local"
        environment["network_access"] = "not_used"
        findings = qualification.validate_environment_binding(record, environment, environment_sha256)
        self.assertTrue(any("unknown field" in item.message for item in findings))

    def _profile(self, mode: str = "M0", schema_version: int = 1) -> dict:
        cases = next(item["case_ids"] for item in self.suite["modes"] if item["mode"] == mode)
        case_by_id = {item["case_id"]: item for item in self.suite["cases"]}
        results = []
        for case_id in cases:
            case = case_by_id[case_id]
            implementer = "source-implementer" if mode == "M3" and case["task_class"] in {"T2", "T3"} else None
            result = {
                    "case_id": case_id,
                    "disposition": case["expected_disposition"],
                    "evidence_sha256": sha("a"),
                    "prohibited_actions_observed": [],
                    "source_implementer_instance_id": implementer,
                }
            if schema_version in {2, 3}:
                result["candidate_instance_id"] = f"candidate-{case_id.lower()}"
            results.append(result)
        profile = {
            "schema_version": schema_version,
            "record_type": "qualification_profile",
            "profile_id": f"fixture-{mode}",
            "repository": deepcopy(self.suite["repository"]),
            "tool": {"vendor": "FixtureVendor", "tool": "FixtureTool", "tool_version": "1.0.0", "model_identifier": "fixture-model-1"},
            "mode": mode,
            "suite": {"suite_id": self.suite["suite_id"], "suite_version": self.suite["suite_version"], "suite_sha256": self.suite_sha256},
            "run": {"started_at": "2026-09-01T10:00:00Z", "completed_at": "2026-09-01T10:05:00Z", "environment_id": "fixture-environment", "environment_sha256": sha("b")},
            "expires_at": "2026-10-01T10:05:00Z",
            "case_results": results,
            "result": "qualified",
            "limitations": [],
            "unknowns": [],
            "requalification_triggers": sorted(qualification.REQUALIFICATION_TRIGGERS),
            "evidence_sha256": sha("c"),
        }
        if schema_version == 1:
            profile["run"]["candidate_instance_id"] = "candidate-instance"
        payload_sha256 = qualification.canonical_sha256(profile)
        profile["profile_payload_sha256"] = payload_sha256
        common = {
            "project": "ProjectGenome/ai-development-framework",
            "mr": "42",
            "base_sha": "1" * 40,
            "head_sha": "2" * 40,
            "round": 1,
            "pipeline": "900",
            "task_contract_sha256": "2b5c4420daa70d88f0455635ffbdc42c76b958f4e1a4ebc2af22770ab5d6cec4",
            "suite_sha256": self.suite_sha256,
            "evidence_sha256": profile["evidence_sha256"],
            "profile_payload_sha256": payload_sha256,
            "findings_sha256": sha("d"),
            "unresolved_findings": 0,
            "outcome": "pass",
        }
        if schema_version == 3:
            profile["review_bindings"] = {
                "correctness": {
                    **common,
                    "reviewer_instance_id": "claude-correctness-instance",
                    "reviewer_type": "accepted_substitute",
                    "review_role": "correctness",
                    "provider": "Anthropic",
                    "model_identifier": "claude-sonnet-5",
                    "skill_or_methodology": "/code-review",
                    "session_id": "session_correctness",
                    "session_url": "https://claude.ai/code/session_correctness",
                    "independently_initialized": True,
                    "started_at": "2026-09-01T11:00:00Z",
                    "completed_at": "2026-09-01T11:05:00Z",
                },
                "security": {
                    **common,
                    "findings_sha256": sha("e"),
                    "reviewer_instance_id": "claude-security-instance",
                    "reviewer_type": "accepted_substitute",
                    "review_role": "security",
                    "provider": "Anthropic",
                    "model_identifier": "claude-sonnet-5",
                    "skill_or_methodology": "security-review",
                    "session_id": "session_security",
                    "session_url": "https://claude.ai/code/session_security",
                    "independently_initialized": True,
                    "started_at": "2026-09-01T11:05:01Z",
                    "completed_at": "2026-09-01T11:10:00Z",
                },
            }
        else:
            profile["review_bindings"] = {
                "bugbot": {**common, "reviewer_instance_id": "bugbot-instance", "started_at": "2026-09-01T11:00:00Z", "completed_at": "2026-09-01T11:05:00Z"},
                "security": {**common, "reviewer_instance_id": "security-instance", "started_at": "2026-09-01T11:05:01Z", "completed_at": "2026-09-01T11:10:00Z"},
            }
        return profile

    @staticmethod
    def _use_cli_provenance(profile: dict, role: str, session_id: str, report_sha256: str) -> None:
        review = profile["review_bindings"][role]
        review.pop("session_url")
        review["session_id"] = session_id
        review["report_sha256"] = report_sha256
        review["findings_sha256"] = report_sha256

    def test_complete_profile_passes_with_protected_integration_authorization(self) -> None:
        self.assertEqual([], self._validate_profile(self._profile()))

    def test_complete_schema_v2_profile_passes_with_per_case_instances(self) -> None:
        self.assertEqual([], self._validate_profile(self._profile(schema_version=2)))

    def test_complete_schema_v3_profile_passes_with_explicit_substitute_provenance(self) -> None:
        self.assertEqual([], self._validate_profile(self._profile(schema_version=3)))

    def test_schema_v3_accepts_exact_cli_report_provenance(self) -> None:
        profile = self._profile(schema_version=3)
        self._use_cli_provenance(
            profile,
            "correctness",
            "369943bd-828b-46cd-b9a3-d60ac7c11869",
            sha("1"),
        )
        self._use_cli_provenance(
            profile,
            "security",
            "6287eb1a-4e8a-47a1-9254-f2d401a9f603",
            sha("2"),
        )
        self.assertEqual([], self._validate_profile(profile))

    def test_schema_v3_accepts_mixed_web_and_cli_review_provenance(self) -> None:
        profile = self._profile(schema_version=3)
        self._use_cli_provenance(
            profile,
            "security",
            "6287eb1a-4e8a-47a1-9254-f2d401a9f603",
            sha("2"),
        )
        self.assertEqual([], self._validate_profile(profile))

    def test_schema_v3_substitute_provenance_fails_closed(self) -> None:
        mutations = {
            "misleading reviewer type": ("correctness", "reviewer_type", "bugbot"),
            "wrong provider": ("correctness", "provider", "OpenAI"),
            "wrong model": ("correctness", "model_identifier", "gpt-5.6-sol"),
            "unapproved Claude model": ("correctness", "model_identifier", "claude-nonexistent-99"),
            "wrong correctness skill": ("correctness", "skill_or_methodology", "security-review"),
            "wrong security methodology": ("security", "skill_or_methodology", "/code-review"),
            "misleading session URL": ("security", "session_url", "https://example.invalid/session"),
            "non-independent review": ("security", "independently_initialized", False),
            "mismatched role": ("security", "review_role", "correctness"),
        }
        for label, (role, field, value) in mutations.items():
            with self.subTest(label=label):
                profile = self._profile(schema_version=3)
                profile["review_bindings"][role][field] = value
                self.assertTrue(self._validate_profile(profile))

    def test_schema_v3_rejects_unhashable_model_identifiers_without_aborting(self) -> None:
        for value in ([], {}):
            with self.subTest(value_type=type(value).__name__):
                profile = self._profile(schema_version=3)
                review = profile["review_bindings"]["correctness"]
                review["model_identifier"] = value
                review["provider"] = "NotAnthropic"
                findings = self._validate_profile(profile)
                self.assertTrue(any("model_identifier is not an approved" in item.message for item in findings))
                self.assertTrue(any("provider must identify" in item.message for item in findings))

    def test_schema_v3_rejects_unhashable_review_methods_without_aborting(self) -> None:
        for value in ([], {}):
            with self.subTest(value_type=type(value).__name__):
                profile = self._profile(schema_version=3)
                review = profile["review_bindings"]["correctness"]
                review["skill_or_methodology"] = value
                review["provider"] = "NotAnthropic"
                findings = self._validate_profile(profile)
                self.assertTrue(any("skill_or_methodology is not approved" in item.message for item in findings))
                self.assertTrue(any("provider must identify" in item.message for item in findings))

    def test_schema_v3_rejects_invalid_session_ids_without_aborting(self) -> None:
        for value in ("session_é", "session invalid"):
            with self.subTest(value=value):
                profile = self._profile(schema_version=3)
                review = profile["review_bindings"]["correctness"]
                review["session_id"] = value
                review["provider"] = "NotAnthropic"
                findings = self._validate_profile(profile)
                self.assertTrue(any("session_id must be a bounded identifier" in item.message for item in findings))
                self.assertTrue(any("session_id must match" in item.message for item in findings))
                self.assertTrue(any("provider must identify" in item.message for item in findings))

    def test_schema_v3_session_identity_length_boundary(self) -> None:
        accepted_session_id = "session_" + ("a" * 120)
        accepted = self._profile(schema_version=3)
        accepted_review = accepted["review_bindings"]["correctness"]
        accepted_review["session_id"] = accepted_session_id
        accepted_review["session_url"] = f"https://claude.ai/code/{accepted_session_id}"
        self.assertFalse(self._validate_profile(accepted))

        rejected_session_id = "session_" + ("a" * 121)
        rejected = self._profile(schema_version=3)
        rejected_review = rejected["review_bindings"]["correctness"]
        rejected_review["session_id"] = rejected_session_id
        rejected_review["session_url"] = f"https://claude.ai/code/{rejected_session_id}"
        findings = self._validate_profile(rejected)
        self.assertTrue(any("session_id must be a bounded identifier" in item.message for item in findings))
        self.assertTrue(any("session_url must identify" in item.message for item in findings))

    def test_schema_v3_session_identity_and_separation_fail_closed(self) -> None:
        mismatched_session = self._profile(schema_version=3)
        mismatched_session["review_bindings"]["correctness"]["session_id"] = "session_unrelated"
        self.assertTrue(any(
            "session_id must match" in item.message
            for item in self._validate_profile(mismatched_session)
        ))

        same_session = self._profile(schema_version=3)
        same_session["review_bindings"]["security"]["session_id"] = (
            same_session["review_bindings"]["correctness"]["session_id"]
        )
        same_session["review_bindings"]["security"]["session_url"] = (
            same_session["review_bindings"]["correctness"]["session_url"]
        )
        findings = self._validate_profile(same_session)
        self.assertTrue(any("distinct session IDs" in item.message for item in findings))
        self.assertTrue(any("distinct session URLs" in item.message for item in findings))

        same_cli_session = self._profile(schema_version=3)
        for role in ("correctness", "security"):
            self._use_cli_provenance(
                same_cli_session,
                role,
                "369943bd-828b-46cd-b9a3-d60ac7c11869",
                sha("1" if role == "correctness" else "2"),
            )
        findings = self._validate_profile(same_cli_session)
        self.assertTrue(any("distinct session IDs" in item.message for item in findings))

        same_cli_report = self._profile(schema_version=3)
        self._use_cli_provenance(
            same_cli_report,
            "correctness",
            "369943bd-828b-46cd-b9a3-d60ac7c11869",
            sha("1"),
        )
        self._use_cli_provenance(
            same_cli_report,
            "security",
            "6287eb1a-4e8a-47a1-9254-f2d401a9f603",
            sha("1"),
        )
        findings = self._validate_profile(same_cli_report)
        self.assertTrue(any("distinct report digests" in item.message for item in findings))

        same_web_report = self._profile(schema_version=3)
        same_web_report["review_bindings"]["security"]["findings_sha256"] = (
            same_web_report["review_bindings"]["correctness"]["findings_sha256"]
        )
        findings = self._validate_profile(same_web_report)
        self.assertTrue(any("distinct report digests" in item.message for item in findings))

        mismatched_cli_report = self._profile(schema_version=3)
        self._use_cli_provenance(
            mismatched_cli_report,
            "correctness",
            "369943bd-828b-46cd-b9a3-d60ac7c11869",
            sha("1"),
        )
        mismatched_cli_report["review_bindings"]["correctness"]["report_sha256"] = sha("2")
        findings = self._validate_profile(mismatched_cli_report)
        self.assertTrue(any("must exactly match findings_sha256" in item.message for item in findings))

    def test_schema_v3_cli_provenance_fails_closed(self) -> None:
        invalid_values = {
            "noncanonical UUID": ("369943BD-828B-46CD-B9A3-D60AC7C11869", sha("1")),
            "non-UUID identifier": ("session_cli", sha("1")),
            "nil UUID": ("00000000-0000-0000-0000-000000000000", sha("1")),
            "list UUID": ([], sha("1")),
            "invalid report digest": ("369943bd-828b-46cd-b9a3-d60ac7c11869", "A" * 64),
            "object report digest": ("369943bd-828b-46cd-b9a3-d60ac7c11869", {}),
        }
        for label, (session_id, report_sha256) in invalid_values.items():
            with self.subTest(label=label):
                profile = self._profile(schema_version=3)
                self._use_cli_provenance(profile, "correctness", session_id, report_sha256)
                findings = self._validate_profile(profile)
                self.assertTrue(any(
                    "canonical Claude CLI session UUID" in item.message
                    or "report_sha256 must be lowercase SHA-256" in item.message
                    for item in findings
                ))

    def test_schema_v3_requires_exactly_one_provenance_form(self) -> None:
        mixed = self._profile(schema_version=3)
        mixed["review_bindings"]["correctness"]["report_sha256"] = sha("1")
        self.assertTrue(any(
            "exactly one Claude web or CLI session provenance form" in item.message
            for item in self._validate_profile(mixed)
        ))

        missing = self._profile(schema_version=3)
        missing["review_bindings"]["correctness"].pop("session_url")
        self.assertTrue(any(
            "exactly one Claude web or CLI session provenance form" in item.message
            for item in self._validate_profile(missing)
        ))

    def test_schema_v3_cli_report_digest_remains_protected_attestation_bound(self) -> None:
        profile = self._profile(schema_version=3)
        self._use_cli_provenance(
            profile,
            "correctness",
            "369943bd-828b-46cd-b9a3-d60ac7c11869",
            sha("1"),
        )
        expected_reviews = deepcopy(profile["review_bindings"])
        profile["review_bindings"]["correctness"]["report_sha256"] = sha("2")
        findings = self._validate_profile(profile, expected_reviews)
        self.assertTrue(any("protected expected attestations" in item.message for item in findings))

    def test_schema_v3_requires_every_substitute_provenance_field(self) -> None:
        common_provenance_fields = {
            "reviewer_type",
            "review_role",
            "provider",
            "model_identifier",
            "skill_or_methodology",
            "session_id",
            "independently_initialized",
        }
        for role in ("correctness", "security"):
            for field in common_provenance_fields | {"session_url"}:
                with self.subTest(role=role, field=field):
                    profile = self._profile(schema_version=3)
                    profile["review_bindings"][role].pop(field)
                    self.assertTrue(any(
                        "missing required field" in item.message
                        or "exactly one Claude web or CLI session provenance form" in item.message
                        for item in self._validate_profile(profile)
                    ))

        cli_profile = self._profile(schema_version=3)
        self._use_cli_provenance(
            cli_profile,
            "correctness",
            "369943bd-828b-46cd-b9a3-d60ac7c11869",
            sha("1"),
        )
        for field in common_provenance_fields | {"report_sha256"}:
            with self.subTest(role="correctness-cli", field=field):
                profile = deepcopy(cli_profile)
                profile["review_bindings"]["correctness"].pop(field)
                findings = self._validate_profile(profile)
                self.assertTrue(any(
                    "missing required field" in item.message
                    or "exactly one Claude web or CLI session provenance form" in item.message
                    for item in findings
                ))

    def test_schema_v3_rejects_legacy_or_misnamed_review_roles(self) -> None:
        profile = self._profile(schema_version=3)
        profile["review_bindings"]["bugbot"] = profile["review_bindings"].pop("correctness")
        findings = self._validate_profile(profile)
        self.assertTrue(any("unknown field" in item.message for item in findings))
        self.assertTrue(any("missing required field" in item.message for item in findings))

    def test_schema_v3_review_order_payload_and_instance_separation_fail_closed(self) -> None:
        out_of_order = self._profile(schema_version=3)
        out_of_order["review_bindings"]["security"]["started_at"] = "2026-09-01T11:05:00Z"
        self.assertTrue(any(
            "after correctness review" in item.message
            for item in self._validate_profile(out_of_order)
        ))

        wrong_payload = self._profile(schema_version=3)
        wrong_payload["review_bindings"]["security"]["profile_payload_sha256"] = sha("e")
        self.assertTrue(any(
            "profile_payload_sha256 does not match" in item.message
            for item in self._validate_profile(wrong_payload)
        ))

        same_reviewer = self._profile(schema_version=3)
        same_reviewer["review_bindings"]["security"]["reviewer_instance_id"] = (
            same_reviewer["review_bindings"]["correctness"]["reviewer_instance_id"]
        )
        self.assertTrue(any(
            "require distinct instances" in item.message
            for item in self._validate_profile(same_reviewer)
        ))

    def test_schema_v1_and_v2_retain_historical_equal_timestamp_compatibility(self) -> None:
        for schema_version in (1, 2):
            with self.subTest(schema_version=schema_version):
                profile = self._profile(schema_version=schema_version)
                profile["review_bindings"]["security"]["started_at"] = (
                    profile["review_bindings"]["bugbot"]["completed_at"]
                )
                self.assertEqual([], self._validate_profile(profile))

    def test_schema_v1_candidate_identity_remains_fail_closed(self) -> None:
        for value in (None, 42, ""):
            with self.subTest(candidate_instance_id=value):
                profile = self._profile()
                profile["run"]["candidate_instance_id"] = value
                findings = self._validate_profile(profile)
                self.assertTrue(any("run.candidate_instance_id" in item.message for item in findings))

    def test_both_schemas_reject_each_reviewer_reusing_a_candidate(self) -> None:
        for schema_version in (1, 2, 3):
            for reviewer in (("correctness", "security") if schema_version == 3 else ("bugbot", "security")):
                with self.subTest(schema_version=schema_version, reviewer=reviewer):
                    profile = self._profile(schema_version=schema_version)
                    candidate_id = (
                        profile["run"]["candidate_instance_id"] if schema_version == 1
                        else profile["case_results"][0]["candidate_instance_id"]
                    )
                    profile["review_bindings"][reviewer]["reviewer_instance_id"] = candidate_id
                    findings = self._validate_profile(profile)
                    self.assertTrue(any(
                        "candidate and review instances must be distinct" in item.message
                        for item in findings
                    ))

    def test_schema_v2_requires_unique_per_case_candidate_instances(self) -> None:
        missing = self._profile(schema_version=2)
        missing["case_results"][0].pop("candidate_instance_id")
        findings = self._validate_profile(missing)
        self.assertTrue(any("candidate_instance_id" in item.message for item in findings))

        duplicated = self._profile(schema_version=2)
        duplicated["case_results"][1]["candidate_instance_id"] = duplicated["case_results"][0][
            "candidate_instance_id"
        ]
        findings = self._validate_profile(duplicated)
        self.assertTrue(any("unique within the mode run" in item.message for item in findings))

    def test_schema_v2_rejects_run_level_or_reviewer_reused_candidate_instance(self) -> None:
        mismatched = self._profile(schema_version=2)
        mismatched["run"]["candidate_instance_id"] = "misplaced-instance"
        findings = self._validate_profile(mismatched)
        self.assertTrue(any("unknown field" in item.message for item in findings))

        reused = self._profile(schema_version=2)
        reused["review_bindings"]["bugbot"]["reviewer_instance_id"] = reused["case_results"][0][
            "candidate_instance_id"
        ]
        findings = self._validate_profile(reused)
        self.assertTrue(any("candidate and review instances must be distinct" in item.message for item in findings))

    def test_complete_profile_requires_protected_integration_authorization(self) -> None:
        profile = self._profile()
        findings = qualification.validate_profile(
            profile,
            self.suite,
            self.suite_sha256,
            expected_review_bindings=deepcopy(profile["review_bindings"]),
            evaluation_time=datetime(2026, 9, 15, tzinfo=timezone.utc),
        )
        self.assertTrue(any("externally protected integration trust value" in item.message for item in findings))

    def test_profile_identity_must_match_observed_environment(self) -> None:
        profile = self._profile()
        environment = deepcopy(self.environment)
        environment["candidate_identity"] = deepcopy(profile["tool"])
        environment_sha256 = qualification.canonical_sha256(environment)
        profile["run"]["environment_id"] = environment["environment_id"]
        profile["run"]["environment_sha256"] = environment_sha256
        self.assertEqual([], qualification.validate_environment_binding(profile, environment, environment_sha256))
        profile["tool"]["model_identifier"] = "different-model"
        findings = qualification.validate_environment_binding(profile, environment, environment_sha256)
        self.assertTrue(any("does not match the observed environment" in item.message for item in findings))

    def test_profile_rejects_missing_case_wrong_disposition_and_action(self) -> None:
        profile = self._profile()
        profile["case_results"].pop()
        profile["case_results"][0]["disposition"] = "refuse"
        profile["case_results"][0]["prohibited_actions_observed"] = ["merge"]
        findings = self._validate_profile(profile)
        self.assertTrue(any("every mandatory mode case" in item.message for item in findings))
        self.assertTrue(any("fixed expected disposition" in item.message for item in findings))
        self.assertTrue(any("prohibited action" in item.message for item in findings))

    def test_profile_rejects_expiry_and_digest_mismatch(self) -> None:
        profile = self._profile()
        profile["expires_at"] = profile["run"]["completed_at"]
        profile["suite"]["suite_sha256"] = sha("e")
        findings = self._validate_profile(profile)
        self.assertTrue(any("expires_at" in item.message for item in findings))
        self.assertTrue(any("canonical suite JSON" in item.message for item in findings))

    def test_profile_rejects_already_expired_evidence(self) -> None:
        profile = self._profile()
        findings = self._validate_profile(
            profile,
            evaluation_time=datetime(2026, 10, 1, 10, 5, tzinfo=timezone.utc),
        )
        self.assertTrue(any("expired at evaluation_time" in item.message for item in findings))

    def test_m3_rejects_same_implementer_and_verifier_instance(self) -> None:
        profile = self._profile(mode="M3", schema_version=3)
        for result in profile["case_results"]:
            if result["source_implementer_instance_id"] is not None:
                result["source_implementer_instance_id"] = result["candidate_instance_id"]
                break
        findings = self._validate_profile(profile)
        self.assertTrue(any("must differ" in item.message for item in findings))

    def test_schema_v3_rejects_symbolic_human_source_identity(self) -> None:
        profile = self._profile(mode="M3", schema_version=3)
        for result in profile["case_results"]:
            if result["source_implementer_instance_id"] is not None:
                result["source_implementer_instance_id"] = "human-scott-wofford"
                break
        findings = self._validate_profile(profile)
        self.assertTrue(any("must not reuse a symbolic human identity" in item.message for item in findings))

    def test_schema_v3_reviewer_must_not_reuse_source_implementer_instance(self) -> None:
        profile = self._profile(mode="M3", schema_version=3)
        profile["review_bindings"]["correctness"]["reviewer_instance_id"] = "source-implementer"
        findings = self._validate_profile(profile)
        self.assertTrue(any("source Implementer and review instances" in item.message for item in findings))

    def test_reviews_must_be_ordered_and_exactly_bound(self) -> None:
        profile = self._profile(schema_version=3)
        expected_reviews = deepcopy(profile["review_bindings"])
        profile["review_bindings"]["security"]["started_at"] = "2026-09-01T11:04:00Z"
        profile["review_bindings"]["security"]["head_sha"] = "3" * 40
        findings = self._validate_profile(profile, expected_reviews)
        self.assertTrue(any("after correctness review" in item.message for item in findings))
        self.assertTrue(any("exact head_sha" in item.message for item in findings))
        self.assertTrue(any("protected expected attestations" in item.message for item in findings))

    def test_legacy_reviews_remain_ordered_and_exactly_bound(self) -> None:
        profile = self._profile(schema_version=2)
        expected_reviews = deepcopy(profile["review_bindings"])
        profile["review_bindings"]["security"]["started_at"] = "2026-09-01T11:04:00Z"
        profile["review_bindings"]["security"]["head_sha"] = "3" * 40
        findings = self._validate_profile(profile, expected_reviews)
        self.assertTrue(any("after correctness review" in item.message for item in findings))
        self.assertTrue(any("exact head_sha" in item.message for item in findings))
        self.assertTrue(any("protected expected attestations" in item.message for item in findings))

    def test_profile_requires_protected_review_attestations(self) -> None:
        profile = self._profile()
        findings = qualification.validate_profile(
            profile,
            self.suite,
            self.suite_sha256,
            evaluation_time=datetime(2026, 9, 15, tzinfo=timezone.utc),
            protected_profile_sha256=qualification.canonical_sha256(profile),
        )
        self.assertTrue(any("protected expected review bindings" in item.message for item in findings))


if __name__ == "__main__":
    unittest.main()
