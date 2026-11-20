from __future__ import annotations

import ast
import contextlib
import copy
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("spec_mapper", ROOT / "verification" / "spec_mapper.py")
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)

FIXTURES = ROOT / "verification" / "spec-mapper-fixtures"
GOLDEN = {
    "openspec": "openspec-input",
    "speckit": "speckit-input",
    "kiro-synthetic": "kiro-input",
    "markdown-sections": "sections-input",
}
CRLF = bytes([13, 10])
LF = bytes([10])
VALID = {
    "schema_version": 1,
    "name": "example",
    "detect": ["plan.md"],
    "id_from": "plan.md",
    "rules": [{"source": "plan.md", "operation": "section", "heading": "Outcome", "target": "intended_outcome"}],
}
PLAN = "# Plan\n\n## Outcome\n\nOne outcome.\n\n## Scope\n\n- a.py\n"


def write(path: Path, text: str | bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8", newline="")
    return path


def lf(path: Path) -> bytes:
    """A committed file's bytes with CRLF turned into LF: a checkout with autocrlf converts the fixtures, and the tool's output is always LF."""
    return path.read_bytes().replace(CRLF, LF)


def make_link(link: Path, target: Path) -> bool:
    """A symbolic link, or on Windows a junction; False when the account cannot create either."""
    try:
        os.symlink(target, link, target_is_directory=target.is_dir())
        return True
    except (OSError, NotImplementedError):
        pass
    if os.name == "nt" and target.is_dir():
        done = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, text=True, check=False)
        return done.returncode == 0
    return False


def refused(case: unittest.TestCase, fragment: str, call, *args):
    with case.assertRaises(M.Refused) as caught:
        call(*args)
    case.assertIn(fragment, str(caught.exception))
    return str(caught.exception)


class TempCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.input = self.tmp / "input"
        self.input.mkdir()
        self.out = self.tmp / "draft.md"

    def mapping_file(self, mapping: dict, name: str = "mapping.json") -> str:
        return str(write(self.tmp / name, json.dumps(mapping)))

    def run_main(self, *argv: str) -> tuple[int, str]:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
            code = M.main(list(argv))
        return code, stderr.getvalue()


class MappingSchemaTests(TempCase):
    def test_the_four_built_in_mappings_are_valid_and_each_name_is_its_file_name(self) -> None:
        found = sorted(path.stem for path in M.MAPPINGS_DIR.glob("*.json"))
        self.assertEqual(sorted(GOLDEN), found)
        for name in GOLDEN:
            self.assertEqual(name, M.load_mapping(name)["name"])

    def test_a_valid_mapping_is_accepted_from_a_file(self) -> None:
        self.assertEqual(VALID, M.load_mapping(self.mapping_file(VALID)))

    def _bad(self, change, fragment: str) -> None:
        mapping = copy.deepcopy(VALID)
        change(mapping)
        refused(self, fragment, M.load_mapping, self.mapping_file(mapping))

    def test_a_key_that_is_not_in_the_schema_is_refused_by_name(self) -> None:
        self._bad(lambda m: m.update(extra=1), "unknown key 'extra'")
        self._bad(lambda m: m["rules"][0].update(extra=1), "unknown key 'extra'")

    def test_each_missing_key_is_refused_by_name(self) -> None:
        for key in M.MAPPING_KEYS:
            self._bad(lambda m, key=key: m.pop(key), "missing key '" + key + "'")
        for key in M.RULE_REQUIRED:
            self._bad(lambda m, key=key: m["rules"][0].pop(key), "missing key '" + key + "'")

    def test_wrong_types_and_values_are_refused_by_name(self) -> None:
        self._bad(lambda m: m.update(schema_version=2), "'schema_version'")
        self._bad(lambda m: m.update(schema_version=True), "'schema_version'")
        self._bad(lambda m: m.update(name="Bad Name"), "'name'")
        self._bad(lambda m: m.update(detect=[]), "'detect'")
        self._bad(lambda m: m.update(detect="plan.md"), "'detect'")
        self._bad(lambda m: m.update(rules=[]), "'rules'")
        self._bad(lambda m: m.update(rules={}), "'rules'")
        self._bad(lambda m: m.update(rules=["x"]), "rules[0] must be an object")
        self._bad(lambda m: m["rules"][0].update(operation="run"), "'operation'")
        self._bad(lambda m: m["rules"][0].update(target="class"), "'target'")
        self._bad(lambda m: m["rules"][0].update(heading=""), "'heading'")
        self._bad(lambda m: m["rules"][0].update(heading=5), "'heading'")
        self._bad(lambda m: m["rules"][0].pop("heading"), "needs key 'heading'")
        self._bad(lambda m: (m["rules"][0].pop("heading"), m["rules"][0].update(operation="blocks")), "needs key 'prefix'")
        self._bad(lambda m: m["rules"][0].update(operation="file"), "key 'heading' is not used")
        self._bad(lambda m: m["rules"][0].update(prefix="x"), "key 'prefix' is not used")
        for limit in (0, -1, True, "1", 1.5, M.MAX_LIMIT + 1):
            self._bad(lambda m, limit=limit: m["rules"][0].update(limit=limit), "'limit'")

    def test_a_path_that_could_leave_the_folder_is_refused(self) -> None:
        for pattern in ("../plan.md", "/etc/passwd", "a/../plan.md", "a\\plan.md", "C:plan.md", "a//plan.md", "./plan.md", "**/plan.md", "a/[bc]/plan.md", "a/plan*.md\n", ""):
            self._bad(lambda m, pattern=pattern: m["rules"][0].update(source=pattern), "key 'source'")
            self._bad(lambda m, pattern=pattern: m.update(id_from=pattern), "key 'id_from'")
            self._bad(lambda m, pattern=pattern: m.update(detect=[pattern]), "detect[0]")

    def test_a_duplicate_key_a_non_finite_number_and_unreadable_files_are_refused(self) -> None:
        path = write(self.tmp / "dup.json", '{"schema_version": 1, "schema_version": 1}')
        refused(self, "duplicate key", M.load_mapping, str(path))
        path = write(self.tmp / "nan.json", json.dumps(VALID).replace('"schema_version": 1', '"schema_version": NaN'))
        refused(self, "NaN", M.load_mapping, str(path))
        refused(self, "not valid", M.load_mapping, str(write(self.tmp / "bad.json", "{")))
        refused(self, "not valid", M.load_mapping, str(write(self.tmp / "latin.json", b"{\"a\": \"\xe9\"}")))
        refused(self, "JSON object", M.load_mapping, str(write(self.tmp / "list.json", "[]")))
        refused(self, "larger than", M.load_mapping, str(write(self.tmp / "big.json", "[" + " " * M.MAX_MAPPING_BYTES + "]")))
        refused(self, "neither a built-in name", M.load_mapping, "no-such-mapping")

    def test_a_built_in_name_cannot_be_a_path_and_a_link_is_not_read(self) -> None:
        refused(self, "neither a built-in name", M.load_mapping, "../instantiation/mappings/openspec")
        target = write(self.tmp / "real.json", json.dumps(VALID))
        link = self.tmp / "link.json"
        if not make_link(link, target):
            self.skipTest("this account cannot create a symbolic link or junction to a file")
        refused(self, "symbolic link", M.load_mapping, str(link))


class LinkDetectionTests(TempCase):
    def test_a_symbolic_link_mode_and_a_windows_reparse_point_are_both_links_and_a_plain_file_is_not(self) -> None:
        import stat as stat_module
        from types import SimpleNamespace

        plain = write(self.tmp / "plain.md", "x")
        self.assertFalse(M.is_link(str(plain)))
        for attributes in (
            SimpleNamespace(st_mode=stat_module.S_IFLNK | 0o777, st_file_attributes=0),
            SimpleNamespace(st_mode=stat_module.S_IFDIR | 0o777, st_file_attributes=0x400),
        ):
            with mock.patch.object(M.os, "lstat", lambda path, attributes=attributes: attributes):
                self.assertTrue(M.is_link(str(plain)))
        with mock.patch.object(M.os, "lstat", lambda path: SimpleNamespace(st_mode=stat_module.S_IFREG | 0o644, st_file_attributes=0x20)):
            self.assertFalse(M.is_link(str(plain)))

    def test_a_matching_link_is_refused_by_expand_even_when_the_account_cannot_make_one(self) -> None:
        write(self.input / "plan.md", PLAN)
        real = os.lstat

        class Fake:
            st_mode = 0o120777
            st_file_attributes = 0

        def lstat(path):
            return Fake() if str(path).endswith("plan.md") else real(path)

        with mock.patch.object(M.os, "lstat", lstat):
            refused(self, "plan.md' is a symbolic link or junction", M.expand, str(self.input), "plan.md")


    def test_a_mapping_file_that_is_a_link_is_refused_even_when_the_account_cannot_make_one(self) -> None:
        path = write(self.tmp / "mapping.json", json.dumps(VALID))
        with mock.patch.object(M, "is_link", lambda candidate: candidate == str(path)):
            refused(self, "symbolic link", M.load_mapping, str(path))

    def test_a_pattern_is_matched_with_the_case_it_is_written_in(self) -> None:
        write(self.input / "Plan.md", PLAN)
        self.assertEqual([], M.expand(str(self.input), "plan.md"))
        self.assertEqual(["Plan.md"], [os.path.basename(path) for path in M.expand(str(self.input), "Plan.md")])

    def test_a_built_in_name_is_never_read_as_a_file_of_the_current_folder(self) -> None:
        write(self.tmp / "openspec", json.dumps(VALID))
        previous = os.getcwd()
        os.chdir(self.tmp)
        try:
            self.assertEqual("openspec", M.load_mapping("openspec")["name"])
        finally:
            os.chdir(previous)

    def test_a_folder_name_with_an_unsafe_character_is_refused_for_the_change_id(self) -> None:
        unsafe = self.tmp / "in`put"
        try:
            write(unsafe / "plan.md", PLAN)
        except OSError:
            self.skipTest("this file system refuses a backtick in a name")
        refused(self, "folder name", M.change_id, str(unsafe), VALID)


class OperationTests(unittest.TestCase):
    def test_a_section_is_found_by_its_whole_heading_and_a_block_by_the_start_of_its_heading_only(self) -> None:
        text = "## Outcomes\n\nplural\n\n## Outcome\n\nsingular\n\n### Not a Requirement: x\n\nmid\n\n### Requirement: y\n\nreal\n"
        self.assertEqual(["## Outcome\n\nsingular\n\n### Not a Requirement: x\n\nmid\n\n### Requirement: y\n\nreal"], M.op_section(text, "Outcome"))
        self.assertEqual(["### Requirement: y\n\nreal"], M.op_blocks(text, "Requirement:"))
        self.assertEqual([], M.op_section(text, "Outcom"))

    def test_file_returns_the_whole_text_without_the_outer_blank_lines(self) -> None:
        self.assertEqual(["# A\n\ntext"], M.op_file("\n# A\n\ntext\n\n"))
        self.assertEqual([], M.op_file("  \n\n"))

    def test_section_returns_the_heading_and_everything_below_it_down_to_the_next_heading_of_its_level_or_higher(self) -> None:
        text = "# T\n\n## A\n\nalpha\n\n### A1\n\nnested\n\n## B\n\nbeta\n"
        self.assertEqual(["## A\n\nalpha\n\n### A1\n\nnested"], M.op_section(text, "A"))
        self.assertEqual(["### A1\n\nnested"], M.op_section(text, "A1"))
        self.assertEqual(["## B\n\nbeta"], M.op_section(text, "B"))
        self.assertEqual([], M.op_section(text, "C"))
        self.assertEqual([], M.op_section(text, "a"))

    def test_section_takes_the_first_match_and_ignores_a_heading_inside_a_fenced_block(self) -> None:
        text = "## A\n\n```\n## A\n# not a heading\n```\n\nstill A\n\n## A\n\nsecond\n"
        self.assertEqual(["## A\n\n```\n## A\n# not a heading\n```\n\nstill A"], M.op_section(text, "A"))
        self.assertEqual([], M.op_section("```\n## A\n```\n", "A"))

    def test_blocks_returns_every_block_that_starts_with_the_prefix_in_document_order(self) -> None:
        text = "## Req\n\n### Requirement: one\n\ntext 1\n\n#### Scenario: s\n\nwhen\n\n### Other\n\nx\n\n### Requirement: two\n\ntext 2\n"
        self.assertEqual(
            ["### Requirement: one\n\ntext 1\n\n#### Scenario: s\n\nwhen", "### Requirement: two\n\ntext 2"],
            M.op_blocks(text, "Requirement:"),
        )
        self.assertEqual(["#### Scenario: s\n\nwhen"], M.op_blocks(text, "Scenario:"))
        self.assertEqual([], M.op_blocks(text, "Nothing"))

    def test_blocks_does_not_repeat_a_block_that_lies_inside_an_earlier_one(self) -> None:
        text = "## Req one\n\n### Req nested\n\nx\n\n## Req two\n\ny\n"
        self.assertEqual(["## Req one\n\n### Req nested\n\nx", "## Req two\n\ny"], M.op_blocks(text, "Req"))

    def test_checklist_returns_each_checkbox_line_and_nothing_else(self) -> None:
        text = "- plain\n- [ ] one\n  * [x] two\n+ [X] three\n- [ ]\n- [ ]x\n```\n- [ ] fenced\n```\n1. [ ] numbered\n- [ ] four   \n"
        self.assertEqual(["- [ ] one", "  * [x] two", "+ [X] three", "- [ ] four"], M.op_checklist(text))

    def test_the_rule_dispatch_names_each_operation(self) -> None:
        text = "## A\n\n- [ ] t\n"
        self.assertEqual(["## A\n\n- [ ] t"], M.run_operation({"operation": "file"}, text))
        self.assertEqual(["## A\n\n- [ ] t"], M.run_operation({"operation": "section", "heading": "A"}, text))
        self.assertEqual(["## A\n\n- [ ] t"], M.run_operation({"operation": "blocks", "prefix": "A"}, text))
        self.assertEqual(["- [ ] t"], M.run_operation({"operation": "checklist"}, text))

    def test_a_rule_limit_keeps_the_first_passages_across_files_in_sorted_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "plan.md", "# P\n")
            write(root / "b.md", "- [ ] b1\n- [ ] b2\n")
            write(root / "a.md", "- [ ] a1\n- [ ] a2\n")
            mapping = {
                "schema_version": 1,
                "name": "limited",
                "detect": ["plan.md"],
                "id_from": "plan.md",
                "rules": [{"source": "*.md", "operation": "checklist", "target": "declared_scope", "limit": 3}],
            }
            supplied, read = M.collect(str(root), M.validate_mapping(mapping))
            self.assertEqual([("a.md", "checklist", ["- [ ] a1", "- [ ] a2"]), ("b.md", "checklist", ["- [ ] b1"])], supplied["declared_scope"])
            self.assertEqual(["a.md", "b.md"], read)


class GoldenDraftTests(TempCase):
    def test_each_built_in_mapping_reproduces_its_expected_draft_byte_for_byte(self) -> None:
        for name, folder in GOLDEN.items():
            out = self.tmp / (name + ".md")
            M.make_draft(name, str(FIXTURES / folder), str(out))
            self.assertEqual(lf(FIXTURES / (name + "-expected.md")), out.read_bytes(), name)

    def test_the_real_openspec_and_speckit_inputs_are_the_reading_test_outputs(self) -> None:
        reading = ROOT / "verification" / "spec-tool-bakeoff" / "reading-test" / "artifacts"
        compared = 0
        for ours, theirs in (("openspec-input", "openspec"), ("speckit-input", "speckit")):
            for path in sorted((FIXTURES / ours).rglob("*")):
                other = reading / theirs / path.relative_to(FIXTURES / ours)
                if path.is_file() and other.is_file():
                    self.assertEqual(lf(other), lf(path), str(path))
                    compared += 1
        if not compared:
            self.skipTest("the reading test's outputs are not in this tree (a published copy leaves them out)")

    def test_the_draft_claims_only_what_the_source_says(self) -> None:
        for name, folder in GOLDEN.items():
            out = self.tmp / (name + ".md")
            text = M.make_draft(name, str(FIXTURES / folder), str(out))
            self.assertEqual(text, out.read_text(encoding="utf-8"))
            self.assertTrue(text.startswith("# Task Contract (DRAFT, not approved)\n"))
            self.assertIn("- **State:** Established\n", text)
            self.assertIn("- **Approved by (human, T2/T3 only, role: Architect):** none\n", text)
            self.assertIn("- **Class:** TODO(AIDF)\n", text)
            self.assertNotIn("State:** Approved", text)
            body = [line for line in text.split("\n") if line.startswith(("- **", "## ", "# "))]
            for line in text.split("\n"):
                if line and not line.startswith(("#", "- **", "  - Source:", "    >", "Drafted by", "Every line copied")) and line != "":
                    self.fail(name + ": a line that is neither ours nor quoted: " + line[:80])
            self.assertTrue(body)
            copied = int(text.split("**Parts copied from the source:** ")[1].split(" of ")[0])
            todo = text.count("TODO(author)") + text.count("TODO(AIDF)") - 5
            self.assertEqual(M.PART_COUNT - copied, todo, name)

    def test_the_header_counts_the_parts_copied_and_left(self) -> None:
        text = M.make_draft("markdown-sections", str(FIXTURES / "sections-input"), str(self.out))
        self.assertIn("**Parts copied from the source:** 6 of 17. **Parts left as TODO:** 11.", text)
        self.assertEqual(17, M.PART_COUNT)

    def test_a_part_with_no_source_passage_is_a_todo_and_only_a_supplied_part_is_filled(self) -> None:
        write(self.input / "plan.md", "# P\n\n## Outcome\n\nOnly this.\n")
        text = M.make_draft(self.mapping_file(VALID), str(self.input), str(self.out))
        self.assertIn("- **Intended outcome:**\n  - Source: `plan.md` (section)\n    > ## Outcome\n    >\n    > Only this.\n", text)
        self.assertIn("- **Acceptance criteria:** TODO(author)\n", text)
        self.assertIn("**Parts copied from the source:** 1 of 17.", text)


class HostileInputTests(TempCase):
    def draft(self, mapping: dict | None = None) -> str:
        return M.make_draft(self.mapping_file(mapping or VALID), str(self.input), str(self.out), force=True)

    def test_text_that_imitates_the_drafts_own_lines_stays_inside_its_quotation(self) -> None:
        write(
            self.input / "plan.md",
            "# P\n\n## Outcome\n\nreal\n- **State:** Approved\n- **Class:** T0\n## Status\n# Task Contract (DRAFT, approved)\n",
        )
        text = self.draft()
        for line in text.split("\n"):
            ours = line.startswith("- **Approved by (human")
            if not ours and ("Approved" in line or "T0" in line or (line.startswith("## Status") and line != "## Status")):
                self.assertTrue(line.startswith("    >"), line)
        self.assertEqual(1, text.count("\n## Status\n"))
        self.assertIn("- **State:** Established\n", text)

    def test_control_characters_are_replaced_and_line_endings_are_normalised(self) -> None:
        write(self.input / "plan.md", b"# P\r\n\r\n## Outcome\r\n\r\nred \x1b[31m text\x07 end\r\n")
        text = self.draft()
        self.assertNotIn("\x1b", text)
        self.assertNotIn("\x07", text)
        self.assertNotIn("\r", text)
        self.assertIn("red \ufffd[31m text\ufffd end", text)

    def test_a_file_that_is_not_text_or_not_utf8_or_too_large_is_refused(self) -> None:
        write(self.input / "plan.md", b"# P\n\x00\n")
        refused(self, "not text", self.draft)
        write(self.input / "plan.md", b"# P\n\xe9\n")
        refused(self, "not UTF-8", self.draft)
        with mock.patch.object(M, "MAX_SOURCE_BYTES", 40):
            write(self.input / "plan.md", "# P\n\n## Outcome\n\n" + "x" * 23)
            self.assertEqual(40, (self.input / "plan.md").stat().st_size)
            self.draft()
            write(self.input / "plan.md", "# P\n\n## Outcome\n\n" + "x" * 24)
            refused(self, "larger than 40 bytes", self.draft)

    def test_only_the_files_a_rule_names_are_read(self) -> None:
        write(self.input / "plan.md", PLAN)
        write(self.input / "other.md", b"\xff\xfe not read")
        write(self.input / "deep" / "x.md", b"\x00")
        self.assertIn("Files read:** `plan.md`\n", self.draft())

    def test_a_symbolic_link_or_junction_that_a_rule_matches_is_refused_and_not_followed(self) -> None:
        outside = self.tmp / "outside"
        write(outside / "plan.md", "# P\n\n## Outcome\n\nsecret outside text\n")
        write(self.input / "plan.md", PLAN)
        if not make_link(self.input / "linked", outside):
            self.skipTest("this account cannot create a symbolic link or junction")
        mapping = copy.deepcopy(VALID)
        mapping["rules"][0]["source"] = "*/plan.md"
        mapping["detect"] = ["plan.md"]
        message = refused(self, "symbolic link or junction", self.draft, mapping)
        self.assertIn("linked", message)
        self.assertFalse(self.out.exists())

    def test_a_link_to_a_file_is_refused(self) -> None:
        real = write(self.tmp / "real.md", PLAN)
        if not make_link(self.input / "plan.md", real):
            self.skipTest("this account cannot create a symbolic link to a file")
        refused(self, "symbolic link", self.draft)

    def test_the_input_folder_itself_must_not_be_a_link_or_missing(self) -> None:
        real = self.tmp / "real"
        write(real / "plan.md", PLAN)
        link = self.tmp / "linked-input"
        if make_link(link, real):
            refused(self, "not a folder", M.make_draft, self.mapping_file(VALID), str(link), str(self.out))
        refused(self, "not a folder", M.make_draft, self.mapping_file(VALID), str(self.tmp / "missing"), str(self.out))
        refused(self, "not a folder", M.make_draft, self.mapping_file(VALID), str(real / "plan.md"), str(self.out))

    def test_a_file_name_with_a_character_outside_the_safe_set_is_refused(self) -> None:
        write(self.input / "plan.md", PLAN)
        try:
            write(self.input / "odd`name.md", "# x\n")
        except OSError:
            self.skipTest("this file system refuses a backtick in a name")
        mapping = copy.deepcopy(VALID)
        mapping["rules"][0]["source"] = "*.md"
        refused(self, "has a character outside", self.draft, mapping)

    def test_a_folder_that_does_not_fit_the_mapping_is_refused_naming_the_pattern(self) -> None:
        write(self.input / "other.md", "# x\n")
        refused(self, "no file matches 'plan.md'", self.draft)

    def test_the_change_id_needs_exactly_one_file(self) -> None:
        write(self.input / "a" / "plan.md", PLAN)
        write(self.input / "b" / "plan.md", PLAN)
        mapping = copy.deepcopy(VALID)
        mapping["id_from"] = "*/plan.md"
        mapping["detect"] = ["*/plan.md"]
        mapping["rules"][0]["source"] = "*/plan.md"
        refused(self, "matches 2 files", self.draft, mapping)

    def test_the_change_id_is_the_folder_that_holds_the_file_or_the_input_folder(self) -> None:
        write(self.input / "plan.md", PLAN)
        self.assertEqual(("input", "plan.md"), M.change_id(str(self.input), VALID))
        write(self.tmp / "in2" / "x-change" / "plan.md", PLAN)
        mapping = {**VALID, "id_from": "*/plan.md"}
        self.assertEqual(("x-change", "x-change/plan.md"), M.change_id(str(self.tmp / "in2"), mapping))


class OutputTests(TempCase):
    def setUp(self) -> None:
        super().setUp()
        write(self.input / "plan.md", PLAN)
        self.mapping = self.mapping_file(VALID)

    def test_an_output_inside_the_input_folder_is_refused_and_nothing_is_written(self) -> None:
        refused(self, "inside the input folder", M.make_draft, self.mapping, str(self.input), str(self.input / "draft.md"))
        refused(self, "inside the input folder", M.make_draft, self.mapping, str(self.input), str(self.input / "sub" / ".." / "draft.md"))
        self.assertEqual(["plan.md"], sorted(item.name for item in self.input.iterdir()))

    def test_an_output_inside_the_input_folder_is_refused_in_every_spelling_of_the_path(self) -> None:
        if os.name != "nt":
            self.skipTest("the extended-length prefix is a Windows spelling")
        inside = os.path.abspath(str(self.input / "new.md"))
        for spelling in ("\\\\?\\" + inside, "//?/" + inside.replace("\\", "/"), inside.upper(), inside.replace("\\", "/")):
            refused(self, "inside the input folder", M.make_draft, self.mapping, str(self.input), spelling)
            self.assertFalse((self.input / "new.md").exists(), spelling)
        before = (self.input / "plan.md").read_bytes()
        refused(self, "inside the input folder", M.make_draft, self.mapping, str(self.input), "\\\\?\\" + os.path.abspath(str(self.input / "plan.md")), True)
        self.assertEqual(before, (self.input / "plan.md").read_bytes())

    def test_an_output_that_names_a_file_system_stream_is_refused_and_nothing_is_written(self) -> None:
        if os.name != "nt":
            self.skipTest("file-system streams are a Windows feature")
        for spelling in (str(self.input) + ":draft", str(self.input / "plan.md") + ":draft", str(self.input / "plan.md") + "::$DATA", "\\\\?\\" + os.path.abspath(str(self.input)) + ":draft"):
            if os.name != "nt" and "\\\\?\\" in spelling:
                continue
            refused(self, "stream", M.make_draft, self.mapping, str(self.input), spelling, True)
        self.assertEqual(["plan.md"], sorted(item.name for item in self.input.iterdir()))
        self.assertEqual(PLAN, (self.input / "plan.md").read_text(encoding="utf-8"))

    def test_an_output_that_is_a_hard_link_to_a_planning_file_is_not_replaced_even_with_force(self) -> None:
        link = self.tmp / "linked-draft.md"
        try:
            os.link(self.input / "plan.md", link)
        except (OSError, NotImplementedError):
            self.skipTest("this file system cannot make a hard link")
        refused(self, "more than one name", M.make_draft, self.mapping, str(self.input), str(link), True)
        self.assertEqual(PLAN, (self.input / "plan.md").read_text(encoding="utf-8"))

    def test_an_output_on_another_drive_or_beside_the_input_folder_is_allowed_and_an_unknown_path_form_is_refused(self) -> None:
        sibling = self.tmp / "input-two"
        sibling.mkdir()
        M.make_draft(self.mapping, str(self.input), str(sibling / "draft.md"))
        self.assertTrue((sibling / "draft.md").is_file())
        with mock.patch.object(M.os.path, "realpath", lambda path: "\\\\?\\UNC\\host\\share\\x"):
            refused(self, "not supported", M.plain_path, "x")

    def test_an_existing_output_is_refused_without_force_and_left_untouched(self) -> None:
        write(self.out, "keep")
        refused(self, "use --force", M.make_draft, self.mapping, str(self.input), str(self.out))
        self.assertEqual("keep", self.out.read_text(encoding="utf-8"))
        M.make_draft(self.mapping, str(self.input), str(self.out), force=True)
        self.assertTrue(self.out.read_text(encoding="utf-8").startswith("# Task Contract (DRAFT"))

    def test_an_output_that_is_a_folder_a_link_or_in_a_missing_folder_is_refused(self) -> None:
        refused(self, "not a regular file", M.make_draft, self.mapping, str(self.input), str(self.tmp), True)
        refused(self, "does not exist", M.make_draft, self.mapping, str(self.input), str(self.tmp / "nope" / "draft.md"))
        real = write(self.tmp / "real.md", "keep")
        if make_link(self.tmp / "link.md", real):
            refused(self, "not a regular file", M.make_draft, self.mapping, str(self.input), str(self.tmp / "link.md"), True)
            self.assertEqual("keep", real.read_text(encoding="utf-8"))

    def test_the_draft_is_written_as_utf8_with_line_feeds_and_one_final_newline(self) -> None:
        M.make_draft(self.mapping, str(self.input), str(self.out))
        data = self.out.read_bytes()
        self.assertNotIn(b"\r", data)
        self.assertTrue(data.endswith(b"TODO(AIDF)\n"))
        data.decode("utf-8")


class DeterminismTests(TempCase):
    def test_the_same_input_gives_the_same_bytes_whatever_order_the_file_system_lists_files(self) -> None:
        first = self.tmp / "first.md"
        second = self.tmp / "second.md"
        M.make_draft("openspec", str(FIXTURES / "openspec-input"), str(first))
        real = os.listdir
        with mock.patch.object(M.os, "listdir", lambda path: list(reversed(real(path)))):
            M.make_draft("openspec", str(FIXTURES / "openspec-input"), str(second))
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_a_rule_that_matches_several_files_lists_them_in_sorted_order(self) -> None:
        write(self.input / "plan.md", "# P\n")
        for name in ("c.md", "a.md", "b.md"):
            write(self.input / name, "- [ ] " + name + "\n")
        real = os.listdir
        with mock.patch.object(M.os, "listdir", lambda path: list(reversed(real(path)))):
            found = M.expand(str(self.input), "?.md")
        self.assertEqual(["a.md", "b.md", "c.md"], [os.path.basename(path) for path in found])


class NoExecutionTests(unittest.TestCase):
    def test_the_tool_imports_only_the_standard_modules_it_needs_and_calls_nothing_that_runs_code(self) -> None:
        tree = ast.parse((ROOT / "verification" / "spec_mapper.py").read_text(encoding="utf-8"))
        imported = set()
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
            elif isinstance(node, ast.Call):
                func = node.func
                calls.add(func.id if isinstance(func, ast.Name) else getattr(func, "attr", ""))
        self.assertEqual({"__future__", "argparse", "fnmatch", "json", "os", "re", "stat", "sys", "pathlib", "typing"}, imported)
        self.assertEqual(set(), calls & {"eval", "exec", "__import__", "system", "popen", "run", "Popen", "urlopen", "connect", "load", "loads_unsafe"})
        self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "compile" for n in ast.walk(tree)))

    def test_the_tool_opens_a_file_for_writing_in_one_place_only(self) -> None:
        tree = ast.parse((ROOT / "verification" / "spec_mapper.py").read_text(encoding="utf-8"))
        writes = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "open" and len(node.args) > 1 and getattr(node.args[1], "value", "") not in ("rb",)
        ]
        self.assertEqual(1, len(writes))
        self.assertEqual("w", writes[0].args[1].value)


class CommandTests(TempCase):
    def test_exit_code_zero_writes_the_draft_and_two_refuses_with_a_message(self) -> None:
        write(self.input / "plan.md", PLAN)
        code, err = self.run_main("--mapping", self.mapping_file(VALID), "--input", str(self.input), "--out", str(self.out))
        self.assertEqual((0, ""), (code, err))
        self.assertTrue(self.out.is_file())
        before = self.out.read_bytes()
        code, err = self.run_main("--mapping", self.mapping_file(VALID), "--input", str(self.input), "--out", str(self.out))
        self.assertEqual(2, code)
        self.assertTrue(err.startswith("spec_mapper: refused: output: "))
        self.assertEqual(before, self.out.read_bytes())

    def test_a_refused_run_writes_nothing(self) -> None:
        write(self.input / "other.md", "x")
        code, err = self.run_main("--mapping", self.mapping_file(VALID), "--input", str(self.input), "--out", str(self.out))
        self.assertEqual(2, code)
        self.assertIn("no file matches", err)
        self.assertFalse(self.out.exists())

    def test_the_command_runs_as_a_script_and_a_built_in_name_works(self) -> None:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        done = subprocess.run(
            [sys.executable, str(ROOT / "verification" / "spec_mapper.py"), "--mapping", "markdown-sections", "--input", str(FIXTURES / "sections-input"), "--out", str(self.out)],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertEqual(lf(FIXTURES / "markdown-sections-expected.md"), self.out.read_bytes())
        done = subprocess.run([sys.executable, str(ROOT / "verification" / "spec_mapper.py"), "--mapping", "nope", "--input", str(self.tmp), "--out", str(self.out)], capture_output=True, text=True, env=env, check=False)
        self.assertEqual(2, done.returncode)


class GuideTests(unittest.TestCase):
    def test_the_guide_has_the_section_with_the_exact_command_and_says_what_a_draft_is_not(self) -> None:
        guide = (ROOT / "instantiation" / "spec-tools.md").read_text(encoding="utf-8")
        self.assertIn("python verification/spec_mapper.py --mapping <name or file> --input <folder> --out <draft.md>", guide)
        section = guide.split("## 8. Drafting a Task Contract with the mapper", 1)[1]
        for phrase in ("not an approval", "not a classification", "not evidence", "openspec", "speckit", "kiro-synthetic", "markdown-sections"):
            self.assertIn(phrase, section)


if __name__ == "__main__":
    unittest.main()
