from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "verification" / "qualification_check.py"
SPEC = importlib.util.spec_from_file_location("qualification_check_v2", MODULE_PATH)
assert SPEC and SPEC.loader
qualification = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = qualification
SPEC.loader.exec_module(qualification)

SUITE_PATH = ROOT / "profiles" / "qualification-eval" / "suite-v2.json"
DOC_PATH = ROOT / "profiles" / "qualification-eval" / "REFERENCE-SUITE.md"
CASES_DIR = "profiles/qualification-eval/reference-app/cases"
PINNED_REVISION = "6d647332048862bfa464d11374f53ea6d9cdcfbd"
V1_SUITE_DIGESTS = {
    "suite-v1.json": "ed7dac46128fe633ff01cbd12841b57221353d11c01e16d080131aacace440f3",
    "suite-v1.1.json": "a827a910b3f49ea8eb8220b6ac0edd5f8016c1fbe3163fa8dcec4afec9b96a3b",
}
NEEDS_V1_SUITES = unittest.skipUnless(
    all((ROOT / "profiles" / "qualification-eval" / name).is_file() for name in V1_SUITE_DIGESTS),
    "needs profiles/qualification-eval/suite-v1.json and suite-v1.1.json, which a published copy of this repository does not contain",
)
PINNED_SUITE_SHA256 = "91c8d1eefb846aa44d3af8dec9a34ccbfe72979cbd37ae236af661ffd63710e6"
EXPECTED_CASES = {
    "M0": ["M0-TRANSFORM-01", "M0-BOUNDARY-01", "M0-EVIDENCE-01", "M0-SECRET-01"],
    "M1": [
        "M1-FLOW-01",
        "M1-BILLING-01",
        "M1-MEMBERS-01",
        "M1-SCOPE-01",
        "M1-INVARIANT-01",
        "M1-EVIDENCE-01",
        "M1-AUTHORITY-01",
        "M1-PROVENANCE-01",
    ],
    "M2": ["M2-DESIGN-01"],
    "M3": ["M3-AUDIT-01", "M3-ROUND-01", "M3-PROVENANCE-01"],
}
WITHDRAWN = [
    "M1-CONTRACT-01",
    "M1-TRIPWIRE-01",
    "M2-INVARIANT-01",
    "M2-AUTHORITY-01",
    "M3-SELF-FIX-01",
]
GROUND_TRUTH_LINE = re.compile(
    r"\*\*Class / category / expected disposition:\*\* (T[0-3]) / (positive|negative|boundary) / ([a-z_]+)\."
)


def load_suite() -> dict[str, Any]:
    return json.loads(SUITE_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def git(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=False)


def revision_present() -> bool:
    return git("cat-file", "-e", f"{PINNED_REVISION}^{{commit}}").returncode == 0


class SuiteFileTests(unittest.TestCase):
    def test_the_suite_passes_the_existing_validator_with_the_pinned_digest(self) -> None:
        suite = load_suite()
        findings = qualification.validate_suite(suite)
        self.assertEqual([], [f"{finding.check}: {finding.message}" for finding in findings])
        self.assertEqual(PINNED_SUITE_SHA256, qualification.canonical_sha256(suite))

    @NEEDS_V1_SUITES
    def test_the_suite_has_its_own_identity_and_the_v1_files_have_their_pinned_digests(self) -> None:
        suite = load_suite()
        self.assertEqual("aidf-reference-qualification", suite["suite_id"])
        self.assertEqual("2.0.0", suite["suite_version"])
        for name, digest in V1_SUITE_DIGESTS.items():
            other = json.loads((ROOT / "profiles" / "qualification-eval" / name).read_text(encoding="utf-8"))
            self.assertNotEqual(other["suite_id"], suite["suite_id"])
            self.assertEqual(digest, qualification.canonical_sha256(other), name)

    def test_every_revision_is_the_pinned_stage_one_merge(self) -> None:
        suite = load_suite()
        self.assertEqual(PINNED_REVISION, suite["repository"]["revision"])
        self.assertEqual("ProjectGenome/ai-development-framework", suite["repository"]["project"])
        self.assertEqual("profiles/qualification-protocol-v1.2.md", suite["protocol_path"])
        self.assertTrue((ROOT / suite["protocol_path"]).is_file())
        for case in suite["cases"]:
            self.assertEqual(suite["repository"], {k: case["source"][k] for k in ("project", "revision")})

    def test_the_cases_are_the_sixteen_merged_ones_in_order_with_counts_4_8_1_3(self) -> None:
        suite = load_suite()
        by_mode = {record["mode"]: record["case_ids"] for record in suite["modes"]}
        self.assertEqual(EXPECTED_CASES, by_mode)
        self.assertEqual([4, 8, 1, 3], [len(by_mode[mode]) for mode in ("M0", "M1", "M2", "M3")])
        listed = [case["case_id"] for case in suite["cases"]]
        self.assertEqual([c for mode in ("M0", "M1", "M2", "M3") for c in EXPECTED_CASES[mode]], listed)
        for case in suite["cases"]:
            self.assertIs(True, case["mandatory"])
            self.assertEqual(case["case_id"].split("-")[0], case["mode"])
            self.assertEqual(f"Authored case directory {CASES_DIR}/{case['case_id']}", case["source"]["record"])
        for case_id in WITHDRAWN:
            self.assertNotIn(case_id, listed)

    def test_an_objective_does_not_state_a_disposition_or_a_ground_truth_word(self) -> None:
        for case in load_suite()["cases"]:
            lowered = case["objective"].lower()
            words = [*qualification.DISPOSITIONS, *(d.replace("_", " ") for d in qualification.DISPOSITIONS)]
            words += ["ground truth", "rubric", "planted", "expected disposition"]
            for word in words:
                self.assertNotIn(word, lowered, case["case_id"])


class PinnedRevisionTests(unittest.TestCase):
    def setUp(self) -> None:
        if not revision_present():
            self.skipTest("the pinned revision is not present in this clone (a skip, not a pass)")

    def test_each_case_directory_exists_and_its_ground_truth_matches_the_suite(self) -> None:
        for case in load_suite()["cases"]:
            tree = git("ls-tree", PINNED_REVISION, f"{CASES_DIR}/{case['case_id']}/")
            self.assertEqual(0, tree.returncode, case["case_id"])
            self.assertTrue(tree.stdout.strip(), case["case_id"])
            for name in ("prompt.md", "workspace.txt", "ground_truth.md"):
                present = git("cat-file", "-e", f"{PINNED_REVISION}:{CASES_DIR}/{case['case_id']}/{name}")
                self.assertEqual(0, present.returncode, f"{case['case_id']}/{name}")
            shown = git("show", f"{PINNED_REVISION}:{CASES_DIR}/{case['case_id']}/ground_truth.md")
            self.assertEqual(0, shown.returncode, case["case_id"])
            match = GROUND_TRUTH_LINE.search(shown.stdout.decode("utf-8"))
            self.assertIsNotNone(match, case["case_id"])
            assert match is not None
            self.assertEqual(
                (case["task_class"], case["category"], case["expected_disposition"]),
                match.groups(),
                case["case_id"],
            )

    def test_no_withdrawn_case_directory_is_present_at_the_pinned_revision(self) -> None:
        for case_id in WITHDRAWN:
            tree = git("ls-tree", PINNED_REVISION, f"{CASES_DIR}/{case_id}/")
            self.assertEqual(b"", tree.stdout.strip(), case_id)


class DocumentationTests(unittest.TestCase):
    def test_the_reference_suite_document_states_the_pin_the_digest_and_the_deviation(self) -> None:
        text = DOC_PATH.read_text(encoding="utf-8")
        self.assertIn(PINNED_REVISION, text)
        self.assertIn(PINNED_SUITE_SHA256, text)
        self.assertIn("4/8/1/3", text)
        self.assertIn("4/10/3/4", text)
        for case_id in WITHDRAWN:
            self.assertIn(case_id, text)
        self.assertIn("answer key is public", text.lower())
        self.assertIn("qualification-protocol-v1.2.md", text)
        self.assertIn("author's description", text)
        self.assertIn("The other five M1 cases", text)
        self.assertIn("the declared M0, M1 and M3 differences", text)
        self.assertNotIn("declared M0 and M3 differences", text)
        self.assertIn("does not check that the list contains what protocol v1.2 requires", text)

    def test_protocol_v1_2_declares_the_suite_differences(self) -> None:
        text = re.sub(r"\s+", " ", (ROOT / "profiles" / "qualification-protocol-v1.2.md").read_text(encoding="utf-8"))
        self.assertIn("declares three for `suite-v2.json`", text)
        for case_id in ("M1-SCOPE-01", "M1-INVARIANT-01", "M1-EVIDENCE-01", "M1-AUTHORITY-01", "M1-PROVENANCE-01"):
            self.assertIn(case_id, text)
        self.assertIn("public answer key", text)

    def test_the_readmes_point_at_the_suite_and_its_document(self) -> None:
        for relative in ("README.md", "profiles/README.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("suite-v2.json", text, relative)
            self.assertIn("REFERENCE-SUITE.md", text, relative)
            self.assertIn(PINNED_REVISION, text, relative)
            self.assertIn(PINNED_SUITE_SHA256, text, relative)
            self.assertIn("answer key is public", text.lower(), relative)

    def test_the_expired_private_pilot_profile_is_not_described_as_current(self) -> None:
        stale = re.compile(
            r"is \*{0,2}qualified|Status: active\.|Active: `codex-cli`|qualification is active",
            re.IGNORECASE,
        )
        for relative in ("README.md", "profiles/README.md", "IMPLEMENTATION-STATUS.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            flat = re.sub(r"\s+", " ", text)
            self.assertIsNone(stale.search(flat), relative)
            self.assertIn("requalification", text.lower(), relative)

    def test_the_conflict_is_disclosed_in_the_implementation_status(self) -> None:
        text = (ROOT / "IMPLEMENTATION-STATUS.md").read_text(encoding="utf-8")
        self.assertIn("suite-v2.json", text)
        self.assertIn("4/10/3/4", text)


if __name__ == "__main__":
    unittest.main()
