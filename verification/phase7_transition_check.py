"""Fail closed unless the transition is evaluating the exact approved Phase 7 MR content."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

MAX_ARTIFACT_BYTES = 256 * 1024
MAX_MANIFEST_FILES = 64
SHA256 = re.compile(r"[0-9a-f]{64}")
GIT_SHA = re.compile(r"[0-9a-f]{40}")


def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def safe_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and all(part not in {"", ".", ".."} for part in path.parts)


def canonical_digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValueError(f"unsafe or oversized approved file: {path.as_posix()}")
    data = path.read_bytes()
    canonical = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(canonical).hexdigest()


def bounded_regular_bytes(path: Path, label: str) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValueError(f"{label} must be a bounded regular non-symlink file")
    data = path.read_bytes()
    if len(data) > MAX_ARTIFACT_BYTES:
        raise ValueError(f"{label} exceeds the byte limit")
    return data


def require_ancestor(ancestor: str, descendant: str, root: Path) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=10,
    )
    if result.returncode != 0:
        raise ValueError("protected target is not descended from the approved transition base")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--changed-files", required=True)
    parser.add_argument("--mr-iid", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--project-path", required=True)
    parser.add_argument("--target-project-id", required=True)
    parser.add_argument("--target-branch", required=True)
    parser.add_argument("--diff-base-sha", required=True)
    parser.add_argument("--target-branch-sha", required=True)
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--event-type", required=True)
    parser.add_argument("--source-branch-sha", required=True)
    parser.add_argument("--commit-sha", required=True)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    try:
        manifest_candidate = root / args.manifest
        changed_candidate = root / args.changed_files
        if manifest_candidate.is_symlink() or changed_candidate.is_symlink():
            raise ValueError("inputs must be regular non-symlink files")
        manifest_path = manifest_candidate.resolve(strict=True)
        changed_path = changed_candidate.resolve(strict=True)
        if root not in manifest_path.parents or root not in changed_path.parents:
            raise ValueError("inputs must remain beneath the repository root")
        manifest = json.loads(
            bounded_regular_bytes(manifest_path, "manifest").decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid JSON constant: {value}")),
        )
        if not isinstance(manifest, dict) or set(manifest) != {
            "schema_version", "merge_request_iid", "project_path", "target_branch",
            "source_branch", "approved_base_ancestor", "files"
        }:
            raise ValueError("manifest fields are not exact")
        if manifest["schema_version"] != 2 or manifest["merge_request_iid"] != args.mr_iid:
            raise ValueError("merge request identity is not authorized")
        if (
            manifest["project_path"] != args.project_path
            or args.project_id != args.target_project_id
            or manifest["target_branch"] != args.target_branch
            or manifest["source_branch"] != args.source_branch
        ):
            raise ValueError("project or branch context is not authorized")
        if not GIT_SHA.fullmatch(args.diff_base_sha) or not GIT_SHA.fullmatch(args.commit_sha):
            raise ValueError("pipeline SHA context is malformed")
        if args.event_type == "detached":
            if args.target_branch_sha or args.source_branch_sha:
                raise ValueError("detached pipeline contains unexpected branch SHA metadata")
        elif args.event_type == "merged_result":
            if (
                not GIT_SHA.fullmatch(args.target_branch_sha)
                or not GIT_SHA.fullmatch(args.source_branch_sha)
                or args.diff_base_sha != args.target_branch_sha
                or args.commit_sha in {args.target_branch_sha, args.source_branch_sha}
            ):
                raise ValueError("merged-result pipeline SHA context is malformed or stale")
            require_ancestor(args.target_branch_sha, args.commit_sha, root)
            require_ancestor(args.source_branch_sha, args.commit_sha, root)
        else:
            raise ValueError("merge request pipeline event type is not authorized")
        approved_base = manifest["approved_base_ancestor"]
        if not isinstance(approved_base, str) or not GIT_SHA.fullmatch(approved_base):
            raise ValueError("approved base ancestor is malformed")
        require_ancestor(approved_base, args.diff_base_sha, root)
        files = manifest["files"]
        if not isinstance(files, dict) or not files or len(files) > MAX_MANIFEST_FILES:
            raise ValueError("manifest files must be a bounded non-empty object")
        if any(not safe_path(path) or not isinstance(digest, str) or not SHA256.fullmatch(digest) for path, digest in files.items()):
            raise ValueError("manifest contains an unsafe path or digest")
        raw_changed = bounded_regular_bytes(changed_path, "changed-file artifact")
        if not raw_changed.endswith(b"\x00"):
            raise ValueError("changed-file artifact must be bounded and NUL-terminated")
        changed = [item.decode("utf-8", errors="strict") for item in raw_changed[:-1].split(b"\x00")]
        if len(changed) != len(set(changed)) or set(changed) != set(files):
            raise ValueError("changed-file population does not exactly match the approved manifest")
        for relative, expected in files.items():
            candidate = root / relative
            if candidate.is_symlink():
                raise ValueError(f"approved file must not be a symlink: {relative}")
            target = candidate.resolve(strict=True)
            if root not in target.parents or canonical_digest(target) != expected:
                raise ValueError(f"approved content mismatch: {relative}")
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, TypeError) as exc:
        print(f"FAIL [phase7-transition] {exc}")
        return 1
    print("PASS: exact Phase 7 MR context, file population, and content are approved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
