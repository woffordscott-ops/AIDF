"""Tests for verification/run_review.py. The reviewer is a small Python script; no test starts a real reviewer."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("run_review", ROOT / "verification" / "run_review.py")
assert SPEC and SPEC.loader
run_review = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = run_review
SPEC.loader.exec_module(run_review)

REPORT = "verification/x-verifier-report-round1.md"
STAND_IN = r'''
import json, os, subprocess, sys
mode, checkout = sys.argv[1], sys.argv[2]
def out(text):
    sys.stdout.buffer.write(text.encode("utf-8"))
if mode == "env":
    out(json.dumps(sorted(os.environ)) + "\nOutcome: PASS\n")
elif mode == "crlf":
    out("# Report\r\n\r\nOutcome: PASS\r\n")
elif mode == "noline":
    out("# Report\nno outcome here\n")
elif mode == "trailing":
    out("Outcome: PASS\nthanks\n")
elif mode == "marker":
    open(os.path.join(os.path.dirname(sys.argv[3]), "reviewer-started.marker"), "w").write("started")
    out("Outcome: PASS\n")
elif mode == "twooutcomes":
    out("# Report\nOutcome: BLOCKED\nmore text\nOutcome: PASS\n")
elif mode == "quotedoutcome":
    out("# Report\n  Outcome: BLOCKED\n> Outcome: BLOCKED\nthe line Outcome: BLOCKED is quoted\nOutcome: PASS\n")
elif mode == "caches":
    names = ("RUFF_CACHE_DIR", "MYPY_CACHE_DIR", "PYTHONPYCACHEPREFIX", "PYTEST_ADDOPTS")
    out(json.dumps({name: os.environ.get(name) for name in names}) + "\nOutcome: PASS\n")
elif mode == "ruffcache":
    os.makedirs(os.environ["RUFF_CACHE_DIR"], exist_ok=True)
    open(os.path.join(os.environ["RUFF_CACHE_DIR"], "x"), "w").write("cache")
    out("Outcome: PASS\n")
elif mode == "ownclonecache":
    os.makedirs(os.path.join(checkout, ".mypy_cache"), exist_ok=True)
    open(os.path.join(checkout, ".mypy_cache", "x"), "w").write("cache")
    out("Outcome: PASS\n")
elif mode == "edit":
    open(os.path.join(checkout, "app.txt"), "w").write("changed")
    out("Outcome: PASS\n")
elif mode == "untracked":
    open(os.path.join(checkout, "new.txt"), "w").write("x")
    out("Outcome: PASS\n")
elif mode == "move":
    subprocess.run(["git", "-C", checkout, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "--allow-empty", "-q", "-m", "x"], check=True)
    out("Outcome: PASS\n")
elif mode == "update-ref":
    subprocess.run(["git", "-C", checkout, "update-ref", "refs/heads/stolen", "HEAD"], check=True)
    out("Outcome: PASS\n")
elif mode == "hookplant":
    open(os.path.join(sys.argv[4], "post-index-change"), "w").write("#!/bin/sh\nexit 0\n")
    out("Outcome: PASS\n")
elif mode == "filter":
    marker = sys.argv[4]
    open(os.path.join(checkout, ".git", "config"), "a").write("[filter \"x\"]\n\tclean = sh -c 'echo ran > " + marker.replace(os.sep, "/") + "'\n")
    os.makedirs(os.path.join(checkout, ".git", "info"), exist_ok=True)
    open(os.path.join(checkout, ".git", "info", "attributes"), "a").write("* filter=x\n")
    out("Outcome: PASS\n")
elif mode == "hidden":
    open(os.path.join(checkout, "app.txt"), "w").write("changed")
    subprocess.run(["git", "-C", checkout, "update-index", "--skip-worktree", "app.txt"], check=True)
    out("Outcome: PASS\n")
elif mode == "outlink":
    os.symlink(sys.argv[4], os.path.join(os.path.dirname(sys.argv[3]), "answer.bin"))
    out("Outcome: PASS\n")
elif mode == "rootconfig":
    open(os.path.join(sys.argv[4], ".git", "config"), "a").write("[core]\n\tabbrev = 9\n")
    out("Outcome: PASS\n")
elif mode == "namedfile":
    open(os.path.join(checkout, os.environ["REVIEW_TEST_KEY"]), "w").write("x")
    out("Outcome: PASS\n")
elif mode == "outswap":
    outdir = os.path.dirname(sys.argv[3])
    os.rename(outdir, outdir + ".aside")
    os.symlink(sys.argv[4], outdir)
    out("Outcome: PASS\n")
elif mode == "stderr127":
    sys.stderr.write("cannot start the reviewer: " + os.environ.get("REVIEW_TEST_KEY", "") + " \x1b[8m hidden\n")
    sys.exit(127)
elif mode == "secret":
    out("the key is " + os.environ.get("REVIEW_TEST_KEY", "") + "\nOutcome: PASS\n")
elif mode == "origin":
    subprocess.run(["git", "-C", sys.argv[4], "update-ref", "refs/heads/touched", "HEAD"], check=True)
    out("Outcome: PASS\n")
elif mode == "grandchild":
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(90)"])
    open(sys.argv[4], "w").write(str(child.pid))
    import time; time.sleep(90)
elif mode == "pidsleep":
    open(sys.argv[4], "w").write(str(os.getpid()))
    import time; time.sleep(90)
elif mode == "empty":
    pass
elif mode == "link":
    os.symlink(os.path.join(os.path.dirname(sys.argv[4]), "elsewhere-target"), os.path.join(sys.argv[4], sys.argv[5]))
    out("Outcome: PASS\n")
elif mode == "orphan":
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(90)"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    open(sys.argv[4], "w").write(str(child.pid))
    out("Outcome: PASS\n")
elif mode == "selfkill":
    import signal
    os.kill(os.getpid(), signal.SIGKILL)
elif mode == "nul":
    out("Outcome: PASS\0\nOutcome: PASS\n")
elif mode == "big":
    out("x" * (1024 * 1024 + 1) + "\nOutcome: PASS\n")
elif mode == "latin1":
    sys.stdout.buffer.write(b"caf\xe9\nno outcome\n")
elif mode == "fail":
    out("Outcome: PASS\n"); sys.exit(3)
elif mode == "sleep":
    import time; time.sleep(30)
elif mode == "echo":
    out("read from a file: " + sys.argv[4] + "\nOutcome: PASS\n")
else:
    out("Outcome: PASS\n")
'''


def pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        listing = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, check=False).stdout
        return str(pid) in listing
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        state = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()[0]
    except (OSError, IndexError):
        return True
    return state != "Z"


def stop(pid: int) -> None:
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, check=False)
    else:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


class Fixture:
    def __init__(self, preflight_exit: int = 0, autocrlf: str | None = None):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        base = Path(self.tmp.name)
        self.repo = base / "repo"
        self.repo.mkdir()
        self.out = base / "out"
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.name", "t")
        git(self.repo, "config", "user.email", "t@t")
        if autocrlf:
            git(self.repo, "config", "core.autocrlf", autocrlf)
        (self.repo / "verification").mkdir()
        (self.repo / "app.txt").write_text("app\n", encoding="utf-8")
        (self.repo / "verification" / "preflight.py").write_text(
            f"import sys\nprint('PREFLIGHT-OUTPUT', sys.argv[1:])\nsys.exit({preflight_exit})\n", encoding="utf-8"
        )
        (self.repo / "verification" / "x-task-contract.json").write_text(
            json.dumps({"declared_scope": ["app.txt", "verification/tests/**", REPORT, "verification/x-verifier-report-round*.md"]}), encoding="utf-8"
        )
        (self.repo / "verification" / "x-evidence-pack.json").write_text("{}", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "base")
        self.head = git(self.repo, "rev-parse", "HEAD")
        self.script = base / "stand_in.py"
        self.script.write_text(STAND_IN, encoding="utf-8")
        self.brief = base / "brief.txt"
        self.brief.write_text("Check the thing.\n", encoding="utf-8")

    def close(self) -> None:
        self.tmp.cleanup()

    def run(
        self, mode: str, *extra: str, env: dict[str, str] | None = None, report: str = REPORT, reviewer_args: tuple[str, ...] = (),
        command_override: list[str] | None = None, model: str = "m",
    ) -> tuple[int, str]:
        argv = self.argv(mode, *extra, report=report, reviewer_args=reviewer_args, command_override=command_override, model=model)
        buffer = io.StringIO()
        with mock.patch.dict(os.environ, env or {}), contextlib.redirect_stdout(buffer):
            status = run_review.main(argv)
        return status, buffer.getvalue()

    def argv(
        self, mode: str, *extra: str, report: str = REPORT, reviewer_args: tuple[str, ...] = (),
        command_override: list[str] | None = None, model: str = "m",
    ) -> list[str]:
        command = json.dumps(command_override or [sys.executable, str(self.script), mode, "{checkout}", "{brief_file}", *reviewer_args])
        return [
            "--root", str(self.repo), "--contract", "verification/x-task-contract.json", "--evidence", "verification/x-evidence-pack.json",
            "--brief", str(self.brief), "--report", report, "--out", str(self.out), "--reviewer-command", command, *(["--model", model] if model else []), *extra,
        ]

    def log(self) -> dict[str, object]:
        return json.loads((self.out / "review-run.json").read_text(encoding="utf-8"))

    def commits(self) -> int:
        return int(git(self.repo, "rev-list", "--count", "HEAD"))


class FixtureCase(unittest.TestCase):
    def fixture(self, **kwargs: object) -> Fixture:
        fixture = Fixture(**kwargs)  # type: ignore[arg-type]
        self.addCleanup(fixture.close)
        return fixture


class StartTests(FixtureCase):
    def test_a_dirty_tracked_tree_is_refused(self):
        fx = self.fixture()
        (fx.repo / "app.txt").write_text("dirty\n", encoding="utf-8")
        status, out = fx.run("ok")
        self.assertEqual(1, status)
        self.assertIn("uncommitted tracked changes", out)
        self.assertEqual(1, fx.commits())

    def test_a_head_that_is_not_the_current_head_is_refused(self):
        fx = self.fixture()
        (fx.repo / "app.txt").write_text("two\n", encoding="utf-8")
        git(fx.repo, "commit", "-qam", "two")
        status, out = fx.run("ok", "--head", fx.head)
        self.assertEqual(1, status)
        self.assertIn("not the current HEAD", out)

    def test_a_previous_head_that_is_not_an_ancestor_is_refused(self):
        fx = self.fixture()
        git(fx.repo, "checkout", "-q", "-b", "other")
        (fx.repo / "app.txt").write_text("other\n", encoding="utf-8")
        git(fx.repo, "commit", "-qam", "other")
        side = git(fx.repo, "rev-parse", "HEAD")
        git(fx.repo, "checkout", "-q", fx.head)
        status, out = fx.run("ok", "--previous", side)
        self.assertEqual(1, status)
        self.assertIn("not an ancestor", out)

    def test_an_output_directory_inside_the_repository_is_refused(self):
        fx = self.fixture()
        fx.out = fx.repo / "inside"
        status, out = fx.run("ok")
        self.assertEqual(1, status)
        self.assertIn("outside the repository", out)

    def test_the_clone_has_its_own_refs_and_no_origin(self):
        fx = self.fixture()
        status, out = fx.run("update-ref")
        self.assertEqual(0, status, out)
        self.assertNotIn("stolen", git(fx.repo, "for-each-ref"))
        self.assertEqual("", git(fx.out / "checkout", "remote"))


class PreflightTests(FixtureCase):
    def test_a_failing_preflight_blocks_the_reviewer(self):
        fx = self.fixture(preflight_exit=1)
        status, out = fx.run("ok")
        self.assertEqual(1, status)
        self.assertIn("preflight failed", out)
        self.assertFalse((fx.out / "answer.bin").exists())
        self.assertEqual(1, fx.commits())

    def test_a_skipped_preflight_is_written_into_the_brief_and_the_log(self):
        fx = self.fixture(preflight_exit=1)
        status, out = fx.run("ok", "--skip-preflight", "ci is down")
        self.assertEqual(0, status, out)
        self.assertIn("SKIPPED by the human: ci is down", (fx.out / "brief.md").read_text(encoding="utf-8"))
        self.assertEqual("ci is down", fx.log()["preflight_skipped"])

    def test_the_preflight_output_and_the_header_are_in_the_brief(self):
        fx = self.fixture()
        status, out = fx.run("ok", "--preflight-arg=--offline", "--previous", fx.head)
        self.assertEqual(0, status, out)
        brief = (fx.out / "brief.md").read_text(encoding="utf-8")
        for expected in ("PREFLIGHT-OUTPUT", "--offline", fx.head, f"git diff {fx.head} {fx.head}", "Check the thing.", "Outcome: PASS_WITH_ADVISORIES"):
            self.assertIn(expected, brief)


class EnvironmentTests(FixtureCase):
    def test_only_the_allowlist_and_the_passed_names_arrive(self):
        fx = self.fixture()
        hostile = {"GIT_ALLOW_PROTOCOL": "file", "GITLAB_TOKEN": "tok-12345678", "MY_PRIVATE": "v", "REVIEW_TEST_KEY": "key-12345678", "PYTHONPATH": "x"}
        status, out = fx.run("env", "--pass-env", "REVIEW_TEST_KEY", env=hostile)
        self.assertEqual(0, status, out)
        names = {name.upper() for name in json.loads((fx.out / "answer.bin").read_text(encoding="utf-8").splitlines()[0])}
        self.assertIn("REVIEW_TEST_KEY", names)
        for gone in ("GIT_ALLOW_PROTOCOL", "GITLAB_TOKEN", "MY_PRIVATE", "PYTHONPATH"):
            self.assertNotIn(gone, names)
        self.assertEqual(set(), {n for n in names if n.startswith("GIT_")})
        self.assertNotIn("key-12345678", json.dumps(fx.log()))
        self.assertEqual(["REVIEW_TEST_KEY"], fx.log()["passed_variables"])

    def test_a_passed_git_variable_or_a_missing_one_is_refused(self):
        fx = self.fixture()
        status, out = fx.run("ok", "--pass-env", "GIT_SSH_COMMAND")
        self.assertEqual(1, status)
        self.assertIn("never passed", out)
        fx2 = self.fixture()
        status, out = fx2.run("ok", "--pass-env", "NO_SUCH_VARIABLE_FOR_TEST")
        self.assertEqual(1, status)
        self.assertIn("not set", out)

    def test_a_batch_launcher_refuses_arguments_with_shell_characters(self):
        self.assertIsNone(run_review.unsafe_for_batch_launcher(["-p", "--model", "claude-opus-5-5-high", "C:\\Users\\a b\\brief.md"]))
        for bad in ("a & calc", "a|b", "100%", 'say "x"', "a\nb", "^x", "a>b"):
            self.assertEqual(bad, run_review.unsafe_for_batch_launcher(["ok", bad]))

    def test_the_default_profile_carries_the_documented_flags_and_the_brief_by_path(self):
        command = run_review.build_command(
            run_review.default_profile("linux"), {"executable": "agent", "model": "m", "brief_file": "/tmp/b.md", "checkout": "/c"}
        )
        self.assertEqual(["agent", "-p", "--output-format", "text", "--trust", "--force", "--sandbox", "enabled", "--model", "m"], command[:10])
        self.assertIn("/tmp/b.md", command[-1])


class AnswerTests(FixtureCase):
    def test_a_crlf_answer_is_committed_byte_for_byte_when_autocrlf_is_true(self):
        fx = self.fixture(autocrlf="true")
        status, out = fx.run("crlf")
        self.assertEqual(0, status, out)
        answer = (fx.out / "answer.bin").read_bytes()
        self.assertIn(b"\r\n", answer)
        blob = subprocess.run(["git", "cat-file", "blob", f"HEAD:{REPORT}"], cwd=fx.repo, check=True, capture_output=True).stdout
        self.assertEqual(hashlib.sha256(answer).hexdigest(), hashlib.sha256(blob).hexdigest())
        self.assertEqual(answer, (fx.repo / REPORT).read_bytes())
        self.assertEqual(REPORT, git(fx.repo, "show", "--name-only", "--format=", "HEAD"))
        self.assertEqual(fx.head, git(fx.repo, "rev-parse", "HEAD~1"))

    def test_an_answer_without_an_outcome_line_or_with_text_after_it_is_rejected(self):
        for mode in ("noline", "trailing"):
            fx = self.fixture()
            status, _out = fx.run(mode)
            self.assertEqual(1, status, mode)
            self.assertTrue((fx.out / "answer.rejected").exists(), mode)
            self.assertEqual(1, fx.commits(), mode)
            self.assertFalse((fx.repo / REPORT).exists(), mode)

    def test_a_nonconforming_answer_is_committed_only_with_a_stated_waiver(self):
        fx = self.fixture()
        status, out = fx.run("noline", "--accept-nonconforming", "reviewer added a closing paragraph")
        self.assertEqual(0, status, out)
        self.assertIn("WAIVER", out)
        self.assertEqual("reviewer added a closing paragraph", fx.log()["accepted_nonconforming"])
        self.assertEqual(2, fx.commits())

    def test_outcome_line_reading(self):
        self.assertEqual(("BLOCKED", ""), run_review.outcome_line(b"x\r\nOutcome: BLOCKED\r\n\r\n"))
        self.assertEqual("PASS_WITH_ADVISORIES", run_review.outcome_line(b"Outcome: PASS_WITH_ADVISORIES")[0])
        for bad in (b"", b"Outcome: PASS now", b"outcome: PASS", b"Outcome: PASS\nbye", b"\xff\xfe"):
            self.assertIsNone(run_review.outcome_line(bad)[0], bad)

    def test_an_answer_with_the_value_of_a_secret_variable_is_refused(self):
        key = "key-12345678"
        cases = (
            ("secret", ("--pass-env", "REVIEW_TEST_KEY"), (), {"REVIEW_TEST_KEY": key}),
            ("echo", (), (key,), {"MY_API_KEY": key}),
        )
        for mode, passed, reviewer_args, env in cases:
            fx = self.fixture()
            status, out = fx.run(mode, *passed, env=env, reviewer_args=reviewer_args)
            self.assertEqual(1, status, mode)
            self.assertIn("contains the value of the variable", out, mode)
            self.assertNotIn(key, out, mode)
            self.assertNotIn(key, (fx.out / "review-run.json").read_text(encoding="utf-8"), mode)
            self.assertEqual(1, fx.commits(), mode)
        fx = self.fixture()
        status, out = fx.run("echo", env={"HARMLESS_SETTING": "value-12345678"}, reviewer_args=("value-12345678",))
        self.assertEqual(0, status, out)

    def test_a_reviewer_that_exits_with_an_error_commits_nothing(self):
        fx = self.fixture()
        status, out = fx.run("fail")
        self.assertEqual(1, status)
        self.assertIn("exited with status 3", out)
        self.assertEqual(1, fx.commits())

    def test_a_timeout_kills_the_reviewer_and_commits_nothing(self):
        fx = self.fixture()
        status, out = fx.run("sleep", "--timeout", "1")
        self.assertEqual(1, status)
        self.assertIn("past the timeout", out)
        self.assertEqual(1, fx.commits())


class CheckoutIntegrityTests(FixtureCase):
    def test_a_reviewer_that_changes_the_checkout_makes_the_run_invalid(self):
        for mode in ("edit", "untracked", "move"):
            fx = self.fixture()
            status, out = fx.run(mode)
            self.assertEqual(1, status, mode)
            self.assertIn("the run is invalid", out, mode)
            self.assertTrue(fx.log()["invalid_run"], mode)
            self.assertEqual(1, fx.commits(), mode)

    def test_a_change_to_the_origin_repository_makes_the_run_invalid(self):
        fx = self.fixture()
        status, out = fx.run("origin", reviewer_args=(str(fx.repo),))
        self.assertEqual(1, status)
        self.assertIn("the repository the tool ran in changed", out)
        self.assertEqual(1, fx.commits())
        self.assertIn("touched", git(fx.repo, "for-each-ref"))


class CommitTests(FixtureCase):
    def test_a_report_path_outside_the_declared_scope_is_refused(self):
        fx = self.fixture()
        status, out = fx.run("ok", report="verification/elsewhere.md")
        self.assertEqual(1, status)
        self.assertIn("declared_scope", out)
        self.assertEqual(1, fx.commits())
        status, out = fx.run("ok", report="app.txt")
        self.assertEqual(1, status)
        self.assertEqual(1, fx.commits())

    def test_scope_patterns_and_literal_entries(self):
        contract = {"declared_scope": ["verification/x-verifier-report*.md", "verification/y-security-review-report-round2.md", "app/**", "plain.txt"]}
        self.assertTrue(run_review.report_in_scope(contract, "verification/x-verifier-report-round2.md"))
        self.assertTrue(run_review.report_in_scope(contract, "verification/y-security-review-report-round2.md"))
        self.assertFalse(run_review.report_in_scope(contract, "verification/x-verifier-report/round.md"))
        self.assertFalse(run_review.report_in_scope(contract, "app/a/b.md"))
        self.assertFalse(run_review.report_in_scope(contract, "plain.txt"))
        self.assertFalse(run_review.report_in_scope({}, "x"))

    def test_the_real_shape_of_a_contract_with_literal_report_paths_is_accepted(self):
        scope = json.loads((ROOT / "verification" / "review-run-review-task-contract.json").read_text(encoding="utf-8"))
        for path in (
            "verification/review-run-review-verifier-report.md",
            "verification/review-run-review-verifier-report-round2.md",
            "verification/review-run-review-security-review-report.md",
        ):
            self.assertTrue(run_review.report_in_scope(scope, path), path)
        self.assertFalse(run_review.report_in_scope(scope, "verification/run_review.py"))

    def test_odd_report_paths_are_refused(self):
        contract = {"declared_scope": ["verification/**", "**", "*"]}
        for path in (
            "verification/../x-verifier-report.md",
            "../x-verifier-report.md",
            "/x-verifier-report.md",
            "verification\\x-verifier-report.md",
            "C:/x-verifier-report.md",
            "verification/x-verifier-report.md.",
            "verification/x-verifier-report.md ",
            "verification//x-verifier-report.md",
            "verification/./x-verifier-report.md",
            "verification/tests/test_run_review.py",
            "",
        ):
            self.assertFalse(run_review.report_in_scope(contract, path), repr(path))
        self.assertTrue(run_review.report_in_scope(contract, "verification/x-verifier-report.md"))

    def test_an_existing_report_is_never_overwritten(self):
        fx = self.fixture()
        self.assertEqual(0, fx.run("ok")[0])
        fx.out = fx.out.parent / "out2"
        status, out = fx.run("ok")
        self.assertEqual(1, status)
        self.assertIn("already exists", out)

    def test_staged_changes_or_a_moved_head_stop_the_commit(self):
        fx = self.fixture()
        (fx.repo / "app.txt").write_text("staged\n", encoding="utf-8")
        git(fx.repo, "add", "app.txt")
        with self.assertRaises(run_review.Refusal) as caught:
            run_review.commit_report(fx.repo, REPORT, b"Outcome: PASS\n", fx.head, "m")
        self.assertIn("staged", str(caught.exception))
        git(fx.repo, "commit", "-qm", "moved")
        with self.assertRaises(run_review.Refusal) as caught:
            run_review.commit_report(fx.repo, REPORT, b"Outcome: PASS\n", fx.head, "m")
        self.assertIn("HEAD moved", str(caught.exception))
        self.assertFalse((fx.repo / REPORT).exists())

    def test_commit_report_refuses_an_existing_report_itself(self):
        fx = self.fixture()
        (fx.repo / REPORT).write_text("old\n", encoding="utf-8")
        with self.assertRaises(run_review.Refusal) as caught:
            run_review.commit_report(fx.repo, REPORT, b"Outcome: PASS\n", fx.head, "m")
        self.assertIn("already exists", str(caught.exception))

    def test_only_the_report_is_committed_and_nothing_is_pushed(self):
        fx = self.fixture()
        git(fx.repo, "remote", "add", "origin", str(fx.repo.parent / "nowhere.git"))
        status, out = fx.run("ok")
        self.assertEqual(0, status, out)
        self.assertEqual(REPORT, git(fx.repo, "show", "--name-only", "--format=", "HEAD"))
        self.assertNotIn("push", out.lower().replace("never pushes", ""))


class LogTests(FixtureCase):
    def test_the_log_has_the_listed_fields_and_is_not_committed(self):
        fx = self.fixture()
        status, out = fx.run("ok", "--role", "security", "--round", "2")
        self.assertEqual(0, status, out)
        log = fx.log()
        for key in ("started", "finished", "reviewer_started", "reviewer_finished", "model", "head", "previous_head", "exit_status", "outcome",
                    "answer_sha256", "passed_variables", "role", "round", "report_commit"):
            self.assertIn(key, log, key)
        self.assertEqual("PASS", log["outcome"])
        self.assertEqual(hashlib.sha256((fx.out / "answer.bin").read_bytes()).hexdigest(), log["answer_sha256"])
        self.assertNotIn("review-run.json", git(fx.repo, "ls-files"))
        self.assertIn("security round 2", git(fx.repo, "log", "-1", "--format=%s"))


class CommitMechanismTests(FixtureCase):
    def test_a_hook_that_stages_a_file_cannot_add_it_to_the_report_commit(self):
        fx = self.fixture()
        hook = fx.repo / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\necho x > extra.txt\ngit add extra.txt\n", encoding="utf-8", newline="\n")
        hook.chmod(0o755)
        status, out = fx.run("ok")
        self.assertEqual(0, status, out)
        self.assertEqual(REPORT, git(fx.repo, "show", "--name-only", "--format=", "HEAD"))
        self.assertEqual("", git(fx.repo, "diff", "--cached", "--name-only"))

    def test_gitattributes_cannot_change_the_stored_report(self):
        fx = self.fixture(autocrlf="true")
        (fx.repo / ".gitattributes").write_text("*.md text eol=lf\n", encoding="utf-8", newline="\n")
        git(fx.repo, "add", ".gitattributes")
        git(fx.repo, "commit", "-qm", "attributes")
        status, out = fx.run("crlf")
        self.assertEqual(0, status, out)
        answer = (fx.out / "answer.bin").read_bytes()
        blob = subprocess.run(["git", "cat-file", "blob", f"HEAD:{REPORT}"], cwd=fx.repo, check=True, capture_output=True).stdout
        self.assertEqual(answer, blob)
        self.assertEqual(2, fx.commits() - 1)

    def test_a_report_directory_that_leads_outside_the_repository_is_refused(self):
        fx = self.fixture()
        elsewhere = fx.repo.parent / "elsewhere"
        elsewhere.mkdir()
        link = fx.repo / "verification" / "linked"
        try:
            os.symlink(elsewhere, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links are not available")
        with self.assertRaises(run_review.Refusal) as caught:
            run_review.commit_report(fx.repo, "verification/linked/x-verifier-report.md", b"Outcome: PASS\n", fx.head, "m")
        self.assertIn("outside the repository", str(caught.exception))
        self.assertEqual([], list(elsewhere.iterdir()))

    def test_the_checked_out_branch_moves_and_the_index_matches_it(self):
        fx = self.fixture()
        branch = git(fx.repo, "branch", "--show-current")
        status, out = fx.run("ok")
        self.assertEqual(0, status, out)
        self.assertEqual(git(fx.repo, "rev-parse", "HEAD"), git(fx.repo, "rev-parse", branch))
        self.assertEqual("", git(fx.repo, "status", "--porcelain", "--untracked-files=no"))


class TimeoutTests(FixtureCase):
    def test_the_timeout_kills_a_grandchild_that_holds_the_output(self):
        fx = self.fixture()
        pid_file = fx.repo.parent / "grandchild.pid"
        status, out = fx.run("grandchild", "--timeout", "2", reviewer_args=(str(pid_file),))
        self.assertEqual(1, status)
        self.assertIn("past the timeout", out)
        pid = int(pid_file.read_text(encoding="utf-8"))
        self.addCleanup(stop, pid)
        self.assertFalse(pid_alive(pid), "the reviewer's child is still running after the timeout")
        self.assertEqual(1, fx.commits())

    @unittest.skipIf(sys.platform == "win32", "the reviewer leads its own session on POSIX only")
    def test_an_interrupt_or_a_termination_of_the_tool_kills_the_reviewer(self):
        import signal
        import time

        for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            fx = self.fixture()
            pid_file = fx.repo.parent / "reviewer.pid"
            argv = fx.argv("pidsleep", "--timeout", "120", reviewer_args=(str(pid_file),))
            # A CI runner starts jobs with SIGINT ignored, and an ignored SIGINT is inherited: the tool would then never see the interrupt.
            ours = signal.signal(signal.SIGINT, signal.SIG_DFL)
            try:
                tool = subprocess.Popen([sys.executable, str(ROOT / "verification" / "run_review.py"), *argv], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            finally:
                signal.signal(signal.SIGINT, ours)
            deadline = time.monotonic() + 60
            while not pid_file.exists() and time.monotonic() < deadline:
                time.sleep(0.2)
            self.assertTrue(pid_file.exists(), "the reviewer did not start")
            time.sleep(0.5)
            pid = int(pid_file.read_text(encoding="utf-8"))
            self.addCleanup(stop, pid)
            tool.send_signal(number)
            output, _ = tool.communicate(timeout=60)
            self.assertEqual(130, tool.returncode, (number, output))
            self.assertFalse(pid_alive(pid), f"the reviewer survived signal {number}")
            self.assertEqual(1, fx.commits())
            self.assertTrue(json.loads((fx.out / "review-run.json").read_text(encoding="utf-8"))["interrupted"])


class LifelineTests(FixtureCase):
    def _start(self, fx: Fixture, **popen: object) -> tuple[subprocess.Popen[bytes], int]:
        import time

        pid_file = fx.repo.parent / "reviewer.pid"
        argv = fx.argv("pidsleep", "--timeout", "300", reviewer_args=(str(pid_file),))
        tool = subprocess.Popen(
            [sys.executable, str(ROOT / "verification" / "run_review.py"), *argv], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **popen  # type: ignore[call-overload]
        )
        deadline = time.monotonic() + 60
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.2)
        self.assertTrue(pid_file.exists(), "the reviewer did not start")
        time.sleep(0.5)
        pid = int(pid_file.read_text(encoding="utf-8"))
        self.addCleanup(stop, pid)
        return tool, pid

    def _gone(self, pid: int, seconds: int = 20) -> bool:
        import time

        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if not pid_alive(pid):
                return True
            time.sleep(0.2)
        return False

    @unittest.skipIf(sys.platform == "win32", "POSIX signals")
    def test_a_signal_the_tool_cannot_catch_does_not_leave_the_reviewer_running(self):
        import signal

        for number in (signal.SIGKILL, signal.SIGQUIT):
            fx = self.fixture()
            tool, pid = self._start(fx, start_new_session=True)
            os.killpg(tool.pid, number)
            tool.communicate(timeout=60)
            self.assertTrue(self._gone(pid), f"the reviewer survived signal {number} sent to the tool's group")

    @unittest.skipIf(sys.platform == "win32", "POSIX signals")
    def test_a_kill_of_the_tool_alone_does_not_leave_the_reviewer_running(self):
        import signal

        fx = self.fixture()
        tool, pid = self._start(fx)
        tool.send_signal(signal.SIGKILL)
        tool.communicate(timeout=60)
        self.assertTrue(self._gone(pid), "the reviewer survived a kill of the tool")

    @unittest.skipUnless(sys.platform == "win32", "Windows job object")
    def test_a_forced_end_of_the_tool_does_not_leave_the_reviewer_running(self):
        fx = self.fixture()
        tool, pid = self._start(fx)
        subprocess.run(["taskkill", "/F", "/PID", str(tool.pid)], capture_output=True, check=False)
        tool.communicate(timeout=60)
        self.assertTrue(self._gone(pid), "the reviewer survived a forced end of the tool")


class LifelineEdgeTests(FixtureCase):
    def _wait_gone(self, pid: int, seconds: int = 20) -> bool:
        import time

        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if not pid_alive(pid):
                return True
            time.sleep(0.2)
        return False

    def test_a_failure_right_after_the_reviewer_starts_does_not_leave_it_running(self):
        import time

        fx = self.fixture()
        pid_file = fx.repo.parent / "started.pid"
        command = [sys.executable, str(fx.script), "pidsleep", str(fx.repo), str(fx.brief), str(pid_file)]
        real_start = run_review.Lifeline.start

        def start_then_fail(self_: object, *args: object, **kwargs: object) -> object:
            real_start(self_, *args, **kwargs)  # type: ignore[arg-type]
            deadline = time.monotonic() + 30
            while not pid_file.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            raise KeyboardInterrupt

        with mock.patch.object(run_review.Lifeline, "start", start_then_fail), self.assertRaises(KeyboardInterrupt):
            run_review.run_reviewer(command, fx.repo, dict(os.environ), 60)
        pid = int(pid_file.read_text(encoding="utf-8"))
        self.addCleanup(stop, pid)
        self.assertTrue(self._wait_gone(pid), "the reviewer survived a failure right after it started")

    def test_a_child_that_stays_in_the_reviewers_group_is_killed_when_the_reviewer_ends(self):
        fx = self.fixture()
        pid_file = fx.repo.parent / "orphan.pid"
        status, out = fx.run("orphan", reviewer_args=(str(pid_file),))
        self.assertEqual(0, status, out)
        pid = int(pid_file.read_text(encoding="utf-8"))
        self.addCleanup(stop, pid)
        self.assertTrue(self._wait_gone(pid), "a child of the reviewer is still running after a normal end")

    @unittest.skipIf(sys.platform == "win32", "POSIX watchdog")
    def test_a_watchdog_that_cannot_start_its_watch_thread_does_not_leave_the_reviewer_running(self):
        fx = self.fixture()
        pid_file = fx.repo.parent / "wd.pid"
        script = fx.repo.parent / "wd.py"
        script.write_text(
            "import sys, threading\n"
            "def boom(self): raise RuntimeError('cannot start new thread')\n"
            "threading.Thread.start = boom\n"
            "r, w = __import__('os').pipe()\n"
            "sys.argv = ['x', str(r), sys.argv[1]]\n"
            f"exec({run_review.WATCHDOG!r})\n",
            encoding="utf-8",
        )
        command = json.dumps([sys.executable, str(fx.script), "pidsleep", str(fx.repo), str(fx.brief), str(pid_file)])
        done = subprocess.run([sys.executable, str(script), command], cwd=ROOT, capture_output=True, timeout=60, check=False)
        self.assertEqual((1, b""), (done.returncode, done.stderr))
        import time

        # The watchdog ends the reviewer at once, so it may never get to write its pid; if it did, it must be gone.
        deadline = time.monotonic() + 8
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        if pid_file.exists():
            pid = int(pid_file.read_text(encoding="utf-8"))
            self.addCleanup(stop, pid)
            self.assertTrue(self._wait_gone(pid), "the reviewer was left running by a watchdog that could not watch")

    @unittest.skipIf(sys.platform == "win32", "POSIX descriptors")
    def test_a_tool_started_with_standard_input_closed_still_runs_the_reviewer(self):
        code = (
            "import os, sys\nos.close(0)\nfrom verification import run_review\n"
            "status, out, err = run_review.run_reviewer([sys.executable, '-c', 'print(7)'], os.getcwd(), dict(os.environ), 60)\n"
            "print(status, out.strip())\n"
        )
        done = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL, check=False)
        self.assertIn("0 b'7'", done.stdout, done.stderr)

    @unittest.skipIf(sys.platform == "win32", "POSIX descriptors")
    def test_an_interrupt_right_after_the_pipe_is_closed_does_not_close_it_twice(self):
        lifeline = run_review.Lifeline()
        read_end, lifeline.write_end = os.pipe()
        self.addCleanup(os.close, read_end)
        real_close = os.close
        calls: list[int] = []

        def interrupted_close(descriptor: int) -> None:
            calls.append(descriptor)
            real_close(descriptor)
            raise KeyboardInterrupt

        with mock.patch.object(run_review.os, "close", interrupted_close), self.assertRaises(KeyboardInterrupt):
            lifeline.release()
        lifeline.finish()  # must not close the same descriptor again
        self.assertEqual(1, len(calls))

    def test_a_reviewer_that_cannot_start_is_refused(self):
        fx = self.fixture()
        status, out = fx.run("ok", command_override=[str(fx.repo.parent / "no-such-reviewer-xyz")])
        self.assertEqual(1, status)
        self.assertIn("REFUSED", out)
        self.assertTrue(any(text in out for text in ("cannot start the reviewer", "WinError", "cannot find", "was not found")), out[:300])
        self.assertEqual(1, fx.commits())

    @unittest.skipIf(sys.platform == "win32", "POSIX exit statuses")
    def test_a_reviewer_ended_by_a_signal_is_logged_as_128_plus_the_signal(self):
        fx = self.fixture()
        status, out = fx.run("selfkill")
        self.assertEqual(1, status, out)
        self.assertEqual(137, fx.log()["reviewer_exit"])

    @unittest.skipUnless(sys.platform == "win32", "Windows job object")
    def test_the_reviewer_is_created_suspended_and_put_into_the_job_before_it_runs(self):
        seen: list[dict[str, object]] = []
        real = subprocess.Popen

        def spy(*args: object, **kwargs: object) -> object:
            seen.append(kwargs)
            return real(*args, **kwargs)  # type: ignore[call-overload]

        with mock.patch.object(run_review.subprocess, "Popen", spy):
            code, out, _err = run_review.run_reviewer([sys.executable, "-c", "print(1)"], ROOT, dict(os.environ), 60)
        self.assertEqual((0, b"1"), (code, out.strip()))
        self.assertTrue(int(seen[0]["creationflags"]) & run_review.CREATE_SUSPENDED)  # type: ignore[call-overload]


class NoHookTests(FixtureCase):
    def test_no_hook_and_no_fsmonitor_command_runs_during_a_whole_run(self):
        fx = self.fixture()
        marker = fx.repo.parent / "ran"
        for name in ("post-index-change", "reference-transaction", "post-checkout", "post-commit"):
            hook = fx.repo / ".git" / "hooks" / name
            hook.write_text(f"#!/bin/sh\necho {name} >> '{marker.as_posix()}'\n", encoding="utf-8", newline="\n")
            hook.chmod(0o755)
        monitor = fx.repo.parent / "monitor.sh"
        monitor.write_text(f"#!/bin/sh\necho fsmonitor >> '{marker.as_posix()}'\nprintf '\\0'\n", encoding="utf-8", newline="\n")
        monitor.chmod(0o755)
        git(fx.repo, "config", "core.fsmonitor", monitor.as_posix())
        status, out = fx.run("ok")
        self.assertEqual(0, status, out)
        self.assertFalse(marker.exists(), marker.read_text(encoding="utf-8") if marker.exists() else "")


class SignalWindowTests(FixtureCase):
    @unittest.skipIf(sys.platform == "win32", "POSIX signals")
    def test_sigterm_sighup_and_sigquit_are_held_while_the_report_moves_and_then_raise(self):
        import signal

        saved = run_review.install_signal_handlers()
        try:
            for number in (signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT):
                reached: list[int] = []
                with self.assertRaises(run_review.Interrupted), run_review.signals_deferred():
                    os.kill(os.getpid(), number)
                    reached.append(number)
                self.assertEqual([number], reached, "the signal was not held back")
        finally:
            for number, handler in saved:
                signal.signal(number, handler)

    def test_a_failure_of_the_branch_update_leaves_no_file_and_no_index_entry(self):
        fx = self.fixture()
        real = run_review.git

        def failing(root: Path, *args: str, **kwargs: object) -> object:
            if args and args[0] == "update-ref":
                raise run_review.Refusal("update-ref failed")
            return real(root, *args, **kwargs)  # type: ignore[arg-type]

        with mock.patch.object(run_review, "git", failing), self.assertRaises(run_review.Refusal):
            run_review.commit_report(fx.repo, REPORT, b"Outcome: PASS\n", fx.head, "m")
        self.assertFalse((fx.repo / REPORT).exists())
        self.assertNotIn(REPORT, git(fx.repo, "ls-files"))
        self.assertEqual(fx.head, git(fx.repo, "rev-parse", "HEAD"))


    def test_a_failure_after_the_branch_has_moved_keeps_the_file_and_the_index_entry(self):
        fx = self.fixture()
        real = run_review.git

        def moved_then_failing(root: Path, *args: str, **kwargs: object) -> object:
            result = real(root, *args, **kwargs)  # type: ignore[arg-type]
            if args and args[0] == "update-ref":
                raise KeyboardInterrupt
            return result

        with mock.patch.object(run_review, "git", moved_then_failing), self.assertRaises(KeyboardInterrupt):
            run_review.commit_report(fx.repo, REPORT, b"Outcome: PASS\n", fx.head, "m")
        head = git(fx.repo, "rev-parse", "HEAD")
        self.assertNotEqual(fx.head, head, "the branch did not move")
        self.assertTrue((fx.repo / REPORT).exists(), "the rollback deleted the committed report's file")
        self.assertIn(REPORT, git(fx.repo, "ls-files"))
        self.assertEqual("", git(fx.repo, "status", "--porcelain", "--untracked-files=no"))

    def test_a_failed_write_of_the_report_leaves_no_partial_file(self):
        fx = self.fixture()
        real_fdopen = os.fdopen

        def failing(descriptor: int, *args: object, **kwargs: object) -> object:
            handle = real_fdopen(descriptor, *args, **kwargs)  # type: ignore[call-overload]
            handle.close()
            raise OSError(28, "No space left on device")

        with mock.patch.object(run_review.os, "fdopen", failing), self.assertRaises(OSError):
            run_review.commit_report(fx.repo, REPORT, b"Outcome: PASS\n", fx.head, "m")
        self.assertFalse((fx.repo / REPORT).exists(), "a partial report file was left")
        self.assertEqual("", git(fx.repo, "status", "--porcelain", "--untracked-files=no"))
        self.assertEqual(fx.head, git(fx.repo, "rev-parse", "HEAD"))

    def test_sigint_is_held_back_in_the_window_and_raised_after_it(self):
        import signal

        reached: list[int] = []
        # Under a CI runner SIGINT is ignored from the start; the test needs Python's normal handler.
        self.addCleanup(signal.signal, signal.SIGINT, signal.signal(signal.SIGINT, signal.default_int_handler))
        with self.assertRaises(KeyboardInterrupt), run_review.signals_deferred():
            signal.raise_signal(signal.SIGINT)
            reached.append(1)
        self.assertEqual([1], reached, "SIGINT was not held back")
        self.assertIs(signal.default_int_handler, signal.getsignal(signal.SIGINT))


class WindowGitCallTests(FixtureCase):
    """The git programs started while the report moves are created in their own process group on Windows, so a console Ctrl-C reaches the tool
    (which holds it) and not them; nothing else is started that way, and nothing is on POSIX."""

    def record(self, fx: Fixture, fail: str | None = None) -> list[tuple[bool, int, list[str]]]:
        calls: list[tuple[bool, int, list[str]]] = []
        state = {"inside": False}
        real_run = subprocess.run
        real_window = run_review.signals_deferred

        @contextlib.contextmanager
        def window() -> Iterator[None]:
            with real_window():
                state["inside"] = True
                try:
                    yield
                finally:
                    state["inside"] = False

        def watch(command: list[str], *args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            flags = kwargs.get("creationflags", 0)
            calls.append((state["inside"], flags if isinstance(flags, int) else -1, [str(word) for word in command]))
            if fail and fail in command:
                return subprocess.CompletedProcess(command, 1, b"", b"induced failure")
            return real_run(command, *args, **kwargs)  # type: ignore[call-overload, no-any-return]

        with mock.patch.object(run_review.subprocess, "run", side_effect=watch), mock.patch.object(run_review, "signals_deferred", window):
            try:
                run_review.commit_report(fx.repo, REPORT, b"Outcome: PASS\n", fx.head, "m")
            except run_review.Refusal:
                if not fail:
                    raise
        return calls

    @unittest.skipUnless(sys.platform == "win32", "process groups are a Windows console feature")
    def test_the_git_programs_in_the_window_start_in_their_own_process_group_and_the_others_do_not(self):
        calls = self.record(self.fixture())
        isolated = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined, unused-ignore]
        inside = [command for within, _, command in calls if within]
        self.assertTrue(any("update-ref" in command for command in inside), inside)
        self.assertTrue(any("update-index" in command and "--refresh" in command for command in inside), inside)
        for within, flags, command in calls:
            self.assertEqual(isolated if within else 0, flags, command)

    @unittest.skipUnless(sys.platform == "win32", "process groups are a Windows console feature")
    def test_the_rollback_after_a_failed_branch_update_is_isolated_too(self):
        calls = self.record(self.fixture(), fail="update-ref")
        isolated = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined, unused-ignore]
        rollback = [(flags, command) for within, flags, command in calls if within and ("rev-parse" in command or "--force-remove" in command)]
        self.assertTrue(any("--force-remove" in command for _, command in rollback), "the rollback did not run")
        for flags, command in rollback:
            self.assertEqual(isolated, flags, command)

    @unittest.skipIf(sys.platform == "win32", "POSIX passes no creation flag")
    def test_no_creation_flag_is_passed_on_posix(self):
        calls = self.record(self.fixture())
        self.assertTrue(calls)
        for _, flags, command in calls:
            self.assertEqual(0, flags, command)

    @unittest.skipUnless(sys.platform == "win32", "SIGBREAK is a Windows console signal")
    def test_sigbreak_is_held_back_in_the_window_and_raised_after_it(self):
        import signal

        def custom(_number: int, _frame: object) -> None:
            return None

        outer = signal.signal(signal.SIGBREAK, custom)  # type: ignore[attr-defined, unused-ignore]  # not SIG_DFL: a restore to the default is then seen
        self.addCleanup(signal.signal, signal.SIGBREAK, outer)  # type: ignore[attr-defined, unused-ignore]
        previous = signal.getsignal(signal.SIGBREAK)  # type: ignore[attr-defined, unused-ignore]
        reached: list[int] = []
        with self.assertRaises(KeyboardInterrupt), run_review.signals_deferred():
            signal.raise_signal(signal.SIGBREAK)  # type: ignore[attr-defined, unused-ignore]
            reached.append(1)
        self.assertEqual([1], reached, "SIGBREAK was not held back")
        self.assertEqual(previous, signal.getsignal(signal.SIGBREAK))  # type: ignore[attr-defined, unused-ignore]

    @unittest.skipUnless(sys.platform == "win32", "SIGBREAK is a Windows console signal")
    def test_both_handlers_are_restored_when_the_window_ends_with_an_exception(self):
        import signal

        def custom(_number: int, _frame: object) -> None:
            return None

        outer = signal.signal(signal.SIGBREAK, custom)  # type: ignore[attr-defined, unused-ignore]  # not SIG_DFL: a restore to the default is then seen
        self.addCleanup(signal.signal, signal.SIGBREAK, outer)  # type: ignore[attr-defined, unused-ignore]
        before = (signal.getsignal(signal.SIGINT), signal.getsignal(signal.SIGBREAK))  # type: ignore[attr-defined, unused-ignore]
        with self.assertRaises(RuntimeError), run_review.signals_deferred():
            raise RuntimeError("the body failed")
        self.assertEqual(before, (signal.getsignal(signal.SIGINT), signal.getsignal(signal.SIGBREAK)))  # type: ignore[attr-defined, unused-ignore]

    @unittest.skipUnless(sys.platform == "win32", "SIGBREAK is a Windows console signal")
    def test_a_held_signal_is_raised_even_when_the_window_ends_with_another_exception(self):
        import signal

        with self.assertRaises(KeyboardInterrupt) as caught, run_review.signals_deferred():
            signal.raise_signal(signal.SIGBREAK)  # type: ignore[attr-defined, unused-ignore]
            raise run_review.Refusal("git was ended")
        self.assertIsInstance(caught.exception.__cause__, run_review.Refusal)

    @unittest.skipUnless(sys.platform == "win32", "SIGBREAK is a Windows console signal")
    def test_a_failed_installation_of_the_second_handler_restores_the_first(self):
        import signal

        before = signal.getsignal(signal.SIGINT)
        real = signal.signal
        calls: list[int] = []

        def failing(number: int, handler: object) -> object:
            calls.append(number)
            if len(calls) == 2:
                raise OSError("cannot install the handler")
            return real(number, handler)  # type: ignore[arg-type]

        with mock.patch.object(run_review.signal, "signal", failing), self.assertRaises(OSError), run_review.signals_deferred():
            self.fail("the window must not open")
        self.assertEqual(before, signal.getsignal(signal.SIGINT))


CONSOLE_DRIVER = r"""
import ctypes, importlib.util, signal, subprocess, sys, threading, time
from pathlib import Path

scratch, module = Path(sys.argv[1]), sys.argv[2]
ctypes.windll.kernel32.SetConsoleCtrlHandler(None, False)  # Ctrl-C processing on: a process started with it off hands that to its children
signal.signal(signal.SIGINT, lambda *_: None)
signal.signal(signal.SIGBREAK, lambda *_: None)
spec = importlib.util.spec_from_file_location("run_review", module)
rr = importlib.util.module_from_spec(spec)
sys.modules["run_review"] = rr
spec.loader.exec_module(rr)
child = scratch / "child.py"
child.write_text(
    "import sys, time\nmarker = sys.argv[1]\nopen(marker + '.ready', 'w').close()\n"
    "try:\n    time.sleep(3)\n    open(marker + '.finished', 'w').close()\n"
    "except KeyboardInterrupt:\n    open(marker + '.interrupted', 'w').close()\n"
)
real, state = subprocess.run, {}


def stand_in(command, **kwargs):
    # the git program that run_review would start is a child that waits; it is created with the flags run_review chose
    return real([sys.executable, str(child), str(scratch / state["name"])], capture_output=True, creationflags=kwargs["creationflags"])


def send_when_ready(name, event):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline and not (scratch / (name + ".ready")).exists():
        time.sleep(0.05)
    time.sleep(0.5)
    ctypes.windll.kernel32.GenerateConsoleCtrlEvent(event, 0)  # 0 is CTRL_C_EVENT, 1 is CTRL_BREAK_EVENT, to every process on this console


rr.subprocess.run = stand_in
import traceback
try:
  for name, isolated, event in (("plain-c", False, 0), ("isolated-c", True, 0), ("plain-b", False, 1), ("isolated-b", True, 1)):
      state["name"] = name
      sender = threading.Thread(target=send_when_ready, args=(name, event))
      sender.start()
      try:
          rr.git(scratch, "status", isolated=isolated)
      except rr.Refusal:
          (scratch / (name + ".refused")).touch()  # the child was ended by the event: git() reports a refusal
      sender.join()
except BaseException:
    (scratch / "driver.err").write_text(traceback.format_exc())
(scratch / "driver.done").touch()
"""


class ConsoleCtrlCTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "console Ctrl-C and Ctrl-Break are Windows console events")
    def test_a_console_event_reaches_a_plain_git_and_not_an_isolated_one(self):
        """Run in a hidden console of its own, not the test runner's: run_review.git starts a stand-in that waits, with the creation flags it
        chose; a Ctrl-C and then a Ctrl-Break event is sent to the console. The plain stand-in is interrupted by the first and ended by the second;
        the isolated one runs to its end through both."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            scratch = Path(tmp)
            (scratch / "driver.py").write_text(CONSOLE_DRIVER, encoding="utf-8")
            startup = subprocess.STARTUPINFO()  # type: ignore[attr-defined, unused-ignore]
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined, unused-ignore]
            startup.wShowWindow = 0
            process = subprocess.Popen(
                [sys.executable, str(scratch / "driver.py"), str(scratch), str(ROOT / "verification" / "run_review.py")],
                creationflags=subprocess.CREATE_NEW_CONSOLE, startupinfo=startup,  # type: ignore[attr-defined, unused-ignore]
            )
            try:
                try:
                    process.wait(timeout=180)
                except subprocess.TimeoutExpired:
                    self.fail("the console driver did not finish")
            finally:
                if process.poll() is None:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True, check=False)
            names = sorted(path.name for path in scratch.iterdir())
            self.assertIn("driver.done", names)
            self.assertIn("plain-c.interrupted", names, "the Ctrl-C did not reach the control child; the experiment shows nothing")
            self.assertIn("plain-b.refused", names, "the Ctrl-Break did not end the control child; the experiment shows nothing")
            self.assertNotIn("plain-b.finished", names)
            for name in ("isolated-c", "isolated-b"):
                self.assertIn(f"{name}.finished", names, names)
                self.assertNotIn(f"{name}.interrupted", names)
                self.assertNotIn(f"{name}.refused", names)


class SecurityControlsTests(FixtureCase):
    def tearDown(self) -> None:
        run_review.distrust()

    @unittest.skipUnless(sys.platform == "win32", "Windows searches the current directory for a bare program name")
    def test_a_program_planted_in_the_current_directory_is_not_run_in_place_of_git(self):
        fx = self.fixture()
        planted = fx.repo.parent / "elsewhere"
        planted.mkdir()
        shutil.copy(Path(os.environ["SystemRoot"]) / "System32" / "cmd.exe", planted / "git.exe")
        previous = Path.cwd()
        os.chdir(planted)
        self.addCleanup(os.chdir, previous)
        with mock.patch.dict(os.environ):
            os.environ.pop("NoDefaultCurrentDirectoryInExePath", None)
            self.assertEqual(fx.head, run_review.git_text(fx.repo, "rev-parse", "HEAD"))

    def test_a_program_found_inside_the_repository_the_clone_or_the_output_is_refused(self):
        fx = self.fixture()
        planted = fx.repo / ("git.exe" if sys.platform == "win32" else "git")
        planted.write_text("x", encoding="utf-8")
        planted.chmod(0o755)
        run_review.distrust(fx.repo)
        with mock.patch.object(run_review.shutil, "which", return_value=str(planted)), self.assertRaises(run_review.Refusal) as caught:
            run_review.tool("git")
        self.assertIn("inside the repository", str(caught.exception))

    def test_a_reviewer_program_inside_the_repository_is_refused(self):
        fx = self.fixture()
        planted = fx.repo / ("reviewer.exe" if sys.platform == "win32" else "reviewer")
        planted.write_text("x", encoding="utf-8")
        planted.chmod(0o755)
        status, out = fx.run("ok", command_override=[str(planted)])
        self.assertEqual(1, status)
        self.assertIn("lies inside the repository", out)
        self.assertEqual(1, fx.commits())

    def test_a_hooks_directory_that_was_written_into_stops_every_git_call(self):
        fx = self.fixture()
        hooks = run_review.no_hooks_dir()
        (hooks / "post-index-change").write_text("x", encoding="utf-8")
        self.addCleanup((hooks / "post-index-change").unlink)
        with self.assertRaises(run_review.Refusal):
            run_review.git(fx.repo, "status")

    def test_a_hook_planted_in_the_hooks_directory_by_the_reviewer_is_never_run_and_nothing_is_committed(self):
        fx = self.fixture()
        hooks = run_review.no_hooks_dir()
        status, out = fx.run("hookplant", reviewer_args=(str(hooks),))
        self.assertEqual(1, status, out)
        self.assertIn("no longer empty", out)
        self.assertEqual(1, fx.commits())
        self.assertFalse((fx.repo / REPORT).exists())
        (hooks / "post-index-change").unlink()

    def test_a_filter_planted_in_the_clones_configuration_is_not_run(self):
        fx = self.fixture()
        marker = fx.repo.parent / "filter-ran"
        status, out = fx.run("filter", reviewer_args=(str(marker),))
        self.assertEqual(0, status, out)
        self.assertFalse(marker.exists(), "git ran a command from the clone's configuration")

    def test_an_edit_hidden_with_skip_worktree_is_found(self):
        fx = self.fixture()
        status, out = fx.run("hidden")
        self.assertEqual(1, status, out)
        self.assertIn("changed in the clone: app.txt", out)
        self.assertEqual(1, fx.commits())

    @unittest.skipIf(sys.platform == "win32", "needs a symbolic link")
    def test_a_link_planted_at_the_answer_path_is_not_followed(self):
        fx = self.fixture()
        target = fx.repo.parent / "outside-target"
        status, out = fx.run("outlink", reviewer_args=(str(target),))
        self.assertEqual(1, status, out)
        self.assertFalse(target.exists(), "the answer was written through a planted link")
        self.assertEqual(1, fx.commits())

    def test_a_changed_repository_configuration_is_found_before_any_git_command_reads_it(self):
        fx = self.fixture()
        status, out = fx.run("rootconfig", reviewer_args=(str(fx.repo),))
        self.assertEqual(1, status, out)
        self.assertIn("configuration", out)
        self.assertEqual(1, fx.commits())

    def test_reviewer_text_is_redacted_and_escaped_before_it_is_printed_or_logged(self):
        fx = self.fixture()
        status, out = fx.run("stderr127", "--pass-env", "REVIEW_TEST_KEY", env={"REVIEW_TEST_KEY": "key-12345678"})
        self.assertEqual(1, status, out)
        self.assertNotIn("key-12345678", out)
        self.assertNotIn("\x1b", out)
        self.assertNotIn("key-12345678", (fx.out / "review-run.json").read_text(encoding="utf-8"))
        self.assertIn("<redacted>", out)

    def test_the_longest_secret_is_redacted_first(self):
        self.assertEqual("--key=<redacted>", run_review.redact("--key=abcdefgh12345678", {"A": "abcdefgh", "B": "abcdefgh12345678"}))

    def test_a_secret_is_found_in_the_common_encodings_and_when_split_over_lines(self):
        import base64
        import urllib.parse

        value = "s3cret/value+98765"
        secrets = {"REVIEW_TEST_KEY": value}
        forms = [
            base64.b64encode(value.encode()), b"xx" + base64.b64encode(b"a" + value.encode()), base64.urlsafe_b64encode(value.encode()),
            value.encode("utf-16-le"), value.encode().hex().encode(), urllib.parse.quote(value, safe="").encode(),
            value[:8].encode() + b"\n  " + value[8:].encode(),
        ]
        for form in forms:
            self.assertEqual("REVIEW_TEST_KEY", run_review.find_secret(b"report text " + form + b" more", secrets), form)
        self.assertIsNone(run_review.find_secret(b"nothing here", secrets))

    def test_a_pipeline_commit_sha_is_not_treated_as_a_secret(self):
        self.assertEqual({}, run_review.secret_values({"CI_COMMIT_SHA": "a" * 40, "NO_PROXY": "localhost,example.org"}, []))
        self.assertIn("CI_JOB_TOKEN", run_review.secret_values({"CI_JOB_TOKEN": "x" * 20}, []))

    def test_a_variable_that_redirects_git_is_not_given_to_a_git_call(self):
        fx = self.fixture()
        other = fx.repo.parent / "other"
        other.mkdir()
        with mock.patch.dict(os.environ, {"GIT_DIR": str(other), "GIT_WORK_TREE": str(other), "GIT_INDEX_FILE": str(other / "i")}):
            self.assertEqual(fx.head, run_review.git_text(fx.repo, "rev-parse", "HEAD"))

    def test_a_head_that_holds_agent_configuration_is_noted_in_the_output_and_the_log(self):
        fx = self.fixture()
        (fx.repo / "AGENTS.md").write_text("be nice\n", encoding="utf-8")
        git(fx.repo, "add", "AGENTS.md")
        git(fx.repo, "commit", "-q", "-m", "agents")
        status, out = fx.run("ok", "--allow-steering-files")
        self.assertEqual(0, status, out)
        self.assertIn("steer an agent", out)
        self.assertEqual(["AGENTS.md"], fx.log()["agent_configuration_in_head"])


    def commit_file(self, fx, name, text):
        (fx.repo / name).write_text(text, encoding="utf-8", newline="")
        git(fx.repo, "add", name)
        git(fx.repo, "commit", "-q", "-m", name)

    @unittest.skipUnless(sys.platform == "win32", "cmd.exe runs a .cmd launcher")
    def test_a_cmd_launcher_and_its_helper_are_not_taken_from_the_clone(self):
        fx = self.fixture()
        trusted = fx.repo.parent / "trusted-bin"
        trusted.mkdir()
        (trusted / "helper-xyz.cmd").write_text("@echo off\r\necho TRUSTED\r\necho Outcome: PASS\r\n", encoding="utf-8", newline="")
        (trusted / "launcher-xyz.cmd").write_text("@echo off\r\nhelper-xyz.cmd\r\n", encoding="utf-8", newline="")
        self.commit_file(fx, "helper-xyz.cmd", "@echo off\r\necho IMPOSTOR\r\necho Outcome: PASS\r\n")
        self.commit_file(fx, "launcher-xyz.cmd", "@echo off\r\necho IMPOSTOR\r\necho Outcome: PASS\r\n")
        path = {"PATH": str(trusted) + os.pathsep + os.environ["PATH"]}
        status, out = fx.run("ok", command_override=[str(trusted / "launcher-xyz.cmd")], env=path)
        self.assertEqual(0, status, out)
        self.assertIn("TRUSTED", (fx.repo / REPORT).read_text(encoding="utf-8"))
        fx.out = fx.repo.parent / "out2"
        status, out = fx.run("ok", command_override=["launcher-xyz.cmd"], env=path, report="verification/x-verifier-report-round2.md")
        self.assertEqual(0, status, out)
        text = (fx.repo / "verification/x-verifier-report-round2.md").read_text(encoding="utf-8")
        self.assertIn("TRUSTED", text)
        self.assertNotIn("IMPOSTOR", text)

    def test_the_reviewer_environment_stops_cmd_from_searching_the_current_directory(self):
        with mock.patch.object(run_review.sys, "platform", "win32"):
            environment, _ = run_review.reviewer_environment({"PATH": "x"}, [])
        self.assertEqual("1", environment["NoDefaultCurrentDirectoryInExePath"])
        with mock.patch.object(run_review.sys, "platform", "linux"):
            environment, _ = run_review.reviewer_environment({"PATH": "x"}, [])
        self.assertNotIn("NoDefaultCurrentDirectoryInExePath", environment)

    def test_a_reviewer_program_with_a_relative_directory_part_is_refused(self):
        with self.assertRaises(run_review.Refusal) as caught:
            run_review.reviewer_program("sub/agent")
        self.assertIn("relative path", str(caught.exception))

    def test_the_prefix_and_share_spellings_of_a_windows_path_are_normalised(self):
        self.assertEqual("C:\\a\\b", run_review.plain("\\\\?\\C:\\a\\b"))
        self.assertEqual("\\\\host\\share\\x", run_review.plain("\\\\?\\UNC\\host\\share\\x"))
        self.assertEqual("C:\\a\\b", run_review.plain("\\\\localhost\\C$\\a\\b"))
        self.assertEqual("/usr/bin/git", run_review.plain("/usr/bin/git"))

    @unittest.skipUnless(sys.platform == "win32", "Windows path spellings")
    def test_a_program_reached_through_a_prefixed_path_is_still_inside_the_repository(self):
        fx = self.fixture()
        planted = fx.repo / "tools" / "git.exe"
        planted.parent.mkdir()
        planted.write_text("x", encoding="utf-8")
        run_review.distrust(fx.repo)
        self.assertTrue(run_review.is_inside("\\\\?\\" + str(planted), run_review._UNTRUSTED))
        self.assertTrue(run_review.is_inside("\\\\localhost\\" + str(planted).replace(":", "$", 1), run_review._UNTRUSTED))

    def test_the_clone_comparison_sees_a_retargeted_link_a_mode_change_and_does_not_open_a_fifo(self):
        base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, base, True)
        for name in ("a", "b"):
            (base / name).mkdir()
        (base / "f.txt").write_text("x", encoding="utf-8")
        (base / ".git").mkdir()
        (base / ".git" / "HEAD").write_text("ref: x\n", encoding="utf-8")
        link = base / "link"
        try:
            os.symlink(base / "a", link, target_is_directory=True)
            junction = False
        except OSError:
            subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(base / "a")], check=True, capture_output=True)
            junction = True
        before = run_review.clone_state(base)
        self.assertTrue(before["link"].startswith("link "), before)
        self.assertNotIn("link/", before)
        if junction:
            os.rmdir(link)
            subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(base / "b")], check=True, capture_output=True)
        else:
            link.unlink()
            os.symlink(base / "b", link, target_is_directory=True)
        self.assertIn("changed in the clone: link", run_review.clone_changes(base, before))
        if sys.platform != "win32":
            before = run_review.clone_state(base)
            (base / "f.txt").chmod(0o755)
            self.assertIn("changed in the clone: f.txt", run_review.clone_changes(base, before))
            os.mkfifo(base / "pipe")
            self.assertIn("special", run_review.clone_state(base)["pipe"])

    @unittest.skipUnless(sys.platform == "win32", "a junction")
    def test_a_junction_in_the_clone_is_not_followed_out_of_it(self):
        base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, base, True)
        (base / "far").mkdir()
        (base / "far" / "far.txt").write_text("x", encoding="utf-8")
        (base / "clone").mkdir()
        subprocess.run(["cmd", "/c", "mklink", "/J", str(base / "clone" / "j"), str(base / "far")], check=True, capture_output=True)
        self.assertFalse([key for key in run_review.clone_state(base / "clone") if "far.txt" in key])

    def test_a_change_to_the_worktree_configuration_or_the_global_configuration_is_found(self):
        fx = self.fixture()
        git(fx.repo, "config", "extensions.worktreeConfig", "true")
        worktree = fx.repo.parent / "wt"
        git(fx.repo, "worktree", "add", "-q", "--detach", str(worktree))
        before = run_review.configuration_state(worktree)
        git(worktree, "config", "--worktree", "core.abbrev", "9")
        self.assertNotEqual(before, run_review.configuration_state(worktree))
        glob = fx.repo.parent / "global.cfg"
        glob.write_text("", encoding="utf-8")
        with mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(glob)}):
            before = run_review.configuration_state(fx.repo)
            glob.write_text("[core]\n\tabbrev = 9\n", encoding="utf-8")
            self.assertNotEqual(before, run_review.configuration_state(fx.repo))
        home = fx.repo.parent / "home"
        home.mkdir()
        with mock.patch.dict(os.environ, {"HOME": str(home), "USERPROFILE": str(home)}):
            before = run_review.configuration_state(fx.repo)
            (home / ".gitconfig").write_text("[core]\n\tabbrev = 9\n", encoding="utf-8")
            self.assertNotEqual(before, run_review.configuration_state(fx.repo))

    @unittest.skipIf(sys.platform == "win32", "a directory moved while the reviewer runs")
    def test_an_output_directory_replaced_during_the_run_is_refused(self):
        fx = self.fixture()
        elsewhere = fx.repo.parent / "elsewhere"
        elsewhere.mkdir()
        status, out = fx.run("outswap", reviewer_args=(str(elsewhere),))
        self.assertEqual(1, status, out)
        self.assertIn("no longer the directory", out)
        self.assertEqual([], list(elsewhere.iterdir()))
        self.assertEqual(1, fx.commits())

    def test_a_value_in_a_file_name_or_in_the_preflight_text_never_reaches_the_screen_or_the_log(self):
        fx = self.fixture()
        status, out = fx.run("namedfile", "--pass-env", "REVIEW_TEST_KEY", "--preflight-arg", "key-12345678", env={"REVIEW_TEST_KEY": "key-12345678"})
        self.assertEqual(1, status, out)
        self.assertIn("changed in the clone", out)
        self.assertNotIn("key-12345678", out)
        self.assertNotIn("key-12345678", (fx.out / "review-run.json").read_text(encoding="utf-8"))

    def test_a_value_is_redacted_before_the_text_is_cut(self):
        value = "key-12345678"
        with mock.patch.dict(run_review._ACTIVE_SECRETS, {"K": value}):
            text = run_review.clean("p" * 290 + value, 300)
        self.assertNotIn("key-", text)
        self.assertNotIn("1234", text)

    def test_pipeline_variables_that_name_a_branch_or_a_user_are_not_secrets_and_a_short_squeezed_value_is_not_searched(self):
        found = run_review.secret_values({"CI_COMMIT_REF_NAME": "feature/long-branch", "GITLAB_USER_NAME": "Scott Wofford", "CI_PROJECT_PATH": "group/project"}, [])
        self.assertEqual({}, found)
        self.assertIn("CI_JOB_JWT", run_review.secret_values({"CI_JOB_JWT": "x" * 20}, []))
        self.assertIsNone(run_review.find_secret(b"a report that says abcd somewhere", {"MIXED": "a b   c d"}))


    @unittest.skipUnless(sys.platform == "win32", "cmd.exe runs a .cmd launcher")
    def test_a_batch_launcher_named_without_its_extension_is_refused_dangerous_arguments(self):
        fx = self.fixture()
        trusted = fx.repo.parent / "trusted-bin"
        trusted.mkdir()
        (trusted / "bare-launcher-xyz.cmd").write_text("@echo off\r\necho %1\r\necho Outcome: PASS\r\n", encoding="utf-8", newline="")
        path = {"PATH": str(trusted) + os.pathsep + os.environ["PATH"]}
        status, out = fx.run("ok", command_override=["bare-launcher-xyz", "{model}"], env=path, model="m&echo X")
        self.assertEqual(1, status, out)
        self.assertIn("cmd.exe", out)
        self.assertEqual(1, fx.commits())

    def test_files_that_steer_an_agent_are_noted_also_when_their_names_are_not_ascii(self):
        fx = self.fixture()
        (fx.repo / ".cursor" / "rules").mkdir(parents=True)
        (fx.repo / ".cursor" / "rules" / "\u00fcbersicht.mdc").write_text("alwaysApply: true\n", encoding="utf-8")
        (fx.repo / "docs" / "\u00fc").mkdir(parents=True)
        (fx.repo / "docs" / "\u00fc" / "AGENTS.md").write_text("x\n", encoding="utf-8")
        git(fx.repo, "add", "-A")
        git(fx.repo, "commit", "-q", "-m", "rules")
        status, out = fx.run("ok", "--allow-steering-files")
        self.assertEqual(0, status, out)
        self.assertIn("NOTE", out)
        self.assertEqual(2, len(fx.log()["agent_configuration_in_head"]), fx.log())

    def test_a_device_path_keeps_its_prefix_and_only_a_drive_path_loses_it(self):
        self.assertEqual("\\\\?\\GLOBALROOT\\Device\\x", run_review.plain("\\\\?\\GLOBALROOT\\Device\\x"))
        self.assertEqual("\\\\?\\Volume{1}\\x", run_review.plain("\\\\?\\Volume{1}\\x"))

    @unittest.skipUnless(sys.platform == "win32", "the machine-name spelling of an administrative share")
    def test_a_program_reached_through_the_machine_name_share_is_still_inside_the_repository(self):
        import socket

        fx = self.fixture()
        planted = fx.repo / "tools" / "git.exe"
        planted.parent.mkdir()
        planted.write_text("x", encoding="utf-8")
        share = "\\\\" + socket.gethostname() + "\\" + str(planted).replace(":", "$", 1)
        if not os.path.exists(share):
            self.skipTest("the administrative share is not reachable here")
        run_review.distrust(fx.repo)
        self.assertTrue(run_review.is_inside(share, run_review._UNTRUSTED))

    def test_a_global_git_configuration_under_home_is_compared_when_home_differs_from_the_profile(self):
        fx = self.fixture()
        profile = fx.repo.parent / "profile"
        home = fx.repo.parent / "home2"
        profile.mkdir()
        home.mkdir()
        with mock.patch.dict(os.environ, {"HOME": str(home), "USERPROFILE": str(profile), "XDG_CONFIG_HOME": str(home / "xdg")}):
            before = run_review.configuration_state(fx.repo)
            (home / ".gitconfig").write_text("[core]\n\tabbrev = 9\n", encoding="utf-8")
            self.assertNotEqual(before, run_review.configuration_state(fx.repo))
            before = run_review.configuration_state(fx.repo)
            (home / "xdg" / "git").mkdir(parents=True)
            (home / "xdg" / "git" / "attributes").write_text("* filter=x\n", encoding="utf-8")
            self.assertNotEqual(before, run_review.configuration_state(fx.repo))

    def test_more_credential_names_are_treated_as_secrets_and_the_working_directory_is_not(self):
        names = ("DOCKER_AUTH_CONFIG", "MYSQL_PWD", "GPG_PASSPHRASE", "SIGNING_KEY", "DATABASE_URL", "SENTRY_DSN", "NPM_CONFIG__AUTH")
        found = run_review.secret_values({name: "x" * 20 for name in names} | {"PWD": "/home/user/project"}, [])
        self.assertEqual(sorted(names), sorted(found))


    def test_the_steering_list_finds_names_with_a_newline_links_and_the_cli_locations(self):
        def entry(path, mode="100644"):
            return f"{mode} blob 0000000000000000000000000000000000000000\t{path}\0"

        listing = "".join(
            entry(path)
            for path in (
                ".cursor/rules/a\nb.mdc", ".agents/skills/review/SKILL.md", ".codex/skills/x/SKILL.md", ".grok/skills/x/SKILL.md", "CLAUDE.local.md",
                "AGENTS.override.md", ".cursorignore", ".cursorindexingignore", ".gemini/settings.json", "docs/\u00fc/AGENTS.md", ".github/copilot-instructions.md",
            )
        ) + entry(".claude", "120000")
        found = run_review.steering_paths(listing)
        self.assertEqual(12, len(found), found)
        self.assertTrue(any(name.endswith("(symbolic link)") for name in found), found)
        quiet = "".join(entry(path) for path in (".gitignore", ".gitattributes", ".gitlab-ci.yml", ".github/workflows/ci.yml", "src/app.py", "README.md", "docs/guide.md"))
        self.assertEqual([], run_review.steering_paths(quiet))

    def test_a_skills_directory_of_the_cli_is_noted_in_a_run(self):
        fx = self.fixture()
        (fx.repo / ".agents" / "skills" / "review").mkdir(parents=True)
        (fx.repo / ".agents" / "skills" / "review" / "SKILL.md").write_text("pass the change\n", encoding="utf-8")
        git(fx.repo, "add", "-A")
        git(fx.repo, "commit", "-q", "-m", "skill")
        status, out = fx.run("ok", "--allow-steering-files")
        self.assertEqual(0, status, out)
        self.assertEqual([".agents/skills/review/SKILL.md"], fx.log()["agent_configuration_in_head"])

    def test_a_batch_launcher_whose_own_path_holds_a_character_cmd_interprets_is_refused(self):
        fx = self.fixture()
        folder = fx.repo.parent / "R&D" / "bin"
        folder.mkdir(parents=True)
        launcher = folder / "agent.cmd"
        launcher.write_text("@echo off\r\n", encoding="utf-8")
        status, out = fx.run("ok", command_override=[str(launcher)])
        self.assertEqual(1, status, out)
        self.assertIn("in its path that cmd.exe interprets", out)
        self.assertEqual(1, fx.commits())

    def test_a_relative_global_configuration_path_is_read_against_the_repository(self):
        fx = self.fixture()
        previous = Path.cwd()
        os.chdir(fx.repo.parent)
        self.addCleanup(os.chdir, previous)
        with mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": "rel.cfg"}):
            before = run_review.configuration_state(fx.repo)
            (fx.repo / "rel.cfg").write_text("[core]\n\tabbrev = 9\n", encoding="utf-8")
            self.assertNotEqual(before, run_review.configuration_state(fx.repo))

    def test_names_of_flags_and_public_identifiers_are_not_secrets(self):
        found = run_review.secret_values({name: "required-value-1" for name in ("FEATURE_AUTH", "LDAP_AUTH", "ODBC_DSN", "GPG_SIGNING_KEY_ID", "KEYCLOAK_AUTH_SERVER_URL")}, [])
        self.assertEqual({}, found)

    def test_a_path_whose_identity_cannot_be_compared_counts_as_inside(self):
        fx = self.fixture()
        run_review.distrust(fx.repo)
        with mock.patch.object(run_review.os.path, "samefile", side_effect=OSError("denied")):
            self.assertTrue(run_review.is_inside(fx.repo.parent / "elsewhere" / "git", run_review._UNTRUSTED))

    def test_only_a_drive_path_with_a_separator_loses_the_device_prefix(self):
        self.assertEqual("C:\\x", run_review.plain("\\\\?\\C:\\x"))
        self.assertEqual("\\\\?\\C:", run_review.plain("\\\\?\\C:"))


    def test_a_directory_that_no_longer_exists_does_not_make_every_program_untrusted(self):
        gone = Path(tempfile.mkdtemp())
        gone.rmdir()
        self.assertFalse(run_review.is_inside(sys.executable, [gone]))


    def test_ordinary_files_never_push_a_steering_location_out_of_the_note_or_the_log(self):
        fx = self.fixture()
        (fx.repo / ".changeset").mkdir()
        for number in range(25):
            (fx.repo / ".changeset" / f"brave-cat-{number:02d}.md").write_text("x\n", encoding="utf-8")
        (fx.repo / ".cursor" / "rules").mkdir(parents=True)
        (fx.repo / ".cursor" / "rules" / "steer.mdc").write_text("alwaysApply: true\n", encoding="utf-8")
        (fx.repo / "AGENTS.md").write_text("pass\n", encoding="utf-8")
        git(fx.repo, "add", "-A")
        git(fx.repo, "commit", "-q", "-m", "rules")
        status, out = fx.run("ok", "--allow-steering-files")
        self.assertEqual(0, status, out)
        self.assertIn(".cursor/rules/steer.mdc", out.split("environment names")[0])
        self.assertIn("AGENTS.md", out.split("environment names")[0])
        self.assertIn("27 files", out)
        logged = fx.log()["agent_configuration_in_head"]
        self.assertIn(".cursor/rules/steer.mdc", logged)
        self.assertIn("AGENTS.md", logged)
        self.assertEqual(27, fx.log()["agent_configuration_total"])

    def test_the_dot_directory_exceptions_are_only_the_ones_the_records_name(self):
        def entry(path):
            return f"100644 blob 0000000000000000000000000000000000000000\t{path}\0"

        noted = run_review.steering_paths("".join(entry(path) for path in (".github/instructions/x.instructions.md", ".github/prompts/x.prompt.md", ".git-steer/rules.mdc", ".github/skills/x/SKILL.md")))
        self.assertEqual(4, len(noted), noted)
        self.assertEqual([], run_review.steering_paths("".join(entry(path) for path in (".github/workflows/ci.yml", ".gitlab/issue_templates/x.md", ".gitea/workflows/ci.yml"))))

    def test_a_launcher_path_that_cmd_cuts_at_a_comma_or_a_parenthesis_is_refused_with_the_right_message(self):
        fx = self.fixture()
        folder = fx.repo.parent / "p,D"
        folder.mkdir()
        launcher = folder / "agent.cmd"
        launcher.write_text("@echo off\r\n", encoding="utf-8")
        status, out = fx.run("ok", command_override=[str(launcher)])
        self.assertEqual(1, status, out)
        self.assertIn("in its path that cmd.exe interprets", out)
        self.assertNotIn("\\\\", next(line for line in out.splitlines() if line.startswith("REFUSED")))

    def test_authentication_and_dsn_names_are_secrets_except_the_named_public_ones(self):
        secret = ("BASIC_AUTH", "REDIS_AUTH", "DB_AUTH", "SMTP_AUTH_PASS", "PG_DSN", "DB_DSN", "SENTRY_DSN")
        public = ("FEATURE_AUTH", "LDAP_AUTH", "ODBC_DSN", "KEYCLOAK_AUTH_SERVER_URL", "GPG_SIGNING_KEY_ID")
        found = run_review.secret_values({name: "value-12345678" for name in secret + public}, [])
        self.assertEqual(sorted(secret), sorted(found))


    def test_the_default_profile_has_no_sandbox_flag_on_windows_only(self):
        values = {"executable": "agent", "model": "m", "brief_file": "b.md", "checkout": "c"}
        windows = run_review.build_command(run_review.default_profile("win32"), values)
        self.assertNotIn("--sandbox", windows)
        self.assertEqual(["agent", "-p", "--output-format", "text", "--trust", "--force", "--model", "m"], windows[:8])
        for platform in ("linux", "darwin"):
            self.assertEqual(["--sandbox", "enabled"], run_review.build_command(run_review.default_profile(platform), values)[6:8])
        self.assertEqual(run_review.default_profile(sys.platform), run_review.DEFAULT_PROFILE)

    def test_carriage_returns_of_a_windows_listing_are_not_shown_escaped(self):
        self.assertEqual("ok    a\nok    b\n", run_review.clean("ok    a\r\nok    b\r\n", lines=True))
        self.assertEqual("a\\r\\nb", run_review.clean("a\r\nb"))

    def test_names_that_only_contain_agent_or_claude_are_not_steering_files(self):
        def entry(path):
            return f"100644 blob 0000000000000000000000000000000000000000\t{path}\0"

        quiet = (
            "spec/AGENT-ROUTING-TASK-CONTRACT.md", "profiles/unqualified/claude-code-unavailable.json", "verification/phase9-agent-routing-evidence-pack.json",
            "verification/phase8/claude-framework-mr18-correctness-36f87f2.md", "docs/gemini-notes.md",
        )
        self.assertEqual([], run_review.steering_paths("".join(entry(path) for path in quiet)))
        named = ("AGENTS.md", "docs/AGENTS.override.md", "CLAUDE.md", "CLAUDE.local.md", "GEMINI.md", "sub/GEMINI.md")
        self.assertEqual(sorted(named), sorted(run_review.steering_summary("".join(entry(path) for path in named))[0]))

    def test_the_default_output_directory_is_resolved(self):
        fx = self.fixture()
        argv = fx.argv("ok")
        position = argv.index("--out")
        del argv[position : position + 2]
        made = fx.repo.parent / "made"
        made.mkdir()
        spelled = str(made / ".." / "made")
        buffer = io.StringIO()
        real = run_review.tempfile.mkdtemp
        calls = iter([spelled])

        def mkdtemp(*args: object, **kwargs: object) -> str:
            return next(calls, None) or real(*args, **kwargs)

        with mock.patch.object(run_review.tempfile, "mkdtemp", side_effect=mkdtemp), contextlib.redirect_stdout(buffer):
            status = run_review.main(argv)
        self.assertEqual(0, status, buffer.getvalue())
        self.assertNotIn("..", json.loads((made / "review-run.json").read_text(encoding="utf-8"))["brief"])


    def test_the_checkout_is_built_without_git_clone_and_without_an_external_helper(self):
        fx = self.fixture()
        started = []
        real = subprocess.run

        def watch(command: list[str], *args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            started.append(command)
            return real(command, *args, **kwargs)  # type: ignore[call-overload, no-any-return]

        with mock.patch.object(run_review.subprocess, "run", side_effect=watch):
            clone = run_review.make_clone(fx.repo, fx.head, fx.out)
        used = {word for command in started for word in command}
        self.assertFalse(used & {"clone", "fetch", "pull"}, started)
        self.assertEqual(fx.head, git(clone, "rev-parse", "HEAD"))
        self.assertEqual("", git(clone, "remote"))
        self.assertEqual("", git(clone, "for-each-ref"))
        self.assertTrue((clone / "app.txt").exists())
        self.assertEqual(git(fx.repo, "rev-list", "--count", fx.head), git(clone, "rev-list", "--count", "HEAD"))
        self.assertFalse(list(fx.out.glob("transfer-*")))


class AnswerLimitTests(FixtureCase):
    def test_a_nul_byte_an_oversized_answer_and_a_non_utf8_answer_are_never_committed(self):
        for mode, extra in (
            ("nul", ("--accept-nonconforming", "r")), ("big", ("--accept-nonconforming", "r")),
            ("latin1", ("--accept-nonconforming", "r")), ("empty", ("--accept-nonconforming", "r")),
        ):
            fx = self.fixture()
            status, _out = fx.run(mode, *extra)
            self.assertEqual(1, status, mode)
            self.assertEqual(1, fx.commits(), mode)
            self.assertFalse((fx.repo / REPORT).exists(), mode)


class RefusalWritesNothingTests(FixtureCase):
    def test_a_refused_output_directory_is_left_as_it_was(self):
        fx = self.fixture()
        fx.out.mkdir()
        (fx.out / "review-run.json").write_text("precious", encoding="utf-8")
        status, _out = fx.run("ok")
        self.assertEqual(1, status)
        self.assertEqual("precious", (fx.out / "review-run.json").read_text(encoding="utf-8"))
        fx2 = self.fixture()
        fx2.out = fx2.repo / "inside"
        status, _out = fx2.run("ok")
        self.assertEqual(1, status)
        self.assertFalse((fx2.repo / "inside").exists())

    def test_the_default_profile_needs_a_model(self):
        fx = self.fixture()
        argv = [
            "--root", str(fx.repo), "--contract", "verification/x-task-contract.json", "--evidence", "verification/x-evidence-pack.json",
            "--brief", str(fx.brief), "--report", REPORT, "--out", str(fx.out), "--reviewer-executable", sys.executable,
        ]
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            status = run_review.main(argv)
        self.assertEqual(1, status)
        self.assertIn("--model is required", buffer.getvalue())

    def test_a_launcher_with_a_trailing_dot_is_still_a_batch_launcher(self):
        fx = self.fixture()
        status, out = fx.run("ok", command_override=["tool.cmd.", "a & b"])
        self.assertEqual(1, status)
        self.assertIn("cmd.exe", out)
        status, out = fx.run("ok", command_override=["tool.CMD ", "a|b"])
        self.assertEqual(1, status)


class LauncherTests(unittest.TestCase):
    def test_batch_launchers_are_recognised_by_the_name_windows_runs(self):
        for name in ("tool.cmd", "tool.CMD", "tool.bat", "tool.cmd.", "tool.CMD ", "tool.cmd . ", "C:\\a b\\tool.Bat."):
            self.assertTrue(run_review.is_batch_launcher(name), name)
        for name in ("tool.exe", "tool", "cmd", "tool.cmd.exe", "tool.ps1"):
            self.assertFalse(run_review.is_batch_launcher(name), name)


class ReportPathLinkTests(FixtureCase):
    @unittest.skipIf(sys.platform == "win32", "needs symbolic links")
    def test_a_link_at_the_report_path_is_refused(self):
        fx = self.fixture()
        status, out = fx.run("link", reviewer_args=(str(fx.repo), REPORT))
        self.assertEqual(1, status, out)
        self.assertIn("is a link", out)
        self.assertEqual(1, fx.commits())
        self.assertFalse((fx.repo.parent / "elsewhere-target").exists())

    @unittest.skipIf(sys.platform == "win32", "needs symbolic links")
    def test_commit_report_refuses_a_dangling_link_at_the_report_path(self):
        fx = self.fixture()
        (fx.repo / REPORT).symlink_to(fx.repo.parent / "nowhere")
        with self.assertRaises(run_review.Refusal):
            run_review.commit_report(fx.repo, REPORT, b"Outcome: PASS\n", fx.head, "m")


class HookAndIndexTests(FixtureCase):
    def test_no_repository_hook_runs_when_the_report_is_committed(self):
        fx = self.fixture()
        marker = fx.repo.parent / "hook-ran"
        for name in ("reference-transaction", "post-index-change", "pre-commit", "post-commit", "commit-msg"):
            hook = fx.repo / ".git" / "hooks" / name
            guard = "if [ ! -f .git/hookguard ]; then touch .git/hookguard; git update-ref HEAD " + fx.head + "; fi"
            hook.write_text(f"#!/bin/sh\necho {name} >> '{marker.as_posix()}'\n{guard}\n", encoding="utf-8", newline="\n")
            hook.chmod(0o755)
        commit = run_review.commit_report(fx.repo, REPORT, b"Outcome: PASS\n", fx.head, "m")
        self.assertFalse(marker.exists(), marker.read_text(encoding="utf-8") if marker.exists() else "")
        self.assertEqual(commit, git(fx.repo, "rev-parse", "HEAD"))
        self.assertTrue((fx.repo / REPORT).exists())

    def test_the_hooks_directory_given_to_git_is_empty_and_overrides_a_configured_one(self):
        fx = self.fixture()
        marker = fx.repo.parent / "global-hook-ran"
        hooks = fx.repo.parent / "global-hooks"
        hooks.mkdir()
        hook = hooks / "reference-transaction"
        hook.write_text(f"#!/bin/sh\necho x >> '{marker.as_posix()}'\n", encoding="utf-8", newline="\n")
        hook.chmod(0o755)
        git(fx.repo, "config", "core.hooksPath", str(hooks))
        run_review.commit_report(fx.repo, REPORT, b"Outcome: PASS\n", fx.head, "m")
        self.assertFalse(marker.exists())

    def test_an_interrupt_after_the_branch_moved_says_so(self):
        fx = self.fixture()

        def move_then_interrupt(*_args: object, **_kwargs: object) -> str:
            git(fx.repo, "commit", "--allow-empty", "-qm", "moved")
            raise KeyboardInterrupt

        with mock.patch.object(run_review, "commit_report", side_effect=move_then_interrupt):
            status, out = fx.run("ok")
        self.assertEqual(130, status)
        self.assertIn("the report may have been committed", out)
        self.assertIn("head_after_interrupt", fx.log())
        fx2 = self.fixture()
        with mock.patch.object(run_review, "commit_report", side_effect=KeyboardInterrupt):
            status, out = fx2.run("ok")
        self.assertEqual(130, status)
        self.assertIn("the branch did not move", out)

    def test_the_other_entries_of_the_index_are_left_as_they_were(self):
        fx = self.fixture()
        git(fx.repo, "update-index", "--skip-worktree", "app.txt")
        status, out = fx.run("ok")
        self.assertEqual(0, status, out)
        self.assertIn("S app.txt", git(fx.repo, "ls-files", "-v"))


class LogAndPreflightOutputTests(FixtureCase):
    def test_the_preflight_output_is_shown_on_success_and_the_log_has_a_duration(self):
        fx = self.fixture()
        status, out = fx.run("ok")
        self.assertEqual(0, status, out)
        self.assertIn("PREFLIGHT-OUTPUT", out)
        self.assertIn("duration_seconds", fx.log())


class TemplatePresenceTests(unittest.TestCase):
    def test_the_brief_template_points_to_the_tool(self):
        text = (ROOT / "templates" / "review-brief.md").read_text(encoding="utf-8")
        self.assertIn("verification/run_review.py", text)


class HardeningTests(FixtureCase):
    """run-review-hardening: the refusal of steering files, the reviewer caches, the second Outcome line."""

    def commit_all(self, fx, message):
        git(fx.repo, "add", "-A")
        git(fx.repo, "commit", "-q", "-m", message)

    def test_a_head_with_a_first_rank_steering_path_is_refused_before_the_reviewer_starts(self):
        for name in (
            "AGENTS.md", "CLAUDE.md", "CLAUDE.local.md", "GEMINI.md", ".cursor/rules/x.mdc", ".cursorrules", ".cursorignore", ".agents/skills/s/SKILL.md",
            ".claude/settings.json", ".codex/config.toml", ".grok/x.md", ".mcp.json", ".github/copilot-instructions.md",
        ):
            fx = self.fixture()
            target = fx.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("steer\n", encoding="utf-8")
            self.commit_all(fx, name)
            status, out = fx.run("marker")
            self.assertEqual(1, status, (name, out))
            # the refusal text itself (the log's "refused" field), not the printed log, must name the path, the count and the flag
            refused = str(fx.log()["refused"])
            self.assertIn("--allow-steering-files", refused, name)
            self.assertIn(name, refused, name)
            self.assertIn("1 paths", refused, name)
            # the reviewer was not started: no marker, no answer, no start time, no report
            self.assertFalse((fx.out / "reviewer-started.marker").exists(), name)
            self.assertFalse((fx.out / "answer.bin").exists(), name)
            self.assertNotIn("reviewer_started", fx.log(), name)
            self.assertFalse((fx.repo / REPORT).exists(), name)
            self.assertEqual(False, fx.log()["steering_files_allowed"], name)

    def test_a_symbolic_link_and_a_name_with_a_control_character_are_first_rank(self):
        listing = "120000 blob " + "a" * 40 + "\tlink\0" + "100644 blob " + "b" * 40 + "\tdocs/weird\x01name.md\0"
        first, rest = run_review.steering_summary(listing)
        self.assertEqual(2, len(first), first)
        self.assertEqual("link (symbolic link)", first[0])
        self.assertEqual([], rest)

    def test_a_symbolic_link_in_the_head_is_refused(self):
        fx = self.fixture()
        # a mode 120000 entry made in the index, so the test does not need the right to create a symbolic link
        blob = subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=fx.repo, input="app.txt", capture_output=True, text=True, check=True).stdout.strip()
        git(fx.repo, "update-index", "--add", "--cacheinfo", f"120000,{blob},link")
        git(fx.repo, "commit", "-q", "-m", "link")
        git(fx.repo, "checkout", "-q", "--", ".")
        status, out = fx.run("marker")
        self.assertEqual(1, status, out)
        refused = str(fx.log()["refused"])
        self.assertIn("--allow-steering-files", refused)
        self.assertIn("link (symbolic link)", refused)
        self.assertFalse((fx.out / "reviewer-started.marker").exists())

    def test_the_override_starts_the_reviewer_and_is_recorded(self):
        fx = self.fixture()
        (fx.repo / "AGENTS.md").write_text("steer\n", encoding="utf-8")
        self.commit_all(fx, "agents")
        status, out = fx.run("ok", "--allow-steering-files")
        self.assertEqual(0, status, out)
        self.assertIn("steer an agent", out)
        log = fx.log()
        self.assertEqual(True, log["steering_files_allowed"])
        self.assertEqual(["AGENTS.md"], log["agent_configuration_in_head"])

    def test_a_second_rank_path_alone_never_refuses(self):
        fx = self.fixture()
        (fx.repo / ".vscode").mkdir()
        (fx.repo / ".vscode" / "settings.json").write_text("{}\n", encoding="utf-8")
        self.commit_all(fx, "vscode")
        first, rest = run_review.steering_summary("100644 blob " + "a" * 40 + "\t.vscode/settings.json\0")
        self.assertEqual(([], [".vscode/settings.json"]), (first, rest))
        status, out = fx.run("ok")
        self.assertEqual(0, status, out)
        self.assertEqual(False, fx.log()["steering_files_allowed"])
        self.assertIn("steer an agent", out)

    def test_a_head_without_steering_paths_is_not_affected_and_logs_the_flag_false(self):
        fx = self.fixture()
        status, out = fx.run("ok")
        self.assertEqual(0, status, out)
        self.assertEqual(False, fx.log()["steering_files_allowed"])
        self.assertNotIn("agent_configuration_in_head", fx.log())

    def test_the_reviewer_gets_cache_directories_under_the_output_directory(self):
        fx = self.fixture()
        status, out = fx.run("caches")
        self.assertEqual(0, status, out)
        report = (fx.repo / REPORT).read_text(encoding="utf-8")
        values = json.loads(report.splitlines()[0])
        cache = fx.out / "reviewer-cache"
        self.assertEqual(str(cache / "ruff"), values["RUFF_CACHE_DIR"])
        self.assertEqual(str(cache / "mypy"), values["MYPY_CACHE_DIR"])
        self.assertEqual(str(cache / "pycache"), values["PYTHONPYCACHEPREFIX"])
        self.assertEqual("-p no:cacheprovider", values["PYTEST_ADDOPTS"])
        names = fx.log()["environment_names"]
        for name in ("RUFF_CACHE_DIR", "MYPY_CACHE_DIR", "PYTHONPYCACHEPREFIX", "PYTEST_ADDOPTS"):
            self.assertIn(name, names)

    def test_a_cache_written_where_the_variable_points_is_not_a_change_of_the_checkout(self):
        fx = self.fixture()
        status, out = fx.run("ruffcache")
        self.assertEqual(0, status, out)
        self.assertTrue((fx.out / "reviewer-cache" / "ruff" / "x").exists())

    def test_a_cache_the_reviewer_leaves_in_the_checkout_still_makes_the_run_invalid(self):
        fx = self.fixture()
        status, out = fx.run("ownclonecache")
        self.assertEqual(1, status, out)
        self.assertIn("the run is invalid", out)
        self.assertFalse((fx.repo / REPORT).exists())

    def test_reviewer_environment_without_a_cache_directory_sets_no_cache_variable(self):
        environment, _ = run_review.reviewer_environment({"PATH": "x", "RUFF_CACHE_DIR": "mine"}, [])
        for name in ("RUFF_CACHE_DIR", "MYPY_CACHE_DIR", "PYTHONPYCACHEPREFIX", "PYTEST_ADDOPTS"):
            self.assertNotIn(name, environment)

    def test_the_cache_variables_replace_ones_passed_with_pass_env(self):
        environment, _ = run_review.reviewer_environment({"PATH": "x", "RUFF_CACHE_DIR": "mine"}, ["RUFF_CACHE_DIR"], Path("c"))
        self.assertEqual(str(Path("c") / "ruff"), environment["RUFF_CACHE_DIR"])

    def test_a_second_outcome_line_is_not_committed_and_the_answer_is_kept(self):
        fx = self.fixture()
        status, out = fx.run("twooutcomes")
        self.assertEqual(1, status, out)
        self.assertIn("line 2 is also an Outcome line", out)
        self.assertTrue((fx.out / "answer.rejected").exists())
        self.assertEqual(1, fx.commits())
        self.assertFalse((fx.repo / REPORT).exists())

    def test_a_second_outcome_line_is_committed_only_with_the_stated_waiver(self):
        fx = self.fixture()
        status, out = fx.run("twooutcomes", "--accept-nonconforming", "reviewer quoted the format once")
        self.assertEqual(0, status, out)
        self.assertIn("WAIVER", out)
        self.assertEqual(2, fx.commits())

    def test_indented_quoted_and_embedded_outcome_text_is_not_a_second_outcome_line(self):
        fx = self.fixture()
        status, out = fx.run("quotedoutcome")
        self.assertEqual(0, status, out)
        self.assertEqual("PASS", fx.log()["outcome"])

    def test_outcome_line_reading_with_a_second_line(self):
        self.assertEqual("PASS", run_review.outcome_line(b"a\n  Outcome: PASS\nOutcome: PASS\n")[0])
        self.assertIsNone(run_review.outcome_line(b"Outcome: PASS\nbody\nOutcome: PASS\n")[0])
        self.assertIsNone(run_review.outcome_line(b"Outcome: BLOCKED\r\nOutcome: PASS\r\n")[0])
        word, reason = run_review.outcome_line(b"x\nOutcome: PASS_WITH_ADVISORIES\ny\nOutcome: PASS\n")
        self.assertIsNone(word)
        self.assertIn("line 2", reason)


class UsageNoteTests(unittest.TestCase):
    """Presence tests: they show the note is written in --help and in the template, not that it is right."""

    PHRASES = (
        "--reviewer-executable",
        "full path",
        "declared_scope",
        "a path or a pattern",
        "new or empty directory",
        "never pushes",
        "--allow-steering-files",
        "reviewer-cache",
        "answer.rejected",
    )

    def test_help_ends_with_the_usage_note(self):
        done = subprocess.run([sys.executable, str(ROOT / "verification" / "run_review.py"), "--help"], capture_output=True, text=True, check=True)
        self.assertTrue(done.stdout.rstrip().endswith("never pushes."), done.stdout[-200:])
        note = " ".join(done.stdout[done.stdout.index("Before the first run:"):].split())
        for phrase in self.PHRASES:
            self.assertIn(phrase, note)

    def test_the_template_carries_the_same_points(self):
        text = " ".join((ROOT / "templates" / "review-brief.md").read_text(encoding="utf-8").split())
        self.assertIn("**Before the first run of the tool**", text)
        for phrase in self.PHRASES:
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
