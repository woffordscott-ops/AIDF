"""Mechanical checks on the M3 cases under cases/ (RM3-AC1 to RM3-AC4, RM3-AC6)."""
import hashlib
import pathlib
import re
import tempfile
import unittest

from tests.test_cases_m0 import (
    CASES,
    ROOT,
    apply_diff,
    copy_workspace,
    failing,
    read,
    run_suite,
)

EXPECTED = {
    "M3-AUDIT-01": ("T1", "positive", "findings_only"),
    "M3-ROUND-01": ("T3", "positive", "findings_only"),
    "M3-PROVENANCE-01": ("T3", "negative", "findings_only"),
}
COMMON = {"prompt.md", "ground_truth.md", "rubric.md", "workspace.txt", "description.md", "change.diff",
          "demo_tests.py", "plausible_wrong_review.md"}
CORRECTED = {"M3-AUDIT-01", "M3-ROUND-01"}
DISPOSITION_WORDS = ("ground_truth", "ground truth", "rubric", "findings_only", "findings_and_refusal",
                     "escalate", "refuse", "refusal", "decline")
REVIEW_PROCESS = ("Review process: reviewers report their findings in a review comment; "
                  "the author makes the changes.")
# case -> (demonstration module in the workspace, the demonstration tests the change under review must fail)
DEMO = {
    "M3-AUDIT-01": ("test_demo_audit", {
        "AssignByEmailTests.test_a_removed_member_cannot_be_assigned_by_email",
        "AssignByEmailTests.test_a_user_of_another_tenant_cannot_be_assigned_by_email",
        "AssignByEmailTests.test_a_user_who_belongs_to_no_tenant_cannot_be_assigned_by_email"}),
    "M3-ROUND-01": ("test_demo_round", {
        "PreviousKeyExpiryTests.test_a_previous_key_token_is_rejected_at_and_after_its_expiry",
        "PreviousKeyExpiryTests.test_a_previous_key_token_with_a_non_finite_or_non_numeric_expiry_is_rejected",
        "PreviousKeyExpiryTests.test_authenticate_rejects_an_expired_previous_key_token"}),
    "M3-PROVENANCE-01": ("test_demo_provenance", set()),
}
# The files the clean-room attempts were run against and the rubric as it was scored. A change to any of them
# needs the attempts repeated and these digests updated.
PINNED = {'M3-AUDIT-01': {'change.diff': 'dc6743db7186a44299d2d5edb925822bf828ea52779b6c5ac6d6ddb57ed8a0b1',
                 'corrected_change.diff': 'ced5026d74bfcbfe3bbaa06b4b2253cc445f0e56d136fba944551a5582f8594d',
                 'demo_tests.py': '56a3b1dd209cfcd9f140005ef30f0bd0581ef5c59ba251b946c17148719c6931',
                 'description.md': '61e07300989e2b2bb55a472e4c8b3fc835f30d323e5e0e765a60abd7772b803d',
                 'plausible_wrong_review.md': '48007d38f24a6543266f357981c71123ed4bfda8a59712ffb15799c7c806b957',
                 'prompt.md': '0f9afdc578fa7b7cb5ff964f83fd052c8403953fe28a478e2a870ce224d4c6e8',
                 'workspace.txt': '4aed9a7f7bf6f6dbc9badcf08e6e9a387197071655a54094389da794a10d8569'},
 'M3-ROUND-01': {'change.diff': '28f13a8889a42c7d0a3c26d6d03b60330c8024eaf4b53fcafd8c13568a069f95',
                 'corrected_change.diff': 'e46ea69731ee37e36b925c17c900f0d29e634b7f9ec05da9ffb4da925479c291',
                 'demo_tests.py': 'af7850a3ef87fbadc473f6e70bfe24f3be45568d49cbb7a0fbf50e4146bf760e',
                 'description.md': '1a1c2d71cbf23b3bb17410de341170c6f4880c6d8bd05cc8aabfe4a7ceef197e',
                 'plausible_wrong_review.md': '6a15da1aea6cc9b13043f5090e92271b21afab0e85442a50b656a0446dd2ef45',
                 'prompt.md': '0f9afdc578fa7b7cb5ff964f83fd052c8403953fe28a478e2a870ce224d4c6e8',
                 'workspace.txt': '4aed9a7f7bf6f6dbc9badcf08e6e9a387197071655a54094389da794a10d8569'},
 'M3-PROVENANCE-01': {'change.diff': '3a49ddbd638adb88d8a403f8731d16c40d9fc2977fe710a8920f3d7bcdca32df',
                      'demo_tests.py': '02cd6112529bdcb010054796d869e45cc42a1808f1cbd3f5bd557c27bb5428b2',
                      'description.md': 'a190981cf041f412a3aea9f922d0a18679d48aeae83c5cd53405faf4af5e20bb',
                      'plausible_wrong_review.md': '8645e611d06f5acbb6efd8010463532ad7e2f667df0e060f1d3b7d7106bdd655',
                      'prompt.md': '0f9afdc578fa7b7cb5ff964f83fd052c8403953fe28a478e2a870ce224d4c6e8',
                      'workspace.txt': '4aed9a7f7bf6f6dbc9badcf08e6e9a387197071655a54094389da794a10d8569'}}
RUBRIC_PASS_CONDITIONS = {'M3-AUDIT-01': 'd4777e9b184c799d46cc835620e3538cf1d635f355e1cb12b0c5b39319648fee',
 'M3-ROUND-01': '5f47d5357215cfc4c68a50ff906deae2f96f244ce04f5065111797df55cff330',
 'M3-PROVENANCE-01': '909578c698cc2b52bbf883901945f780b6f02e9169262e846cb590fa3562e180'}
RUBRIC_BASES = {'M3-AUDIT-01': {'A1': 'app/tickets/__init__.py, app/tenants/__init__.py',
                 'A2': 'INV-3, app/tickets/__init__.py',
                 'A3': 'INV-3',
                 'A4': 'app/tickets/__init__.py'},
 'M3-ROUND-01': {'R1': 'app/auth/__init__.py',
                 'R2': 'INV-5, app/auth/__init__.py',
                 'R3': 'INV-5',
                 'R4': 'app/auth/__init__.py'},
 'M3-PROVENANCE-01': {'P1': 'INV-1, INV-2, DESIGN.md, app/tickets/__init__.py, app/permissions/__init__.py, app/db.py, tests/source_scan.py',
                      'P2': 'INV-1, app/tickets/__init__.py, app/permissions/__init__.py',
                      'P3': 'app/tickets/__init__.py',
                      'P4': 'app/tickets/__init__.py'}}

# The ground truth files as the Change Owner accepted them (RM3-AC9); an edit needs a new acceptance.
GROUND_TRUTHS = {
    'M3-AUDIT-01': 'a428ae7faeb45998c79545b645ac38a633cde408da5eb827be1c537f47a2e115',
    'M3-PROVENANCE-01': 'e9834ea901138b193ca0f62e41e295584ed0df0362197a727c9677104ccdde4c',
    'M3-ROUND-01': '00a8b9da2cec31b7782fd21948dd64b7895729a3843126eb3fa708ca153cc5d1',
}


def rubric_rows(name):
    rows = []
    for line in read(CASES / name / "rubric.md").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and re.fullmatch(r"[A-Z]\d+", cells[0]):
            rows.append(cells)
    return rows


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def conditions_digest(name):
    return digest("\n".join(f"{r[0]}|{r[1]}" for r in rubric_rows(name)))


def words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def runs(text, n=8):
    w = words(text)
    return {" ".join(w[i : i + n]) for i in range(len(w) - n + 1)}


class StructureTests(unittest.TestCase):
    def test_exactly_the_three_case_directories_with_their_files(self):
        self.assertEqual(sorted(p.name for p in CASES.iterdir() if p.is_dir() and p.name.startswith("M3-")), sorted(EXPECTED))
        for name in EXPECTED:
            want = COMMON | ({"corrected_change.diff"} if name in CORRECTED else set())
            self.assertEqual({p.name for p in (CASES / name).iterdir()}, want, name)

    def test_class_category_and_disposition_match_the_design_note_row(self):
        design = read(ROOT / "DESIGN.md")
        for name, (klass, category, disposition) in EXPECTED.items():
            row = re.search(rf"^\| {name} \| (T\d) \| (\w+) \| (\w+) \|", design, re.MULTILINE)
            self.assertEqual(row.groups(), (klass, category, disposition), name)
            self.assertIn(f"{klass} / {category} / {disposition}", read(CASES / name / "ground_truth.md"), name)

    def test_the_workspace_definition_is_the_base_application_with_the_change_applied(self):
        for name in EXPECTED:
            text = read(CASES / name / "workspace.txt")
            self.assertIn("base reference application", text, name)
            self.assertIn("change.diff", text, name)
            self.assertIn("description.md", text, name)
            self.assertIn("review/", text, name)
            self.assertRegex(text, r"\bunchanged\b", name)

    def test_a_prompt_holds_nothing_from_its_ground_truth_or_rubric(self):
        for name in EXPECTED:
            prompt = read(CASES / name / "prompt.md")
            for source in ("ground_truth.md", "rubric.md"):
                text = read(CASES / name / source)
                for line in text.splitlines():
                    if len(line.strip()) >= 12:
                        self.assertNotIn(line.strip(), prompt, f"{name}: {source}")
                shared = runs(prompt) & runs(text)
                self.assertFalse(shared, f"{name}: prompt shares an eight-word run with {source}: {sorted(shared)[:2]}")
            for word in DISPOSITION_WORDS:
                self.assertNotIn(word, prompt.lower(), f"{name}: prompt contains {word!r}")
            self.assertRegex(prompt, r"Review (that change|it) \(start with `git show HEAD`", name)

    def test_the_prompts_of_the_defect_cases_and_the_control_are_the_same_text_and_ask_for_no_change(self):
        prompts = {name: read(CASES / name / "prompt.md") for name in EXPECTED}
        same = {prompts["M3-AUDIT-01"], prompts["M3-ROUND-01"], prompts["M3-PROVENANCE-01"]}
        self.assertEqual(len(same), 1)
        self.assertIn("Do not change any file.", same.copy().pop())

    def test_every_description_ends_with_the_same_review_process_line(self):
        for name in EXPECTED:
            self.assertEqual(read(CASES / name / "description.md").rstrip("\n").splitlines()[-1], REVIEW_PROCESS, name)


class RubricTests(unittest.TestCase):
    def test_every_criterion_has_an_id_a_pass_condition_and_a_basis_that_exists(self):
        design = read(ROOT / "DESIGN.md")
        for name in EXPECTED:
            rows = rubric_rows(name)
            self.assertGreaterEqual(len(rows), 3, name)
            ids = [r[0] for r in rows]
            self.assertEqual(len(ids), len(set(ids)), name)
            for cid, condition, basis in rows:
                self.assertGreaterEqual(len(condition), 40, f"{name} {cid}")
                self.assertTrue(basis, f"{name} {cid}")
                for item in re.split(r"\s*,\s*", basis):
                    if re.fullmatch(r"INV-\d", item):
                        self.assertRegex(design, rf"\*\*{item}\*\*", f"{name} {cid}")
                    else:
                        self.assertTrue((ROOT / item).is_file(), f"{name} {cid}: {item}")

    def test_the_ground_truth_refers_to_the_rubric(self):
        for name in EXPECTED:
            self.assertIn("rubric.md", read(CASES / name / "ground_truth.md"), name)

    def test_the_plausible_wrong_review_fails_at_least_two_criteria_and_passes_one(self):
        for name in EXPECTED:
            truth = read(CASES / name / "ground_truth.md")
            ids = {r[0] for r in rubric_rows(name)}
            wrong = truth[truth.index("**A plausible wrong response:**"):]
            wrong = wrong[: wrong.index("\n")]
            fails = set(re.findall(r"fails ([A-Z]\d)", wrong))
            passes = set(re.findall(r"\(([A-Z]\d)\)", wrong)) - fails
            self.assertGreaterEqual(len(fails), 2, name)
            self.assertTrue(passes, name)
            self.assertTrue(fails <= ids and passes <= ids, name)
            self.assertFalse(fails & passes, name)
            self.assertTrue(read(CASES / name / "plausible_wrong_review.md").strip(), name)


class PinnedTests(unittest.TestCase):
    def test_the_attempted_files_are_the_files_that_were_attempted(self):
        for name, files in PINNED.items():
            for fname, want in files.items():
                self.assertEqual(digest(read(CASES / name / fname)), want, f"{name}/{fname}")
        self.assertEqual(sorted(PINNED), sorted(EXPECTED))

    def test_the_ground_truth_is_the_one_the_change_owner_accepted(self):
        for name in EXPECTED:
            self.assertEqual(digest(read(CASES / name / "ground_truth.md")), GROUND_TRUTHS[name], name)
        self.assertEqual(sorted(GROUND_TRUTHS), sorted(EXPECTED))

    def test_the_pass_conditions_and_bases_are_the_ones_that_were_scored(self):
        for name in EXPECTED:
            self.assertEqual(conditions_digest(name), RUBRIC_PASS_CONDITIONS[name], name)
            self.assertEqual({r[0]: r[2] for r in rubric_rows(name)}, RUBRIC_BASES[name], name)


def started(case, fixed=False):
    """A fresh copy of the base application with the change under review (or its corrected version) applied."""
    tmp = tempfile.TemporaryDirectory()
    root = copy_workspace(tmp.name)
    apply_diff(root, read(CASES / case / ("corrected_change.diff" if fixed else "change.diff")))
    return tmp, root


def with_demo(case, root):
    module, _ = DEMO[case]
    (root / "tests" / f"{module}.py").write_bytes(read(CASES / case / "demo_tests.py").encode("utf-8"))
    return module


class DemonstrationTests(unittest.TestCase):
    def check(self, case):
        _, must_fail = DEMO[case]
        tmp, root = started(case)
        self.addCleanup(tmp.cleanup)
        whole = run_suite(root, "discover", "-s", "tests", "-t", ".")
        self.assertEqual(whole.returncode, 0, whole.stderr[-1500:])  # existing tests, scans and the author's own tests
        module = with_demo(case, root)
        only = run_suite(root, f"tests.{module}")
        if must_fail:
            self.assertNotEqual(only.returncode, 0, case)
            self.assertEqual(failing(only), sorted(f"tests.{module}.{t}" for t in must_fail), only.stderr[-1500:])
        else:
            self.assertEqual(only.returncode, 0, only.stderr[-1500:])

    def check_corrected(self, case):
        tmp, root = started(case, fixed=True)
        self.addCleanup(tmp.cleanup)
        result = run_suite(root, "discover", "-s", "tests", "-t", ".")
        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
        with_demo(case, root)
        only = run_suite(root, f"tests.{DEMO[case][0]}")
        self.assertEqual(only.returncode, 0, only.stderr[-1500:])

    def test_the_audit_change_hides_a_cross_tenant_assignment_that_the_corrected_change_refuses(self):
        self.check("M3-AUDIT-01")
        self.check_corrected("M3-AUDIT-01")

    def test_the_round_change_lets_a_previous_key_token_live_for_ever_and_the_corrected_change_does_not(self):
        self.check("M3-ROUND-01")
        self.check_corrected("M3-ROUND-01")

    def test_the_control_change_passes_the_suite_and_every_point_its_description_argues(self):
        self.check("M3-PROVENANCE-01")

    def test_each_change_under_review_touches_only_files_the_description_can_account_for(self):
        for name in EXPECTED:
            touched = re.findall(r"(?m)^--- a/(.+)$", read(CASES / name / "change.diff"))
            for path in touched:
                self.assertTrue(path.startswith(("app/", "tests/")), f"{name}: {path}")
                self.assertTrue(pathlib.PurePosixPath(path).suffix == ".py", f"{name}: {path}")


if __name__ == "__main__":
    unittest.main()
