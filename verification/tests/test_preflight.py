"""Tests for verification/preflight.py: command extraction, the attestation lookup, and the exit status of a skipped lookup."""

from __future__ import annotations

import contextlib
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
SPEC = importlib.util.spec_from_file_location("preflight", ROOT / "verification" / "preflight.py")
assert SPEC and SPEC.loader
preflight = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = preflight
SPEC.loader.exec_module(preflight)

TEMPLATE = """stages:
  - verify

checker-fixtures:
  stage: verify
  script:
    - test "$(git --version)" = "git version 2.52.0"
    - python3 --version
    - python3 -m unittest discover -s verification/tests -v
    - 'python3 -m pip install --only-binary=:all: --require-hashes -r verification/requirements-static.txt'
    - python3 -c "print(1)" | cat
    - curl http://example.invalid
    - |
      python3 -I - <<'PY'
      print("not a one-line command")
      PY

static-analysis:
  stage: verify
  script:
    - ruff check verification
    - mypy --strict verification/aidf_check.py

aidf-governance:
  script:
    - |
      python3 -I - <<'PY'
      records = (
          ("verification/aidf_check.py", checker_sha256),
          ("verification/policy.json", policy_sha256),
      )
      for relative, expected in records + selected_records:
          check(relative, expected)
      phase8_records = (
          (".gitlab-ci.yml", "49d7232a86f03f895eb80aeb44ddae923727f510387da951a9a07c188ec25828"),
      )
      selected_records = phase8_records if candidate_sha == "x" else ()
      for command, extra in (
          ("contract", ["--contract", "x"]),
      ):
          pass
      for command, extra in (
          ("exemptions", ["--policy-b64", policy_b64]),
          ("secrets", []),
          ("test-delta", []),
          ("dependencies", []),
      ):
          run(command)
      PY
"""


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def init_repo(path: Path) -> None:
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.email", "t@example.invalid")
    git(path, "config", "user.name", "t")


class ExtractionTests(unittest.TestCase):
    def test_job_commands_runs_only_the_allowed_single_line_commands(self):
        runnable, skipped = preflight.job_commands(TEMPLATE, "checker-fixtures")
        self.assertEqual(["python3 --version", "python3 -m unittest discover -s verification/tests -v"], runnable)
        self.assertIn('test "$(git --version)" = "git version 2.52.0"', skipped)
        self.assertIn("python3 -m pip install --only-binary=:all: --require-hashes -r verification/requirements-static.txt", skipped)
        self.assertIn('python3 -c "print(1)" | cat', skipped)
        self.assertIn("curl http://example.invalid", skipped)
        self.assertNotIn("|", runnable)

    def test_static_analysis_commands(self):
        runnable, _ = preflight.job_commands(TEMPLATE, "static-analysis")
        self.assertEqual(["ruff check verification", "mypy --strict verification/aidf_check.py"], runnable)

    def test_a_missing_job_is_an_error_not_an_empty_list(self):
        with self.assertRaises(ValueError):
            preflight.job_commands(TEMPLATE, "no-such-job")

    def test_attested_records_are_the_records_tuple_only(self):
        self.assertEqual(
            [("verification/aidf_check.py", "checker_sha256"), ("verification/policy.json", "policy_sha256")],
            preflight.attested_records(TEMPLATE),
        )

    def test_governance_commands_are_the_last_block(self):
        self.assertEqual(["exemptions", "secrets", "test-delta", "dependencies"], preflight.governance_commands(TEMPLATE))

    def test_a_record_entry_of_another_shape_fails_closed(self):
        for entry in ('("verification/other.py", "' + "0" * 64 + '"),', '("verification/other.py", variable + 1),', "extra_record,"):
            changed = TEMPLATE.replace(
                '("verification/policy.json", policy_sha256),', '("verification/policy.json", policy_sha256),\n          ' + entry, 1
            )
            self.assertNotEqual(TEMPLATE, changed)
            with self.assertRaises(ValueError, msg=entry):
                preflight.attested_records(changed)

    def test_a_changed_record_loop_fails_closed(self):
        for variant in (
            "for relative, expected in records:",
            "for relative, expected in records + selected_records + head_records:",
        ):
            changed = TEMPLATE.replace("for relative, expected in records + selected_records:", variant, 1)
            self.assertNotEqual(TEMPLATE, changed)
            with self.assertRaises(ValueError, msg=variant):
                preflight.attested_records(changed)

    REBINDINGS = (
        'records = (("verification/other.py", other_sha256),)',
        "records += (1,)",
        "records = records[:1]",
        "for records in ():\n          pass",
        "with open('f') as records:\n          pass",
        "import os as records",
        "def records():\n          pass",
        "class records:\n          pass",
        "(records := ())",
        "global records",
        "del records",
        "selected_records = ()",
        "selected_records += ()",
        "try:\n          pass\n      except OSError as selected_records:\n          pass",
        "f = lambda records: 0",
        "match candidate_sha:\n          case records:\n              pass",
        "match candidate_sha:\n          case [*records]:\n              pass",
        "match candidate_sha:\n          case {**selected_records}:\n              pass",
        "match candidate_sha:\n          case [1, 2] as records:\n              pass",
        "from os import *",
        "import records.sub",
        "def f(*records):\n          pass",
        "def f(**selected_records):\n          pass",
        "type records = int",
    )

    def test_each_rebinding_form_listed_here_fails_closed(self):
        for statement in self.REBINDINGS:
            changed = TEMPLATE.replace("      phase8_records = (\n", "      " + statement + "\n      phase8_records = (\n", 1)
            self.assertNotEqual(TEMPLATE, changed)
            with self.assertRaises(ValueError, msg=statement) as caught:
                preflight.attested_records(changed)
            self.assertIn("other than exactly once", str(caught.exception), msg=statement)

    def test_a_loop_that_can_skip_an_entry_or_is_not_top_level_fails_closed(self):
        loop = "      for relative, expected in records + selected_records:\n          check(relative, expected)\n"
        self.assertIn(loop, TEMPLATE)
        for name, replacement in (
            ("break", loop + "          break\n"),
            ("continue", loop + "          continue\n"),
            ("nested", "      if candidate_sha:\n          for relative, expected in records + selected_records:\n              check(relative, expected)\n"),
            ("absent", "      pass\n"),
        ):
            changed = TEMPLATE.replace(loop, replacement, 1)
            self.assertNotEqual(TEMPLATE, changed)
            with self.assertRaises(ValueError, msg=name):
                preflight.attested_records(changed)

    def test_names_that_are_only_read_or_are_not_variables_do_not_count_as_bindings(self):
        for statement in ("x = records[0]", "f(records=1)", "y = obj.records", "z = 'records'", "from os import records_dir", "print(selected_records)"):
            changed = TEMPLATE.replace("      phase8_records = (\n", "      " + statement + "\n      phase8_records = (\n", 1)
            self.assertNotEqual(TEMPLATE, changed)
            self.assertEqual(2, len(preflight.attested_records(changed)), msg=statement)

    def test_statements_before_the_loop_that_end_the_script_are_a_stated_limit_and_pass(self):
        changed = TEMPLATE.replace("      phase8_records = (\n", "      raise SystemExit(0)\n      phase8_records = (\n", 1)
        self.assertEqual(2, len(preflight.attested_records(changed)))

    def test_what_the_script_computes_is_not_examined_and_those_shapes_pass(self):
        emptied = TEMPLATE.replace(
            "      phase8_records = (\n",
            "      class _Skip:\n          def __radd__(self, other):\n              return ()\n      phase8_records = (\n",
            1,
        ).replace("if candidate_sha == \"x\" else ()", "if candidate_sha == \"x\" else _Skip()", 1)
        patched_exit = TEMPLATE.replace("      phase8_records = (\n", "      import atexit\n      atexit.register(os._exit, 0)\n      phase8_records = (\n", 1)
        patched_hash = TEMPLATE.replace("      phase8_records = (\n", "      hashlib.sha256 = lambda b: b\n      phase8_records = (\n", 1)
        for changed in (emptied, patched_exit, patched_hash):
            self.assertNotEqual(TEMPLATE, changed)
            self.assertEqual(2, len(preflight.attested_records(changed)))

    def test_a_python_error_in_the_policy_job_fails_closed(self):
        with self.assertRaises(ValueError):
            preflight.attested_records(TEMPLATE.replace("      phase8_records = (\n", "      phase8_records = (((\n", 1))

    def test_missing_blocks_are_errors(self):
        with self.assertRaises(ValueError):
            preflight.attested_records("stages: []\n")
        with self.assertRaises(ValueError):
            preflight.governance_commands("stages: []\n")

    def test_default_policy_repo_is_the_sibling_of_origin(self):
        self.assertEqual("git@host.invalid:Group/aidf-ci-policy.git", preflight.default_policy_repo("git@host.invalid:Group/ai-development-framework.git"))
        self.assertEqual("https://host.invalid/Group/aidf-ci-policy.git", preflight.default_policy_repo("https://host.invalid/Group/ai-development-framework"))


class AttestationTests(unittest.TestCase):
    RECORDS = (("verification/aidf_check.py", "checker_sha256"), ("verification/policy.json", "policy_sha256"),)

    def files(self, checker: bytes, policy: bytes):
        trusted = {"trusted/aidf_check.py": b"line one\r\nline two\r\n", "trusted/policy.json": b"{}\r\n"}
        committed = {"verification/aidf_check.py": checker, "verification/policy.json": policy}
        return trusted.get, committed.get

    def test_matching_files_pass_with_line_endings_normalised(self):
        trusted, committed = self.files(b"line one\nline two\n", b"{}\n")
        self.assertEqual(([], []), preflight.check_attestation(list(self.RECORDS), trusted, committed))

    def test_a_changed_attested_file_is_named(self):
        trusted, committed = self.files(b"line one\nline two\nline three\n", b"{}\n")
        mismatches, errors = preflight.check_attestation(list(self.RECORDS), trusted, committed)
        self.assertEqual([], errors)
        self.assertEqual(1, len(mismatches))
        self.assertIn("attested record hash mismatch: verification/aidf_check.py", mismatches[0])
        self.assertIn("cross-repository T3", mismatches[0])

    def test_an_unknown_record_variable_fails_closed(self):
        trusted, committed = self.files(b"x", b"y")
        mismatches, errors = preflight.check_attestation([("verification/new.py", "new_sha256")], trusted, committed)
        self.assertEqual([], mismatches)
        self.assertEqual(1, len(errors))
        self.assertIn("unknown attested record variable", errors[0])

    def test_a_missing_file_is_a_finding(self):
        trusted, _ = self.files(b"x", b"y")
        mismatches, errors = preflight.check_attestation(list(self.RECORDS), trusted, {}.get)
        self.assertEqual([], mismatches)
        self.assertEqual(2, len(errors))


class PackWordingTests(unittest.TestCase):
    def test_the_sentence_that_was_blocked_in_review_preflight_is_flagged(self):
        pack = json.loads((ROOT / "verification" / "review-preflight-evidence-pack.json").read_text(encoding="utf-8"))
        examined, flagged = preflight.pack_wording(pack)
        self.assertGreater(examined, 5)
        self.assertTrue(
            any("a policy that attests files by another mechanism fails the lookup closed" in text for text in flagged),
            msg="the B7 sentence is not flagged",
        )

    def test_a_synthetic_guarantee_is_flagged_and_a_cited_one_is_not(self):
        examined, flagged = preflight.pack_wording(
            {
                "a": "The parser never accepts a second entry. It reads one file.",
                "b": ["The parser never accepts a second entry (test_second_entry_is_refused).", "Run python3 -m unittest to see that all pass."],
            }
        )
        self.assertEqual(4, examined)
        self.assertEqual(["The parser never accepts a second entry."], flagged)

    def test_a_program_name_followed_by_a_word_is_not_a_cited_command(self):
        sentences = [
            "The tool never runs git again.",
            "The check cannot fail because python is strict.",
            "No test covers mypy output in any other mode.",
            "The parser never accepts python here.",
            "The pipeline always uses python 3.12 for this.",
            "The step never calls mypy e.g., in strict mode.",
            "The check cannot fail because ruff i.e., the linter is pinned.",
        ]
        examined, flagged = preflight.pack_wording({"x": sentences})
        self.assertEqual((len(sentences), sentences), (examined, flagged))
        _, cited = preflight.pack_wording(
            {"x": ["It never fails: python verification/preflight.py prints ALL OK.", "It cannot differ (git diff --quiet exits 0).", "It never fails: python run.py prints ALL OK."]}
        )
        self.assertEqual([], cited)

    def test_a_pack_without_guarantee_words_has_no_flags(self):
        self.assertEqual((2, []), preflight.pack_wording({"x": "It reads the file. It prints a line."}))


    def test_the_step_does_not_set_the_failed_flag_for_flagged_sentences_or_an_unreadable_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "pack.json"
            good.write_text(json.dumps({"x": "It never fails."}), encoding="utf-8")
            report = preflight.Report()
            with contextlib.redirect_stdout(io.StringIO()) as out:
                preflight.report_pack_wording(report, good)
                preflight.report_pack_wording(report, Path(tmp) / "missing.json")
        self.assertFalse(report.failed)
        self.assertIn("examined 1 sentences, flagged 1", out.getvalue())
        self.assertIn("the pack could not be read", out.getvalue())


class CiLikeEnvironmentTests(unittest.TestCase):
    def test_an_inherited_git_variable_cannot_re_enable_local_path_fetching(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            init_repo(repo)
            (repo / "f").write_text("x", encoding="utf-8")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "one")
            with mock.patch.dict(os.environ, {"GIT_ALLOW_PROTOCOL": "file"}):
                ambient = subprocess.run(["git", "ls-remote", repo.as_uri()], capture_output=True, text=True, check=False)
                env, removed = preflight.ci_like_environment(str(Path(tmp) / "home"), str(Path(tmp) / "empty"))
            if ambient.returncode != 0:
                self.skipTest("git here does not allow file:// fetching, so the inherited variable cannot be shown to matter")
            reduced = subprocess.run(["git", "ls-remote", repo.as_uri()], capture_output=True, text=True, check=False, env=env)
        self.assertIn("GIT_ALLOW_PROTOCOL", removed)
        self.assertNotEqual(0, reduced.returncode)

    def test_the_environment_removes_user_configuration_and_secrets(self):
        with mock.patch.dict(
            os.environ, {"GITLAB_TOKEN": "t", "HTTPS_PROXY": "p", "GIT_CONFIG_GLOBAL": "mine", "GIT_CONFIG_COUNT": "5", "PATH": os.environ.get("PATH", "")}
        ):
            env, removed = preflight.ci_like_environment("/home/fixed", "/home/fixed/empty")
        self.assertEqual("/home/fixed", env["HOME"])
        self.assertEqual("/home/fixed/empty", env["GIT_CONFIG_GLOBAL"])
        self.assertEqual("/home/fixed/empty", env["GIT_CONFIG_SYSTEM"])
        self.assertEqual("1", env["GIT_CONFIG_NOSYSTEM"])
        self.assertEqual(("1", "protocol.file.allow", "never"), (env["GIT_CONFIG_COUNT"], env["GIT_CONFIG_KEY_0"], env["GIT_CONFIG_VALUE_0"]))
        self.assertNotIn("GITLAB_TOKEN", env)
        self.assertEqual({"GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0"}, {k for k in env if k.startswith("GIT_")})
        self.assertNotIn("HTTPS_PROXY", env)
        self.assertIn("GITLAB_TOKEN", removed)
        self.assertIn("PATH", env)


class MainTests(unittest.TestCase):
    """The command line against temporary repositories: one project, one policy repository."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.policy = base / "aidf-ci-policy"
        self.project = base / "project"
        self.policy.mkdir()
        self.project.mkdir()
        init_repo(self.policy)
        (self.policy / "trusted").mkdir()
        (self.policy / "trusted" / "aidf_check.py").write_bytes(b"# checker\r\n")
        (self.policy / "trusted" / "policy.json").write_bytes(b"{}\r\n")
        (self.policy / "aidf-enforced.template.yml").write_text(TEMPLATE, encoding="utf-8", newline="\n")
        git(self.policy, "add", "-A")
        git(self.policy, "commit", "-q", "-m", "policy")
        init_repo(self.project)
        (self.project / "verification").mkdir()
        (self.project / "verification" / "aidf_check.py").write_bytes(b"# checker\n")
        (self.project / "verification" / "policy.json").write_bytes(b"{}\n")
        git(self.project, "add", "-A")
        git(self.project, "commit", "-q", "-m", "base")
        git(self.project, "update-ref", "refs/remotes/origin/main", "HEAD")

    def run_main(self, *extra: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = preflight.main(
                ["--root", str(self.project), "--contract", "c.json", "--evidence", "e.json", "--policy-repo", str(self.policy), *extra]
            )
        return code, out.getvalue()

    def set_policy_template(self, text: str) -> None:
        (self.policy / "aidf-enforced.template.yml").write_text(text, encoding="utf-8", newline="\n")
        git(self.policy, "add", "-A")
        git(self.policy, "commit", "-q", "-m", "template")

    def commit_change(self, path: str, data: bytes) -> None:
        (self.project / path).write_bytes(data)
        git(self.project, "add", "-A")
        git(self.project, "commit", "-q", "-m", "change")

    def test_an_unchanged_attested_file_matches(self):
        _, output = self.run_main()
        self.assertIn("ok    attested files match the policy repository", output)

    def test_a_changed_protected_file_fails_and_names_the_file(self):
        self.commit_change("verification/aidf_check.py", b"# changed\n")
        code, output = self.run_main()
        self.assertEqual(1, code)
        self.assertIn("FAIL  attested files", output)
        self.assertIn("verification/aidf_check.py", output)
        self.assertNotIn("ok    attested files match", output)

    def test_allow_protected_prints_the_reference_and_does_not_fail_that_step(self):
        self.commit_change("verification/aidf_check.py", b"# changed\n")
        _, output = self.run_main("--allow-protected", "T3-change-42")
        self.assertIn("allowed by T3-change-42", output)
        self.assertNotIn("FAIL  attested files", output)

    def test_allow_protected_does_not_excuse_an_unknown_record_variable(self):
        self.set_policy_template(
            TEMPLATE.replace(
                '("verification/policy.json", policy_sha256),', '("verification/policy.json", policy_sha256),\n          ("verification/new.py", new_sha256),', 1
            )
        )
        code, output = self.run_main("--allow-protected", "T3-change-42")
        self.assertEqual(1, code)
        self.assertIn("FAIL  attested files", output)
        self.assertIn("unknown attested record variable new_sha256", output)

    def test_the_steps_run_on_a_clean_checkout_of_the_head(self):
        script = self.project / "verification" / "check_absent.py"
        script.write_text(
            "import sys\nfrom pathlib import Path\nsys.exit(1 if Path('verification/untracked.txt').exists() else 0)\n", encoding="utf-8", newline="\n"
        )
        git(self.project, "add", "-A")
        git(self.project, "commit", "-q", "-m", "script")
        self.set_policy_template(TEMPLATE.replace("    - python3 --version\n", "    - python3 verification/check_absent.py\n", 1))
        (self.project / "verification" / "untracked.txt").write_text("x", encoding="utf-8")
        _, output = self.run_main()
        self.assertIn("ok    python3 verification/check_absent.py", output)
        self.assertTrue((self.project / "verification" / "untracked.txt").exists())

    def test_an_absolute_path_does_not_escape_the_clean_checkout(self):
        checker = self.project / "verification" / "aidf_check.py"
        checker.write_text(
            "import sys\nfrom pathlib import Path\nsys.exit(0 if Path(sys.argv[-1]).exists() else 1)\n", encoding="utf-8", newline="\n"
        )
        git(self.project, "add", "-A")
        git(self.project, "commit", "-q", "-m", "checker")
        (self.project / "verification" / "c.json").write_text("{}", encoding="utf-8")
        for value in ("verification/c.json", (self.project / "verification" / "c.json").as_posix()):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                preflight.main(["--root", str(self.project), "--contract", value, "--evidence", "e.json", "--policy-repo", str(self.policy), "--offline"])
            self.assertNotIn("ok    contract\n", out.getvalue(), msg=value)

    def test_a_path_outside_the_repository_is_refused(self):
        code, output = self.run_main("--contract", str(Path(self.tmp.name) / "outside.json"))
        self.assertEqual(2, code)
        self.assertIn("must be paths inside the repository", output)

    def test_the_policy_ref_is_main_or_a_full_sha(self):
        code, output = self.run_main("--policy-ref", "some-branch")
        self.assertEqual(2, code)
        self.assertIn("--policy-ref must be main or a full 40-character commit SHA", output)
        sha = git(self.policy, "rev-parse", "HEAD")
        _, output = self.run_main("--policy-ref", sha)
        self.assertIn(f"aidf-ci-policy at {sha}", output)

    def test_the_policy_ref_selects_that_commit_and_not_main(self):
        first = git(self.policy, "rev-parse", "HEAD")
        (self.policy / "trusted" / "policy.json").write_bytes(b'{"changed": true}\r\n')
        git(self.policy, "add", "-A")
        git(self.policy, "commit", "-q", "-m", "attested file changed in the policy")
        second = git(self.policy, "rev-parse", "HEAD")
        self.assertNotEqual(first, second)
        _, at_first = self.run_main("--policy-ref", first)
        self.assertIn(f"aidf-ci-policy at {first}", at_first)
        self.assertIn("ok    attested files match the policy repository", at_first)
        _, at_main = self.run_main()
        self.assertIn(f"aidf-ci-policy at {second}", at_main)
        self.assertIn("attested record hash mismatch: verification/policy.json", at_main)

    def test_a_policy_repository_fetched_through_a_transport_is_read(self):
        url = self.policy.as_uri()
        probe = subprocess.run(["git", "ls-remote", url], capture_output=True, text=True, check=False)
        if probe.returncode != 0:
            self.skipTest(f"git cannot fetch a local repository through file:// here ({probe.stderr.strip()[:120]})")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            preflight.main(["--root", str(self.project), "--contract", "c.json", "--evidence", "e.json", "--policy-repo", url])
        head = git(self.policy, "rev-parse", "HEAD")
        self.assertIn(f"aidf-ci-policy at {head}", out.getvalue())
        self.assertIn("ok    attested files match the policy repository", out.getvalue())

    ENV_TEST = (
        "import os\nimport subprocess\nimport unittest\n\n\n"
        "class EnvTests(unittest.TestCase):\n"
        "    def test_the_environment_is_ci_like(self):\n"
        "        self.assertEqual('1', os.environ.get('GIT_CONFIG_NOSYSTEM'))\n"
        "        self.assertEqual('never', os.environ.get('GIT_CONFIG_VALUE_0'))\n"
        "        self.assertNotIn('GITLAB_TOKEN', os.environ)\n\n\n"
        "if __name__ == '__main__':\n    unittest.main()\n"
    )

    def test_ci_like_runs_the_unit_test_step_in_the_reduced_environment_and_plain_does_not(self):
        (self.project / "verification" / "tests").mkdir()
        self.commit_change("verification/tests/test_env.py", self.ENV_TEST.encode("utf-8"))
        with mock.patch.dict(os.environ, {"GITLAB_TOKEN": "t"}):
            for key in ("GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0"):
                os.environ.pop(key, None)
            _, plain = self.run_main()
            _, ci_like = self.run_main("--ci-like")
        self.assertRegex(plain, r"FAIL  python3 -m unittest discover")
        self.assertRegex(ci_like, r"ok    ci-like: python3 -m unittest discover")
        self.assertIn("ci-like environment: HOME=", ci_like)
        self.assertIn("ci-like cannot reproduce:", ci_like)
        self.assertIn("not parity with the pipeline", ci_like)

    def test_the_pack_wording_step_prints_a_count_and_never_fails(self):
        (self.project / "e.json").write_text(json.dumps({"x": "It never fails. It reads a file."}), encoding="utf-8")
        git(self.project, "add", "-A")
        git(self.project, "commit", "-q", "-m", "pack")
        _, output = self.run_main()
        self.assertIn("ok    pack wording: examined 2 sentences, flagged 1 (advisory)", output)
        self.assertIn("note  pack wording: guarantee word without a cited test or command: It never fails.", output)

    def test_a_base_that_is_not_an_ancestor_of_the_head_fails(self):
        git(self.project, "checkout", "-q", "-b", "side")
        self.commit_change("verification/side.txt", b"x")
        git(self.project, "checkout", "-q", "main")
        self.commit_change("verification/main.txt", b"y")
        git(self.project, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(self.project, "checkout", "-q", "side")
        _, output = self.run_main()
        self.assertIn("FAIL  base", output)

    def test_an_uncommitted_tracked_change_is_refused(self):
        (self.project / "verification" / "policy.json").write_bytes(b"{ }\n")
        code, output = self.run_main()
        self.assertEqual(2, code)
        self.assertIn("uncommitted tracked changes", output)

    def test_an_unreachable_policy_repository_is_not_a_pass(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = preflight.main(
                ["--root", str(self.project), "--contract", "c.json", "--evidence", "e.json", "--policy-repo", str(Path(self.tmp.name) / "missing")]
            )
        self.assertEqual(1, code)
        self.assertIn("FAIL  policy lookup", out.getvalue())
        self.assertIn("SKIPPED: policy repository unreachable", out.getvalue())
        self.assertNotIn("FAIL  attested files", out.getvalue())

    def test_offline_is_explicit_and_says_the_list_may_not_match(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            preflight.main(["--root", str(self.project), "--contract", "c.json", "--evidence", "e.json", "--offline"])
        self.assertIn("offline: the built-in command list may not match the pipeline", out.getvalue())
        self.assertNotIn("SKIPPED", out.getvalue())


class TemplatePresenceTests(unittest.TestCase):
    """Presence tests: they show the fields and lines are written, not that they are right."""

    def read(self, path: str) -> str:
        return (ROOT / path).read_text(encoding="utf-8")

    def test_task_contract_has_the_protected_files_field_and_the_new_rule_checklist(self):
        text = self.read("templates/task-contract.md")
        self.assertIn("**Protected files touched**", text)
        self.assertIn("verification/preflight.py", text)
        self.assertIn("**New rule or checker**", text)
        self.assertIn("call a waiver a waiver", text)

    def test_the_pack_template_has_the_guarantee_sentence_rule(self):
        text = " ".join(self.read("templates/evidence-pack.md").split())
        self.assertIn("names the test that fails when the guarantee is false", text)
        self.assertIn("written as a limit", text)

    def test_the_task_contract_checklist_has_the_enumerating_check_item(self):
        text = self.read("templates/task-contract.md")
        self.assertIn("close the class (parse, do not pattern-match)", text)
        self.assertIn("closing one reported shape is not a fix", text)

    def test_review_brief_has_the_standing_lines(self):
        text = self.read("templates/review-brief.md")
        for needle in (
            "preflight.py",
            "say plainly at the top of the report whether your shell worked",
            "apply `core/05-review.md` §4",
            "routes you tried and found closed",
            "PASS_WITH_ADVISORIES",
            "do not raise them as defects",
        ):
            self.assertIn(needle, text)

    def test_the_changelog_records_the_preflight(self):
        self.assertIn("verification/preflight.py", self.read("CHANGELOG.md"))


if __name__ == "__main__":
    unittest.main()
