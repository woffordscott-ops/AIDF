"""Draft a Task Contract from a team's planning files and a mapping file.

    python verification/spec_mapper.py --mapping <built-in name or file> --input <folder> --out <draft.md> [--force]

The input folder is untrusted data. The tool reads only the files that a rule of the mapping names, inside that
folder, follows no symbolic link or junction, reads no file above a size limit, runs nothing and uses no network.
It writes one file, the draft. Exit code 0: written. Exit code 2: refused, with a message on stderr.

The draft copies what the sources say, every copied line inside a quotation with its source file named, and writes
TODO(author) or TODO(AIDF) for every part that only a person or AIDF can fill. It never writes Approved and never
chooses a class.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any, NoReturn

MAX_SOURCE_BYTES = 262_144
MAX_MAPPING_BYTES = 65_536
MAX_RULES = 64
MAX_LIMIT = 1_000
SCHEMA_VERSION = 1
MAPPINGS_DIR = Path(__file__).resolve().parent.parent / "instantiation" / "mappings"

TARGETS = (
    "opening_problem",
    "opening_change",
    "opening_technical",
    "intended_outcome",
    "acceptance_criteria",
    "declared_scope",
    "approach",
    "dependency_changes",
)
OPERATIONS = ("file", "section", "blocks", "checklist")
MAPPING_KEYS = ("schema_version", "name", "detect", "rules", "id_from")
RULE_KEYS = ("source", "operation", "heading", "prefix", "target", "limit")
RULE_REQUIRED = ("source", "operation", "target")
OPERATION_EXTRA_KEY = {"file": None, "section": "heading", "blocks": "prefix", "checklist": None}

PATTERN_SEGMENT = re.compile(r"[A-Za-z0-9._ *?-]+")
SAFE_PATH = re.compile(r"[A-Za-z0-9._ /-]+")
BUILTIN_NAME = re.compile(r"[a-z0-9-]+")
HEADING = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")
FENCE = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})")
CHECKBOX = re.compile(r"^[ \t]*[-*+][ \t]+\[[ xX]\][ \t]+\S")
CONTROL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
REPARSE_POINT = 0x400

# the parts of the draft, in order: (key, label). A key in TARGETS is filled from a source; the others are TODO(AIDF).
OPENING = (
    ("read_first", "Read this first", "TODO(author)"),
    ("opening_problem", "Problem", "TODO(author)"),
    ("why_it_matters", "Why it matters", "TODO(author)"),
    ("opening_change", "The change", "TODO(author)"),
    ("opening_technical", "Technical details", "TODO(author)"),
    ("decide", "What you need to decide", "TODO(author)"),
)
PART_A = (
    ("intended_outcome", "Intended outcome", "TODO(author)"),
    ("acceptance_criteria", "Acceptance criteria", "TODO(author)"),
    ("declared_scope", "Declared scope", "TODO(author)"),
    ("outcome_records", "Outcome records", "TODO(AIDF)"),
)
PART_B = (
    ("approach", "Approach", "TODO(author)"),
    ("invariants", "Invariants touched", "TODO(AIDF)"),
    ("evidence_strategy", "Evidence strategy", "TODO(AIDF)"),
    ("protected_files", "Protected files touched", "TODO(AIDF)"),
    ("recovery", "Recovery / reversal approach", "TODO(AIDF)"),
    ("review_budget", "Review budget", "TODO(AIDF)"),
    ("dependency_changes", "Dependency changes", "TODO(AIDF)"),
)
STATUS = (
    ("State", "Established"),
    ("Established by (author)", "TODO(author)"),
    ("Approved by (human, T2/T3 only, role: Architect)", "none"),
    ("Date", "TODO(author)"),
    ("Class", "TODO(AIDF)"),
    ("Spec Confidence at intake", "TODO(AIDF)"),
    ("Re-evaluated to Clear by", "TODO(AIDF)"),
)
PART_COUNT = len(OPENING) + len(PART_A) + len(PART_B)


class Refused(Exception):
    """The input, the mapping or the output is not acceptable; nothing is written."""


def refuse(message: str) -> NoReturn:
    raise Refused(message)


# ---------------------------------------------------------------- the mapping


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            refuse("mapping: duplicate key '" + key + "'")
        result[key] = value
    return result


def _no_constant(name: str) -> NoReturn:
    refuse("mapping: the value " + name + " is not allowed")


def check_pattern(pattern: Any, where: str) -> str:
    if not isinstance(pattern, str) or not pattern or len(pattern) > 200:
        refuse(where + ": must be a non-empty string of at most 200 characters")
    if pattern.startswith("/") or "\\" in pattern or ":" in pattern:
        refuse(where + ": '" + pattern + "' must be a relative path with '/' separators")
    for segment in pattern.split("/"):
        if segment in ("", ".", ".."):
            refuse(where + ": '" + pattern + "' leaves or doubles the folder (segment '" + segment + "')")
        if segment == "**" or not PATTERN_SEGMENT.fullmatch(segment):
            refuse(where + ": '" + pattern + "' has a segment that is not a name with * or ? (segment '" + segment + "')")
    return pattern


def validate_mapping(raw: Any) -> dict[str, Any]:
    """Return the mapping when it has exactly the closed shape, otherwise refuse with the key at fault."""
    if not isinstance(raw, dict):
        refuse("mapping: must be a JSON object")
    for key in raw:
        if key not in MAPPING_KEYS:
            refuse("mapping: unknown key '" + str(key) + "'")
    for key in MAPPING_KEYS:
        if key not in raw:
            refuse("mapping: missing key '" + key + "'")
    if raw["schema_version"] != SCHEMA_VERSION or isinstance(raw["schema_version"], bool):
        refuse("mapping: key 'schema_version' must be " + str(SCHEMA_VERSION))
    if not isinstance(raw["name"], str) or not BUILTIN_NAME.fullmatch(raw["name"]):
        refuse("mapping: key 'name' must be lower-case letters, digits and '-'")
    detect = raw["detect"]
    if not isinstance(detect, list) or not 1 <= len(detect) <= MAX_RULES:
        refuse("mapping: key 'detect' must be a list of 1 to " + str(MAX_RULES) + " file patterns")
    for index, pattern in enumerate(detect):
        check_pattern(pattern, "mapping: detect[" + str(index) + "]")
    check_pattern(raw["id_from"], "mapping: key 'id_from'")
    rules = raw["rules"]
    if not isinstance(rules, list) or not 1 <= len(rules) <= MAX_RULES:
        refuse("mapping: key 'rules' must be a list of 1 to " + str(MAX_RULES) + " rules")
    for index, rule in enumerate(rules):
        where = "mapping: rules[" + str(index) + "]"
        if not isinstance(rule, dict):
            refuse(where + " must be an object")
        for key in rule:
            if key not in RULE_KEYS:
                refuse(where + ": unknown key '" + str(key) + "'")
        for key in RULE_REQUIRED:
            if key not in rule:
                refuse(where + ": missing key '" + key + "'")
        check_pattern(rule["source"], where + ": key 'source'")
        operation = rule["operation"]
        if operation not in OPERATIONS:
            refuse(where + ": key 'operation' must be one of " + ", ".join(OPERATIONS))
        if rule["target"] not in TARGETS:
            refuse(where + ": key 'target' must be one of " + ", ".join(TARGETS))
        needed = OPERATION_EXTRA_KEY[operation]
        for key in ("heading", "prefix"):
            if key == needed:
                if not isinstance(rule.get(key), str) or not rule[key].strip() or len(rule[key]) > 200:
                    refuse(where + ": operation '" + operation + "' needs key '" + key + "' as a non-empty string")
            elif key in rule:
                refuse(where + ": key '" + key + "' is not used by operation '" + operation + "'")
        if "limit" in rule and (not isinstance(rule["limit"], int) or isinstance(rule["limit"], bool) or not 1 <= rule["limit"] <= MAX_LIMIT):
            refuse(where + ": key 'limit' must be a whole number from 1 to " + str(MAX_LIMIT))
    return raw


def load_mapping(reference: str) -> dict[str, Any]:
    """A built-in name (instantiation/mappings/<name>.json) or the path of a mapping file."""
    if BUILTIN_NAME.fullmatch(reference) and (MAPPINGS_DIR / (reference + ".json")).is_file():
        path = MAPPINGS_DIR / (reference + ".json")
    else:
        path = Path(reference)
        if not path.is_file():
            built_in = sorted(item.stem for item in MAPPINGS_DIR.glob("*.json")) if MAPPINGS_DIR.is_dir() else []
            refuse("mapping: '" + reference + "' is neither a built-in name (" + ", ".join(built_in) + ") nor a file")
    if is_link(str(path)):
        refuse("mapping: a symbolic link or junction is not read")
    if path.stat().st_size > MAX_MAPPING_BYTES:
        refuse("mapping: larger than " + str(MAX_MAPPING_BYTES) + " bytes")
    try:
        text = path.read_bytes().decode("utf-8")
        raw = json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_no_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        refuse("mapping: not valid UTF-8 JSON (" + type(error).__name__ + ")")
    return validate_mapping(raw)


# ---------------------------------------------------------------- reading the input folder


def is_link(path: str) -> bool:
    attributes = os.lstat(path)
    return stat.S_ISLNK(attributes.st_mode) or bool(getattr(attributes, "st_file_attributes", 0) & REPARSE_POINT)


def expand(root: str, pattern: str) -> list[str]:
    """The files under root whose path matches the pattern segment by segment, in sorted order. A link that matches is refused."""
    found: list[str] = []

    def walk(directory: str, segments: list[str]) -> None:
        for name in sorted(os.listdir(directory)):
            if not fnmatch.fnmatchcase(name, segments[0]):
                continue
            path = os.path.join(directory, name)
            if is_link(path):
                refuse("input: '" + os.path.relpath(path, root).replace(os.sep, "/") + "' is a symbolic link or junction")
            if len(segments) > 1:
                if os.path.isdir(path):
                    walk(path, segments[1:])
            elif os.path.isfile(path):
                found.append(path)

    walk(root, pattern.split("/"))
    return found


def relative(root: str, path: str) -> str:
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    if not SAFE_PATH.fullmatch(rel):
        refuse("input: the file name '" + rel.encode("ascii", "backslashreplace").decode("ascii") + "' has a character outside letters, digits, '.', '_', ' ' and '-'")
    return rel


def read_text(root: str, path: str) -> str:
    rel = relative(root, path)
    attributes = os.lstat(path)
    if not stat.S_ISREG(attributes.st_mode):
        refuse("input: '" + rel + "' is not a regular file")
    if attributes.st_size > MAX_SOURCE_BYTES:
        refuse("input: '" + rel + "' is larger than " + str(MAX_SOURCE_BYTES) + " bytes")
    with open(path, "rb") as handle:
        data = handle.read(MAX_SOURCE_BYTES + 1)
    if len(data) > MAX_SOURCE_BYTES:
        refuse("input: '" + rel + "' is larger than " + str(MAX_SOURCE_BYTES) + " bytes")
    if b"\x00" in data:
        refuse("input: '" + rel + "' is not text (a NUL byte)")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        refuse("input: '" + rel + "' is not UTF-8")
    return CONTROL.sub("\ufffd", text.replace("\r\n", "\n").replace("\r", "\n"))


# ---------------------------------------------------------------- the four operations


def headings(lines: list[str]) -> list[tuple[int, int, str]]:
    """(line index, level, text) of each ATX heading outside a fenced block."""
    result: list[tuple[int, int, str]] = []
    fence = ""
    for index, line in enumerate(lines):
        marker = FENCE.match(line)
        if marker:
            if not fence:
                fence = marker.group(1)[0]
            elif marker.group(1)[0] == fence:
                fence = ""
            continue
        if fence:
            continue
        match = HEADING.match(line)
        if match:
            result.append((index, len(match.group(1)), match.group(2)))
    return result


def block(lines: list[str], found: list[tuple[int, int, str]], position: int) -> tuple[int, int]:
    """The line range of the heading at found[position] up to the next heading of the same or a higher level."""
    start, level, _ = found[position]
    end = len(lines)
    for later in found[position + 1 :]:
        if later[1] <= level:
            end = later[0]
            break
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    return start, end


def op_file(text: str) -> list[str]:
    return [text.strip("\n")] if text.strip() else []


def op_section(text: str, heading: str) -> list[str]:
    lines = text.split("\n")
    found = headings(lines)
    for position, (_, _, title) in enumerate(found):
        if title == heading:
            start, end = block(lines, found, position)
            return ["\n".join(lines[start:end])]
    return []


def op_blocks(text: str, prefix: str) -> list[str]:
    lines = text.split("\n")
    found = headings(lines)
    passages: list[str] = []
    last_end = -1
    for position, (index, _, title) in enumerate(found):
        if title.startswith(prefix) and index >= last_end:
            start, end = block(lines, found, position)
            passages.append("\n".join(lines[start:end]))
            last_end = end
    return passages


def op_checklist(text: str) -> list[str]:
    lines = text.split("\n")
    fence = ""
    passages: list[str] = []
    for line in lines:
        marker = FENCE.match(line)
        if marker:
            fence = "" if fence and marker.group(1)[0] == fence else (fence or marker.group(1)[0])
            continue
        if not fence and CHECKBOX.match(line):
            passages.append(line.rstrip())
    return passages


def run_operation(rule: dict[str, Any], text: str) -> list[str]:
    operation = rule["operation"]
    if operation == "file":
        return op_file(text)
    if operation == "section":
        return op_section(text, rule["heading"])
    if operation == "blocks":
        return op_blocks(text, rule["prefix"])
    return op_checklist(text)


# ---------------------------------------------------------------- the draft


def change_id(root: str, mapping: dict[str, Any]) -> tuple[str, str]:
    matches = expand(root, mapping["id_from"])
    if len(matches) != 1:
        refuse("input: id_from '" + mapping["id_from"] + "' matches " + str(len(matches)) + " files; exactly one is needed")
    parent = os.path.dirname(matches[0])
    name = os.path.basename(os.path.abspath(root)) if os.path.abspath(parent) == os.path.abspath(root) else os.path.basename(parent)
    if not SAFE_PATH.fullmatch(name):
        refuse("input: the folder name for the change id has a character outside letters, digits, '.', '_', ' ' and '-'")
    return name, relative(root, matches[0])


def check_detect(root: str, mapping: dict[str, Any]) -> None:
    for pattern in mapping["detect"]:
        if not expand(root, pattern):
            refuse("input: the folder does not fit mapping '" + mapping["name"] + "': no file matches '" + pattern + "'")


def collect(root: str, mapping: dict[str, Any]) -> tuple[dict[str, list[tuple[str, str, list[str]]]], list[str]]:
    """The passages per target as (source file, operation, passages), and the files read, both in a fixed order."""
    supplied: dict[str, list[tuple[str, str, list[str]]]] = {}
    read: set[str] = set()
    for rule in mapping["rules"]:
        remaining = rule.get("limit", MAX_LIMIT)
        for path in expand(root, rule["source"]):
            if remaining <= 0:
                break
            passages = run_operation(rule, read_text(root, path))[:remaining]
            if passages:
                remaining -= len(passages)
                rel = relative(root, path)
                read.add(rel)
                supplied.setdefault(rule["target"], []).append((rel, rule["operation"], passages))
    return supplied, sorted(read)


def quote(text: str) -> list[str]:
    return ["> " + line if line else ">" for line in text.split("\n")]


def render_part(chunks: list[tuple[str, str, list[str]]]) -> list[str]:
    lines: list[str] = []
    for rel, operation, passages in chunks:
        lines.append("  - Source: `" + rel + "` (" + operation + ")")
        glue = "\n" if operation == "checklist" else "\n\n"
        lines.extend("    " + line for line in quote(glue.join(passages)))
    return lines


def render_draft(mapping: dict[str, Any], identity: tuple[str, str], supplied: dict[str, list[tuple[str, str, list[str]]]], read: list[str]) -> str:
    copied = sum(1 for key, _, _ in OPENING + PART_A + PART_B if key in supplied)
    out = [
        "# Task Contract (DRAFT, not approved)",
        "",
        "Drafted by `spec_mapper` with the mapping `" + mapping["name"] + "`. A draft is not an approval, a classification or evidence: a person fills each TODO, chooses the class and has it approved before any implementation.",
        "Every line copied from a planning file sits in a quotation under its source file; nothing else in this draft comes from the sources.",
        "",
        "- **Change id:** `" + identity[0] + "` (the name of the folder that holds `" + identity[1] + "`)",
        "- **Files read:** " + ", ".join("`" + item + "`" for item in read),
        "- **Parts copied from the source:** " + str(copied) + " of " + str(PART_COUNT) + ". **Parts left as TODO:** " + str(PART_COUNT - copied) + ".",
        "",
    ]

    def emit(title: str, parts: tuple[tuple[str, str, str], ...]) -> None:
        out.extend(["## " + title, ""])
        for key, label, todo in parts:
            if key in supplied:
                out.append("- **" + label + ":**")
                out.extend(render_part(supplied[key]))
            else:
                out.append("- **" + label + ":** " + todo)
        out.append("")

    emit("Approver's opening", OPENING)
    emit("Part A: Minimal", PART_A)
    emit("Part B: Plan", PART_B)
    out.extend(["## Status", ""])
    out.extend("- **" + label + ":** " + value for label, value in STATUS)
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------- the command


EXTENDED_PREFIX = "\\\\?\\"


def plain_path(path: str) -> str:
    """The real, case-normalised form of a path; the Windows extended-length prefix of a drive path is removed and any other prefix is refused."""
    real = os.path.realpath(path)
    if real.startswith(EXTENDED_PREFIX):
        real = real[len(EXTENDED_PREFIX) :]
        if real[1:3] != ":\\":
            refuse("output: this form of path is not supported; use an ordinary path")
    if "?" in os.path.splitdrive(real)[0]:
        refuse("output: this form of path is not supported; use an ordinary path")
    return os.path.normcase(real)


def check_output(root: str, out: str, force: bool) -> None:
    if os.name == "nt" and ":" in os.path.splitdrive(os.path.abspath(out))[1]:
        refuse("output: a ':' after the drive (a file-system stream) is not supported; use an ordinary file name")
    parent = os.path.realpath(os.path.dirname(os.path.abspath(out)) or ".")
    if not os.path.isdir(parent):
        refuse("output: the folder of '" + os.path.basename(out) + "' does not exist")
    real_root = plain_path(root)
    target = plain_path(os.path.join(parent, os.path.basename(out)))
    if os.path.splitdrive(real_root)[0] == os.path.splitdrive(target)[0] and os.path.commonpath([real_root, target]) == real_root:
        refuse("output: the draft must not be written inside the input folder")
    if os.path.lexists(out):
        if is_link(out) or not os.path.isfile(out):
            refuse("output: '" + os.path.basename(out) + "' exists and is not a regular file")
        if os.stat(out).st_nlink > 1:
            refuse("output: '" + os.path.basename(out) + "' has more than one name (a hard link); it is not replaced")
        if not force:
            refuse("output: '" + os.path.basename(out) + "' exists; use --force to replace it")


def make_draft(mapping_reference: str, input_folder: str, out: str, force: bool = False) -> str:
    mapping = load_mapping(mapping_reference)
    root = os.path.abspath(input_folder)
    if not os.path.isdir(root) or is_link(root):
        refuse("input: '" + os.path.basename(root) + "' is not a folder (or is a symbolic link or junction)")
    check_output(root, out, force)
    check_detect(root, mapping)
    identity = change_id(root, mapping)
    supplied, read = collect(root, mapping)
    text = render_draft(mapping, identity, supplied, read)
    with open(out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Draft a Task Contract from planning files and a mapping.")
    parser.add_argument("--mapping", required=True, help="a built-in name (see instantiation/mappings/) or a mapping file")
    parser.add_argument("--input", required=True, help="the folder of planning files (read only)")
    parser.add_argument("--out", required=True, help="the draft to write (a new file)")
    parser.add_argument("--force", action="store_true", help="replace an existing draft")
    args = parser.parse_args(argv)
    try:
        make_draft(args.mapping, args.input, args.out, args.force)
    except Refused as error:
        print("spec_mapper: refused: " + str(error), file=sys.stderr)
        return 2
    print("spec_mapper: wrote " + os.path.basename(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
