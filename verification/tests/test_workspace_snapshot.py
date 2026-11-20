"""Tests for verification/workspace_snapshot.py."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("workspace_snapshot", ROOT / "verification" / "workspace_snapshot.py")
assert SPEC and SPEC.loader
ws = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ws
SPEC.loader.exec_module(ws)


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name).resolve()
        self.root = self.base / "work"
        self.root.mkdir()
        (self.root / "a.txt").write_text("one", encoding="utf-8")
        (self.root / "sub").mkdir()
        (self.root / "sub" / "b.txt").write_text("two", encoding="utf-8")

    def link(self, target: Path, name: Path) -> None:
        try:
            os.symlink(target, name, target_is_directory=target.is_dir())
        except (OSError, NotImplementedError):
            self.skipTest("this account cannot create symbolic links")


class SnapshotTests(Base):
    def test_lists_files_with_size_and_digest(self) -> None:
        record = ws.snapshot(self.root)
        self.assertEqual(sorted(record["files"]), ["a.txt", "sub/b.txt"])
        self.assertEqual(record["files"]["a.txt"]["size"], 3)
        self.assertEqual(len(record["files"]["a.txt"]["sha256"]), 64)
        self.assertEqual(record["root"], "<workspace>")

    def test_a_record_taken_twice_compares_equal(self) -> None:
        first = ws.snapshot(self.root)
        second = ws.snapshot(self.root)
        self.assertEqual(ws.compare(first, second), {"added": [], "removed": [], "changed": [], "touched": []})

    def test_an_added_file(self) -> None:
        before = ws.snapshot(self.root)
        (self.root / "sub" / "c.txt").write_text("x", encoding="utf-8")
        self.assertEqual(ws.compare(before, ws.snapshot(self.root))["added"], ["sub/c.txt"])

    def test_a_removed_file(self) -> None:
        before = ws.snapshot(self.root)
        (self.root / "a.txt").unlink()
        diff = ws.compare(before, ws.snapshot(self.root))
        self.assertEqual(diff["removed"], ["a.txt"])
        self.assertEqual(diff["added"], [])

    def test_a_changed_file_even_with_the_same_size(self) -> None:
        before = ws.snapshot(self.root)
        (self.root / "a.txt").write_text("xyz", encoding="utf-8")
        diff = ws.compare(before, ws.snapshot(self.root))
        self.assertEqual(diff["changed"], ["a.txt"])

    def test_only_the_mtime_differing_is_touched_not_changed(self) -> None:
        before = ws.snapshot(self.root)
        path = self.root / "a.txt"
        stat = path.stat()
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
        diff = ws.compare(before, ws.snapshot(self.root))
        self.assertEqual(diff["touched"], ["a.txt"])
        self.assertEqual(diff["changed"], [])

    def test_an_excluded_name_is_skipped_at_any_depth(self) -> None:
        (self.root / ".git").mkdir()
        (self.root / ".git" / "HEAD").write_text("ref", encoding="utf-8")
        (self.root / "sub" / ".git").mkdir()
        (self.root / "sub" / ".git" / "x").write_text("x", encoding="utf-8")
        self.assertEqual(sorted(ws.snapshot(self.root)["files"]), ["a.txt", "sub/b.txt"])
        self.assertIn(".git/HEAD", ws.snapshot(self.root, exclude=())["files"])

    def test_a_link_pointing_outside_is_recorded_and_not_followed(self) -> None:
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("s", encoding="utf-8")
        self.link(outside, self.root / "out")
        record = ws.snapshot(self.root)
        self.assertEqual(record["links"]["out"], {"outside": True})
        self.assertNotIn("out/secret.txt", record["files"])

    def test_a_directory_junction_is_recorded_and_not_followed(self) -> None:
        if sys.platform != "win32":
            self.skipTest("directory junctions exist on Windows only")
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("s", encoding="utf-8")
        done = subprocess.run(["cmd", "/c", "mklink", "/J", str(self.root / "junc"), str(outside)], capture_output=True, text=True, check=False)
        if done.returncode:
            self.skipTest("this account cannot create a junction: " + done.stderr.strip())
        record = ws.snapshot(self.root)
        self.assertEqual(record["links"]["junc"], {"outside": True})
        self.assertNotIn("junc/secret.txt", record["files"])

    def test_a_link_inside_is_not_outside(self) -> None:
        self.link(self.root / "sub", self.root / "inner")
        self.assertEqual(ws.snapshot(self.root)["links"]["inner"], {"outside": False})

    def test_a_file_link_retargeted_is_a_change(self) -> None:
        one = self.base / "t1.txt"
        two = self.root / "t2.txt"
        one.write_text("1", encoding="utf-8")
        two.write_text("2", encoding="utf-8")
        self.link(one, self.root / "ln")
        before = ws.snapshot(self.root)
        (self.root / "ln").unlink()
        self.link(two, self.root / "ln")
        diff = ws.compare(before, ws.snapshot(self.root))
        self.assertEqual(diff["changed"], ["ln"])

    def test_not_a_directory_is_refused(self) -> None:
        with self.assertRaises(ws.SnapshotError):
            ws.snapshot(self.root / "a.txt")

    def test_taking_a_record_writes_nothing_in_the_directory(self) -> None:
        before = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*"))
        ws.snapshot(self.root)
        after = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*"))
        self.assertEqual(before, after)


class RecordTests(Base):
    def test_redaction_removes_the_directory_and_the_home_in_both_forms(self) -> None:
        text = f"{self.root} and {str(self.root).replace(chr(92), '/')} and {Path.home()}"
        out = ws.redact(text, self.root)
        self.assertNotIn(str(self.root), out)
        self.assertNotIn(str(self.root).replace("\\", "/"), out)
        self.assertNotIn(str(Path.home()), out)
        self.assertIn("<workspace>", out)
        self.assertIn("<home>", out)

    def test_redaction_covers_json_escaped_backslashes(self) -> None:
        text = json.dumps({"p": str(self.root)})
        self.assertNotIn(self.base.name, ws.redact(text, self.root))

    def test_a_written_record_names_no_path_of_the_machine(self) -> None:
        out = self.base / "rec" / "r.json"
        ws.write_record(ws.snapshot(self.root), out, self.root)
        text = out.read_text(encoding="utf-8")
        self.assertNotIn(str(self.base), text)
        self.assertEqual(json.loads(text)["root"], "<workspace>")

    def test_writing_inside_the_recorded_directory_is_refused(self) -> None:
        with self.assertRaises(ws.SnapshotError):
            ws.write_record(ws.snapshot(self.root), self.root / "r.json", self.root)
        self.assertFalse((self.root / "r.json").exists())

    def test_an_output_path_that_is_a_hard_link_is_refused(self) -> None:
        victim = self.root / "a.txt"
        alias = self.base / "alias.json"
        try:
            os.link(victim, alias)
        except (OSError, NotImplementedError):
            self.skipTest("this account cannot create a hard link")
        with self.assertRaises(ws.SnapshotError):
            ws.write_record(ws.snapshot(self.root), alias, self.root)
        self.assertEqual(victim.read_text(encoding="utf-8"), "one")

    def test_writing_to_the_directory_itself_is_refused(self) -> None:
        with self.assertRaises(ws.SnapshotError):
            ws.write_record(ws.snapshot(self.root), self.root, self.root)

    def test_the_command_line_snapshot_and_compare(self) -> None:
        a, b = self.base / "a.json", self.base / "b.json"
        self.assertEqual(ws.main(["snapshot", str(self.root), str(a)]), 0)
        (self.root / "new.txt").write_text("n", encoding="utf-8")
        self.assertEqual(ws.main(["snapshot", str(self.root), str(b)]), 0)
        self.assertEqual(ws.main(["compare", str(a), str(b)]), 0)
        self.assertEqual(ws.main(["snapshot", str(self.root), str(self.root / "in.json")]), 1)


if __name__ == "__main__":
    unittest.main()
