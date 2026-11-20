"""Reference transform for M0-TRANSFORM-01: rename ROLE_RANK to ROLE_LEVEL and nothing else.

make_diff(root) returns the unified diff, as text with LF line ends, that the transform produces for the
reference application at root. The candidate's expected answer is that diff, byte for byte (expected.diff).
"""
import difflib
import pathlib
import re

OLD = "ROLE_RANK"
NEW = "ROLE_LEVEL"
PATTERN = re.compile(rf"\b{OLD}\b")
SKIP_DIRS = {"cases", "__pycache__"}
SKIP_FILES = {"test_cases_m0.py"}


def _read(path):
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def candidates(root):
    for path in sorted(pathlib.Path(root).rglob("*")):
        rel = path.relative_to(root)
        if not path.is_file() or SKIP_DIRS & set(rel.parts) or path.name in SKIP_FILES:
            continue
        if path.suffix in {".py", ".md"}:
            yield rel, path


def transform(root):
    """Map each changed relative path (posix) to its new text."""
    changed = {}
    for rel, path in candidates(root):
        before = _read(path)
        after = PATTERN.sub(NEW, before)
        if after != before:
            changed[rel.as_posix()] = (before, after)
    return changed


def make_diff(root):
    parts = []
    for name, (before, after) in sorted(transform(root).items()):
        parts.extend(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile=f"a/{name}", tofile=f"b/{name}", n=3))
    return "".join(parts)


def apply(root):
    """Write the transform into root (used on a throwaway copy)."""
    for name, (_, after) in transform(root).items():
        pathlib.Path(root, name).write_bytes(after.encode("utf-8"))
