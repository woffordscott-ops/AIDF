"""Controlled mutations prove that negative fixtures depend on their enforcement controls."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "verification" / "aidf_check.py"
SPEC = importlib.util.spec_from_file_location("aidf_check_mutation", MODULE_PATH)
assert SPEC and SPEC.loader
aidf = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = aidf
SPEC.loader.exec_module(aidf)
FIXTURES = ROOT / "verification" / "fixtures"


def fixture(relative: str):
    return json.loads((FIXTURES / relative).read_text(encoding="utf-8"))


def git_patch(path: str, added: list[str]) -> str:
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        f"@@ -1,0 +1,{len(added)} @@\n"
        + "".join(f"+{line}\n" for line in added)
    )


class CounterfactualMutationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = json.loads((ROOT / "verification" / "policy.json").read_text(encoding="utf-8"))
        self.contract = fixture("positive/contract-t2.json")

    def assert_control_is_material(self, control: str, call) -> None:
        self.assertTrue(call(), f"negative case unexpectedly passed before mutating {control}")
        with mock.patch.object(aidf, control, return_value=[]):
            self.assertEqual([], call(), f"disabling {control} did not admit its negative case")

    def test_contract_validator_is_material(self) -> None:
        record = fixture("negative/contract-not-clear.json")
        self.assert_control_is_material("validate_contract", lambda: aidf.validate_contract(record))

    def test_e3_validator_is_material(self) -> None:
        evidence = fixture("negative/evidence-missing-e3.json")
        self.assertTrue(aidf.validate_evidence(evidence, self.contract))
        with mock.patch.object(aidf, "_validate_e3", return_value=[]):
            self.assertEqual([], aidf.validate_evidence(evidence, self.contract))

    def test_scope_control_is_material(self) -> None:
        call = lambda: aidf.check_scope(["outside/service.py"], self.contract)
        self.assertTrue(call())
        with mock.patch.object(aidf, "_matches", return_value=True):
            self.assertEqual([], call())

    def test_tripwire_control_is_material(self) -> None:
        contract = fixture("negative/contract-t1-tripwire.json")
        contract["tripwires"] = []
        call = lambda: aidf.check_tripwires(["src/auth/login.py"], "", self.policy, contract)
        self.assertTrue(call())
        with mock.patch.object(aidf, "detect_tripwires", return_value=set()):
            self.assertEqual([], call())

    def test_dependency_control_is_material(self) -> None:
        contract = fixture("negative/contract-unapproved-dependency.json")
        patch = git_patch("requirements.txt", ["fixture-package==1.0.0"])
        call = lambda: aidf.check_dependencies(["requirements.txt"], patch, self.policy, contract)
        self.assertTrue(call())
        with mock.patch.object(aidf, "_dependency_references", return_value={}):
            self.assertEqual([], call())

    def test_secret_control_is_material(self) -> None:
        parts = fixture("negative/secret-canary-parts.json")
        canary = parts["prefix"] + parts["kind"] + parts["value"]
        patch = git_patch("src/service.py", [f'value = "{canary}"'])
        self.assertTrue(aidf.check_secrets(patch))
        with mock.patch.object(aidf, "SECRET_PATTERNS", ()):
            self.assertEqual([], aidf.check_secrets(patch))

    def test_exemption_cap_is_material(self) -> None:
        records = fixture("negative/exemptions-six-open.json")
        self.assert_control_is_material("validate_exemptions", lambda: aidf.validate_exemptions(records))

    def test_exemption_registry_link_is_material(self) -> None:
        contract = deepcopy(self.contract)
        contract.update({"change_id": "fixture-6", "class": "T1"})
        contract.pop("approved_by")
        contract.pop("approved_date")
        evidence = fixture("positive/evidence-t2.json")
        evidence.update({"change_id": "fixture-6", "class": "T1", "e3": {"status": "exempted", "exemption_id": "EX-6"}})
        for field in ("e4", "e5", "e6"):
            evidence.pop(field)
        records = fixture("positive/exemptions-five-open.json")
        self.assertTrue(aidf.validate_evidence(evidence, contract, records))
        with mock.patch.object(aidf, "_validate_e3", return_value=[]):
            self.assertEqual([], aidf.validate_evidence(evidence, contract, records))


if __name__ == "__main__":
    unittest.main()
