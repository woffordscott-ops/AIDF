"""Counterfactual checks for the offline Layer 3 structural validator."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "check_context_pack", ROOT / "instantiation" / "check_context_pack.py"
)
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)
FIXTURES = ROOT / "instantiation" / "fixtures"


class ContextPackChecks(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        self.manifest = json.loads((FIXTURES / "greenfield-manifest.json").read_text(encoding="utf-8"))
        self.patterns: dict[str, object] = {"schema_version": 1, "entries": []}
        self._write_pack()

    def _write(self, relative: str, content: str) -> None:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _document(self, name: str) -> str:
        return (
            "---\nowner: project-architect\nload_when: relevant path or trip-wire\n"
            "max_length: 3 pages\nlast_verified: 2026-09-18\n---\n"
            f"# {name}\n\nEvidence and retained unknowns are declared here.\n"
        )

    def _write_pack(self) -> None:
        for name, path in self.manifest["artifacts"].items():
            if name == "pattern_registry":
                self._write(path, json.dumps(self.patterns))
            elif name == "repository_map":
                source = self.manifest["source_commit"] or "none (pre-code)"
                paths = "\n".join(self.manifest["repository_map"]["paths"])
                self._write(
                    path,
                    self._document(name)
                    + f"\nSource commit: {source}\n<!-- AIDF-TREE-BEGIN -->\n{paths}\n<!-- AIDF-TREE-END -->\n",
                )
            else:
                self._write(path, self._document(name))
        self._write("project-context-pack.json", json.dumps(self.manifest))

    def _git(self, *args: str) -> str:
        return subprocess.check_output(["git", "-C", str(self.project), *args], stderr=subprocess.DEVNULL).decode().strip()

    def _existing(self) -> str:
        self._git("init", "-q")
        self._git("config", "user.name", "Fixture")
        self._git("config", "user.email", "fixture@example.invalid")
        self._write("README.md", "# Existing project\n")
        self._git("add", "README.md")
        self._git("commit", "-qm", "Baseline")
        source = self._git("rev-parse", "HEAD")
        self.manifest = json.loads((FIXTURES / "existing-manifest.json").read_text(encoding="utf-8"))
        self.manifest["source_commit"] = source
        self.manifest["repository_map"] = {"source_commit": source, "paths": ["README.md"]}
        self._write_pack()
        return source

    def test_greenfield_accepts_empty_pre_code_map(self) -> None:
        checker.check_pack(self.project, "project-context-pack.json")

    def test_existing_accepts_exact_ancestor_commit_and_tree(self) -> None:
        self._existing()
        checker.check_pack(self.project, "project-context-pack.json")

    def test_existing_rejects_tampered_inventory(self) -> None:
        self._existing()
        self.manifest["repository_map"]["paths"] = ["wrong.md"]
        self._write_pack()
        with self.assertRaisesRegex(ValueError, "exact source Git tree"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_existing_rejects_unknown_source_commit(self) -> None:
        self._existing()
        self.manifest["source_commit"] = "a" * 40
        self.manifest["repository_map"]["source_commit"] = "a" * 40
        self._write_pack()
        with self.assertRaisesRegex(ValueError, "Git object check failed"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_existing_rejects_shallow_repository_before_source_checks(self) -> None:
        self._existing()
        original_git = checker._git

        def shallow_git(
            root: Path,
            *arguments: str,
            expected_root_identity: tuple[int, int] | None = None,
        ) -> bytes:
            if arguments == ("rev-parse", "--is-shallow-repository"):
                return b"true\n"
            return original_git(
                root, *arguments, expected_root_identity=expected_root_identity
            )

        with (
            mock.patch.object(checker, "_git", side_effect=shallow_git),
            self.assertRaisesRegex(ValueError, "complete non-shallow Git history"),
        ):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_existing_rejects_source_commit_unrelated_to_head(self) -> None:
        self._existing()
        tree = self._git("rev-parse", "HEAD^{tree}")
        unrelated = self._git("commit-tree", tree, "-m", "Unrelated source")
        self.manifest["source_commit"] = unrelated
        self.manifest["repository_map"]["source_commit"] = unrelated
        self._write_pack()
        with self.assertRaisesRegex(ValueError, "source commit must be an ancestor of HEAD"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_existing_preserves_unexpected_merge_base_failure(self) -> None:
        self._existing()
        with (
            mock.patch.object(checker, "_git_status", return_value=2),
            self.assertRaisesRegex(ValueError, "Git object check failed: merge-base --is-ancestor"),
        ):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_source_commit_length_matches_git_object_format(self) -> None:
        self.assertEqual(checker._validate_source_oid("a" * 40, b"sha1"), "a" * 40)
        self.assertEqual(checker._validate_source_oid("b" * 64, b"sha256"), "b" * 64)
        for source, object_format in (("a" * 64, b"sha1"), ("b" * 40, b"sha256")):
            with self.subTest(object_format=object_format), self.assertRaisesRegex(
                ValueError, "repository object format"
            ):
                checker._validate_source_oid(source, object_format)

    def test_existing_rejects_nested_directory_as_git_root(self) -> None:
        self._existing()
        nested = self.project / "nested"
        shutil.copytree(self.project / "context", nested / "context")
        shutil.copyfile(self.project / "project-context-pack.json", nested / "project-context-pack.json")
        with self.assertRaisesRegex(ValueError, "source Git repository root"):
            checker.check_pack(nested, "project-context-pack.json")

    def test_rejects_repository_map_document_mismatch(self) -> None:
        self._write("context/repository-map.md", self._document("map"))
        with self.assertRaisesRegex(ValueError, "inventory markers"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_rejects_misordered_repository_map_markers(self) -> None:
        map_path = "context/repository-map.md"
        existing = (self.project / map_path).read_text(encoding="utf-8")
        start = "<!-- AIDF-TREE-BEGIN -->"
        end = "<!-- AIDF-TREE-END -->"
        misordered = (
            existing.replace(start, "<!-- SWAP -->")
            .replace(end, start)
            .replace("<!-- SWAP -->", end)
        )
        self._write(map_path, misordered)
        with self.assertRaisesRegex(ValueError, "misordered inventory markers"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_rejects_ambiguous_repository_map_source(self) -> None:
        map_path = "context/repository-map.md"
        existing = (self.project / map_path).read_text(encoding="utf-8")
        self._write(map_path, existing + "\nSource commit: another\n")
        with self.assertRaisesRegex(ValueError, "stale source commit"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_rejects_path_escape(self) -> None:
        self.manifest["artifacts"]["security_model"] = "../secret.md"
        self._write("project-context-pack.json", json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError, "escapes"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_rejects_windows_reserved_paths_before_opening(self) -> None:
        reserved_paths = (
            "CON",
            "context/nul.md",
            "context/PrN.txt",
            "context/COM9",
            "context/LPT1.log",
            "context/COM¹.txt",
            "context/clock$",
            "context/conin$",
            "context/report.md. ",
        )
        with mock.patch.object(checker.os, "open") as open_file:
            for path in reserved_paths:
                with self.subTest(path=path), self.assertRaisesRegex(
                    ValueError, "Windows-reserved component"
                ):
                    checker._open_regular_file(self.project, path)
        open_file.assert_not_called()

    def test_allows_non_device_windows_portable_names(self) -> None:
        for path in ("context/console.md", "context/com10.md", "context/auxiliary.md"):
            with self.subTest(path=path):
                self.assertEqual(checker._relative_path(path).as_posix(), path)

    def test_rejects_symlink_artifact_when_supported(self) -> None:
        target = self.project / "context" / "security-model.md"
        target.unlink()
        try:
            target.symlink_to(self.project / "context" / "testing-strategy.md")
        except (NotImplementedError, OSError):
            self.skipTest("local account cannot create symlinks")
        with self.assertRaisesRegex(ValueError, "symlink or reparse"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_windows_rejects_reparse_project_root_before_resolving(self) -> None:
        reparse_root = mock.Mock(
            st_mode=stat.S_IFDIR,
            st_dev=1,
            st_ino=10,
            st_file_attributes=checker.WINDOWS_REPARSE_ATTRIBUTE,
        )
        with (
            mock.patch.object(checker.os, "stat", return_value=reparse_root),
            mock.patch.object(checker.Path, "resolve") as resolve,
            self.assertRaisesRegex(ValueError, "project root.*reparse indirection"),
        ):
            checker._validated_project_root(self.project)
        resolve.assert_not_called()

    def test_rejects_project_root_identity_change_during_resolution(self) -> None:
        before = mock.Mock(
            st_mode=stat.S_IFDIR,
            st_dev=1,
            st_ino=10,
            st_file_attributes=0,
        )
        after = mock.Mock(
            st_mode=stat.S_IFDIR,
            st_dev=1,
            st_ino=11,
            st_file_attributes=0,
        )
        with (
            mock.patch.object(checker.os, "stat", side_effect=[before, after]),
            mock.patch.object(checker.Path, "resolve", return_value=self.project),
            self.assertRaisesRegex(ValueError, "project root identity changed"),
        ):
            checker._validated_project_root(self.project)

    def test_rejects_resolved_root_with_different_identity(self) -> None:
        original = mock.Mock(
            st_mode=stat.S_IFDIR, st_dev=1, st_ino=10, st_file_attributes=0
        )
        redirected = mock.Mock(
            st_mode=stat.S_IFDIR, st_dev=1, st_ino=11, st_file_attributes=0
        )
        resolved = self.project / "redirected"
        with (
            mock.patch.object(checker.os, "stat", side_effect=[original, original, redirected]),
            mock.patch.object(checker.Path, "resolve", return_value=resolved),
            self.assertRaisesRegex(ValueError, "identity changed during validation"),
        ):
            checker._validated_project_root(self.project)

    def test_validated_project_root_returns_the_verified_identity(self) -> None:
        identity = mock.Mock(
            st_mode=stat.S_IFDIR, st_dev=1, st_ino=10, st_file_attributes=0
        )
        with (
            mock.patch.object(checker.os, "stat", return_value=identity) as stat_path,
            mock.patch.object(checker.Path, "resolve", return_value=self.project),
        ):
            resolved, verified_identity = checker._validated_project_root(self.project)
        self.assertEqual(resolved, self.project)
        self.assertEqual(verified_identity, (1, 10))
        self.assertEqual(stat_path.call_count, 3)

    def test_posix_open_rejects_replaced_project_root(self) -> None:
        replaced_root = mock.Mock(st_mode=stat.S_IFDIR, st_dev=1, st_ino=11)
        with (
            mock.patch.object(checker.os, "name", "posix"),
            mock.patch.object(checker.os, "O_NOFOLLOW", 0x20000, create=True),
            mock.patch.object(checker.os, "O_NONBLOCK", 0x4000, create=True),
            mock.patch.object(checker.os, "O_DIRECTORY", 0x10000, create=True),
            mock.patch.object(checker.os, "open", return_value=123),
            mock.patch.object(checker.os, "fstat", return_value=replaced_root),
            mock.patch.object(checker.os, "close"),
            self.assertRaisesRegex(ValueError, "project root identity changed"),
        ):
            checker._open_regular_file(
                self.project,
                "context/security-model.md",
                expected_root_identity=(1, 10),
            )

    def test_existing_ignores_git_replacement_objects(self) -> None:
        source = self._existing()
        self._write("attacker-controlled.md", "substituted tree\n")
        self._git("add", "attacker-controlled.md")
        self._git("commit", "-qm", "Replacement tree")
        replacement = self._git("rev-parse", "HEAD")
        self._git("replace", source, replacement)
        self.addCleanup(lambda: self._git("replace", "-d", source))
        checker.check_pack(self.project, "project-context-pack.json")

    def test_existing_rejects_grafted_ancestor_forgery(self) -> None:
        source = self._existing()
        original_head = self._git("rev-parse", "HEAD")
        blob = subprocess.run(
            ["git", "-C", str(self.project), "hash-object", "-w", "--stdin"],
            input=b"attacker tree\n",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
        ).stdout.decode().strip()
        tree = subprocess.run(
            ["git", "-C", str(self.project), "mktree"],
            input=f"100644 blob {blob}\tforged.md\n".encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
        ).stdout.decode().strip()
        forged = subprocess.run(
            ["git", "-C", str(self.project), "commit-tree", tree, "-m", "Forged unrelated history"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
        ).stdout.decode().strip()
        self.assertNotEqual(source, forged)
        grafts = self.project / ".git" / "info" / "grafts"
        grafts.parent.mkdir(parents=True, exist_ok=True)
        grafts.write_text(f"{original_head} {forged}\n", encoding="utf-8")
        self.addCleanup(lambda: grafts.unlink(missing_ok=True))
        self.manifest["source_commit"] = forged
        self.manifest["repository_map"] = {"source_commit": forged, "paths": ["forged.md"]}
        self._write_pack()
        with self.assertRaisesRegex(
            ValueError, "existing-project source commit must be an ancestor of HEAD"
        ):
            checker.check_pack(self.project, "project-context-pack.json")

    def _patch_commit_graph_parent(self, graph_path: Path, *, child: str, new_parent: str) -> None:
        data = bytearray(graph_path.read_bytes())
        self.assertEqual(bytes(data[:4]), b"CGPH")
        hash_version = data[5]
        hash_len = 20 if hash_version == 1 else 32
        num_chunks = data[6]
        chunks: dict[bytes, int] = {}
        pos = 8
        for _ in range(num_chunks + 1):
            signature = bytes(data[pos : pos + 4])
            offset = struct.unpack(">Q", data[pos + 4 : pos + 12])[0]
            if signature != b"\x00\x00\x00\x00":
                chunks[signature] = offset
            pos += 12
        oidf_offset = chunks[b"OIDF"]
        oidl_offset = chunks[b"OIDL"]
        cdat_offset = chunks[b"CDAT"]
        total = struct.unpack(">I", data[oidf_offset + 255 * 4 : oidf_offset + 256 * 4])[0]

        def index_of(commit_hex: str) -> int:
            needle = bytes.fromhex(commit_hex)
            for i in range(total):
                start = oidl_offset + i * hash_len
                if bytes(data[start : start + hash_len]) == needle:
                    return i
            raise AssertionError(f"commit {commit_hex} not present in commit-graph OIDL")

        child_index = index_of(child)
        parent_index = index_of(new_parent)
        entry_size = hash_len + 16
        parent1_offset = cdat_offset + child_index * entry_size + hash_len
        struct.pack_into(">I", data, parent1_offset, parent_index)
        digest_name = "sha1" if hash_version == 1 else "sha256"
        trailer = hashlib.new(digest_name, bytes(data[:-hash_len])).digest()
        data[-hash_len:] = trailer
        os.chmod(graph_path, stat.S_IWRITE | stat.S_IREAD)
        graph_path.write_bytes(bytes(data))

    def test_existing_rejects_commit_graph_ancestor_forgery(self) -> None:
        source = self._existing()
        original_head = self._git("rev-parse", "HEAD")
        blob = subprocess.run(
            ["git", "-C", str(self.project), "hash-object", "-w", "--stdin"],
            input=b"attacker tree via commit-graph\n",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
        ).stdout.decode().strip()
        tree = subprocess.run(
            ["git", "-C", str(self.project), "mktree"],
            input=f"100644 blob {blob}\tforged.md\n".encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
        ).stdout.decode().strip()
        forged = subprocess.run(
            ["git", "-C", str(self.project), "commit-tree", tree, "-m", "Forged unrelated history"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
        ).stdout.decode().strip()
        self.assertNotEqual(source, forged)

        self._git("update-ref", "refs/heads/__forged_reachable__", forged)
        self._git("commit-graph", "write", "--reachable")
        self._git("update-ref", "-d", "refs/heads/__forged_reachable__")
        graph_path = self.project / ".git" / "objects" / "info" / "commit-graph"
        self.assertTrue(graph_path.exists())
        self._patch_commit_graph_parent(graph_path, child=original_head, new_parent=forged)
        self.addCleanup(lambda: graph_path.unlink(missing_ok=True))

        self.manifest["source_commit"] = forged
        self.manifest["repository_map"] = {"source_commit": forged, "paths": ["forged.md"]}
        self._write_pack()
        with self.assertRaisesRegex(
            ValueError, "existing-project source commit must be an ancestor of HEAD"
        ):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_bound_git_root_rejects_windows_identity_change(self) -> None:
        close_handle = mock.Mock(return_value=True)
        create_file = mock.Mock(return_value=42)
        fake_kernel32 = mock.Mock(CreateFileW=create_file, CloseHandle=close_handle)
        fake_wintypes = mock.Mock()
        fake_wintypes.HANDLE = lambda value=-1: mock.Mock(value=value)
        with (
            mock.patch.object(checker.os, "name", "nt"),
            mock.patch.object(
                checker, "ctypes", mock.Mock(WinDLL=mock.Mock(return_value=fake_kernel32)), create=True
            ),
            mock.patch.object(checker, "wintypes", fake_wintypes, create=True),
            mock.patch.object(checker, "_project_root_identity", return_value=(1, 999)),
            self.assertRaisesRegex(
                ValueError, "project root identity changed before Git validation"
            ),
        ):
            checker._bound_git_root(self.project, (1, 10))
        close_handle.assert_called_once()

    def test_bound_git_root_rejects_posix_identity_change(self) -> None:
        changed_identity = mock.Mock(st_dev=1, st_ino=999)
        close = mock.Mock()
        with (
            mock.patch.object(checker.os, "name", "posix"),
            mock.patch.object(checker.os, "O_NOFOLLOW", 0x20000, create=True),
            mock.patch.object(checker.os, "O_DIRECTORY", 0x10000, create=True),
            mock.patch.object(checker.os, "open", return_value=55),
            mock.patch.object(checker.os, "fstat", return_value=changed_identity),
            mock.patch.object(checker.os, "close", close),
            self.assertRaisesRegex(
                ValueError, "project root identity changed before Git validation"
            ),
        ):
            checker._bound_git_root(self.project, (1, 10))
        close.assert_called_once_with(55)

    def test_bound_git_root_rejects_when_proc_fd_unavailable(self) -> None:
        matching_identity = mock.Mock(st_dev=1, st_ino=10)
        close = mock.Mock()
        with (
            mock.patch.object(checker.os, "name", "posix"),
            mock.patch.object(checker.os, "O_NOFOLLOW", 0x20000, create=True),
            mock.patch.object(checker.os, "O_DIRECTORY", 0x10000, create=True),
            mock.patch.object(checker.os, "open", return_value=77),
            mock.patch.object(checker.os, "fstat", return_value=matching_identity),
            mock.patch.object(checker.os, "close", close),
            mock.patch.object(checker.Path, "exists", return_value=False),
            self.assertRaisesRegex(
                ValueError, "platform cannot bind Git validation to the project root"
            ),
        ):
            checker._bound_git_root(self.project, (1, 10))
        close.assert_called_once_with(77)

    @unittest.skipUnless(os.name != "nt" and hasattr(os, "mkfifo"), "requires POSIX FIFOs")
    def test_rejects_fifo_artifact_without_blocking(self) -> None:
        target = self.project / "context" / "security-model.md"
        target.unlink()
        os.mkfifo(target)
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "instantiation" / "check_context_pack.py"),
                "--project-root",
                str(self.project),
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn("artifact is not a regular file", completed.stderr)

    def test_posix_leaf_open_uses_nonblocking_flag(self) -> None:
        regular = mock.Mock(st_mode=stat.S_IFREG)
        with (
            mock.patch.object(checker.os, "name", "posix"),
            mock.patch.object(checker.os, "O_NOFOLLOW", 0x100, create=True),
            mock.patch.object(checker.os, "O_NONBLOCK", 0x200, create=True),
            mock.patch.object(checker.os, "O_DIRECTORY", 0x400, create=True),
            mock.patch.object(checker.os, "open", side_effect=[10, 11, 12]) as open_file,
            mock.patch.object(checker.os, "fstat", return_value=regular),
            mock.patch.object(checker.os, "close"),
        ):
            descriptor, info = checker._open_regular_file(
                self.project, "context/security-model.md"
            )
        self.assertEqual((descriptor, info), (12, regular))
        self.assertTrue(all(call.args[1] & 0x200 for call in open_file.call_args_list))

    def test_artifacts_are_snapshotted_once_for_identity_and_content(self) -> None:
        original_open = checker._open_regular_file
        with mock.patch.object(checker, "_open_regular_file", wraps=original_open) as open_file:
            checker.check_pack(self.project, "project-context-pack.json")
        opened = [call.args[1] for call in open_file.call_args_list]
        for path in ("project-context-pack.json", *self.manifest["artifacts"].values()):
            with self.subTest(path=path):
                self.assertEqual(opened.count(path), 1)

    def test_rejects_artifacts_with_the_same_file_identity(self) -> None:
        target = self.project / "context" / "security-model.md"
        target.unlink()
        try:
            os.link(self.project / "context" / "testing-strategy.md", target)
        except (NotImplementedError, OSError):
            self.skipTest("local filesystem cannot create hard links")
        with self.assertRaisesRegex(ValueError, "identify distinct files"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_windows_final_path_normalizes_drive_and_unc_namespaces(self) -> None:
        self.assertEqual(
            checker._normalize_windows_final_path(r"\\?\C:\project\context\file.md"),
            Path(r"C:\project\context\file.md"),
        )
        self.assertEqual(
            checker._normalize_windows_final_path(r"\\?\UNC\server\share\context\file.md"),
            Path(r"\\server\share\context\file.md"),
        )

    def test_windows_final_path_rejects_volume_guid_only_namespace(self) -> None:
        with self.assertRaisesRegex(ValueError, "drive-letter or UNC namespace"):
            checker._normalize_windows_final_path(
                r"\\?\Volume{01234567-89ab-cdef-0123-456789abcdef}\context\file.md"
            )

    def test_windows_final_path_rejects_unrecognized_namespace(self) -> None:
        values = (
            r"C:\project\context\file.md",
            r"\\?\GLOBALROOT\Device\HarddiskVolume1\file.md",
        )
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError, "unsupported namespace"
            ):
                checker._normalize_windows_final_path(value)

    def test_windows_final_path_error_names_the_artifact(self) -> None:
        with (
            mock.patch.object(
                checker,
                "_windows_final_path",
                side_effect=ValueError("unsupported namespace"),
                create=True,
            ),
            self.assertRaisesRegex(
                ValueError,
                r"unsupported Windows final path for artifact: context/security-model\.md",
            ),
        ):
            checker._windows_artifact_final_path(123, "context/security-model.md")

    def test_windows_opened_identity_rejects_redirected_handle(self) -> None:
        requested = mock.Mock(st_dev=1, st_ino=10)
        redirected = mock.Mock(st_dev=1, st_ino=11)
        with (
            mock.patch.object(
                checker,
                "_windows_component_identities",
                side_effect=[((1, 10),), ((1, 10),)],
            ),
            mock.patch.object(checker.os, "fstat", return_value=redirected),
            mock.patch.object(checker.os, "stat", return_value=requested),
            self.assertRaisesRegex(ValueError, "identity changed during safe open"),
        ):
            checker._validate_windows_opened_path(
                self.project,
                checker.PurePosixPath("context/security-model.md"),
                123,
                "context/security-model.md",
                ((1, 10),),
            )

    def test_windows_components_are_checked_before_open(self) -> None:
        events: list[str] = []
        identity = mock.Mock(st_mode=stat.S_IFREG, st_dev=1, st_ino=10)

        def components(*args: object) -> tuple[tuple[int, int], ...]:
            del args
            events.append("components")
            return ((1, 10),)

        def open_file(*args: object, **kwargs: object) -> int:
            del args, kwargs
            events.append("open")
            return 123

        with (
            mock.patch.object(checker.os, "name", "nt"),
            mock.patch.object(checker.os, "O_BINARY", 0x8000, create=True),
            mock.patch.object(checker, "_windows_component_identities", side_effect=components),
            mock.patch.object(checker.os, "open", side_effect=open_file),
            mock.patch.object(checker.os, "fstat", return_value=identity),
            mock.patch.object(checker.os, "stat", return_value=identity),
            mock.patch.object(
                checker,
                "_windows_artifact_final_path",
                return_value=self.project / "context" / "security-model.md",
            ),
            mock.patch.object(checker.os, "close"),
        ):
            checker._open_regular_file(self.project, "context/security-model.md")
        self.assertEqual(events[:3], ["components", "open", "components"])

    def test_windows_revalidates_project_root_before_every_artifact_open(self) -> None:
        safe_root = mock.Mock(
            st_mode=stat.S_IFDIR,
            st_dev=1,
            st_ino=10,
            st_file_attributes=0,
        )
        reparse_root = mock.Mock(
            st_mode=stat.S_IFDIR,
            st_dev=1,
            st_ino=10,
            st_file_attributes=checker.WINDOWS_REPARSE_ATTRIBUTE,
        )
        directory = mock.Mock(
            st_mode=stat.S_IFDIR,
            st_dev=1,
            st_ino=11,
            st_file_attributes=0,
        )
        regular = mock.Mock(
            st_mode=stat.S_IFREG,
            st_dev=1,
            st_ino=12,
            st_file_attributes=0,
        )
        root_checks = 0

        def stat_path(
            path: str | os.PathLike[str], *, follow_symlinks: bool
        ) -> object:
            nonlocal root_checks
            self.assertFalse(follow_symlinks)
            candidate = os.fspath(path)
            if candidate == os.fspath(self.project):
                root_checks += 1
                return reparse_root if root_checks >= 3 else safe_root
            if os.path.basename(candidate) == "context":
                return directory
            return regular

        with (
            mock.patch.object(checker.os, "name", "nt"),
            mock.patch.object(checker.os, "O_BINARY", 0x8000, create=True),
            mock.patch.object(checker.os, "stat", side_effect=stat_path),
            mock.patch.object(checker.os, "open", return_value=123),
            mock.patch.object(checker.os, "fstat", return_value=regular),
            mock.patch.object(
                checker,
                "_windows_artifact_final_path",
                return_value=self.project / "context" / "security-model.md",
            ),
            mock.patch.object(checker.os, "close"),
        ):
            descriptor, _ = checker._open_regular_file(
                self.project, "context/security-model.md"
            )
            checker.os.close(descriptor)
            with self.assertRaisesRegex(ValueError, "project root.*reparse indirection"):
                checker._open_regular_file(
                    self.project, "context/security-model.md"
                )

        self.assertEqual(root_checks, 3)

    def test_windows_component_walk_rejects_reparse_points(self) -> None:
        root = mock.Mock(
            st_mode=stat.S_IFDIR,
            st_dev=1,
            st_ino=9,
            st_file_attributes=0,
        )
        reparse = mock.Mock(
            st_mode=stat.S_IFDIR,
            st_dev=1,
            st_ino=10,
            st_file_attributes=checker.WINDOWS_REPARSE_ATTRIBUTE,
        )
        with (
            mock.patch.object(checker.os, "stat", side_effect=[root, reparse]),
            self.assertRaisesRegex(ValueError, "symlink or reparse point"),
        ):
            checker._windows_component_identities(
                self.project,
                checker.PurePosixPath("context/security-model.md"),
                "context/security-model.md",
            )

    def test_windows_opened_path_rejects_root_alias(self) -> None:
        identity = mock.Mock(st_dev=1, st_ino=10)
        with (
            mock.patch.object(
                checker,
                "_windows_component_identities",
                side_effect=[((1, 10),), ((1, 10),)],
            ),
            mock.patch.object(checker.os, "fstat", return_value=identity),
            mock.patch.object(checker.os, "stat", return_value=identity),
            mock.patch.object(
                checker, "_windows_artifact_final_path", return_value=Path(r"C:\project\file.md")
            ),
            mock.patch.object(checker, "_windows_anchor", side_effect=["s:", "c:"]),
            self.assertRaisesRegex(ValueError, "unsupported Windows path alias"),
        ):
            checker._validate_windows_opened_path(
                self.project,
                checker.PurePosixPath("context/security-model.md"),
                123,
                "context/security-model.md",
                ((1, 10),),
            )

    @unittest.skipUnless(os.name == "nt", "requires the Windows handle API")
    def test_windows_final_path_resolves_a_real_regular_file_handle(self) -> None:
        target = self.project / "context" / "security-model.md"
        descriptor = os.open(target, os.O_RDONLY | os.O_BINARY)
        self.addCleanup(os.close, descriptor)
        self.assertEqual(
            os.path.normcase(os.path.abspath(checker._windows_final_path(descriptor))),
            os.path.normcase(os.path.abspath(target)),
        )

    @unittest.skipUnless(os.name == "nt", "requires the Windows handle API")
    def test_windows_opened_identity_accepts_a_real_regular_file_handle(self) -> None:
        path = checker.PurePosixPath("context/security-model.md")
        descriptor = os.open(self.project.joinpath(*path.parts), os.O_RDONLY | os.O_BINARY)
        self.addCleanup(os.close, descriptor)
        info = checker._validate_windows_opened_path(
            self.project,
            path,
            descriptor,
            path.as_posix(),
            checker._windows_component_identities(self.project, path, path.as_posix()),
        )
        expected = os.fstat(descriptor)
        self.assertEqual((info.st_dev, info.st_ino), (expected.st_dev, expected.st_ino))

    def test_rejects_unavailable_file_identity(self) -> None:
        unavailable = mock.Mock(st_ino=0, st_dev=0)
        with (
            mock.patch.object(checker, "_open_regular_file", return_value=(123, unavailable)),
            mock.patch.object(checker.os, "close") as close,
            self.assertRaisesRegex(ValueError, "file identity is unavailable"),
        ):
            checker._file_identity(self.project, "context/security-model.md")
        close.assert_called_once_with(123)

    def test_git_output_limit_is_enforced_while_streaming(self) -> None:
        class FakeProcess:
            def __init__(self) -> None:
                self.stdout = io.BytesIO(b"123456789")
                self.returncode = 0

            def kill(self) -> None:
                self.returncode = -1

            def wait(self, timeout: int | None = None) -> int:
                del timeout
                return self.returncode

        with (
            mock.patch.object(checker, "MAX_TREE_BYTES", 8),
            mock.patch.object(checker.subprocess, "Popen", return_value=FakeProcess()),
            self.assertRaisesRegex(ValueError, "Git object check failed"),
        ):
            checker._git(self.project, "ls-tree", "HEAD")

    def test_rejects_duplicate_json_keys(self) -> None:
        self._write("project-context-pack.json", '{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_rejects_excessive_json_nesting_without_traceback(self) -> None:
        with (
            mock.patch.object(checker.json, "loads", side_effect=RecursionError),
            self.assertRaisesRegex(ValueError, "JSON nesting exceeds the safe limit"),
        ):
            checker._json(self.project, "project-context-pack.json")

    def test_bounded_cli_fails_closed_on_worker_timeout(self) -> None:
        with (
            mock.patch.object(
                checker.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired([sys.executable], checker.CHECK_TIMEOUT_SECONDS),
            ),
            mock.patch.object(sys, "stderr", new_callable=io.StringIO) as stderr,
        ):
            result = checker._run_bounded_check(self.project, "project-context-pack.json")
        self.assertEqual(result, 1)
        self.assertIn("validation exceeded", stderr.getvalue())

    def test_bounded_cli_accepts_valid_pack(self) -> None:
        self.assertEqual(
            checker._run_bounded_check(self.project, "project-context-pack.json"),
            0,
        )

    def test_rejects_missing_metadata(self) -> None:
        self._write("context/security-model.md", "# Undeclared\n")
        with self.assertRaisesRegex(ValueError, "frontmatter"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_rejects_non_canonical_iso_dates(self) -> None:
        for invalid in ("20260918", "2026-W38-5", "2026-9-18"):
            with self.subTest(invalid=invalid):
                document = self._document("Security model").replace("2026-09-18", invalid)
                self._write("context/security-model.md", document)
                with self.assertRaisesRegex(ValueError, "invalid last_verified"):
                    checker.check_pack(self.project, "project-context-pack.json")

    def test_rejects_non_enforceable_max_length(self) -> None:
        document = self._document("Security model").replace(
            "max_length: 3 pages", "max_length: concise"
        )
        self._write("context/security-model.md", document)
        with self.assertRaisesRegex(ValueError, "invalid max_length"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_rejects_document_exceeding_max_length(self) -> None:
        document = self._document("Security model").replace(
            "max_length: 3 pages", "max_length: 1 page"
        )
        self._write(
            "context/security-model.md",
            document + ("word " * (checker.WORDS_PER_PAGE + 1)),
        )
        with self.assertRaisesRegex(ValueError, "exceeds max_length"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_rejects_architecture_overview_above_three_page_policy(self) -> None:
        document = self._document("Architecture overview").replace(
            "max_length: 3 pages", "max_length: 4 pages"
        )
        self._write("context/architecture-overview.md", document)
        with self.assertRaisesRegex(ValueError, "exceeds 3-page policy"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_non_architecture_document_may_declare_four_pages(self) -> None:
        document = self._document("Security model").replace(
            "max_length: 3 pages", "max_length: 4 pages"
        )
        self._write("context/security-model.md", document)
        checker.check_pack(self.project, "project-context-pack.json")

    def test_greenfield_rejects_invented_pattern(self) -> None:
        self.patterns["entries"] = [self._pattern()]
        self._write_pack()
        with self.assertRaisesRegex(ValueError, "invent incumbent precedent"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_greenfield_rejects_claimed_inventory(self) -> None:
        self.manifest["repository_map"]["paths"] = ["src/main.py"]
        self._write_pack()
        with self.assertRaisesRegex(ValueError, "must not claim a Git inventory"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_existing_rejects_unapproved_ratification(self) -> None:
        self._existing()
        pattern = self._pattern()
        pattern["state"] = "RATIFIED"
        self.patterns["entries"] = [pattern]
        self._write_pack()
        with self.assertRaisesRegex(ValueError, "lacks Architect"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_existing_rejects_provisional_approval_claim(self) -> None:
        self._existing()
        pattern = self._pattern()
        pattern["ratifier"] = "Architect"
        self.patterns["entries"] = [pattern]
        self._write_pack()
        with self.assertRaisesRegex(ValueError, "claims approval"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_existing_rejects_duplicate_pattern_id(self) -> None:
        self._existing()
        self.patterns["entries"] = [self._pattern(), self._pattern()]
        self._write_pack()
        with self.assertRaisesRegex(ValueError, "duplicate pattern ID"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_existing_rejects_non_canonical_or_invalid_pattern_dates(self) -> None:
        self._existing()
        for invalid in ("20260918", "2026-W38-5", "2026-02-30"):
            with self.subTest(invalid=invalid):
                pattern = self._pattern()
                pattern["date"] = invalid
                self.patterns["entries"] = [pattern]
                self._write_pack()
                with self.assertRaisesRegex(ValueError, "invalid pattern date"):
                    checker.check_pack(self.project, "project-context-pack.json")

    def test_existing_rejects_unknown_pattern_state(self) -> None:
        self._existing()
        pattern = self._pattern()
        pattern["state"] = "APPROVED"
        self.patterns["entries"] = [pattern]
        self._write_pack()
        with self.assertRaisesRegex(ValueError, "unsupported pattern state"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_existing_ratification_needs_decision_document(self) -> None:
        self._existing()
        pattern = self._pattern()
        pattern.update({"state": "RATIFIED", "ratifier": "Scott Wofford", "decision_record": "context/decision.md"})
        self.patterns["entries"] = [pattern]
        self._write_pack()
        with self.assertRaisesRegex(ValueError, "could not be opened safely"):
            checker.check_pack(self.project, "project-context-pack.json")
        self._write(
            "context/decision.md",
            self._document("Architect decision")
            + "\nPattern ID: PAT-001\nDecision: RATIFIED\n"
            "Ratified by: Scott Wofford\nDecision date: 2026-09-18\n",
        )
        checker.check_pack(self.project, "project-context-pack.json")

    def test_existing_rejects_mismatched_decision_record(self) -> None:
        self._existing()
        pattern = self._pattern()
        pattern.update({"state": "RATIFIED", "ratifier": "Scott Wofford", "decision_record": "context/decision.md"})
        self.patterns["entries"] = [pattern]
        self._write_pack()
        self._write("context/decision.md", self._document("Unrelated decision"))
        with self.assertRaisesRegex(ValueError, "does not match"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_rejects_unhashable_artifact_path_without_aborting(self) -> None:
        malformed = deepcopy(self.manifest)
        malformed["artifacts"]["security_model"] = []
        self._write("project-context-pack.json", json.dumps(malformed))
        with self.assertRaisesRegex(ValueError, "must be strings"):
            checker.check_pack(self.project, "project-context-pack.json")

    def test_rejects_unknown_manifest_field(self) -> None:
        self.manifest["automatic_approval"] = True
        self._write("project-context-pack.json", json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError, "context-pack manifest"):
            checker.check_pack(self.project, "project-context-pack.json")

    @staticmethod
    def _pattern() -> dict[str, object]:
        return {
            "id": "PAT-001",
            "pattern": "Observed boundary",
            "scope": "project docs",
            "state": "PROVISIONAL",
            "basis": "observed at source commit",
            "date": "2026-09-18",
            "ratifier": None,
            "decision_record": None,
        }


if __name__ == "__main__":
    unittest.main()
