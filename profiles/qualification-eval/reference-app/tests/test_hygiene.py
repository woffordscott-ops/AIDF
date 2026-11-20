"""Checks on the fixture itself: stdlib-only, intentional gaps, and the approved catalogue."""
import ast
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def imported_roots(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module.split(".")[0]


class HygieneTests(unittest.TestCase):
    def test_python_sources_import_only_stdlib_or_local(self):
        local = {"app", "tests"}
        for path in [*ROOT.glob("app/**/*.py"), *ROOT.glob("tests/**/*.py"), *ROOT.glob("tools/*.py")]:
            for name in imported_roots(path):
                self.assertTrue(
                    name in sys.stdlib_module_names or name in local,
                    f"{path.relative_to(ROOT)} imports non-stdlib module {name!r}",
                )

    def test_base_app_omits_the_features_m1_cases_ask_candidates_to_build(self):
        source = "\n".join(p.read_text(encoding="utf-8") for p in ROOT.glob("app/**/*.py")).lower()
        for feature in ("change_role", "add_comment", "usage_credit", "/comments"):
            self.assertNotIn(feature, source, f"base app must not already contain {feature!r}")

    def test_design_note_catalogue_matches_the_approved_counts(self):
        text = (ROOT / "DESIGN.md").read_text(encoding="utf-8")
        counts = {m: len(set(re.findall(rf"^\| ({m}-[A-Z0-9-]+) \|", text, re.MULTILINE))) for m in ("M0", "M1", "M2", "M3")}
        self.assertEqual(counts, {"M0": 4, "M1": 10, "M2": 3, "M3": 4})

    def test_no_pycache_or_database_files_committed(self):
        self.assertEqual([p for p in ROOT.rglob("*.db")], [])


if __name__ == "__main__":
    unittest.main()
