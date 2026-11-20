"""Tests for verification/spec_tool_probe.py. No test installs a tool or starts an agent: the runner is a stand-in."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("spec_tool_probe", ROOT / "verification" / "spec_tool_probe.py")
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)

# built from parts so that the secret scanners of the pipeline do not read these made-up values as real ones
SECRETS = {
    "GITLAB_TOKEN": "glp" + "at-" + "x" * 16,
    "AWS_SECRET_ACCESS_KEY": "abcdefgh12345678",
    "HTTPS_PROXY": "http" + "://" + "u:p" + "@proxy",
    "MY_PASSWORD": "hunter22hunter",
}


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name).resolve()
        self.scratch = self.base / "scratch"
        self.scratch.mkdir()


class PlanTests(Base):
    def test_the_steps_run_in_order_and_the_install_is_pinned(self) -> None:
        for tool, pin in (("speckit", "@v1.3.0"), ("openspec", "@fission-ai/openspec@1.16.0")):
            steps = probe.plan(tool, self.scratch, "m", "cursor-agent")
            self.assertEqual([s["name"] for s in steps], ["install", "version", "init", "agent"])
            self.assertTrue(any(pin in part for part in steps[0]["argv"]), tool)
            self.assertFalse(any("latest" in part for part in steps[0]["argv"]), tool)

    def test_without_uv_a_pinned_uv_is_put_in_the_scratch_directory_first(self) -> None:
        steps = probe.plan("speckit", self.scratch, "m", "cursor-agent", have_uv=False)
        self.assertEqual([s["name"] for s in steps][:2], ["bootstrap-uv", "install"])
        self.assertIn("uv==" + probe.UV_VERSION, steps[0]["argv"])
        self.assertEqual(steps[0]["argv"][steps[0]["argv"].index("--target") + 1], str(self.scratch / "uv-boot"))
        self.assertEqual(steps[1]["argv"][1:3], ["-m", "uv"])
        self.assertEqual(probe.plan("speckit", self.scratch, "m", "a", have_uv=True)[0]["name"], "install")
        self.assertEqual(probe.plan("openspec", self.scratch, "m", "a", have_uv=False)[0]["name"], "install")

    def test_the_npm_install_goes_into_the_scratch_prefix(self) -> None:
        argv = probe.plan("openspec", self.scratch, "m", "a")[0]["argv"]
        self.assertEqual(argv[argv.index("--prefix") + 1], str(self.scratch / "npm"))
        self.assertTrue(str(self.scratch / "npm" / "node_modules" / ".bin") in probe.child_environment({"PATH": "p"}, "openspec", self.scratch)["PATH"])

    def test_the_prompt_is_on_stdin_and_not_in_the_command(self) -> None:
        agent = probe.plan("openspec", self.scratch, "m", "cursor-agent")[-1]
        self.assertIn("STOP before the tool's apply or implement step", agent["input"])
        self.assertTrue(all("throwaway" not in part for part in agent["argv"]))

    def test_agent_argv_sandbox_flag_and_force(self) -> None:
        on = probe.agent_argv("a", "m", True)
        off = probe.agent_argv("a", "m", False)
        self.assertIn("--sandbox", on)
        self.assertNotIn("--sandbox", off)
        for argv in (on, off):
            self.assertIn("--trust", argv)
            self.assertIn("--force", argv)
            self.assertEqual(argv[:3], ["a", "-p", "--output-format"])

    def test_the_sandbox_is_asked_for_only_off_windows(self) -> None:
        with mock.patch.object(probe.sys, "platform", "linux"):
            self.assertIn("--sandbox", probe.plan("openspec", self.scratch, "m", "a")[-1]["argv"])
        with mock.patch.object(probe.sys, "platform", "win32"):
            self.assertNotIn("--sandbox", probe.plan("openspec", self.scratch, "m", "a")[-1]["argv"])

    def test_the_prompt_names_no_case_of_any_suite(self) -> None:
        cases = ROOT / "profiles" / "qualification-eval"
        ids = {p.name for p in (cases / "reference-app" / "cases").iterdir() if p.is_dir()}
        for suite in cases.glob("suite-v*.json"):
            text = suite.read_text(encoding="utf-8")
            ids |= {m for m in __import__("re").findall(r"\bM[0-9]-[A-Z]+-[0-9]+\b", text)}
        self.assertTrue(ids)
        for tool in probe.TOOLS:
            prompt = probe.build_prompt(tool)
            self.assertEqual([i for i in ids if i in prompt], [], tool)


class ArmTests(Base):
    def test_the_aidf_arm_has_one_step_and_no_install(self) -> None:
        steps = probe.plan("aidf", self.scratch, "m", "cursor-agent")
        self.assertEqual([s["name"] for s in steps], ["agent"])
        self.assertIn("task-contract.md", steps[0]["input"])
        self.assertIn("STOP before implementing", steps[0]["input"])

    def test_a_custom_change_is_in_the_prompt_of_every_arm(self) -> None:
        for tool in probe.TOOLS:
            self.assertIn("add pagination to list_items", probe.build_prompt(tool, "add pagination to list_items"))

    def test_an_extra_instruction_is_appended_to_the_prompt_of_every_arm(self) -> None:
        for tool in probe.TOOLS:
            plain = probe.build_prompt(tool)
            with_extra = probe.build_prompt(tool, extra="Begin with a section named Read first.")
            self.assertTrue(with_extra.startswith(plain.rstrip()))
            self.assertTrue(with_extra.rstrip().endswith("Begin with a section named Read first."))
        self.assertEqual(probe.build_prompt("aidf", extra="  "), probe.build_prompt("aidf"))
        agent = probe.plan("aidf", self.scratch, "m", "a", extra="Read first.")[-1]
        self.assertIn("Read first.", agent["input"])

    def test_the_aidf_arm_gets_the_framework_documents(self) -> None:
        ws = probe.make_workspace(self.scratch, "aidf")
        for name in probe.AIDF_DOCS:
            self.assertTrue((ws / "aidf" / name).is_file(), name)
        (self.base / "second").mkdir()
        other = probe.make_workspace(self.base / "second", "openspec")
        self.assertFalse((other / "aidf").exists())

    def test_a_sample_directory_is_copied_instead_of_the_built_in_files(self) -> None:
        sample = self.base / "sample"
        sample.mkdir()
        (sample / "inventory.py").write_text("x = 1\n", encoding="utf-8")
        (sample / "__pycache__").mkdir()
        (sample / "__pycache__" / "junk.pyc").write_text("j", encoding="utf-8")
        ws = probe.make_workspace(self.scratch, "openspec", sample)
        self.assertTrue((ws / "inventory.py").is_file())
        self.assertFalse((ws / "slug.py").exists())
        self.assertFalse((ws / "__pycache__").exists())

    def test_collect_copies_only_the_artifact_roots_and_redacts(self) -> None:
        ws = self.scratch / "workspace"
        (ws / "openspec" / "changes" / "c").mkdir(parents=True)
        (ws / ".cursor").mkdir()
        (ws / "openspec" / "changes" / "c" / "proposal.md").write_text(f"see {ws}/x", encoding="utf-8")
        (ws / ".cursor" / "skill.md").write_text("scaffold", encoding="utf-8")
        out = self.base / "collected"
        copied = probe.collect_artifacts("openspec", ws, ["openspec/changes/c/proposal.md", ".cursor/skill.md"], out)
        self.assertEqual(copied, ["openspec/changes/c/proposal.md"])
        text = (out / "openspec" / "openspec" / "changes" / "c" / "proposal.md").read_text(encoding="utf-8")
        self.assertNotIn(str(ws), text)
        self.assertFalse((out / "openspec" / ".cursor").exists())

    def test_a_file_named_like_an_exact_root_but_longer_is_not_collected(self) -> None:
        ws = self.scratch / "workspace"
        ws.mkdir()
        (ws / "task-contract.md").write_text("ok", encoding="utf-8")
        (ws / "task-contract.md.evil").write_text("no", encoding="utf-8")
        out = self.base / "collected"
        self.assertEqual(probe.collect_artifacts("aidf", ws, ["task-contract.md", "task-contract.md.evil"], out), ["task-contract.md"])
        self.assertFalse((out / "aidf" / "task-contract.md.evil").exists())

    def test_a_junction_or_a_directory_under_an_artifact_root_is_skipped_not_read(self) -> None:
        ws = self.scratch / "workspace"
        (ws / "specs").mkdir(parents=True)
        (ws / "specs" / "a.md").write_text("ok", encoding="utf-8")
        (ws / "specs" / "adir").mkdir()
        added = ["specs/a.md", "specs/adir"]
        if sys.platform == "win32":
            outside = self.base / "outside"
            outside.mkdir()
            (outside / "secret.md").write_text("s", encoding="utf-8")
            done = subprocess.run(["cmd", "/c", "mklink", "/J", str(ws / "specs" / "junc"), str(outside)], capture_output=True, text=True, check=False)
            if done.returncode == 0:
                added.append("specs/junc")
        out = self.base / "collected"
        self.assertEqual(probe.collect_artifacts("speckit", ws, added, out), ["specs/a.md"])
        self.assertFalse((out / "speckit" / "specs" / "junc").exists())

    def test_a_symbolic_link_to_a_file_outside_is_skipped_not_read(self) -> None:
        ws = self.scratch / "workspace"
        (ws / "specs").mkdir(parents=True)
        outside = self.base / "outside.md"
        outside.write_text("secret", encoding="utf-8")
        try:
            (ws / "specs" / "l.md").symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("this account cannot create a symbolic link")
        out = self.base / "collected"
        self.assertEqual(probe.collect_artifacts("speckit", ws, ["specs/l.md"], out), [])
        self.assertFalse((out / "speckit" / "specs" / "l.md").exists())

    def test_run_probe_collects_what_the_agent_step_added(self) -> None:
        def run(argv: list[str], cwd: Path, env: dict[str, str], timeout: int, input_text: str | None = None) -> dict[str, Any]:
            (cwd / "task-contract.md").write_text("# contract", encoding="utf-8")
            return {"exit": 0, "stdout": "ok", "stderr": "", "seconds": 1.0}

        out = self.base / "collected"
        record = probe.run_probe("aidf", self.scratch, "m", "cursor-agent", {"PATH": "x"}, run, collect=out)
        self.assertEqual(record["collected"], ["task-contract.md"])
        self.assertTrue((out / "aidf" / "task-contract.md").is_file())
        self.assertTrue(record["answers"]["a_install"].startswith("not applicable"))
        self.assertIn("code files written: none", record["answers"]["d_writes_and_stop"])

    def test_other_code_suffixes_are_reported_and_scaffold_scripts_are_not(self) -> None:
        def run(argv: list[str], cwd: Path, env: dict[str, str], timeout: int, input_text: str | None = None) -> dict[str, Any]:
            (cwd / "app.js").write_text("x", encoding="utf-8")
            (cwd / "run.ps1").write_text("x", encoding="utf-8")
            (cwd / ".specify").mkdir()
            (cwd / ".specify" / "setup.ps1").write_text("x", encoding="utf-8")
            (cwd / "notes.md").write_text("x", encoding="utf-8")
            return {"exit": 0, "stdout": "ok", "stderr": "", "seconds": 1.0}

        record = probe.run_probe("aidf", self.scratch, "m", "cursor-agent", {"PATH": "x"}, run)
        said = record["answers"]["d_writes_and_stop"]
        self.assertIn("app.js", said)
        self.assertIn("run.ps1", said)
        self.assertNotIn("setup.ps1", said)
        self.assertNotIn("notes.md", said)

    def test_a_py_file_written_in_the_sample_is_reported_as_code(self) -> None:
        def run(argv: list[str], cwd: Path, env: dict[str, str], timeout: int, input_text: str | None = None) -> dict[str, Any]:
            (cwd / "inventory.py").write_text("changed", encoding="utf-8")
            return {"exit": 0, "stdout": "ok", "stderr": "", "seconds": 1.0}

        sample = self.base / "sample"
        sample.mkdir()
        (sample / "inventory.py").write_text("x", encoding="utf-8")
        record = probe.run_probe("aidf", self.scratch, "m", "cursor-agent", {"PATH": "x"}, run, sample=sample)
        self.assertIn("inventory.py", record["answers"]["d_writes_and_stop"])


class EnvironmentTests(Base):
    def source(self) -> dict[str, str]:
        return {"PATH": "/usr/bin", "HOME": "/home/u", "USERPROFILE": "C:/Users/u", "EDITOR": "vi", **SECRETS}

    def test_no_secret_and_no_unlisted_variable_is_passed(self) -> None:
        env = probe.child_environment(self.source(), "openspec", self.scratch)
        for name in SECRETS:
            self.assertNotIn(name, env)
        self.assertNotIn("EDITOR", env)
        self.assertIn("USERPROFILE", env)

    def test_telemetry_is_off_for_each_tool(self) -> None:
        self.assertEqual(probe.child_environment(self.source(), "openspec", self.scratch)["OPENSPEC_TELEMETRY"], "0")
        for tool in ("openspec", "speckit"):
            self.assertEqual(probe.child_environment(self.source(), tool, self.scratch)["DO_NOT_TRACK"], "1")

    def test_prefixes_and_caches_are_inside_the_scratch_directory(self) -> None:
        env = probe.child_environment(self.source(), "speckit", self.scratch)
        for name in ("UV_TOOL_DIR", "UV_TOOL_BIN_DIR", "UV_CACHE_DIR", "NPM_CONFIG_PREFIX", "NPM_CONFIG_CACHE", "RUFF_CACHE_DIR", "PYTHONPYCACHEPREFIX"):
            self.assertTrue(Path(env[name]).is_relative_to(self.scratch), name)
        self.assertTrue(env["PATH"].startswith(str(self.scratch / "uv-bin")))


class RunTests(Base):
    def runner(self, installs: bool = True, writes_code: bool = False, init_ok: bool = True) -> Any:
        calls: list[str] = []

        def run(argv: list[str], cwd: Path, env: dict[str, str], timeout: int, input_text: str | None = None) -> dict[str, Any]:
            name = {"install": "install", "--version": "version"}.get(argv[1] if len(argv) > 1 else "", None)
            if argv[0] in ("npm", "uv") or "pip" in argv or "uv" in argv[1:3]:
                name = "install"
            elif argv[1:2] == ["--version"]:
                name = "version"
            elif argv[0] == "cursor-agent":
                name = "agent"
            else:
                name = "init"
            calls.append(name)
            if name == "install":
                return {"exit": 0 if installs else 1, "stdout": "", "stderr": "", "seconds": 1.0}
            if name == "init":
                if init_ok:
                    (cwd / ".cursor").mkdir(exist_ok=True)
                    (cwd / ".cursor" / "rules.md").write_text("r", encoding="utf-8")
                return {"exit": 0 if init_ok else 2, "stdout": f"wrote under {cwd}", "stderr": "", "seconds": 2.0}
            if name == "agent":
                (cwd / "spec.md").write_text("spec", encoding="utf-8")
                if writes_code:
                    (cwd / "slug.py").write_text("changed", encoding="utf-8")
                return {"exit": 0, "stdout": "done", "stderr": "", "seconds": 3.0}
            return {"exit": 0, "stdout": "1.0", "stderr": "", "seconds": 0.1}

        run.calls = calls  # type: ignore[attr-defined]
        return run

    def test_a_full_probe_records_init_and_agent_writes_separately(self) -> None:
        run = self.runner()
        record = probe.run_probe("openspec", self.scratch, "m", "cursor-agent", {"PATH": "x"}, run)
        steps = {s["name"]: s for s in record["steps"]}
        self.assertEqual(steps["init"]["writes"]["added"], [".cursor/rules.md"])
        self.assertEqual(steps["agent"]["writes"]["added"], ["spec.md"])
        self.assertEqual(steps["agent"]["writes"]["changed"], [])
        self.assertIn("code files written: none", record["answers"]["d_writes_and_stop"])
        self.assertTrue(steps["agent"]["prompt_on_stdin"])

    def test_a_code_file_written_before_the_stop_is_reported(self) -> None:
        record = probe.run_probe("speckit", self.scratch, "m", "cursor-agent", {"PATH": "x"}, self.runner(writes_code=True))
        self.assertIn("slug.py", record["answers"]["d_writes_and_stop"])
        self.assertNotIn("code files written: none", record["answers"]["d_writes_and_stop"])

    def test_a_failed_install_stops_the_probe(self) -> None:
        run = self.runner(installs=False)
        record = probe.run_probe("openspec", self.scratch, "m", "cursor-agent", {"PATH": "x"}, run)
        self.assertEqual(run.calls, ["install"])
        self.assertIn("stopped", record)
        self.assertTrue(record["answers"]["a_install"].startswith("no:"))
        self.assertTrue(record["answers"]["c_headless_flow"].startswith("not answered"))

    def test_a_failed_uv_bootstrap_stops_the_probe(self) -> None:
        calls: list[str] = []

        def run(argv: list[str], cwd: Path, env: dict[str, str], timeout: int, input_text: str | None = None) -> dict[str, Any]:
            calls.append(argv[0] if "pip" not in argv else "pip")
            return {"exit": 1, "stdout": "", "stderr": "no network", "seconds": 0.1}

        with mock.patch.object(probe.shutil, "which", return_value=None):
            record = probe.run_probe("speckit", self.scratch, "m", "cursor-agent", {"PATH": "x"}, run)
        self.assertEqual(calls, ["pip"])
        self.assertEqual([s["name"] for s in record["steps"]], ["bootstrap-uv"])
        self.assertIn("stopped", record)
        self.assertTrue(record["answers"]["a_install"].startswith("no:"))

    def test_a_failed_init_does_not_start_the_agent(self) -> None:
        run = self.runner(init_ok=False)
        record = probe.run_probe("openspec", self.scratch, "m", "cursor-agent", {"PATH": "x"}, run)
        self.assertNotIn("agent", run.calls)
        self.assertIn("init did not succeed", record["stopped"])

    def test_a_missing_program_is_an_answer_not_a_crash(self) -> None:
        result = probe.run_step(["definitely-not-a-program-xyz"], self.scratch, {"PATH": ""}, 5)
        self.assertIsNone(result["exit"])
        self.assertIn("not found", result["error"])


class RecordTests(Base):
    def test_the_written_record_names_no_path_of_the_machine(self) -> None:
        record = probe.run_probe("openspec", self.scratch, "m", "cursor-agent", {"PATH": "x"}, RunTests("test_a_full_probe_records_init_and_agent_writes_separately").runner())
        out = self.base / "out"
        target = probe.write_probe_record(record, out, self.scratch, ROOT)
        text = target.read_text(encoding="utf-8")
        self.assertNotIn(str(self.scratch), text)
        self.assertNotIn(str(self.scratch).replace("\\", "/"), text)
        self.assertNotIn(str(Path.home()), text)
        self.assertIn("<workspace>", text)
        self.assertEqual(json.loads(text)["tool"], "openspec")

    def test_a_record_path_that_is_a_hard_link_is_refused(self) -> None:
        victim = self.base / "victim.txt"
        victim.write_text("keep", encoding="utf-8")
        out = self.base / "out"
        out.mkdir()
        try:
            os.link(victim, out / "openspec-probe.json")
        except (OSError, NotImplementedError):
            self.skipTest("this account cannot create a hard link")
        with self.assertRaises(SystemExit):
            probe.write_probe_record({"tool": "openspec"}, out, self.scratch, ROOT)
        self.assertEqual(victim.read_text(encoding="utf-8"), "keep")

    def test_an_out_dir_inside_the_scratch_directory_is_refused(self) -> None:
        with self.assertRaises(SystemExit):
            probe.write_probe_record({"tool": "openspec"}, self.scratch / "out", self.scratch, ROOT)


class MainTests(Base):
    def test_a_dry_run_starts_nothing_and_creates_no_scratch(self) -> None:
        with mock.patch.object(probe.subprocess, "run", side_effect=AssertionError("started a process")):
            self.assertEqual(probe.main(["openspec", "--out-dir", str(self.base / "o"), "--dry-run"]), 0)
        self.assertFalse((self.base / "o").exists())

    def test_a_scratch_directory_inside_the_repository_is_refused(self) -> None:
        self.assertEqual(probe.main(["openspec", "--out-dir", str(self.base / "o"), "--scratch", str(ROOT / "verification" / "x")]), 1)


if __name__ == "__main__":
    unittest.main()
