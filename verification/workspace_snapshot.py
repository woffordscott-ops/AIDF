"""Record what is in a directory and compare two records: the file-level log of what a run wrote and when.

A record lists every file (relative path, size, SHA-256, mtime in nanoseconds) and every symbolic link (relative path, whether it points outside the
directory). A link is never followed. Two records compare as added, removed, changed (the bytes or the size differ) and touched (only the mtime
differs). Nothing is ever written inside the directory that is recorded, and the absolute path of the machine does not appear in what is written.

    python verification/workspace_snapshot.py snapshot DIR OUT.json [--exclude NAME ...]
    python verification/workspace_snapshot.py compare BEFORE.json AFTER.json

Stage 1 of the spec-tool bake-off (spec/AIDF-SPEC-TOOL-BAKEOFF-STAGES-0-1-TASK-CONTRACT.md, criterion 5). It is evidence tooling, not a gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

DEFAULT_EXCLUDE = (".git",)
PLACEHOLDER = "<workspace>"
HOME_PLACEHOLDER = "<home>"
CHUNK = 1 << 20


class SnapshotError(Exception):
    pass


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def snapshot(root: Path, exclude: tuple[str, ...] = DEFAULT_EXCLUDE) -> dict[str, Any]:
    """The record of `root`. The names in `exclude` are skipped at any depth. A symbolic link or a Windows directory junction is recorded, never followed."""
    root = root.resolve()
    if not root.is_dir():
        raise SnapshotError(f"{root.name} is not a directory")
    files: dict[str, dict[str, Any]] = {}
    links: dict[str, dict[str, Any]] = {}
    for current, dirs, names in os.walk(root, followlinks=False):
        here = Path(current)
        kept = []
        for name in sorted(dirs):
            full = here / name
            rel = full.relative_to(root).as_posix()
            if name in exclude:
                continue
            if _is_link(full):
                links[rel] = {"outside": _points_outside(full, root)}
            else:
                kept.append(name)
        dirs[:] = kept
        for name in sorted(names):
            full = here / name
            rel = full.relative_to(root).as_posix()
            if name in exclude:
                continue
            if _is_link(full):
                links[rel] = {"outside": _points_outside(full, root)}
                continue
            info = full.stat()
            files[rel] = {"size": info.st_size, "sha256": _digest(full), "mtime_ns": info.st_mtime_ns}
    return {"root": PLACEHOLDER, "exclude": list(exclude), "files": files, "links": links}


def _is_link(path: Path) -> bool:
    """A symbolic link, or a directory junction (which Path.is_symlink does not report and os.walk descends into on Windows)."""
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def _points_outside(link: Path, root: Path) -> bool:
    try:
        target = link.resolve()
    except OSError:
        return True
    return root != target and root not in target.parents


def compare(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list[str]]:
    """Added, removed, changed and touched paths between two records (files and links together, each list sorted)."""
    old = _entries(before)
    new = _entries(after)
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed: list[str] = []
    touched: list[str] = []
    for path in sorted(set(old) & set(new)):
        a, b = old[path], new[path]
        if a.get("sha256") != b.get("sha256") or a.get("size") != b.get("size") or a.get("outside") != b.get("outside"):
            changed.append(path)
        elif a.get("mtime_ns") != b.get("mtime_ns"):
            touched.append(path)
    return {"added": added, "removed": removed, "changed": changed, "touched": touched}


def _entries(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    merged.update(record.get("files", {}))
    for path, entry in record.get("links", {}).items():
        merged[path] = {"link": True, **entry}
    return merged


def redact(text: str, root: Path | None = None) -> str:
    """Replace the absolute path of `root` and of the home directory, in both slash forms, so that a record written to the repository names none."""
    pairs: list[tuple[str, str]] = []
    if root is not None:
        pairs.append((str(root.resolve()), PLACEHOLDER))
    pairs.append((str(Path.home()), HOME_PLACEHOLDER))
    out = text
    for real, placeholder in sorted(pairs, key=lambda pair: -len(pair[0])):
        if not real:
            continue
        for form in {real, real.replace("\\", "/"), real.replace("\\", "\\\\")}:
            out = out.replace(form, placeholder)
    return out


def write_record(record: dict[str, Any], out: Path, recorded_root: Path | None = None) -> None:
    """Write the record as JSON. Refuses to write inside the directory that was recorded."""
    text = redact(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n", recorded_root)
    if recorded_root is not None:
        target = out.resolve()
        base = recorded_root.resolve()
        if target == base or base in target.parents:
            raise SnapshotError("the record may not be written inside the recorded directory")
    if out.is_file() and out.stat().st_nlink > 1:
        raise SnapshotError("the output path is a file with more than one link; it may be a hard link to a file in the recorded directory")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    snap = sub.add_parser("snapshot")
    snap.add_argument("directory", type=Path)
    snap.add_argument("out", type=Path)
    snap.add_argument("--exclude", nargs="*", default=list(DEFAULT_EXCLUDE))
    comp = sub.add_parser("compare")
    comp.add_argument("before", type=Path)
    comp.add_argument("after", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot":
            record = snapshot(args.directory, tuple(args.exclude))
            write_record(record, args.out, args.directory)
            print(f"recorded {len(record['files'])} files and {len(record['links'])} links")
            return 0
        diff = compare(json.loads(args.before.read_text(encoding="utf-8")), json.loads(args.after.read_text(encoding="utf-8")))
        print(json.dumps(diff, indent=2))
        return 0
    except (SnapshotError, OSError, ValueError) as error:
        print(f"snapshot: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
