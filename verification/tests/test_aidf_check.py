from __future__ import annotations

import argparse
import base64
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "verification" / "aidf_check.py"
SPEC = importlib.util.spec_from_file_location("aidf_check", MODULE_PATH)
assert SPEC and SPEC.loader
aidf = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = aidf
SPEC.loader.exec_module(aidf)
FIXTURES = ROOT / "verification" / "fixtures"
EXPANDED_POLICY = FIXTURES / "positive" / "automation-policy-expanded-streamlined.json"
NEEDS_EXPANDED_POLICY = unittest.skipUnless(
    EXPANDED_POLICY.is_file(),
    "needs verification/fixtures/positive/automation-policy-expanded-streamlined.json, which a published copy of this repository does not contain",
)


def fixture(relative: str):
    return json.loads((FIXTURES / relative).read_text(encoding="utf-8"))


def text_fixture(relative: str) -> str:
    return (FIXTURES / relative).read_text(encoding="utf-8")


def trusted_policy_args(policy: dict) -> dict:
    return {
        "expected_project_id": policy["project_id"],
        "expected_policy_sha256": aidf.automation_policy_sha256(policy),
    }


def git_patch(path: str, *, added: list[str] | None = None, removed: list[str] | None = None) -> str:
    additions = added or []
    removals = removed or []
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        f"@@ -1,{len(removals)} +1,{len(additions)} @@\n"
        + "".join(f"-{line}\n" for line in removals)
        + "".join(f"+{line}\n" for line in additions)
    )


class VerificationChecksTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = fixture("positive/contract-t2.json")
        self.policy = json.loads((ROOT / "verification" / "policy.json").read_text(encoding="utf-8"))

    def test_contract_accepts_positive_fixture(self) -> None:
        self.assertEqual([], aidf.validate_contract(self.contract))

    def test_strict_json_rejects_duplicate_object_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "record.json").write_text('{"class":"T3","class":"T0"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON object key 'class'"):
                aidf.load_json(root, "record.json")

    def test_strict_json_rejects_nonfinite_numbers_from_base64(self) -> None:
        encoded = base64.b64encode(b'{"coverage_before":NaN}').decode("ascii")
        with self.assertRaisesRegex(ValueError, "non-finite JSON number 'NaN'"):
            aidf.load_json_base64(encoded, "--policy-b64")

    def test_strict_json_rejects_float_overflow(self) -> None:
        encoded = base64.b64encode(b'{"coverage_before":1e400}').decode("ascii")
        with self.assertRaisesRegex(ValueError, "non-finite JSON number '1e400'"):
            aidf.load_json_base64(encoded, "--policy-b64")

    def test_schema_version_rejects_boolean_true(self) -> None:
        contract = deepcopy(self.contract)
        contract["schema_version"] = True
        findings = aidf.validate_contract(contract)
        self.assertTrue(any("schema_version must be 1" in item.message for item in findings))

    def test_contract_rejects_non_clear_fixture(self) -> None:
        findings = aidf.validate_contract(fixture("negative/contract-not-clear.json"))
        self.assertTrue(any("spec_confidence" in item.message for item in findings))

    def test_evidence_accepts_positive_fixture(self) -> None:
        self.assertEqual([], aidf.validate_evidence(fixture("positive/evidence-t2.json"), self.contract))

    def test_evidence_rejects_missing_counterfactual(self) -> None:
        findings = aidf.validate_evidence(fixture("negative/evidence-missing-e3.json"), self.contract)
        self.assertTrue(any("requires an e3" in item.message for item in findings))

    def test_e1_cannot_be_unavailable(self) -> None:
        evidence = fixture("positive/evidence-t2.json")
        evidence["e1"]["status"] = "unavailable"
        findings = aidf.validate_evidence(evidence, self.contract)
        self.assertTrue(any("e1.status" in item.message for item in findings))

    def test_linked_e3_exemption_is_accepted(self) -> None:
        contract = deepcopy(self.contract)
        contract.update({"change_id": "fixture-1", "class": "T1"})
        contract.pop("approved_by")
        contract.pop("approved_date")
        evidence = fixture("positive/evidence-t2.json")
        evidence.update({"change_id": "fixture-1", "class": "T1", "e3": {"status": "exempted", "exemption_id": "EX-1"}})
        for field in ("e4", "e5", "e6"):
            evidence.pop(field)
        records = fixture("positive/exemptions-five-open.json")
        self.assertEqual([], aidf.validate_evidence(evidence, contract, records))

    def test_unregistered_e3_exemption_is_rejected(self) -> None:
        contract = deepcopy(self.contract)
        contract.update({"change_id": "fixture-6", "class": "T1"})
        contract.pop("approved_by")
        contract.pop("approved_date")
        evidence = fixture("positive/evidence-t2.json")
        evidence.update({"change_id": "fixture-6", "class": "T1", "e3": {"status": "exempted", "exemption_id": "EX-6"}})
        for field in ("e4", "e5", "e6"):
            evidence.pop(field)
        findings = aidf.validate_evidence(evidence, contract, fixture("positive/exemptions-five-open.json"))
        self.assertTrue(any("exactly one registry record" in item.message for item in findings))

    def test_exemption_cap_accepts_five_open(self) -> None:
        self.assertEqual([], aidf.validate_exemptions(fixture("positive/exemptions-five-open.json")))

    def test_exemption_cap_rejects_six_open(self) -> None:
        findings = aidf.validate_exemptions(fixture("negative/exemptions-six-open.json"))
        self.assertTrue(any("hard cap is 5" in item.message for item in findings))

    def test_scope_accepts_declared_file(self) -> None:
        self.assertEqual([], aidf.check_scope(["src/service.py"], self.contract))

    def test_scope_rejects_undeclared_file(self) -> None:
        findings = aidf.check_scope(["outside/service.py"], self.contract)
        self.assertTrue(any("outside declared scope" in item.message for item in findings))

    def test_tripwire_accepts_t3_declaration(self) -> None:
        contract = fixture("positive/contract-t3-tripwire.json")
        self.assertEqual([], aidf.check_tripwires(["src/auth/login.py"], "", self.policy, contract))

    def test_tripwire_rejects_lower_class(self) -> None:
        contract = fixture("negative/contract-t1-tripwire.json")
        findings = aidf.check_tripwires(["src/auth/login.py"], "", self.policy, contract)
        self.assertTrue(any("force T3" in item.message for item in findings))

    def test_declared_tripwire_forces_t3_without_detected_signal(self) -> None:
        contract = fixture("negative/contract-t1-tripwire.json")
        findings = aidf.check_tripwires(["src/benign.py"], "", self.policy, contract)
        self.assertTrue(any("force T3" in item.message for item in findings))

    def test_policy_covers_every_locked_tripwire_family(self) -> None:
        self.assertEqual([], aidf.validate_policy(self.policy))
        represented = {
            item["id"]
            for field in ("tripwire_paths", "tripwire_content_terms")
            for item in self.policy[field]
        }
        self.assertEqual(aidf.TRIPWIRE_FAMILIES, represented)

    @NEEDS_EXPANDED_POLICY
    def test_automation_policy_accepts_expanded_streamlined_pilot(self) -> None:
        policy = fixture("positive/automation-policy-expanded-streamlined.json")
        self.assertEqual([], aidf.validate_automation_policy(policy, today=date(2026, 8, 30)))
        resolved = aidf.resolve_automation_policy(
            policy, today=date(2026, 8, 30), **trusted_policy_args(policy)
        )
        self.assertTrue(resolved["authorization_active"])
        self.assertEqual("T2", resolved["effective_auto_merge_max_class"])
        self.assertEqual([], resolved["human_involvement"]["checkpoint_actions"])

    def test_automation_policy_accepts_bounded_custom_profile(self) -> None:
        policy = fixture("positive/automation-policy-custom.json")
        self.assertEqual([], aidf.validate_automation_policy(policy, today=date(2026, 8, 30)))
        self.assertEqual(
            "T1",
            aidf.resolve_automation_policy(
                policy, today=date(2026, 8, 30), **trusted_policy_args(policy)
            )["effective_auto_merge_max_class"],
        )

    def test_automation_policy_rejects_t3_autonomy(self) -> None:
        findings = aidf.validate_automation_policy(
            fixture("negative/automation-policy-t3.json"), today=date(2026, 8, 30)
        )
        self.assertTrue(any("T0, T1, or T2" in item.message for item in findings))

    def test_automation_policy_expiry_fails_to_safe_profile(self) -> None:
        policy = fixture("negative/automation-policy-expired.json")
        findings = aidf.validate_automation_policy(policy, today=date(2026, 8, 30))
        self.assertTrue(any("expired" in item.message for item in findings))
        resolved = aidf.resolve_automation_policy(
            policy, today=date(2026, 8, 30), **trusted_policy_args(policy)
        )
        self.assertFalse(resolved["authorization_active"])
        self.assertEqual("none", resolved["effective_auto_merge_max_class"])
        self.assertIn("merge", resolved["human_involvement"]["checkpoint_actions"])

    @NEEDS_EXPANDED_POLICY
    def test_automation_policy_rejects_unknown_fields_and_loosening_override(self) -> None:
        policy = fixture("positive/automation-policy-expanded-streamlined.json")
        policy["unexpected"] = True
        policy["task_override_policy"] = "may_loosen"
        findings = aidf.validate_automation_policy(policy, today=date(2026, 8, 30))
        self.assertTrue(any("unknown field" in item.message for item in findings))
        self.assertTrue(any("tighten_only" in item.message for item in findings))

    def test_automation_policy_custom_action_sets_are_closed(self) -> None:
        policy = fixture("positive/automation-policy-custom.json")
        policy["human_involvement"]["checkpoint_actions"] = ["merge", "merge"]
        policy["human_involvement"]["notification_actions"] = ["run_arbitrary_code"]
        findings = aidf.validate_automation_policy(policy, today=date(2026, 8, 30))
        self.assertTrue(any("duplicates" in item.message for item in findings))
        self.assertTrue(any("unknown action" in item.message for item in findings))

    def test_automation_policy_malformed_nested_values_fail_safe(self) -> None:
        policy = fixture("positive/automation-policy-custom.json")
        policy["human_involvement"]["checkpoint_actions"] = [{}]
        policy["authorization"]["recorded_roles"] = [{}, "Architect"]
        resolved = aidf.resolve_automation_policy(
            policy, today=date(2026, 8, 30), **trusted_policy_args(policy)
        )
        self.assertFalse(resolved["authorization_active"])
        self.assertEqual("none", resolved["effective_auto_merge_max_class"])

    @NEEDS_EXPANDED_POLICY
    def test_automation_policy_requires_project_and_digest_binding(self) -> None:
        policy = fixture("positive/automation-policy-expanded-streamlined.json")
        digest = aidf.automation_policy_sha256(policy)
        wrong_project = aidf.resolve_automation_policy(
            policy,
            expected_project_id="ProjectGenome/another-project",
            expected_policy_sha256=digest,
            today=date(2026, 8, 30),
        )
        wrong_digest = aidf.resolve_automation_policy(
            policy,
            expected_project_id=policy["project_id"],
            expected_policy_sha256="0" * 64,
            today=date(2026, 8, 30),
        )
        self.assertFalse(wrong_project["authorization_active"])
        self.assertFalse(wrong_digest["authorization_active"])

    @NEEDS_EXPANDED_POLICY
    def test_automation_task_override_tightens_every_axis(self) -> None:
        policy = fixture("positive/automation-policy-expanded-streamlined.json")
        override = {
            "max_autonomous_class": "T1",
            "remediation_scope": "declared_scope",
            "max_ci_retries": 1,
            "checkpoint_actions": ["merge"],
            "notification_actions": ["merge_request_create", "remediation_apply", "merge", "ci_retry"],
            "auto_merge_max_class": "T1",
        }
        resolved = aidf.resolve_automation_policy(
            policy,
            task_override=override,
            today=date(2026, 8, 30),
            **trusted_policy_args(policy),
        )
        self.assertTrue(resolved["authorization_active"])
        self.assertTrue(resolved["task_override_applied"])
        self.assertEqual("T1", resolved["risk_threshold"]["max_autonomous_class"])
        self.assertEqual("T1", resolved["effective_auto_merge_max_class"])
        self.assertIn("merge", resolved["human_involvement"]["checkpoint_actions"])

    def test_automation_task_override_cannot_loosen_project_policy(self) -> None:
        policy = fixture("positive/automation-policy-custom.json")
        resolved = aidf.resolve_automation_policy(
            policy,
            task_override={"max_autonomous_class": "T2", "max_ci_retries": 3},
            today=date(2026, 8, 30),
            **trusted_policy_args(policy),
        )
        self.assertFalse(resolved["authorization_active"])
        self.assertEqual("none", resolved["effective_auto_merge_max_class"])

    @NEEDS_EXPANDED_POLICY
    def test_automation_task_override_unhashable_enums_fail_safe(self) -> None:
        policy = fixture("positive/automation-policy-expanded-streamlined.json")
        malformed_values = {
            "max_autonomous_class": {},
            "remediation_scope": [],
            "auto_merge_max_class": {},
        }
        for field, value in malformed_values.items():
            with self.subTest(field=field):
                resolved = aidf.resolve_automation_policy(
                    policy,
                    task_override={field: value},
                    today=date(2026, 8, 30),
                    **trusted_policy_args(policy),
                )
                self.assertFalse(resolved["authorization_active"])
                self.assertEqual("none", resolved["effective_auto_merge_max_class"])

    @NEEDS_EXPANDED_POLICY
    def test_automation_task_override_null_on_every_axis_fails_safe(self) -> None:
        policy = fixture("positive/automation-policy-expanded-streamlined.json")
        for field in aidf.AUTOMATION_OVERRIDE_FIELDS:
            with self.subTest(field=field):
                resolved = aidf.resolve_automation_policy(
                    policy,
                    task_override={field: None},
                    today=date(2026, 8, 30),
                    **trusted_policy_args(policy),
                )
                self.assertFalse(resolved["authorization_active"])
                self.assertEqual("none", resolved["effective_auto_merge_max_class"])

    @NEEDS_EXPANDED_POLICY
    def test_automation_policy_cli_accepts_strict_base64(self) -> None:
        policy = fixture("positive/automation-policy-expanded-streamlined.json")
        encoded = base64.b64encode(json.dumps(policy).encode("utf-8")).decode("ascii")
        digest = aidf.automation_policy_sha256(policy)
        output = io.StringIO()
        with redirect_stdout(output):
            result = aidf.main([
                "automation-policy",
                "--root", str(ROOT),
                "--automation-policy-b64", encoded,
                "--expected-project-id", policy["project_id"],
                "--expected-policy-sha256", digest,
            ])
        self.assertEqual(0, result, output.getvalue())

    def test_automation_policy_cli_requires_policy(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            result = aidf.main(["automation-policy", "--root", str(ROOT)])
        self.assertEqual(1, result)
        self.assertIn("--automation-policy is required", output.getvalue())

    def test_tripwire_content_excludes_governance_prose(self) -> None:
        patch = git_patch("core/example.md", added=["truly irreversible"])
        self.assertEqual(set(), aidf.detect_tripwires(["core/example.md"], patch, self.policy))

    def test_tripwire_detects_common_login_filename(self) -> None:
        self.assertIn(
            "authentication-authorization-session-permissions",
            aidf.detect_tripwires(["src/login.py"], git_patch("src/login.py", added=["def login(): pass"]), self.policy),
        )

    def test_dependency_gate_accepts_approved_change(self) -> None:
        patch = git_patch("requirements.txt", added=["fixture-package==1.0.0"])
        self.assertEqual([], aidf.check_dependencies(["requirements.txt"], patch, self.policy, self.contract))

    def test_dependency_gate_rejects_unapproved_change(self) -> None:
        contract = fixture("negative/contract-unapproved-dependency.json")
        patch = git_patch("requirements.txt", added=["fixture-package==1.0.0"])
        findings = aidf.check_dependencies(["requirements.txt"], patch, self.policy, contract)
        self.assertTrue(any("lacks an exact pinned approval" in item.message for item in findings))

    def test_dependency_gate_detects_ci_image_reference(self) -> None:
        contract = fixture("negative/contract-unapproved-dependency.json")
        patch = git_patch(".gitlab-ci.yml", added=["image: python:3.12"])
        findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract)
        self.assertTrue(any(".gitlab-ci.yml" in item.message for item in findings))

    def test_dependency_gate_binds_exact_ci_image(self) -> None:
        contract = json.loads((ROOT / "verification" / "phase2-task-contract.json").read_text(encoding="utf-8"))
        approved = contract["dependency_changes"][0]["dependency"]
        patch = git_patch(".gitlab-ci.yml", added=[f"image: {approved}"])
        self.assertEqual([], aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract))
        changed_patch = patch.replace(approved, "python:3.12.13-slim-bookworm@sha256:" + "0" * 64)
        findings = aidf.check_dependencies([".gitlab-ci.yml"], changed_patch, self.policy, contract)
        self.assertTrue(any("lacks an exact pinned approval" in item.message for item in findings))

    def test_dependency_gate_extracts_nested_ci_image_name(self) -> None:
        contract = json.loads((ROOT / "verification" / "phase2-task-contract.json").read_text(encoding="utf-8"))
        approved = contract["dependency_changes"][1]["dependency"]
        patch = git_patch(".gitlab-ci.yml", added=["  image:", f"    name: {approved}", "    entrypoint: [\"\"]"])
        self.assertEqual([], aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract))

    def test_dependency_gate_binds_exact_git_image(self) -> None:
        contract = json.loads((ROOT / "verification" / "phase2-task-contract.json").read_text(encoding="utf-8"))
        approved = next(
            item["dependency"]
            for item in contract["dependency_changes"]
            if item["dependency"].startswith("alpine/git:")
        )
        patch = git_patch(".gitlab-ci.yml", added=["  image:", f"    name: {approved}", "    entrypoint: [\"\"]"])
        self.assertEqual([], aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract))
        changed_patch = patch.replace(approved, "alpine/git:v2.54.0@sha256:" + "0" * 64)
        findings = aidf.check_dependencies([".gitlab-ci.yml"], changed_patch, self.policy, contract)
        self.assertTrue(any("lacks an exact pinned approval" in item.message for item in findings))

    def test_dependency_gate_binds_exact_trivy_database(self) -> None:
        contract = json.loads((ROOT / "verification" / "phase2-task-contract.json").read_text(encoding="utf-8"))
        approved = next(
            item["dependency"]
            for item in contract["dependency_changes"]
            if item["dependency"].startswith("ghcr.io/aquasecurity/trivy-db@")
        )
        patch = git_patch(".gitlab-ci.yml", added=[f'TRIVY_DB_REPOSITORY: "{approved}"'])
        self.assertEqual([], aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract))
        changed_patch = patch.replace(approved, "ghcr.io/aquasecurity/trivy-db@sha256:" + "0" * 64)
        findings = aidf.check_dependencies([".gitlab-ci.yml"], changed_patch, self.policy, contract)
        self.assertTrue(any("lacks an exact pinned approval" in item.message for item in findings))

    def test_dependency_gate_normalizes_quoted_yaml_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / ".gitlab-ci.yml"
            manifest.write_text(
                'job:\n  "image": "python:latest"\n'
                'variables:\n  "TRIVY_DB_REPOSITORY": "ghcr.io/aquasecurity/trivy-db:2"\n'
                'include:\n  - "project": "trusted/policy"\n    "ref": "main"\n    "file": "policy.yml"\n',
                encoding="utf-8",
            )
            contract = deepcopy(self.contract)
            contract["dependency_changes"].append({
                "path": ".gitlab-ci.yml",
                "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                "pinned": True,
            })
            patch = git_patch(
                ".gitlab-ci.yml",
                added=[
                    '  "image": "python:latest"',
                    '  "TRIVY_DB_REPOSITORY": "ghcr.io/aquasecurity/trivy-db:2"',
                    '  - "project": "trusted/policy"',
                    '    "ref": "main"',
                ],
            )
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
        messages = "\n".join(item.message for item in findings)
        self.assertIn("python:latest", messages)
        self.assertIn("ghcr.io/aquasecurity/trivy-db:2", messages)
        self.assertIn("gitlab-project:trusted/policy@main", messages)

    def test_dependency_gate_rejects_quoted_nested_mutable_image(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".gitlab-ci.yml").write_text(
                'job:\n  "image":\n    "name": "python:latest"\n',
                encoding="utf-8",
            )
            contract = deepcopy(self.contract)
            contract["dependency_changes"].append({
                "path": ".gitlab-ci.yml",
                "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                "pinned": True,
            })
            patch = git_patch(
                ".gitlab-ci.yml",
                added=['  "image":', '    "name": "python:latest"'],
            )
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
        self.assertTrue(any("python:latest" in item.message for item in findings))

    def test_dependency_gate_rejects_escaped_quoted_critical_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            escaped_image_key = '"\\u0069mage"'
            (root / ".gitlab-ci.yml").write_text(
                f"job:\n  {escaped_image_key}: \"python:latest\"\n",
                encoding="utf-8",
            )
            contract = deepcopy(self.contract)
            contract["dependency_changes"].append({
                "path": ".gitlab-ci.yml",
                "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                "pinned": True,
            })
            patch = git_patch(
                ".gitlab-ci.yml",
                added=[f'  {escaped_image_key}: "python:latest"'],
            )
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
        self.assertTrue(any("python:latest" in item.message for item in findings))

    def test_dependency_gate_decodes_escaped_quoted_mutable_value(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            escaped_image_value = '"python\\u003alatest"'
            (root / ".gitlab-ci.yml").write_text(
                f"job:\n  image: {escaped_image_value}\n",
                encoding="utf-8",
            )
            contract = deepcopy(self.contract)
            contract["dependency_changes"].append({
                "path": ".gitlab-ci.yml",
                "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                "pinned": True,
            })
            patch = git_patch(
                ".gitlab-ci.yml",
                added=[f"  image: {escaped_image_value}"],
            )
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
        self.assertTrue(any("python:latest" in item.message for item in findings))

    def test_dependency_gate_rejects_quoted_remote_and_component_includes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / ".gitlab-ci.yml"
            manifest.write_text(
                'include:\n'
                '  - "remote": "https://example.invalid/policy/latest.yml"\n'
                '  - "component": "gitlab.example/group/project/component@main"\n',
                encoding="utf-8",
            )
            contract = deepcopy(self.contract)
            contract["dependency_changes"].append({
                "path": ".gitlab-ci.yml",
                "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                "pinned": True,
            })
            patch = git_patch(
                ".gitlab-ci.yml",
                added=[
                    '  - "remote": "https://example.invalid/policy/latest.yml"',
                    '  - "component": "gitlab.example/group/project/component@main"',
                ],
            )
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
        messages = "\n".join(item.message for item in findings)
        self.assertIn("remote:https://example.invalid/policy/latest.yml", messages)
        self.assertIn("component:gitlab.example/group/project/component@main", messages)

    def test_dependency_gate_rejects_explicit_mapping_dependency_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / ".gitlab-ci.yml"
            lines = [
                "job:",
                "  ? image",
                "  : python:latest",
                "variables:",
                "  ? 'TRIVY_DB_REPOSITORY'",
                "  : ghcr.io/aquasecurity/trivy-db:2",
                "include:",
                "  - ? 'project'",
                "    : trusted/policy",
                "    ? ref",
                "    : main",
                "    ? file",
                "    : policy.yml",
                "  - ? remote",
                "    : https://example.invalid/policy/latest.yml",
                "  - ? component",
                "    : gitlab.example/group/project/component@main",
            ]
            manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
            contract = deepcopy(self.contract)
            contract["dependency_changes"].append({
                "path": ".gitlab-ci.yml",
                "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                "pinned": True,
            })
            patch = git_patch(".gitlab-ci.yml", added=lines)
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
        messages = "\n".join(item.message for item in findings)
        self.assertIn("python:latest", messages)
        self.assertIn("ghcr.io/aquasecurity/trivy-db:2", messages)
        self.assertIn("gitlab-project:trusted/policy@main", messages)
        self.assertIn("remote:https://example.invalid/policy/latest.yml", messages)
        self.assertIn("component:gitlab.example/group/project/component@main", messages)

    def test_dependency_gate_fails_closed_on_unsupported_explicit_mapping_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lines = ["job:", "  ? !!str image", "  : python:latest"]
            (root / ".gitlab-ci.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")
            contract = deepcopy(self.contract)
            contract["dependency_changes"].append({
                "path": ".gitlab-ci.yml",
                "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                "pinned": True,
            })
            patch = git_patch(".gitlab-ci.yml", added=lines)
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
        self.assertTrue(any("unresolved-yaml-key-syntax" in item.message for item in findings))

    def test_dependency_gate_fails_closed_on_tagged_or_aliased_mapping_keys(self) -> None:
        for key_line in ("  !!str image: python:latest", "  &key image: python:latest", "  *key: python:latest"):
            with self.subTest(key_line=key_line), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                lines = ["job:", key_line]
                (root / ".gitlab-ci.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")
                contract = deepcopy(self.contract)
                contract["dependency_changes"].append({
                    "path": ".gitlab-ci.yml",
                    "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                    "pinned": True,
                })
                patch = git_patch(".gitlab-ci.yml", added=lines)
                findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
            self.assertTrue(any("unresolved-yaml-key-syntax" in item.message for item in findings))

    def test_all_checks_accept_precomputed_diff_artifacts(self) -> None:
        with redirect_stdout(io.StringIO()):
            result = aidf.main([
                "all",
                "--root", str(ROOT),
                "--contract", "verification/fixtures/positive/contract-t2.json",
                "--evidence", "verification/fixtures/positive/evidence-t2.json",
                "--policy", "verification/policy.json",
                "--changed-files", "verification/fixtures/positive/changed-files.txt",
                "--diff-file", "verification/fixtures/positive/clean.patch",
            ])
        self.assertEqual(0, result)

    def test_all_checks_accept_integrity_supplied_policy_data(self) -> None:
        encoded_policy = base64.b64encode(json.dumps(self.policy, separators=(",", ":")).encode("utf-8")).decode("ascii")
        with redirect_stdout(io.StringIO()):
            result = aidf.main([
                "all",
                "--root", str(ROOT),
                "--contract", "verification/fixtures/positive/contract-t2.json",
                "--evidence", "verification/fixtures/positive/evidence-t2.json",
                "--policy-b64", encoded_policy,
                "--changed-files", "verification/fixtures/positive/changed-files.txt",
                "--diff-file", "verification/fixtures/positive/clean.patch",
            ])
        self.assertEqual(0, result)

    def test_dependency_gate_rejects_unpinned_requirement_even_if_record_claims_pinned(self) -> None:
        contract = deepcopy(self.contract)
        contract["dependency_changes"][0]["dependency"] = "fixture-package>=1.0.0"
        patch = git_patch("requirements.txt", added=["fixture-package>=1.0.0"])
        findings = aidf.check_dependencies(["requirements.txt"], patch, self.policy, contract)
        self.assertTrue(any("unpinned or unresolved" in item.message for item in findings))

    def test_dependency_gate_rejects_wildcard_requirement(self) -> None:
        contract = deepcopy(self.contract)
        contract["dependency_changes"][0]["dependency"] = "fixture-package==1.*"
        patch = git_patch("requirements.txt", added=["fixture-package==1.*"])
        findings = aidf.check_dependencies(["requirements.txt"], patch, self.policy, contract)
        self.assertTrue(any("unpinned or unresolved" in item.message for item in findings))

    def test_dependency_gate_accepts_hashed_exact_requirement(self) -> None:
        dependency = "tool==1.2.3 --hash=sha256:" + "a" * 64
        contract = deepcopy(self.contract)
        contract["dependency_changes"].append({"path": "requirements-static.txt", "dependency": dependency, "pinned": True})
        patch = git_patch("requirements-static.txt", added=[dependency])
        self.assertEqual([], aidf.check_dependencies(["requirements-static.txt"], patch, self.policy, contract))

    def test_dependency_gate_rejects_malformed_requirement_hash(self) -> None:
        dependency = "tool==1.2.3 --hash=sha256:" + "a" * 63
        contract = deepcopy(self.contract)
        contract["dependency_changes"].append({"path": "requirements-static.txt", "dependency": dependency, "pinned": True})
        patch = git_patch("requirements-static.txt", added=[dependency])
        findings = aidf.check_dependencies(["requirements-static.txt"], patch, self.policy, contract)
        self.assertTrue(any("unpinned or unresolved" in item.message for item in findings))

    def test_dependency_content_lock_rejects_unapproved_ci_include(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".gitlab-ci.yml").write_text(
                "include:\n  - project: unapproved/example\n    ref: deadbeef\n    file: policy.yml\n",
                encoding="utf-8",
            )
            patch = git_patch(".gitlab-ci.yml", added=["include:", "  - project: unapproved/example", "    ref: deadbeef", "    file: policy.yml"])
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, self.contract, root=root)
        self.assertTrue(any("content-sha256" in item.message and "lacks an exact pinned approval" in item.message for item in findings))

    def test_dependency_gate_rejects_mutable_remote_include_even_with_manifest_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / ".gitlab-ci.yml"
            manifest.write_text(
                "include:\n  - remote: https://example.invalid/policy/latest.yml\n",
                encoding="utf-8",
            )
            content_lock = aidf._content_dependency(root, ".gitlab-ci.yml")
            contract = deepcopy(self.contract)
            contract["dependency_changes"].append({
                "path": ".gitlab-ci.yml",
                "dependency": content_lock,
                "pinned": True,
            })
            patch = git_patch(
                ".gitlab-ci.yml",
                added=["include:", "  - remote: https://example.invalid/policy/latest.yml"],
            )
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
        self.assertTrue(any("remote:" in item.message and "unpinned or unresolved" in item.message for item in findings))

    def test_dependency_gate_rejects_inline_mutable_remote_include(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / ".gitlab-ci.yml"
            manifest.write_text(
                "include: [{ remote: 'https://example.invalid/policy/latest.yml' }]\n",
                encoding="utf-8",
            )
            contract = deepcopy(self.contract)
            contract["dependency_changes"].append({
                "path": ".gitlab-ci.yml",
                "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                "pinned": True,
            })
            patch = git_patch(".gitlab-ci.yml", added=["include: [{ remote: 'https://example.invalid/policy/latest.yml' }]"])
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
        self.assertTrue(any("remote:" in item.message and "unpinned or unresolved" in item.message for item in findings))

    def test_dependency_gate_rejects_remote_include_shorthand_forms(self) -> None:
        cases = (
            "include: https://example.invalid/latest.yml\n",
            "include: 'https://example.invalid/latest.yml'\n",
            "include:\n  - https://example.invalid/latest.yml\n",
            "include: [https://example.invalid/latest.yml]\n",
            "? include\n: https://example.invalid/latest.yml\n",
            '"\\u0069nclude": "https://example.invalid/latest.yml"\n',
        )
        for manifest_text in cases:
            with self.subTest(manifest_text=manifest_text), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / ".gitlab-ci.yml").write_text(manifest_text, encoding="utf-8")
                contract = deepcopy(self.contract)
                contract["dependency_changes"].append({
                    "path": ".gitlab-ci.yml",
                    "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                    "pinned": True,
                })
                patch = git_patch(".gitlab-ci.yml", added=manifest_text.splitlines())
                findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
            self.assertTrue(any("remote:https://example.invalid/latest.yml" in item.message for item in findings))

    def test_dependency_gate_ignores_include_text_in_comments_and_scripts(self) -> None:
        manifest_text = (
            "# include: https://example.invalid/not-executable.yml\n"
            "job:\n"
            "  script:\n"
            "    - echo include:hello\n"
            "    - echo remote:https://example.invalid/not-executable.yml\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".gitlab-ci.yml").write_text(manifest_text, encoding="utf-8")
            contract = deepcopy(self.contract)
            contract["dependency_changes"].append({
                "path": ".gitlab-ci.yml",
                "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                "pinned": True,
            })
            patch = git_patch(".gitlab-ci.yml", added=manifest_text.splitlines())
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
        self.assertEqual([], findings)

    def test_dependency_gate_does_not_bind_project_ref_from_inline_comment(self) -> None:
        manifest_text = (
            "include:\n"
            "  - project: group/templates # ref: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
            "    file: /ci.yml\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".gitlab-ci.yml").write_text(manifest_text, encoding="utf-8")
            contract = deepcopy(self.contract)
            contract["dependency_changes"].extend((
                {
                    "path": ".gitlab-ci.yml",
                    "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                    "pinned": True,
                },
                {
                    "path": ".gitlab-ci.yml",
                    "dependency": "gitlab-project:group/templates@" + "a" * 40,
                    "pinned": True,
                },
            ))
            patch = git_patch(".gitlab-ci.yml", added=manifest_text.splitlines())
            findings = aidf.check_dependencies(
                [".gitlab-ci.yml"], patch, self.policy, contract, root=root,
            )
        messages = "\n".join(item.message for item in findings)
        self.assertIn("gitlab-project:group/templates@unresolved-ref", messages)

    def test_dependency_gate_detects_root_flow_include_after_other_keys(self) -> None:
        manifest_text = (
            "{stages: [test], include: https://example.invalid/latest.yml}\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".gitlab-ci.yml").write_text(manifest_text, encoding="utf-8")
            contract = deepcopy(self.contract)
            contract["dependency_changes"].append({
                "path": ".gitlab-ci.yml",
                "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                "pinned": True,
            })
            patch = git_patch(".gitlab-ci.yml", added=manifest_text.splitlines())
            findings = aidf.check_dependencies(
                [".gitlab-ci.yml"], patch, self.policy, contract, root=root,
            )
        self.assertTrue(any("remote:https://example.invalid/latest.yml" in item.message for item in findings))

    def test_dependency_gate_ignores_dependency_text_in_non_yaml_payloads(self) -> None:
        cases = (
            (
                "# image: python:latest\n"
                "# TRIVY_DB_REPOSITORY: ghcr.io/aquasecurity/trivy-db:2\n"
                "job:\n"
                "  script:\n"
                "    - echo image: python:latest\n"
                "    - echo TRIVY_DB_REPOSITORY: ghcr.io/aquasecurity/trivy-db:2\n"
                '    - "echo image: python:latest"\n'
            ),
            (
                "job:\n"
                "  script: |\n"
                "    image: python:latest\n"
                "    TRIVY_DB_REPOSITORY: ghcr.io/aquasecurity/trivy-db:2\n"
            ),
            (
                "job:\n"
                "  script: >-\n"
                "    echo image: python:latest\n"
                "    echo TRIVY_DB_REPOSITORY: ghcr.io/aquasecurity/trivy-db:2\n"
                "  after_script:\n"
                "    - echo complete\n"
            ),
            'job: { script: "echo image: python:latest" }\n',
            (
                "job:\n"
                "  script:\n"
                "    - echo foo{image:python:latest}\n"
                "    - cmd --format={image:python:latest}\n"
                "    - cmd:{image:python:latest}\n"
                '    - tool:{"image":"python:latest"}\n'
                "    - echo {image:python:latest}\n"
                '    - echo \'{"image":"python:latest"}\'\n'
                "    - echo [{image:python:latest}]\n"
                '    - echo [{"image":"python:latest"}]\n'
                "    - echo ${payload:-{image:python:latest}}\n"
            ),
        )
        for manifest_text in cases:
            with self.subTest(manifest_text=manifest_text), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / ".gitlab-ci.yml").write_text(manifest_text, encoding="utf-8")
                contract = deepcopy(self.contract)
                contract["dependency_changes"].append({
                    "path": ".gitlab-ci.yml",
                    "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                    "pinned": True,
                })
                patch = git_patch(".gitlab-ci.yml", added=manifest_text.splitlines())
                findings = aidf.check_dependencies(
                    [".gitlab-ci.yml"], patch, self.policy, contract, root=root,
                )
            self.assertEqual([], findings, manifest_text)

    def test_dependency_gate_detects_dependencies_in_flow_mappings(self) -> None:
        manifest_text = (
            "job: { image: python:latest }\n"
            "variables: { TRIVY_DB_REPOSITORY: ghcr.io/aquasecurity/trivy-db:2 }\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".gitlab-ci.yml").write_text(manifest_text, encoding="utf-8")
            contract = deepcopy(self.contract)
            contract["dependency_changes"].append({
                "path": ".gitlab-ci.yml",
                "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                "pinned": True,
            })
            patch = git_patch(".gitlab-ci.yml", added=manifest_text.splitlines())
            findings = aidf.check_dependencies(
                [".gitlab-ci.yml"], patch, self.policy, contract, root=root,
            )
        messages = "\n".join(item.message for item in findings)
        self.assertIn("python:latest", messages)
        self.assertIn("ghcr.io/aquasecurity/trivy-db:2", messages)

    def test_dependency_gate_ignores_payload_text_in_local_include(self) -> None:
        included_text = (
            "# image: python:latest\n"
            "job:\n"
            "  script: |\n"
            "    echo image: python:latest\n"
            "    echo TRIVY_DB_REPOSITORY: ghcr.io/aquasecurity/trivy-db:2\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "ci").mkdir()
            (root / ".gitlab-ci.yml").write_text(
                "include:\n  - local: ci/jobs.yml\n", encoding="utf-8",
            )
            (root / "ci" / "jobs.yml").write_text(included_text, encoding="utf-8")
            contract = deepcopy(self.contract)
            for path in (".gitlab-ci.yml", "ci/jobs.yml"):
                contract["dependency_changes"].append({
                    "path": path,
                    "dependency": aidf._content_dependency(root, path),
                    "pinned": True,
                })
            patch = git_patch(
                ".gitlab-ci.yml", added=["include:", "  - local: ci/jobs.yml"],
            )
            findings = aidf.check_dependencies(
                [".gitlab-ci.yml"], patch, self.policy, contract, root=root,
            )
        self.assertEqual([], findings)

    def test_dependency_gate_rejects_mutable_template_includes(self) -> None:
        cases = (
            "include:\n  - template: Jobs/SAST.gitlab-ci.yml\n",
            'include:\n  - "template": "Jobs/SAST.gitlab-ci.yml"\n',
            "? include\n: [{template: Jobs/SAST.gitlab-ci.yml}]\n",
        )
        for manifest_text in cases:
            with self.subTest(manifest_text=manifest_text), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / ".gitlab-ci.yml").write_text(manifest_text, encoding="utf-8")
                contract = deepcopy(self.contract)
                contract["dependency_changes"].append({
                    "path": ".gitlab-ci.yml",
                    "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                    "pinned": True,
                })
                patch = git_patch(".gitlab-ci.yml", added=manifest_text.splitlines())
                findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
            self.assertTrue(any("template:Jobs/SAST.gitlab-ci.yml" in item.message or "unresolved-include" in item.message for item in findings))

    def test_dependency_gate_rejects_mutable_image_in_local_include(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "ci").mkdir()
            (root / ".gitlab-ci.yml").write_text("include:\n  - local: ci/jobs.yml\n", encoding="utf-8")
            (root / "ci" / "jobs.yml").write_text("job:\n  image: python:latest\n", encoding="utf-8")
            contract = deepcopy(self.contract)
            contract["dependency_changes"].append({
                "path": ".gitlab-ci.yml",
                "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                "pinned": True,
            })
            patch = git_patch(".gitlab-ci.yml", added=["include:", "  - local: ci/jobs.yml"])
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
        messages = "\n".join(item.message for item in findings)
        self.assertIn("ci/jobs.yml", messages)
        self.assertIn("python:latest", messages)

    def test_dependency_gate_rejects_external_include_nested_in_local_include(self) -> None:
        cases = (
            "include: https://example.invalid/latest.yml\n",
            "include:\n  - template: Jobs/SAST.gitlab-ci.yml\n",
        )
        for included_text in cases:
            with self.subTest(included_text=included_text), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / "ci").mkdir()
                (root / ".gitlab-ci.yml").write_text("include: ci/jobs.yml\n", encoding="utf-8")
                (root / "ci" / "jobs.yml").write_text(included_text, encoding="utf-8")
                contract = deepcopy(self.contract)
                contract["dependency_changes"].extend([
                    {
                        "path": ".gitlab-ci.yml",
                        "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                        "pinned": True,
                    },
                    {
                        "path": "ci/jobs.yml",
                        "dependency": aidf._content_dependency(root, "ci/jobs.yml"),
                        "pinned": True,
                    },
                ])
                patch = git_patch(".gitlab-ci.yml", added=["include: ci/jobs.yml"])
                findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
            self.assertTrue(any(
                "remote:https://example.invalid/latest.yml" in item.message
                or "template:Jobs/SAST.gitlab-ci.yml" in item.message
                for item in findings
            ))

    def test_dependency_gate_rejects_missing_local_include(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".gitlab-ci.yml").write_text("include: ci/missing.yml\n", encoding="utf-8")
            patch = git_patch(".gitlab-ci.yml", added=["include: ci/missing.yml"])
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, self.contract, root=root)
        messages = "\n".join(item.message for item in findings)
        self.assertIn("ci/missing.yml", messages)
        self.assertIn("manifest-removal", messages)

    def test_dependency_gate_scans_changed_local_include_when_root_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "ci").mkdir()
            (root / ".gitlab-ci.yml").write_text("include: ci/jobs.yml\n", encoding="utf-8")
            (root / "ci" / "jobs.yml").write_text("job:\n  image: python:latest\n", encoding="utf-8")
            patch = git_patch("ci/jobs.yml", added=["job:", "  image: python:latest"])
            findings = aidf.check_dependencies(["ci/jobs.yml"], patch, self.policy, self.contract, root=root)
        self.assertTrue(any("ci/jobs.yml" in item.message and "python:latest" in item.message for item in findings))

    def test_dependency_gate_accepts_exact_local_include_inventory(self) -> None:
        image = "python:3.12@sha256:" + "a" * 64
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "ci").mkdir()
            (root / ".gitlab-ci.yml").write_text("include: [ci/jobs.yml]\n", encoding="utf-8")
            (root / "ci" / "jobs.yml").write_text(f"job:\n  image: {image}\n", encoding="utf-8")
            contract = deepcopy(self.contract)
            contract["dependency_changes"].extend([
                {"path": ".gitlab-ci.yml", "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"), "pinned": True},
                {"path": "ci/jobs.yml", "dependency": aidf._content_dependency(root, "ci/jobs.yml"), "pinned": True},
                {"path": "ci/jobs.yml", "dependency": image, "pinned": True},
            ])
            patch = git_patch(".gitlab-ci.yml", added=["include: [ci/jobs.yml]"])
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
        self.assertEqual([], findings)

    def test_dependency_gate_accepts_local_include_with_nested_rules(self) -> None:
        image = "python:3.12@sha256:" + "b" * 64
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "ci").mkdir()
            (root / ".gitlab-ci.yml").write_text(
                "include:\n"
                "  - local: ci/jobs.yml\n"
                "    rules:\n"
                "      - if: '$CI_PIPELINE_SOURCE == \"merge_request_event\"'\n",
                encoding="utf-8",
            )
            (root / "ci" / "jobs.yml").write_text(f"job:\n  image: {image}\n", encoding="utf-8")
            contract = deepcopy(self.contract)
            contract["dependency_changes"].extend([
                {"path": ".gitlab-ci.yml", "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"), "pinned": True},
                {"path": "ci/jobs.yml", "dependency": aidf._content_dependency(root, "ci/jobs.yml"), "pinned": True},
                {"path": "ci/jobs.yml", "dependency": image, "pinned": True},
            ])
            patch = git_patch(".gitlab-ci.yml", added=(root / ".gitlab-ci.yml").read_text(encoding="utf-8").splitlines())
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
        self.assertEqual([], findings)

    def test_dependency_gate_rejects_local_include_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "ci").mkdir()
            (root / ".gitlab-ci.yml").write_text("include:\n  - local: ci/jobs.yml\n", encoding="utf-8")
            (root / "ci" / "jobs.yml").write_text("include:\n  - local: .gitlab-ci.yml\n", encoding="utf-8")
            patch = git_patch(".gitlab-ci.yml", added=["include:", "  - local: ci/jobs.yml"])
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, self.contract, root=root)
        self.assertTrue(any("unresolved-local-include-cycle" in item.message for item in findings))

    def test_dependency_gate_rejects_dynamic_or_globbed_local_include(self) -> None:
        for local in ("$CI_CONFIG_PATH", "ci/**/*.yml", "../outside.yml"):
            with self.subTest(local=local), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / ".gitlab-ci.yml").write_text(f"include:\n  - local: {local}\n", encoding="utf-8")
                patch = git_patch(".gitlab-ci.yml", added=["include:", f"  - local: {local}"])
                findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, self.contract, root=root)
            self.assertTrue(any("unresolved-local-include" in item.message for item in findings))

    def test_dependency_gate_rejects_symlinked_local_include(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "ci").mkdir()
            target = root / "ci" / "real.yml"
            target.write_text("job:\n  image: python:latest\n", encoding="utf-8")
            link = root / "ci" / "jobs.yml"
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            (root / ".gitlab-ci.yml").write_text("include: ci/jobs.yml\n", encoding="utf-8")
            patch = git_patch(".gitlab-ci.yml", added=["include: ci/jobs.yml"])
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, self.contract, root=root)
        self.assertTrue(any("unresolved-local-include-symlink" in item.message for item in findings))

    def test_dependency_gate_fails_closed_on_tagged_or_aliased_include_value(self) -> None:
        for include_line in ("include: !!str https://example.invalid/latest.yml", "include: &source ci/jobs.yml", "include: *source"):
            with self.subTest(include_line=include_line), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / ".gitlab-ci.yml").write_text(include_line + "\n", encoding="utf-8")
                patch = git_patch(".gitlab-ci.yml", added=[include_line])
                findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, self.contract, root=root)
            self.assertTrue(any("unresolved-include-scalar" in item.message for item in findings))

    def test_dependency_gate_rejects_mutable_project_ref(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / ".gitlab-ci.yml"
            manifest.write_text(
                "include: [{ project: trusted/policy, ref: main, file: policy.yml }]\n",
                encoding="utf-8",
            )
            dependency = "gitlab-project:trusted/policy@main"
            contract = deepcopy(self.contract)
            contract["dependency_changes"].extend([
                {"path": ".gitlab-ci.yml", "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"), "pinned": True},
                {"path": ".gitlab-ci.yml", "dependency": dependency, "pinned": True},
            ])
            patch = git_patch(".gitlab-ci.yml", added=["include: [{ project: trusted/policy, ref: main, file: policy.yml }]"])
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
        self.assertTrue(any(dependency in item.message and "unpinned or unresolved" in item.message for item in findings))

    def test_dependency_gate_does_not_bind_nested_ref_to_project_source(self) -> None:
        digest = "a" * 40
        cases = (
            (
                "include:\n"
                "  - project: group/templates\n"
                "    file: /ci.yml\n"
                "    inputs:\n"
                f"      ref: {digest}\n"
            ),
            (
                "include:\n"
                "  - project: group/templates\n"
                "    file: /ci.yml\n"
                "    rules:\n"
                "      - exists:\n"
                "          paths: [.gitlab-ci.yml]\n"
                f"          ref: {digest}\n"
            ),
        )
        for manifest_text in cases:
            with self.subTest(manifest_text=manifest_text), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / ".gitlab-ci.yml").write_text(manifest_text, encoding="utf-8")
                contract = deepcopy(self.contract)
                contract["dependency_changes"].extend([
                    {
                        "path": ".gitlab-ci.yml",
                        "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                        "pinned": True,
                    },
                    {
                        "path": ".gitlab-ci.yml",
                        "dependency": f"gitlab-project:group/templates@{digest}",
                        "pinned": True,
                    },
                ])
                patch = git_patch(".gitlab-ci.yml", added=manifest_text.splitlines())
                findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
            self.assertTrue(any(
                "gitlab-project:group/templates@unresolved-ref" in item.message
                for item in findings
            ))

    def test_dependency_gate_accepts_project_ref_sibling_after_nested_inputs(self) -> None:
        digest = "b" * 40
        manifest_text = (
            "include:\n"
            "  - project: group/templates\n"
            "    file: /ci.yml\n"
            "    inputs:\n"
            "      option: enabled\n"
            f"    ref: {digest}\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".gitlab-ci.yml").write_text(manifest_text, encoding="utf-8")
            contract = deepcopy(self.contract)
            contract["dependency_changes"].extend([
                {
                    "path": ".gitlab-ci.yml",
                    "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"),
                    "pinned": True,
                },
                {
                    "path": ".gitlab-ci.yml",
                    "dependency": f"gitlab-project:group/templates@{digest}",
                    "pinned": True,
                },
            ])
            patch = git_patch(".gitlab-ci.yml", added=manifest_text.splitlines())
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
        self.assertEqual([], findings)

    def test_dependency_gate_accepts_commit_pinned_project_include_with_exact_approval(self) -> None:
        commit = "a" * 40
        dependency = f"gitlab-project:trusted/policy@{commit}"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / ".gitlab-ci.yml"
            manifest.write_text(
                f"include:\n  - project: trusted/policy\n    ref: {commit}\n    file: policy.yml\n",
                encoding="utf-8",
            )
            contract = deepcopy(self.contract)
            contract["dependency_changes"].extend([
                {"path": ".gitlab-ci.yml", "dependency": aidf._content_dependency(root, ".gitlab-ci.yml"), "pinned": True},
                {"path": ".gitlab-ci.yml", "dependency": dependency, "pinned": True},
            ])
            patch = git_patch(
                ".gitlab-ci.yml",
                added=["include:", "  - project: trusted/policy", f"    ref: {commit}", "    file: policy.yml"],
            )
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, contract, root=root)
        self.assertEqual([], findings)

    def test_dependency_content_lock_rejects_gitmodules_addition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".gitmodules").write_text(
                "[submodule \"vendor\"]\n\tpath = vendor\n\turl = ssh://example.invalid/vendor.git\n",
                encoding="utf-8",
            )
            patch = git_patch(".gitmodules", added=["[submodule \"vendor\"]", "\tpath = vendor", "\turl = ssh://example.invalid/vendor.git"])
            findings = aidf.check_dependencies([".gitmodules"], patch, self.policy, self.contract, root=root)
        self.assertTrue(any("content-sha256" in item.message for item in findings))

    def test_dependency_gate_rejects_unapproved_gitlink_pointer_update(self) -> None:
        commit = "b" * 40
        patch = git_patch("vendor/dependency", added=[f"Subproject commit {commit}"], removed=["Subproject commit " + "a" * 40])
        findings = aidf.check_dependencies(["vendor/dependency"], patch, self.policy, self.contract)
        self.assertTrue(any(f"git-oid:{commit}" in item.message and "lacks an exact pinned approval" in item.message for item in findings))

    def test_dependency_gate_accepts_approved_gitlink_pointer_update(self) -> None:
        commit = "b" * 40
        dependency = f"git-oid:{commit}"
        contract = deepcopy(self.contract)
        contract["dependency_changes"].append({"path": "vendor/dependency", "dependency": dependency, "pinned": True})
        patch = git_patch("vendor/dependency", added=[f"Subproject commit {commit}"], removed=["Subproject commit " + "a" * 40])
        self.assertEqual([], aidf.check_dependencies(["vendor/dependency"], patch, self.policy, contract))

    def test_dependency_content_lock_rejects_manifest_removal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            patch = git_patch(".gitlab-ci.yml", removed=["image: python:3.12"])
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, self.contract, root=root)
        self.assertTrue(any("manifest-removal" in item.message for item in findings))

    def test_dependency_content_lock_normalizes_text_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / ".gitlab-ci.yml"
            manifest.write_bytes(b"job:\r\n  image: approved\r\n")
            windows_reference = aidf._content_dependency(root, ".gitlab-ci.yml")
            manifest.write_bytes(b"job:\n  image: approved\n")
            linux_reference = aidf._content_dependency(root, ".gitlab-ci.yml")
        self.assertEqual(windows_reference, linux_reference)

    def test_dependency_gate_rejects_manifest_symlink_introduction(self) -> None:
        patch = git_patch("package.json", added=["deps.json"])
        with mock.patch.object(aidf, "_manifest_symlinks", return_value=["package.json"]):
            findings = aidf.check_dependencies(["package.json"], patch, self.policy, self.contract, root=ROOT)
        self.assertTrue(any("regular, non-symlink dependency manifest" in item.message for item in findings))

    def test_dependency_gate_rejects_change_to_existing_manifest_symlink_target(self) -> None:
        patch = git_patch("deps.json", added=['{"dependencies":{"evil":"latest"}}'])
        with mock.patch.object(aidf, "_manifest_symlinks", return_value=["package.json"]):
            findings = aidf.check_dependencies(["deps.json"], patch, self.policy, self.contract, root=ROOT)
        self.assertTrue(any("package.json" in item.message and "non-symlink" in item.message for item in findings))

    def test_manifest_symlink_discovery_matches_configured_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "package.json"
            dependencies = root / "deps.json"
            with (
                mock.patch.object(aidf.os, "walk", return_value=[(str(root), [], [package.name, dependencies.name])]),
                mock.patch.object(Path, "is_symlink", autospec=True, side_effect=lambda path: path.name == package.name),
            ):
                found = aidf._manifest_symlinks(root, self.policy["dependency_manifests"])
        self.assertEqual(["package.json"], found)

    def test_nested_ci_image_replacement_is_detected_from_final_file(self) -> None:
        replacement = "example.invalid/tool:1@sha256:" + "0" * 64
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".gitlab-ci.yml").write_text(f"job:\n  image:\n    name: {replacement}\n", encoding="utf-8")
            patch = git_patch(".gitlab-ci.yml", added=[f"    name: {replacement}"], removed=["    name: approved.invalid/tool:1@sha256:" + "1" * 64])
            findings = aidf.check_dependencies([".gitlab-ci.yml"], patch, self.policy, self.contract, root=root)
        self.assertTrue(any(replacement in item.message for item in findings))

    def test_malformed_policy_fails_closed_before_tripwire_check(self) -> None:
        malformed = deepcopy(self.policy)
        malformed["tripwire_paths"] = [{"id": "infrastructure"}]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "policy.json").write_text(json.dumps(malformed), encoding="utf-8")
            (root / "contract.json").write_text(json.dumps(self.contract), encoding="utf-8")
            (root / "changed.txt").write_text("src/service.py\n", encoding="utf-8")
            (root / "change.patch").write_text("", encoding="utf-8")
            with mock.patch.object(aidf, "check_tripwires") as checker, redirect_stdout(io.StringIO()):
                result = aidf.main([
                    "tripwires",
                    "--root", str(root),
                    "--policy", "policy.json",
                    "--contract", "contract.json",
                    "--changed-files", "changed.txt",
                    "--diff-file", "change.patch",
                ])
            self.assertEqual(1, result)
            checker.assert_not_called()

    def test_changed_file_artifact_accepts_crlf_delimiters(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "changed.txt").write_bytes(b"src/service.py\r\ntests/test_service.py\r\n")
            args = argparse.Namespace(changed_files="changed.txt", changed_files_nul=False, base=None, head=None)
            self.assertEqual(["src/service.py", "tests/test_service.py"], aidf._changed_files(args, root))

    def test_changed_file_artifact_rejects_lone_carriage_return(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "changed.txt").write_bytes(b"src/service.py\rtests/test_service.py\n")
            args = argparse.Namespace(changed_files="changed.txt", changed_files_nul=False, base=None, head=None)
            with self.assertRaisesRegex(ValueError, "lone or embedded carriage return"):
                aidf._changed_files(args, root)

    def test_e7_requires_operation_specific_recovery_evidence(self) -> None:
        reversible = {
            "operation": "reversible",
            "status": "passed",
            "artifact": "executed revert output",
            "operational_behavior": "pipeline duration remained within the declared five-minute timeout",
            "failure_observability": "required pipeline failure blocks merge",
            "kill_switch": "re-pin the custom CI configuration to the prior protected commit",
            "unrecoverable_effects": "none identified",
        }
        self.assertEqual([], aidf._validate_e7(reversible))
        findings = aidf._validate_e7({"operation": "destructive but recoverable", "artifact": "restore output"})
        self.assertTrue(any("representative_dataset" in item.message for item in findings))
        irreversible = {
            "operation": "truly irreversible",
            "status": "passed",
            "artifact": "pre-execution record",
            "operational_behavior": "fixture-only operation",
            "failure_observability": "fixture failure is reported by the checker",
            "kill_switch": "not applicable because execution is irreversible",
            "unrecoverable_effects": "external notification cannot be withdrawn",
            "recovery_point": "backup-1",
            "restore_path": "documented restore runbook",
            "irrecoverable_effects": "external notification cannot be withdrawn",
            "human_acceptance": "Fixture owner accepted before execution",
        }
        self.assertEqual([], aidf._validate_e7(irreversible))

    def test_e7_rejects_recovery_only_attestation(self) -> None:
        findings = aidf._validate_e7({"operation": "reversible", "artifact": "self-asserted"})
        self.assertTrue(any("operational_behavior" in item.message for item in findings))

    def test_e4_rejects_pending_check(self) -> None:
        evidence = fixture("positive/evidence-t2.json")
        evidence["e4"][0]["artifact"] = "pending; no executing check exists yet"
        findings = aidf.validate_evidence(evidence, self.contract)
        self.assertTrue(any("incomplete artifact" in item.message for item in findings))

    def test_secret_scan_accepts_clean_diff(self) -> None:
        self.assertEqual([], aidf.check_secrets(text_fixture("positive/clean.patch")))

    def test_secret_scan_rejects_unmistakably_fake_canary(self) -> None:
        parts = fixture("negative/secret-canary-parts.json")
        canary = parts["prefix"] + parts["kind"] + parts["value"]
        patch = git_patch("src/service.py", added=[f'value = "{canary}"'])
        findings = aidf.check_secrets(patch)
        self.assertTrue(any("test canary" in item.message for item in findings))

    def test_secret_scan_rejects_gitlab_personal_access_token(self) -> None:
        token = "glpat-" + "A1b2C3d4E5f6G7h8I9j0"
        findings = aidf.check_secrets(git_patch("config/example.env", added=[f'GITLAB_TOKEN="{token}"']))
        self.assertTrue(any("GitLab token" in item.message for item in findings))

    def test_secret_scan_rejects_documented_gitlab_token_prefixes(self) -> None:
        prefixes = (
            "glpat", "gloas", "gldt", "glrt", "glrtr", "glcbt", "glptt",
            "glft", "glimt", "glagent", "glwt", "glsoat", "glffct",
        )
        for prefix in prefixes:
            with self.subTest(prefix=prefix):
                token = prefix + "-" + "A1b2C3d4E5f6G7h8I9j0"
                patch = git_patch("config/example.env", added=[f'GITLAB_TOKEN="{token}"'])
                findings = aidf.check_secrets(patch)
                self.assertTrue(any("GitLab token" in item.message for item in findings))

    def test_secret_scan_rejects_gitlab_session_cookie(self) -> None:
        cookie = "_gitlab_" + "session=" + "A1b2C3d4E5f6G7h8I9j0"
        findings = aidf.check_secrets(git_patch("config/example.env", added=[f'COOKIE="{cookie}"']))
        self.assertTrue(any("GitLab session cookie" in item.message for item in findings))

    def test_secret_scan_rejects_pem_certificate(self) -> None:
        marker = "-----BEGIN " + "CERTIFICATE-----"
        findings = aidf.check_secrets(git_patch("certs/example.pem", added=[marker]))
        self.assertTrue(any("PEM certificate block" in item.message for item in findings))

    def test_secret_scan_rejects_trusted_pem_certificate(self) -> None:
        marker = "-----BEGIN " + "TRUSTED CERTIFICATE-----"
        findings = aidf.check_secrets(git_patch("certs/example.pem", added=[marker]))
        self.assertTrue(any("PEM certificate block" in item.message for item in findings))

    def test_secret_scan_rejects_x509_pem_certificate(self) -> None:
        marker = "-----BEGIN " + "X509 CERTIFICATE-----"
        findings = aidf.check_secrets(git_patch("certs/example.pem", added=[marker]))
        self.assertTrue(any("PEM certificate block" in item.message for item in findings))

    def test_secret_scan_rejects_encrypted_pkcs8_private_key(self) -> None:
        marker = "-----BEGIN " + "ENCRYPTED PRIVATE KEY-----"
        findings = aidf.check_secrets(git_patch("keys/example.pem", added=[marker]))
        self.assertTrue(any("private key block" in item.message for item in findings))

    def test_diff_header_spoof_does_not_hide_following_secret(self) -> None:
        parts = fixture("negative/secret-canary-parts.json")
        canary = parts["prefix"] + parts["kind"] + parts["value"]
        patch = git_patch("src/service.py", added=["++ b/verification/spoofed.md", f'value = "{canary}"'])
        findings = aidf.check_secrets(patch)
        self.assertTrue(any("src/service.py" in item.message for item in findings))

    def test_diff_consistency_rejects_name_patch_disagreement(self) -> None:
        findings = aidf.check_diff_consistency(["src/other.py"], git_patch("src/service.py", added=["VALUE = 1"]))
        self.assertTrue(any("disagree" in item.message for item in findings))

    def test_diff_parser_rejects_file_header_path_spoof(self) -> None:
        patch = git_patch("src/service.py", added=["breaking api change"])
        forged = patch.replace("+++ b/src/service.py", "+++ b/verification/spoof.md")
        with self.assertRaisesRegex(ValueError, "new file header.*disagrees with diff --git path"):
            aidf.check_diff_consistency(["src/service.py"], forged)

    def test_diff_parser_rejects_cross_path_section_spoof(self) -> None:
        forged = (
            "diff --git a/src/service.py b/verification/spoof.md\n"
            "--- a/src/service.py\n"
            "+++ b/verification/spoof.md\n"
            "@@ -1,0 +1 @@\n"
            "+breaking api change\n"
        )
        with self.assertRaisesRegex(ValueError, "cross-path diff sections are not permitted"):
            aidf.check_diff_consistency(["src/service.py", "verification/spoof.md"], forged)

    def test_diff_parser_rejects_unmarked_dev_null_header(self) -> None:
        patch = git_patch("src/service.py", added=["breaking api change"])
        forged = patch.replace("--- a/src/service.py", "--- /dev/null")
        with self.assertRaisesRegex(ValueError, "/dev/null old file header requires new file mode"):
            aidf.check_diff_consistency(["src/service.py"], forged)

    def test_diff_parser_rejects_new_mode_with_regular_old_header(self) -> None:
        forged = git_patch("src/service.py", added=["VALUE = 1"]).replace(
            "--- ", "new file mode 100644\n--- ", 1
        )
        with self.assertRaisesRegex(ValueError, "new file mode requires /dev/null old file header"):
            aidf.check_diff_consistency(["src/service.py"], forged)

    def test_diff_parser_rejects_deleted_mode_with_regular_new_header(self) -> None:
        forged = git_patch("src/service.py", removed=["VALUE = 1"]).replace(
            "--- ", "deleted file mode 100644\n--- ", 1
        )
        with self.assertRaisesRegex(ValueError, "deleted file mode requires /dev/null new file header"):
            aidf.check_diff_consistency(["src/service.py"], forged)

    def test_diff_parser_accepts_legitimate_new_file(self) -> None:
        patch = (
            "diff --git a/src/new.py b/src/new.py\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            "+++ b/src/new.py\n"
            "@@ -0,0 +1 @@\n"
            "+VALUE = 1\n"
        )
        self.assertEqual([], aidf.check_diff_consistency(["src/new.py"], patch))

    def test_diff_parser_accepts_legitimate_deleted_file(self) -> None:
        patch = (
            "diff --git a/src/old.py b/src/old.py\n"
            "deleted file mode 100644\n"
            "--- a/src/old.py\n"
            "+++ /dev/null\n"
            "@@ -1 +0,0 @@\n"
            "-VALUE = 1\n"
        )
        self.assertEqual([], aidf.check_diff_consistency(["src/old.py"], patch))

    def test_diff_parser_accepts_rename_represented_without_rename_detection(self) -> None:
        patch = (
            "diff --git a/src/old.py b/src/old.py\n"
            "deleted file mode 100644\n"
            "--- a/src/old.py\n"
            "+++ /dev/null\n"
            "@@ -1 +0,0 @@\n"
            "-VALUE = 1\n"
            "diff --git a/src/new.py b/src/new.py\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            "+++ b/src/new.py\n"
            "@@ -0,0 +1 @@\n"
            "+VALUE = 1\n"
        )
        self.assertEqual([], aidf.check_diff_consistency(["src/old.py", "src/new.py"], patch))

    def test_assertion_delta_is_advisory(self) -> None:
        notices = aidf.inspect_test_delta(text_fixture("negative/assertion-decline.patch"))
        self.assertEqual(1, len(notices))

    def test_assertion_delta_accepts_clean_fixture(self) -> None:
        self.assertEqual([], aidf.inspect_test_delta(text_fixture("positive/clean.patch")))

    def test_coverage_delta_is_advisory(self) -> None:
        notices = aidf.inspect_test_delta("", coverage_before=90.0, coverage_after=89.5)
        self.assertEqual(1, len(notices))


if __name__ == "__main__":
    unittest.main()
