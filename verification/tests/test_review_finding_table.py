"""Tests for verification/review_finding_table.py: finding extraction, carry-overs, canonical records and the CSV output."""

import csv
import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SPEC = importlib.util.spec_from_file_location("review_finding_table", ROOT / "verification" / "review_finding_table.py")
T = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(T)

HEADING_REPORT = """# Verifier report, round 3

Outcome: BLOCKED on V3-001. See SHA-256 notes.

## Findings

### V3-001 - High - The evidence pack overstates coverage
`verification/example-evidence-pack.json` says 12 tests; there are 9.

### V3-002 - Low - Advisory: helper name
`app/helpers.py` uses a misleading name.

## Status of earlier findings

- V1-004: closed for the returned implementations.
"""

RECORD = [{"id": "R2-001", "blocking": True, "basis": "app/billing.py loses a cent"}, {"id": "R2-002", "blocking": False, "basis": "x"}]
JSON_REPORT = "# Verifier report, round 2\n\n" + json.dumps(RECORD) + "\n"


def run(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8")


class FindingTableTests(unittest.TestCase):
    def setUp(self):
        T.TRACKED = ("app/helpers.py", "verification/example-evidence-pack.json")
        self.addCleanup(setattr, T, "TRACKED", ())

    def test_untracked_and_local_paths_are_dropped_from_the_output(self):
        self.assertEqual(T.resolve(["app/helpers.py", "Users/someone/x/app/helpers.py", "gone.py"]), ["app/helpers.py"])
        self.assertEqual(T.scrub("see C:" + chr(92) + "Users" + chr(92) + "someone and /home/x/y ok"), "see [local path] and [local path] ok")

    def test_private_hosts_and_split_literals_are_scrubbed(self):
        self.assertEqual(T.scrub("push to git.example.home now"), "push to [private host] now")
        self.assertEqual(T.scrub('built as "ab" + "." + "cd" here'), "built as [split string] here")

    def test_heading_findings_with_blocking_and_type(self):
        rows = {r["finding_id"]: r for r in T.findings_of(HEADING_REPORT, 3)}
        self.assertIn("V3-001", rows)
        self.assertIn("V3-002", rows)
        self.assertNotIn("SHA-256", rows)
        self.assertEqual(rows["V3-001"]["blocking"], "yes")
        self.assertEqual(rows["V3-001"]["in_outcome"], "yes")
        self.assertEqual(rows["V3-001"]["type_auto"], "record_text")
        self.assertEqual(rows["V3-002"]["blocking"], "no")
        self.assertEqual(rows["V3-002"]["type_auto"], "code")

    def test_closed_and_earlier_round_findings_are_carry_overs(self):
        rows = {r["finding_id"]: r for r in T.findings_of(HEADING_REPORT, 3)}
        self.assertEqual(rows["V1-004"]["carry_over"], "yes")
        self.assertEqual(rows["V3-001"]["carry_over"], "no")
        self.assertTrue(T.carried("R21-001", "R21-001 stays open", "Findings", 22))
        self.assertFalse(T.carried("R22-001", "R22-001 Low 2 pack", "Findings", 22))

    def test_a_line_naming_three_ids_is_a_reference_not_a_finding(self):
        text = "- REV-003, REV-004 and REV-005 are catalogue gaps.\n"
        self.assertEqual(list(T.findings_of(text, 1)), [])

    def test_canonical_json_records_are_authoritative(self):
        rows = list(T.findings_of(JSON_REPORT, 2))
        self.assertEqual([r["finding_id"] for r in rows], ["R2-001", "R2-002"])
        self.assertEqual([r["blocking"] for r in rows], ["yes", "no"])
        self.assertTrue(all(r["type_method"].endswith("(canonical record)") for r in rows))

    def test_classify_by_cited_files(self):
        self.assertEqual(T.classify([])[0], "unclassified")
        self.assertEqual(T.classify(["app/a.py"])[0], "code")
        self.assertEqual(T.classify(["tests/test_a.py"])[0], "tests")
        self.assertEqual(T.classify(["strategy/a.md"])[0], "record_text")

    def test_csv_from_a_committed_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp) / "repo"
            (repo / "verification").mkdir(parents=True)
            run("init", "-q", cwd=repo)
            run("config", "user.email", "t@example.invalid", cwd=repo)
            run("config", "user.name", "t", cwd=repo)
            (repo / "verification" / "x-verifier-report-round3.md").write_text(HEADING_REPORT, encoding="utf-8")
            (repo / "verification" / "y-security-review-round1.md").write_text("# Security\n\nNo issues.\n", encoding="utf-8")
            (repo / "verification" / "notes.md").write_text("V9-001 not a report\n", encoding="utf-8")
            run("add", "-A", cwd=repo)
            run("commit", "-q", "-m", "reports", cwd=repo)
            out = pathlib.Path(tmp) / "out.csv"
            self.assertEqual(T.main(["--repo", str(repo), "--out", str(out)]), 0)
            with open(out, newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
        self.assertEqual(list(rows[0]), T.COLUMNS)
        self.assertEqual({r["path"] for r in rows}, {"verification/x-verifier-report-round3.md", "verification/y-security-review-round1.md"})
        empty = [r for r in rows if r["type_auto"] == "none_found"]
        self.assertEqual([r["role"] for r in empty], ["security"])
        self.assertTrue(all(r["type_checked"] == "" for r in rows))

    def test_hand_labels_fill_type_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            labels = pathlib.Path(tmp) / "labels.csv"
            labels.write_text("path,finding_id,round,label\nverification/a.md,V3-001,3,process\n", encoding="utf-8")
            rows = [
                {"path": "verification/a.md", "finding_id": "V3-001"},
                {"path": "verification/a.md", "finding_id": "V3-002"},
                {"path": "verification/b.md", "finding_id": ""},
            ]
            T.apply_labels(rows, T.load_labels(labels))
            self.assertEqual([r["type_checked"] for r in rows], ["process", "", ""])
            self.assertEqual(T.load_labels(pathlib.Path(tmp) / "absent.csv"), {})


if __name__ == "__main__":
    unittest.main()
