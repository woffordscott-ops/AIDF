#!/usr/bin/env python3
"""Offline structural checks for a proposed Layer 3 project context pack.

This does not authenticate a human Architect's decision or prove that prose is
true. Those remain explicit review gates in the two instantiation playbooks.
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import re
import stat
import subprocess
import sys
import threading
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

if os.name == "nt":
    import ctypes
    import msvcrt
    from ctypes import wintypes

MAX_FILE_BYTES = 128 * 1024
MAX_TREE_BYTES = 4 * 1024 * 1024
CHECK_TIMEOUT_SECONDS = 120
GIT_OID_RE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
ID_RE = re.compile(r"PAT-[0-9]{3,6}\Z")
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
ARTIFACT_KEYS = frozenset(
    {
        "repository_map",
        "architecture_overview",
        "invariants_register",
        "pattern_registry",
        "adr_log",
        "contract_registry",
        "security_model",
        "testing_strategy",
        "conventions",
        "deployment_operational_model",
        "context_and_cost",
    }
)
FRONTMATTER_KEYS = frozenset({"owner", "load_when", "max_length", "last_verified"})
MAX_LENGTH_RE = re.compile(r"([1-9]|1[0-9]|20) pages?\Z")
WORDS_PER_PAGE = 500
ARCHITECTURE_OVERVIEW_MAX_PAGES = 3
WINDOWS_RESERVED_NAMES = frozenset(
    {
        "aux",
        "clock$",
        "con",
        "conin$",
        "conout$",
        "nul",
        "prn",
        *(f"com{index}" for index in range(1, 10)),
        *(f"lpt{index}" for index in range(1, 10)),
        *(f"com{index}" for index in "¹²³"),
        *(f"lpt{index}" for index in "¹²³"),
    }
)
WINDOWS_REPARSE_ATTRIBUTE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def _relative_path(relative: Any) -> PurePosixPath:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError("artifact path is not a canonical relative POSIX path")
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in relative.split("/")):
        raise ValueError("artifact path escapes the project root")
    for part in path.parts:
        canonical_part = part.rstrip(" .")
        device_name = canonical_part.split(".", 1)[0].casefold()
        if canonical_part != part or device_name in WINDOWS_RESERVED_NAMES:
            raise ValueError("artifact path contains a Windows-reserved component")
    return path


def _normalize_windows_final_path(value: str) -> Path:
    if value.startswith("\\\\?\\Volume{"):
        raise ValueError(
            "Windows artifact paths require a drive-letter or UNC namespace; "
            "volume-GUID-only paths are unsupported"
        )
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
        if not re.match(r"[A-Za-z]:\\", value):
            raise ValueError("Windows artifact final path has an unsupported namespace")
    else:
        raise ValueError("Windows artifact final path has an unsupported namespace")
    return Path(value)


def _windows_final_path(descriptor: int) -> Path:
    handle = wintypes.HANDLE(msvcrt.get_osfhandle(descriptor))
    get_final_path = ctypes.WinDLL("kernel32", use_last_error=True).GetFinalPathNameByHandleW
    get_final_path.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    get_final_path.restype = wintypes.DWORD
    length = get_final_path(handle, None, 0, 0)
    if length == 0:
        raise OSError(ctypes.get_last_error(), "GetFinalPathNameByHandleW failed")
    buffer = ctypes.create_unicode_buffer(length + 1)
    written = get_final_path(handle, buffer, len(buffer), 0)
    if written == 0 or written >= len(buffer):
        raise OSError(ctypes.get_last_error(), "GetFinalPathNameByHandleW failed")
    return _normalize_windows_final_path(buffer.value)


def _windows_artifact_final_path(descriptor: int, relative: Any) -> Path:
    try:
        return _windows_final_path(descriptor)
    except ValueError as exc:
        raise ValueError(f"unsupported Windows final path for artifact: {relative}") from exc


def _stat_identity(info: os.stat_result, relative: Any) -> tuple[int, int]:
    if info.st_ino == 0:
        raise ValueError(f"artifact file identity is unavailable: {relative}")
    return info.st_dev, info.st_ino


def _project_root_identity(root: Path) -> tuple[int, int]:
    info = os.stat(root, follow_symlinks=False)
    if (
        stat.S_ISLNK(info.st_mode)
        or not stat.S_ISDIR(info.st_mode)
        or getattr(info, "st_file_attributes", 0) & WINDOWS_REPARSE_ATTRIBUTE
    ):
        raise ValueError("project root must be a real directory without reparse indirection")
    return _stat_identity(info, "project root")


def _validated_project_root(root: Path) -> tuple[Path, tuple[int, int]]:
    before_identity = _project_root_identity(root)
    resolved = root.resolve(strict=True)
    if (
        before_identity != _project_root_identity(root)
        or before_identity != _project_root_identity(resolved)
    ):
        raise ValueError("project root identity changed during validation")
    return resolved, before_identity


def _windows_component_identities(
    root: Path, path: PurePosixPath, relative: Any
) -> tuple[tuple[int, int], ...]:
    identities = [_project_root_identity(root)]
    current = root
    for part in path.parts:
        current /= part
        info = os.stat(current, follow_symlinks=False)
        if getattr(info, "st_file_attributes", 0) & WINDOWS_REPARSE_ATTRIBUTE:
            raise ValueError(f"symlink or reparse point is not allowed: {relative}")
        identities.append(_stat_identity(info, relative))
    return tuple(identities)


def _windows_anchor(path: Path) -> str:
    return os.path.splitdrive(os.path.normcase(os.path.abspath(path)))[0]


def _validate_windows_opened_path(
    root: Path,
    path: PurePosixPath,
    descriptor: int,
    relative: Any,
    before: tuple[tuple[int, int], ...],
) -> os.stat_result:
    requested = root.joinpath(*path.parts)
    opened = os.fstat(descriptor)
    requested_info = os.stat(requested, follow_symlinks=False)
    after = _windows_component_identities(root, path, relative)
    if before != after or _stat_identity(requested_info, relative) != _stat_identity(
        opened, relative
    ):
        raise ValueError(f"artifact identity changed during safe open: {relative}")
    final_path = _windows_artifact_final_path(descriptor, relative)
    if _windows_anchor(requested) != _windows_anchor(final_path):
        raise ValueError(f"unsupported Windows path alias for artifact: {relative}")
    return opened


def _open_regular_file(
    root: Path,
    relative: Any,
    expected_root_identity: tuple[int, int] | None = None,
) -> tuple[int, os.stat_result]:
    path = _relative_path(relative)
    descriptor = -1
    directory_descriptor = -1
    try:
        if os.name == "nt":
            if (
                expected_root_identity is not None
                and _project_root_identity(root) != expected_root_identity
            ):
                raise ValueError("project root identity changed during safe open")
            before = _windows_component_identities(root, path, relative)
            descriptor = os.open(root.joinpath(*path.parts), os.O_RDONLY | os.O_BINARY)
            info = _validate_windows_opened_path(root, path, descriptor, relative, before)
        else:
            no_follow = getattr(os, "O_NOFOLLOW", None)
            non_block = getattr(os, "O_NONBLOCK", None)
            if no_follow is None or non_block is None:
                raise OSError("platform lacks O_NOFOLLOW or O_NONBLOCK support")
            directory_descriptor = os.open(
                root, os.O_RDONLY | os.O_DIRECTORY | no_follow | non_block
            )
            if expected_root_identity is not None and _stat_identity(
                os.fstat(directory_descriptor), "project root"
            ) != expected_root_identity:
                raise ValueError("project root identity changed during safe open")
            for part in path.parts[:-1]:
                next_descriptor = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | no_follow | non_block,
                    dir_fd=directory_descriptor,
                )
                os.close(directory_descriptor)
                directory_descriptor = next_descriptor
            descriptor = os.open(
                path.parts[-1],
                os.O_RDONLY | no_follow | non_block,
                dir_fd=directory_descriptor,
            )
            info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"artifact is not a regular file: {relative}")
        return descriptor, info
    except OSError as exc:
        if descriptor >= 0:
            os.close(descriptor)
        if exc.errno == errno.ELOOP:
            raise ValueError(f"symlink or reparse point is not allowed: {relative}") from exc
        raise ValueError(f"artifact could not be opened safely: {relative}") from exc
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    finally:
        if directory_descriptor >= 0:
            os.close(directory_descriptor)


def _read(
    root: Path,
    relative: Any,
    snapshots: dict[str, tuple[tuple[int, int], bytes]] | None = None,
    expected_root_identity: tuple[int, int] | None = None,
) -> bytes:
    canonical = _relative_path(relative).as_posix()
    if snapshots is not None and canonical in snapshots:
        return snapshots[canonical][1]
    descriptor, info = _open_regular_file(root, relative, expected_root_identity)
    identity = _stat_identity(info, relative)
    if info.st_size > MAX_FILE_BYTES:
        os.close(descriptor)
        raise ValueError(f"artifact exceeds {MAX_FILE_BYTES} bytes: {relative}")
    with os.fdopen(descriptor, "rb") as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
        after = os.fstat(stream.fileno())
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"artifact exceeds {MAX_FILE_BYTES} bytes: {relative}")
    if identity != _stat_identity(after, relative):
        raise ValueError(f"artifact identity changed during read: {relative}")
    if snapshots is not None:
        snapshots[canonical] = (identity, data)
    return data


def _file_identity(root: Path, relative: Any) -> tuple[int, int]:
    descriptor, info = _open_regular_file(root, relative)
    os.close(descriptor)
    return _stat_identity(info, relative)


def _json(
    root: Path,
    relative: Any,
    snapshots: dict[str, tuple[tuple[int, int], bytes]] | None = None,
    expected_root_identity: tuple[int, int] | None = None,
) -> Any:
    try:
        return json.loads(
            _read(root, relative, snapshots, expected_root_identity).decode("utf-8"),
            object_pairs_hook=_object_pairs,
            parse_constant=_reject_constant,
        )
    except RecursionError as exc:
        raise ValueError(f"JSON nesting exceeds the safe limit: {relative}") from exc


def _fields(value: Any, expected: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} must contain exactly {', '.join(sorted(expected))}")
    return value


def _strict_date(value: Any, label: str) -> None:
    if not isinstance(value, str) or DATE_RE.fullmatch(value) is None:
        raise ValueError(f"invalid {label}")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid {label}") from exc


def _validate_source_oid(value: Any, object_format: bytes | None = None) -> str:
    if not isinstance(value, str) or GIT_OID_RE.fullmatch(value) is None:
        raise ValueError("existing-project source commit must be an exact Git SHA")
    if object_format is not None:
        expected_length = {b"sha1": 40, b"sha256": 64}.get(object_format)
        if expected_length is None or len(value) != expected_length:
            raise ValueError("source SHA does not match the repository object format")
    return value


def _frontmatter(
    root: Path,
    relative: Any,
    snapshots: dict[str, tuple[tuple[int, int], bytes]] | None = None,
    *,
    maximum_pages: int | None = None,
    expected_root_identity: tuple[int, int] | None = None,
) -> None:
    text = _read(root, relative, snapshots, expected_root_identity).decode("utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:21]:
        raise ValueError(f"missing bounded frontmatter: {relative}")
    end = lines.index("---", 1)
    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line:
            raise ValueError(f"invalid frontmatter: {relative}")
        key, value = line.split(":", 1)
        if key in metadata or key not in FRONTMATTER_KEYS or not value.strip():
            raise ValueError(f"invalid frontmatter field: {relative}")
        metadata[key] = value.strip()
    if set(metadata) != FRONTMATTER_KEYS or not any(line.startswith("# ") for line in lines[end + 1 :]):
        raise ValueError(f"incomplete context document: {relative}")
    _strict_date(metadata["last_verified"], f"last_verified: {relative}")
    length_match = MAX_LENGTH_RE.fullmatch(metadata["max_length"])
    if length_match is None:
        raise ValueError(f"invalid max_length: {relative}")
    declared_pages = int(length_match.group(1))
    if maximum_pages is not None and declared_pages > maximum_pages:
        raise ValueError(f"max_length exceeds {maximum_pages}-page policy: {relative}")
    body_words = len(re.findall(r"\S+", "\n".join(lines[end + 1 :])))
    if body_words > declared_pages * WORDS_PER_PAGE:
        raise ValueError(f"document exceeds max_length: {relative}")


def _map_document(
    root: Path,
    relative: Any,
    source: Any,
    paths: Any,
    snapshots: dict[str, tuple[tuple[int, int], bytes]] | None = None,
    expected_root_identity: tuple[int, int] | None = None,
) -> None:
    text = _read(root, relative, snapshots, expected_root_identity).decode("utf-8")
    marker_start = "<!-- AIDF-TREE-BEGIN -->"
    marker_end = "<!-- AIDF-TREE-END -->"
    if text.count(marker_start) != 1 or text.count(marker_end) != 1:
        raise ValueError("repository map lacks unique inventory markers")
    start = text.index(marker_start)
    end = text.index(marker_end)
    if start >= end:
        raise ValueError("repository map has misordered inventory markers")
    inventory = text[start + len(marker_start) : end].strip().splitlines()
    if inventory != paths:
        raise ValueError("repository-map document and manifest inventory differ")
    source_label = source if source is not None else "none (pre-code)"
    source_lines = [line for line in text.splitlines() if line.startswith("Source commit:")]
    if source_lines != [f"Source commit: {source_label}"]:
        raise ValueError("repository-map document has a stale source commit")


def _git_environment() -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    environment["GIT_GRAFT_FILE"] = os.devnull
    environment["GIT_CONFIG_COUNT"] = "1"
    environment["GIT_CONFIG_KEY_0"] = "core.commitGraph"
    environment["GIT_CONFIG_VALUE_0"] = "false"
    return environment


def _close_bound_git_root(descriptor: int) -> None:
    if os.name == "nt":
        if not ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(
            wintypes.HANDLE(descriptor)
        ):
            raise OSError(ctypes.get_last_error(), "CloseHandle failed")
    else:
        os.close(descriptor)


def _bound_git_root(
    root: Path, expected_root_identity: tuple[int, int] | None
) -> tuple[str, int]:
    if expected_root_identity is None:
        return str(root), -1
    if os.name == "nt":
        create_file = ctypes.WinDLL("kernel32", use_last_error=True).CreateFileW
        create_file.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        create_file.restype = wintypes.HANDLE
        handle = create_file(str(root), 0, 0x1 | 0x2, None, 3, 0x02000000, None)
        if handle == wintypes.HANDLE(-1).value:
            raise OSError(ctypes.get_last_error(), "project root handle could not be opened")
        descriptor = int(handle)
        if _project_root_identity(root) != expected_root_identity:
            _close_bound_git_root(descriptor)
            raise ValueError("project root identity changed before Git validation")
        return str(root), descriptor
    no_follow = getattr(os, "O_NOFOLLOW", None)
    if no_follow is None:
        raise ValueError("platform cannot bind Git validation to the project root")
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | no_follow)
    if _stat_identity(os.fstat(descriptor), "project root") != expected_root_identity:
        os.close(descriptor)
        raise ValueError("project root identity changed before Git validation")
    descriptor_path = Path(f"/proc/self/fd/{descriptor}")
    if not descriptor_path.exists():
        os.close(descriptor)
        raise ValueError("platform cannot bind Git validation to the project root")
    return str(descriptor_path), descriptor


def _git(
    root: Path,
    *arguments: str,
    expected_root_identity: tuple[int, int] | None = None,
) -> bytes:
    git_root, root_descriptor = _bound_git_root(root, expected_root_identity)
    popen_options: dict[str, Any] = {}
    if root_descriptor >= 0 and os.name != "nt":
        popen_options["pass_fds"] = (root_descriptor,)
    try:
        process = subprocess.Popen(
            ["git", "-C", git_root, *arguments],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=_git_environment(),
            **popen_options,
        )
    except BaseException:
        if root_descriptor >= 0:
            _close_bound_git_root(root_descriptor)
        raise
    if root_descriptor >= 0 and os.name != "nt":
        _close_bound_git_root(root_descriptor)
        root_descriptor = -1
    if process.stdout is None:
        process.kill()
        process.wait()
        if root_descriptor >= 0:
            _close_bound_git_root(root_descriptor)
        raise ValueError("Git object check could not capture output")
    output = bytearray()
    exceeded = threading.Event()

    def drain_stdout() -> None:
        while chunk := process.stdout.read(64 * 1024):
            if len(output) + len(chunk) > MAX_TREE_BYTES:
                exceeded.set()
                try:
                    process.kill()
                except OSError:
                    pass
                return
            output.extend(chunk)

    reader = threading.Thread(target=drain_stdout, daemon=True)
    reader.start()
    try:
        returncode = process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        reader.join()
        process.stdout.close()
        if root_descriptor >= 0:
            _close_bound_git_root(root_descriptor)
        raise
    reader.join()
    process.stdout.close()
    try:
        if returncode != 0 or exceeded.is_set():
            raise ValueError(f"Git object check failed: {' '.join(arguments[:2])}")
        return bytes(output)
    finally:
        if root_descriptor >= 0:
            _close_bound_git_root(root_descriptor)


def _git_status(
    root: Path,
    *arguments: str,
    expected_root_identity: tuple[int, int] | None = None,
) -> int:
    git_root, root_descriptor = _bound_git_root(root, expected_root_identity)
    run_options: dict[str, Any] = {}
    if root_descriptor >= 0 and os.name != "nt":
        run_options["pass_fds"] = (root_descriptor,)
    try:
        return subprocess.run(
            ["git", "-C", git_root, *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=20,
            env=_git_environment(),
            **run_options,
        ).returncode
    finally:
        if root_descriptor >= 0:
            _close_bound_git_root(root_descriptor)


def _validate_patterns(
    root: Path,
    relative: Any,
    entry_path: str,
    snapshots: dict[str, tuple[tuple[int, int], bytes]] | None = None,
    expected_root_identity: tuple[int, int] | None = None,
) -> None:
    data = _fields(
        _json(root, relative, snapshots, expected_root_identity),
        frozenset({"schema_version", "entries"}),
        "pattern registry",
    )
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("unsupported pattern registry schema")
    entries = data["entries"]
    if not isinstance(entries, list) or len(entries) > 1000:
        raise ValueError("pattern entries must be a bounded list")
    if entry_path == "greenfield" and entries:
        raise ValueError("greenfield bootstrap cannot invent incumbent precedent")
    seen: set[str] = set()
    keys = frozenset({"id", "pattern", "scope", "state", "basis", "date", "ratifier", "decision_record"})
    for entry in entries:
        record = _fields(entry, keys, "pattern entry")
        identifier = record["id"]
        if not isinstance(identifier, str) or not ID_RE.fullmatch(identifier) or identifier in seen:
            raise ValueError("invalid or duplicate pattern ID")
        seen.add(identifier)
        if any(not isinstance(record[key], str) or not record[key].strip() for key in ("pattern", "scope", "basis")):
            raise ValueError(f"incomplete pattern entry: {identifier}")
        if record["state"] == "PROVISIONAL":
            if record["ratifier"] is not None or record["decision_record"] is not None:
                raise ValueError(f"provisional pattern claims approval: {identifier}")
        elif record["state"] == "RATIFIED":
            if not isinstance(record["ratifier"], str) or not record["ratifier"].strip():
                raise ValueError(f"ratified pattern lacks Architect identity: {identifier}")
            _frontmatter(
                root,
                record["decision_record"],
                snapshots,
                expected_root_identity=expected_root_identity,
            )
            decision = _read(
                root, record["decision_record"], snapshots, expected_root_identity
            ).decode("utf-8")
            if not all(
                line in decision.splitlines()
                for line in (
                    f"Pattern ID: {identifier}",
                    "Decision: RATIFIED",
                    f"Ratified by: {record['ratifier']}",
                    f"Decision date: {record['date']}",
                )
            ):
                raise ValueError(f"pattern decision record does not match: {identifier}")
        else:
            raise ValueError(f"unsupported pattern state: {identifier}")
        _strict_date(record["date"], f"pattern date: {identifier}")


def check_pack(root: Path, manifest_relative: str) -> None:
    root, root_identity = _validated_project_root(root)
    snapshots: dict[str, tuple[tuple[int, int], bytes]] = {}
    manifest = _fields(
        _json(root, manifest_relative, snapshots, root_identity),
        frozenset({"schema_version", "entry_path", "project", "source_commit", "repository_map", "artifacts"}),
        "context-pack manifest",
    )
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise ValueError("unsupported context-pack schema")
    entry_path = manifest["entry_path"]
    if entry_path not in ("existing", "greenfield"):
        raise ValueError("entry_path must be existing or greenfield")
    project = manifest["project"]
    if not isinstance(project, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{1,127}", project):
        raise ValueError("invalid project identifier")
    artifacts = _fields(manifest["artifacts"], ARTIFACT_KEYS, "artifacts")
    paths = list(artifacts.values())
    if any(not isinstance(path, str) for path in paths):
        raise ValueError("artifact paths must be strings")
    if len(paths) != len(set(paths)):
        raise ValueError("artifact paths must be distinct")
    identities = []
    for path in paths:
        _read(root, path, snapshots, root_identity)
        identities.append(snapshots[_relative_path(path).as_posix()][0])
    if len(identities) != len(set(identities)):
        raise ValueError("artifact paths must identify distinct files")
    for key, relative in artifacts.items():
        if key == "pattern_registry":
            _validate_patterns(root, relative, entry_path, snapshots, root_identity)
        else:
            _frontmatter(
                root,
                relative,
                snapshots,
                maximum_pages=(
                    ARCHITECTURE_OVERVIEW_MAX_PAGES if key == "architecture_overview" else None
                ),
                expected_root_identity=root_identity,
            )
    source = manifest["source_commit"]
    repository_map = _fields(
        manifest["repository_map"], frozenset({"source_commit", "paths"}), "repository_map"
    )
    if repository_map["source_commit"] != source:
        raise ValueError("repository map and manifest source commits differ")
    map_paths = repository_map["paths"]
    if not isinstance(map_paths, list) or any(not isinstance(path, str) for path in map_paths):
        raise ValueError("repository map paths must be a list of strings")
    _map_document(
        root,
        artifacts["repository_map"],
        source,
        map_paths,
        snapshots,
        root_identity,
    )
    if entry_path == "greenfield":
        if source is not None or map_paths != []:
            raise ValueError("pre-code greenfield map must not claim a Git inventory")
        return
    source = _validate_source_oid(source)
    repository_root = Path(
        _git(
            root,
            "rev-parse",
            "--show-toplevel",
            expected_root_identity=root_identity,
        ).decode("utf-8").strip()
    ).resolve()
    if repository_root != root:
        raise ValueError("project root is not the source Git repository root")
    if (
        _git(
            root,
            "rev-parse",
            "--is-shallow-repository",
            expected_root_identity=root_identity,
        ).strip()
        != b"false"
    ):
        raise ValueError("existing-project validation requires complete non-shallow Git history")
    object_format = _git(
        root,
        "rev-parse",
        "--show-object-format",
        expected_root_identity=root_identity,
    ).strip()
    _validate_source_oid(source, object_format)
    if (
        _git(root, "cat-file", "-t", source, expected_root_identity=root_identity).strip()
        != b"commit"
    ):
        raise ValueError("source SHA does not identify a commit")
    ancestry_status = _git_status(
        root,
        "merge-base",
        "--is-ancestor",
        source,
        "HEAD",
        expected_root_identity=root_identity,
    )
    if ancestry_status == 1:
        raise ValueError("existing-project source commit must be an ancestor of HEAD")
    if ancestry_status != 0:
        raise ValueError("Git object check failed: merge-base --is-ancestor")
    tree = _git(
        root,
        "ls-tree",
        "-r",
        "--name-only",
        "-z",
        source,
        expected_root_identity=root_identity,
    )
    actual = [name.decode("utf-8") for name in tree.rstrip(b"\0").split(b"\0") if name]
    if map_paths != actual:
        raise ValueError("repository map differs from the exact source Git tree")


def _run_check(project_root: Path, manifest: str) -> int:
    try:
        check_pack(project_root, manifest)
    except (OSError, UnicodeError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS: context-pack structural checks (human architecture approval still required)")
    return 0


def _run_bounded_check(project_root: Path, manifest: str) -> int:
    command = [
        sys.executable,
        str(Path(__file__).resolve(strict=True)),
        "--_worker",
        "--project-root",
        str(project_root),
        f"--manifest={manifest}",
    ]
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=CHECK_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        print(
            f"FAIL: context-pack validation exceeded {CHECK_TIMEOUT_SECONDS} seconds",
            file=sys.stderr,
        )
        return 1
    sys.stdout.buffer.write(completed.stdout)
    sys.stderr.buffer.write(completed.stderr)
    return completed.returncode if completed.returncode in (0, 1) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--manifest", default="project-context-pack.json")
    parser.add_argument("--_worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args._worker:
        return _run_check(args.project_root, args.manifest)
    return _run_bounded_check(args.project_root, args.manifest)


if __name__ == "__main__":
    raise SystemExit(main())
