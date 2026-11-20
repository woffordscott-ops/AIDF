"""Mechanical checks on the M2 case under cases/ (RM2-AC1 to RM2-AC4)."""
import hashlib
import re
import unittest

from tests.test_cases_m0 import CASES, ROOT, read

EXPECTED = {
    "M2-DESIGN-01": ("T2", "positive", "design_artifact_only"),
}
COMMON = {"prompt.md", "ground_truth.md", "rubric.md", "workspace.txt"}
EXTRA = {"M2-DESIGN-01": {"plausible_wrong_design.md"}}
# The prompt, the workspace definition and the stored wrong design are the files the clean-room attempts and the
# rubric scoring were run against. A change to one of them needs the attempts repeated and these digests updated.
PINNED = {
    "prompt.md": "a5c35054da1bd86d4fa63d077e5471fac4eaae7adb7d4d6dfa3395c4384cab19",
    "plausible_wrong_design.md": "525ca1e85e3d9f60e69cfa2091960b9ad0bb300418f01a24104f9f41cce093bb",
    "workspace.txt": "2caf29c350e73ef93b87a31cdf9f8c10c9f5a73273725aa442a0992c4d1c58ef",
}
# The rubric as the clean-room attempts were scored against it: the pass conditions as frozen (a digest of the id and
# pass-condition cells) and the base-application fact each criterion rests on, as set after Verifier round 1.
RUBRIC_PASS_CONDITIONS = "2b75f16ed2f0700dc0e45b268dabc815d5a8485f739b5f777bd896d8a2552f17"
RUBRIC_BASES = {
    "D1": "INV-1",
    "D2": "app/db.py",
    "D3": "app/idempotency/__init__.py",
    "D4": "INV-2",
    "D5": "app/auth/__init__.py",
    "D6": "app/db.py",
    "D7": "INV-1, app/db.py",
}
DISPOSITION_WORDS = ("ground_truth", "ground truth", "rubric", "design_artifact_only", "escalate", "refuse")


def rubric_rows(name):
    rows = []
    for line in read(CASES / name / "rubric.md").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and re.fullmatch(r"[A-Z]\d+", cells[0]):
            rows.append(cells)
    return rows


class StructureTests(unittest.TestCase):
    def test_exactly_the_one_case_directory_with_its_files(self):
        self.assertEqual(sorted(p.name for p in CASES.iterdir() if p.is_dir() and p.name.startswith("M2-")), sorted(EXPECTED))
        for name in EXPECTED:
            self.assertEqual({p.name for p in (CASES / name).iterdir()}, COMMON | EXTRA.get(name, set()), name)

    def test_class_category_and_disposition_match_the_design_note_row(self):
        design = read(ROOT / "DESIGN.md")
        for name, (klass, category, disposition) in EXPECTED.items():
            row = re.search(rf"^\| {name} \| (T\d) \| (\w+) \| (\w+) \|", design, re.MULTILINE)
            self.assertEqual(row.groups(), (klass, category, disposition), name)
            self.assertIn(f"{klass} / {category} / {disposition}", read(CASES / name / "ground_truth.md"), name)

    def test_the_workspace_is_the_base_application_unchanged(self):
        for name in EXPECTED:
            text = read(CASES / name / "workspace.txt")
            self.assertIn("base reference application", text, name)
            self.assertRegex(text, r"\bunchanged\b", name)
            self.assertNotRegex(text, r"\b(not|no longer) unchanged\b", name)
            self.assertFalse((CASES / name / "setup.patch").exists(), name)

    def test_a_prompt_holds_nothing_from_its_ground_truth_or_rubric(self):
        for name in EXPECTED:
            prompt = read(CASES / name / "prompt.md")
            for source in ("ground_truth.md", "rubric.md"):
                for line in read(CASES / name / source).splitlines():
                    if len(line.strip()) >= 12:
                        self.assertNotIn(line.strip(), prompt, f"{name}: {source}")
            for word in DISPOSITION_WORDS:
                self.assertNotIn(word, prompt.lower(), f"{name}: prompt contains {word!r}")
            self.assertIn("Do not write code", prompt, name)
            words = re.findall(r"[a-z0-9]+", prompt.lower())
            grams = {" ".join(words[i : i + 8]) for i in range(len(words) - 7)}
            for source in ("ground_truth.md", "rubric.md"):
                other = re.findall(r"[a-z0-9]+", read(CASES / name / source).lower())
                shared = grams & {" ".join(other[i : i + 8]) for i in range(len(other) - 7)}
                self.assertFalse(shared, f"{name}: prompt shares a eight-word run with {source}: {sorted(shared)[:2]}")


class PinnedTests(unittest.TestCase):
    def test_the_attempted_files_are_the_files_that_were_attempted(self):
        for fname, digest in PINNED.items():
            text = read(CASES / "M2-DESIGN-01" / fname)
            self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(), digest, fname)


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

    def test_the_pass_conditions_and_bases_are_the_ones_that_were_scored(self):
        rows = rubric_rows("M2-DESIGN-01")
        conditions = "\n".join(f"{r[0]}|{r[1]}" for r in rows)
        self.assertEqual(hashlib.sha256(conditions.encode("utf-8")).hexdigest(), RUBRIC_PASS_CONDITIONS)
        self.assertEqual({r[0]: r[2] for r in rows}, RUBRIC_BASES)

    def test_the_withdrawn_cases_are_not_in_the_change(self):
        for name in ("M2-INVARIANT-01", "M2-AUTHORITY-01"):
            self.assertFalse((CASES / name).exists(), name)

    def test_the_ground_truth_refers_to_the_rubric(self):
        for name in EXPECTED:
            self.assertIn("rubric.md", read(CASES / name / "ground_truth.md"), name)

    def test_the_plausible_wrong_design_fails_at_least_two_criteria_and_passes_one(self):
        truth = read(CASES / "M2-DESIGN-01" / "ground_truth.md")
        ids = {r[0] for r in rubric_rows("M2-DESIGN-01")}
        fails = set(re.findall(r"fails (D\d)", truth))
        passes = set(re.findall(r"\((D\d)\)", truth)) - fails
        self.assertGreaterEqual(len(fails), 2)
        self.assertTrue(passes)
        self.assertTrue(fails <= ids and passes <= ids)
        self.assertFalse(fails & passes)
        self.assertTrue(read(CASES / "M2-DESIGN-01" / "plausible_wrong_design.md").strip())


if __name__ == "__main__":
    unittest.main()
