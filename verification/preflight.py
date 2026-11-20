"""Run the pipeline's checks on a committed head before asking anyone to review it (templates/review-brief.md).

    python verification/preflight.py --contract <task-contract.json> --evidence <evidence-pack.json> [--root .]
        [--base-ref origin/main] [--policy-repo URL] [--policy-ref SHA] [--offline] [--allow-protected REFERENCE] [--ci-like]

The pipeline that enforces is defined in the protected policy repository (aidf-ci-policy, aidf-enforced.template.yml), not in this
repository's .gitlab-ci.yml. When that repository is reachable this tool reads from it: the files attested for every head, the commands of the jobs
checker-fixtures and static-analysis, and the ordinary governance commands. A mismatch in an attested file means the change needs a cross-repository T3 change.
Exit status 0 means every step ran and passed. A skipped lookup exits non-zero unless --offline is given. It is run by the Implementer,
is not a pipeline job and is not a security control.

--ci-like runs the unit-test step in an environment that removes what the pipeline image lacks (user and system git configuration,
local-path fetching, inherited tokens and proxies, the real home directory). It does not claim parity with the pipeline.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import textwrap
from collections.abc import Callable
from pathlib import Path

POLICY_REPO_NAME = "aidf-ci-policy"
TEMPLATE_PATH = "aidf-enforced.template.yml"
POLICY_JOBS = ("checker-fixtures", "static-analysis")
ALLOWED_COMMANDS = ("python3", "ruff", "mypy")
RECORD_FILES = {"checker_sha256": "trusted/aidf_check.py", "policy_sha256": "trusted/policy.json"}
COVERED_GOVERNANCE = ("exemptions", "secrets", "test-delta")
POLICY_REF_PATTERN = r"main|[0-9a-f]{40}"
RECORD_NAMES = ("records", "selected_records")
SHELL_CHARACTERS = set(";|&<>$`\\\n")
LOCAL_MYPY_TARGETS = ("verification/pack_facts.py", "verification/preflight.py")
OFFLINE_COMMANDS = (
    "python3 -m unittest discover -s verification/tests",
    "python3 -m py_compile verification/aidf_check.py verification/qualification_check.py verification/phase8_qualification_check.py verification/agent_routing_check.py",
    "ruff check verification",
    "mypy --strict verification/aidf_check.py",
    "mypy --strict verification/qualification_check.py",
    "mypy --strict verification/phase8_qualification_check.py",
    "mypy --strict verification/agent_routing_check.py",
)
GUARANTEE_WORDS = re.compile(
    r"\b(?:fails?\b[^.;]{0,40}\bclosed|cannot|never|always|every(?: other)?|all|any other|none)\b", re.IGNORECASE
)
CITES = re.compile(
    r"\btest_\w+"
    r"|\b(?:python3?|ruff|mypy|unittest)\s+(?:-\S|\S*/\S*|[\w-]+\.(?:py|json|ya?ml|md|toml|txt)\b)"
    r"|\bgit\s+(?:diff|show|log|status|rev-parse|merge-base|ls-files|ls-remote|grep|checkout|worktree|fetch|cat-file|update-ref)\b"
)
SENTENCE_BREAK = re.compile(r"(?<=[.;!?])\s+")
SECRET_VARIABLE = re.compile(r"token|proxy|password|passwd|secret|credential|api_?key|^ssh_|^gitlab_|^ci_", re.IGNORECASE)
CI_LIKE_CANNOT = (
    "the pipeline image's tool versions, the programs the image lacks other than git-upload-pack, its network, its runner user and its file system"
)
CHANGED_FILES = "aidf-changed-files.txt"
CHANGE_PATCH = "aidf-change.patch"
GIT_TIMEOUT = 120
STEP_TIMEOUT = 900


def _run(
    argv: list[str], cwd: Path, timeout: int = STEP_TIMEOUT, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[bytes]:
    """Run a command without a shell; a missing program or a timeout is a failed result, not an exception."""
    try:
        return subprocess.run(argv, cwd=cwd, check=False, capture_output=True, timeout=timeout, env=env)
    except (OSError, subprocess.SubprocessError) as exc:
        return subprocess.CompletedProcess(argv, 127, b"", str(exc).encode("utf-8", "replace"))


def _git(root: Path, *args: str, timeout: int = GIT_TIMEOUT) -> subprocess.CompletedProcess[bytes]:
    return _run(["git", "-c", f"safe.directory={root.as_posix()}", *args], root, timeout)


def _text(data: bytes) -> str:
    return data.decode("utf-8", "replace").strip()


def job_commands(template: str, job: str) -> tuple[list[str], list[str]]:
    """The single-line script commands of a job: (runnable, skipped). Runnable means it starts with python3, ruff or mypy and has no shell syntax."""
    lines = template.splitlines()
    try:
        start = lines.index(f"{job}:")
    except ValueError:
        raise ValueError(f"job {job} not found in the policy template") from None
    block: list[str] = []
    for line in lines[start + 1 :]:
        if line and not line[0].isspace():
            break
        block.append(line)
    try:
        script = block.index("  script:")
    except ValueError:
        raise ValueError(f"job {job} has no script") from None
    runnable: list[str] = []
    skipped: list[str] = []
    for line in block[script + 1 :]:
        if line.strip() and not line.startswith("    "):
            break
        if not line.startswith("    - "):
            continue
        command = line[6:].strip()
        if len(command) >= 2 and command[0] == command[-1] and command[0] in "'\"":
            command = command[1:-1]
        first = command.split(" ", 1)[0]
        if first in ALLOWED_COMMANDS and not SHELL_CHARACTERS & set(command) and "pip install" not in command:
            runnable.append(command)
        else:
            skipped.append(command)
    return runnable, skipped


def _policy_script(template: str) -> ast.Module:
    """The embedded Python of the policy job that defines `records`, parsed."""
    for block in re.findall(r"<<'(\w+)'\n(.*?)^\s*\1$", template, re.DOTALL | re.MULTILINE):
        source = textwrap.dedent(block[1])
        if re.search(r"^records = \(", source, re.MULTILINE):
            try:
                return ast.parse(source)
            except SyntaxError as error:
                raise ValueError(f"the policy job's Python cannot be parsed ({error.msg}); update verification/preflight.py") from None
    raise ValueError("records tuple not found in the policy template")


NON_BINDING_FIELDS = {
    ("Attribute", "attr"),
    ("keyword", "arg"),
    ("ImportFrom", "module"),
    ("Constant", "value"),
    ("Constant", "kind"),
}


def _bound_names(node: ast.AST) -> list[str]:
    """The names this one node may bind, delete or rebind.

    Closed by default: every string-valued field of every node counts (so a binding form added to Python later is counted), except
    the few fields that name no variable (an attribute, a keyword argument, a module path, a constant) and a name that is only read.
    """
    if isinstance(node, ast.Name):
        return [] if isinstance(node.ctx, ast.Load) else [node.id]
    if isinstance(node, ast.alias):
        if node.name == "*":
            return list(RECORD_NAMES)
        return [node.asname or node.name.split(".")[0]]
    names: list[str] = []
    for field, value in ast.iter_fields(node):
        if (type(node).__name__, field) in NON_BINDING_FIELDS or field == "type_comment":
            continue
        if isinstance(value, str):
            names.append(value)
        elif isinstance(value, list):
            names.extend(item for item in value if isinstance(item, str))
    return names


def _bindings(tree: ast.AST, name: str) -> int:
    """How many times the code binds, deletes or rebinds `name`."""
    return sum(_bound_names(node).count(name) for node in ast.walk(tree))


def attested_records(template: str) -> list[tuple[str, str]]:
    """(repository path, record variable) pairs of the `records` tuple that the policy job checks for every head.

    The job's Python is parsed, not matched as text: the two names must be bound exactly once (by any statement form, a star import counting
    as a binding of both) and a single top-level loop over `records + selected_records` must run without break or continue. Not examined: the body
    of that loop, whether the statements before it can end the script, and dynamic access to the namespace (globals(), exec, setattr).

    The check establishes the shape of the script only; it does not establish what the script computes. Not examined either: the value of
    `selected_records` and of the names it is built from (an object whose __radd__ returns an empty tuple empties the loop), what the function the loop
    calls and the modules it uses do at run time (a patched hashlib), and how the process exits (an atexit hook).
    """
    tree = _policy_script(template)
    for name in RECORD_NAMES:
        if _bindings(tree, name) != 1:
            raise ValueError(f"the policy job binds `{name}` other than exactly once (update verification/preflight.py)")
    entries: list[tuple[str, str]] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "records" for t in node.targets):
            if not isinstance(node.value, ast.Tuple) or not node.value.elts:
                raise ValueError("records is not a non-empty tuple in the policy template")
            for item in node.value.elts:
                if (
                    isinstance(item, ast.Tuple)
                    and len(item.elts) == 2
                    and isinstance(item.elts[0], ast.Constant)
                    and isinstance(item.elts[0].value, str)
                    and isinstance(item.elts[1], ast.Name)
                ):
                    entries.append((item.elts[0].value, item.elts[1].id))
                else:
                    raise ValueError(f"records holds an entry the preflight cannot read (update verification/preflight.py): {ast.unparse(item)[:80]}")
    if not entries:
        raise ValueError("records must be assigned at the top level of the policy job's Python (update verification/preflight.py)")
    loops = [n for n in ast.walk(tree) if isinstance(n, ast.For) and ast.unparse(n.iter) == "records + selected_records"]
    if len(loops) != 1 or loops[0] not in tree.body:
        raise ValueError("the policy job no longer checks `records + selected_records` in one top-level loop (update verification/preflight.py)")
    if any(isinstance(n, (ast.Break, ast.Continue)) for n in ast.walk(loops[0])):
        raise ValueError("the loop over `records + selected_records` can skip an entry (update verification/preflight.py)")
    return entries


def governance_commands(template: str) -> list[str]:
    """The names of the aidf_check.py commands the policy job runs for an ordinary head (the last `for command, extra in (` block)."""
    index = template.rfind("for command, extra in (\n")
    if index < 0:
        raise ValueError("governance command block not found in the policy template")
    end = template.index("):", index)
    names = re.findall(r'\(\s*"([\w-]+)"\s*,', template[index:end])
    if not names:
        raise ValueError("governance command block is empty in the policy template")
    return names


def canonical_sha256(data: bytes) -> str:
    """SHA-256 after the line-ending normalisation build_policy.py applies to trusted text."""
    text = data.replace(b"\r\n", b"\n")
    if b"\r" in text:
        raise ValueError("lone carriage return")
    return hashlib.sha256(text).hexdigest()


def check_attestation(
    records: list[tuple[str, str]],
    trusted: Callable[[str], bytes | None],
    committed: Callable[[str], bytes | None],
) -> tuple[list[str], list[str]]:
    """(mismatches, errors): attested files whose committed bytes differ from the attested bytes, and conditions the lookup cannot evaluate.

    Only a mismatch can be excused by --allow-protected; an error always fails.
    """
    mismatches: list[str] = []
    errors: list[str] = []
    for path, variable in records:
        source = RECORD_FILES.get(variable)
        if source is None:
            errors.append(f"unknown attested record variable {variable} for {path}: update verification/preflight.py")
            continue
        expected_bytes = trusted(source)
        actual_bytes = committed(path)
        if expected_bytes is None:
            errors.append(f"{source} missing in the policy repository")
            continue
        if actual_bytes is None:
            errors.append(f"{path} is missing at the head")
            continue
        try:
            expected = canonical_sha256(expected_bytes)
        except ValueError:
            errors.append(f"{source} in the policy repository holds a lone carriage return")
            continue
        if hashlib.sha256(actual_bytes).hexdigest() != expected:
            mismatches.append(f"attested record hash mismatch: {path} (changing it needs a cross-repository T3 change to the attestation)")
    return mismatches, errors


def default_policy_repo(origin_url: str) -> str | None:
    """The sibling policy repository of the origin remote, or None when the origin does not end in the project name."""
    match = re.search(r"^(.*[/:])[^/:]+?(?:\.git)?$", origin_url.strip())
    if not match or not match.group(1):
        return None
    return f"{match.group(1)}{POLICY_REPO_NAME}.git"


def fetch_policy(url: str, ref: str, dest: Path) -> tuple[str | None, Path, str]:
    """Resolve one ref of the policy repository. Returns (commit SHA or None, directory to read it from, message).

    A local directory is read in place (no transport, so it works where git-upload-pack is not installed); anything else is fetched into dest.
    """
    local = Path(url)
    if local.is_dir():
        found = _git(local, "rev-parse", "--verify", f"{ref}^{{commit}}")
        if found.returncode != 0:
            return None, local, _text(found.stderr)[-300:]
        return _text(found.stdout), local, ""
    for args in (["init", "-q"], ["fetch", "-q", "--depth", "1", url, ref]):
        result = _git(dest, *args, timeout=GIT_TIMEOUT)
        if result.returncode != 0:
            return None, dest, _text(result.stderr)[-300:]
    sha = _git(dest, "rev-parse", "FETCH_HEAD")
    if sha.returncode != 0:
        return None, dest, _text(sha.stderr)[-300:]
    return _text(sha.stdout), dest, ""


def _blob(root: Path, revision: str, path: str) -> bytes | None:
    result = _git(root, "show", f"{revision}:{path}")
    return result.stdout if result.returncode == 0 else None


class Report:
    def __init__(self) -> None:
        self.failed = False

    def ok(self, name: str) -> None:
        print(f"ok    {name}")

    def fail(self, name: str, detail: str = "") -> None:
        self.failed = True
        print(f"FAIL  {name}")
        for line in detail.splitlines()[-8:]:
            print(f"        {line}")

    def note(self, text: str) -> None:
        print(f"note  {text}")


def repo_relative(root: Path, value: str) -> str | None:
    """The POSIX path of value relative to root, or None when it points outside the repository."""
    path = Path(value)
    resolved = (path if path.is_absolute() else root / path).resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return None


def pack_wording(pack: object) -> tuple[int, list[str]]:
    """(sentences examined, flagged sentences): a sentence with a guarantee word and no cited test or command. Advisory only."""
    sentences: list[str] = []

    def collect(value: object) -> None:
        if isinstance(value, str):
            sentences.extend(part.strip() for part in SENTENCE_BREAK.split(value) if part.strip())
        elif isinstance(value, dict):
            for item in value.values():
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(pack)
    flagged = [text for text in sentences if GUARANTEE_WORDS.search(text) and not CITES.search(text)]
    return len(sentences), flagged


def report_pack_wording(report: Report, pack_path: Path) -> None:
    """Print the pack wording notes and a count. This step only prints: it does not set the failed flag."""
    try:
        examined, flagged = pack_wording(json.loads(pack_path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        report.note(f"pack wording: the pack could not be read ({str(exc)[:80]})")
        return
    for text in flagged:
        report.note(f"pack wording: guarantee word without a cited test or command: {text[:140]}")
    report.ok(f"pack wording: examined {examined} sentences, flagged {len(flagged)} (advisory)")


def ci_like_environment(home: str, empty_config: str) -> tuple[dict[str, str], list[str]]:
    """(environment, names of removed variables): the current environment minus what the pipeline image lacks."""
    env = {k: v for k, v in os.environ.items() if not SECRET_VARIABLE.search(k) and not k.upper().startswith("GIT_")}
    removed = sorted(set(os.environ) - set(env))
    env.update(
        {
            "HOME": home,
            "USERPROFILE": home,
            "XDG_CONFIG_HOME": home,
            "GIT_CONFIG_GLOBAL": empty_config,
            "GIT_CONFIG_SYSTEM": empty_config,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "protocol.file.allow",
            "GIT_CONFIG_VALUE_0": "never",
        }
    )
    return env, removed


def run_command(report: Report, root: Path, command: str, label: str | None = None, env: dict[str, str] | None = None) -> None:
    argv = shlex.split(command)
    if argv and argv[0] == "python3":
        argv[0] = sys.executable
    elif argv and argv[0] in ("ruff", "mypy"):
        argv[:1] = [sys.executable, "-m", argv[0]]
    result = _run(argv, root, env=env)
    name = label or command
    if result.returncode == 0:
        report.ok(name)
    else:
        report.fail(name, _text(result.stdout + result.stderr))


def run_checks(
    report: Report,
    work: Path,
    base: str,
    head: str,
    commands: list[str],
    governance: list[str],
    contract: str,
    evidence: str,
    ci_env: dict[str, str] | None = None,
) -> None:
    """Run every step in a clean checkout of the head, so that untracked or ignored files cannot make a step pass."""
    for command in commands:
        if ci_env is not None and "unittest discover" in command:
            run_command(report, work, command, f"ci-like: {command}", env=ci_env)
        else:
            run_command(report, work, command)
    for target in LOCAL_MYPY_TARGETS:
        if (work / target).is_file():
            run_command(report, work, f"mypy --strict {target}")

    changed = _git(work, "-c", "core.quotePath=false", "diff", "--name-only", "-z", "--no-renames", "--no-ext-diff", "--no-textconv", base, head, "--")
    patch = _git(work, "-c", "core.quotePath=false", "diff", "--unified=0", "--no-renames", "--no-ext-diff", "--no-textconv", base, head, "--")
    if changed.returncode != 0 or patch.returncode != 0:
        report.fail("governance: diff", _text(changed.stderr + patch.stderr))
    else:
        files = [(work / CHANGED_FILES, changed.stdout), (work / CHANGE_PATCH, patch.stdout)]
        try:
            for path, data in files:
                path.write_bytes(data)
            diff_args = f"--changed-files {CHANGED_FILES} --changed-files-nul --diff-file {CHANGE_PATCH}"
            specific = {
                "exemptions": "--policy verification/policy.json",
                "secrets": diff_args,
                "test-delta": diff_args,
            }
            for name in governance:
                run_command(report, work, f"python3 verification/aidf_check.py {name} {specific[name]}", f"governance: {name}")
        finally:
            for path, _ in files:
                path.unlink(missing_ok=True)

    run_command(report, work, f"python3 verification/aidf_check.py contract --contract {contract}", "contract")
    run_command(report, work, f"python3 verification/aidf_check.py evidence --contract {contract} --evidence {evidence}", "evidence")
    run_command(report, work, f"python3 verification/aidf_check.py scope --contract {contract} --base {base} --head {head}", "scope")
    run_command(
        report,
        work,
        f"python3 verification/aidf_check.py tripwires --contract {contract} --policy verification/policy.json --base {base} --head {head}",
        "tripwires",
    )
    run_command(report, work, "python3 verification/export_public_tree.py --scan-only", "public-tree scan")
    if (work / "verification" / "pack_facts.py").is_file():
        run_command(report, work, f"python3 verification/pack_facts.py --evidence {evidence}", "pack facts of own pack")
    report_pack_wording(report, work / evidence)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--root", default=".")
    parser.add_argument("--contract", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--base-ref", default="origin/main")
    parser.add_argument("--policy-repo")
    parser.add_argument("--policy-ref", default="main", help="main or a full commit SHA")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--allow-protected", metavar="REFERENCE")
    parser.add_argument("--ci-like", action="store_true", help="run the unit-test step without user git configuration, local-path fetching or tokens")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    report = Report()
    contract = repo_relative(root, args.contract)
    evidence = repo_relative(root, args.evidence)
    if contract is None or evidence is None:
        print("FAIL  --contract and --evidence must be paths inside the repository (they are read from the clean checkout of the head)")
        return 2
    if not re.fullmatch(POLICY_REF_PATTERN, args.policy_ref):
        print("FAIL  --policy-ref must be main or a full 40-character commit SHA")
        return 2

    head_result = _git(root, "rev-parse", "HEAD")
    base_result = _git(root, "merge-base", args.base_ref, "HEAD")
    if head_result.returncode != 0 or base_result.returncode != 0:
        print(f"FAIL  head or merge base ({args.base_ref}) not found: {_text(head_result.stderr + base_result.stderr)}")
        return 2
    head, merge_base = _text(head_result.stdout), _text(base_result.stdout)
    tip = _git(root, "rev-parse", "--verify", f"{args.base_ref}^{{commit}}")
    base = _text(tip.stdout) if tip.returncode == 0 else merge_base
    dirty = _git(root, "status", "--porcelain", "--untracked-files=no")
    if _text(dirty.stdout):
        print("FAIL  uncommitted tracked changes: commit first, the checks read the committed head")
        return 2

    if _git(root, "merge-base", "--is-ancestor", base, head).returncode != 0:
        report.fail("base", f"{args.base_ref} is not an ancestor of the head: the pipeline requires it; merge or rebase onto {args.base_ref}")
        base = merge_base

    template: str | None = None
    if args.offline:
        report.note("offline: the built-in command list may not match the pipeline and the attested files were not checked")
    else:
        url = args.policy_repo
        if url is None:
            origin = _git(root, "remote", "get-url", "origin")
            url = default_policy_repo(_text(origin.stdout)) if origin.returncode == 0 else None
        with tempfile.TemporaryDirectory() as scratch:
            dest = Path(scratch)
            fetched: str | None = None
            policy_dir = dest
            message = "no policy repository address (pass --policy-repo)"
            if url is not None:
                fetched, policy_dir, message = fetch_policy(url, args.policy_ref, dest)
            if fetched is None:
                report.fail("policy lookup", f"SKIPPED: policy repository unreachable ({message})")
            else:
                report.note(
                    f"policy repository {POLICY_REPO_NAME} at {fetched}; the commit set in the project's CI/CD setting is the authority and may differ"
                )
                raw = _blob(policy_dir, fetched, TEMPLATE_PATH)
                if raw is None:
                    report.fail("policy lookup", f"SKIPPED: {TEMPLATE_PATH} not found in the policy repository")
                else:
                    template = raw.decode("utf-8", "replace")
                    try:
                        mismatches, errors = check_attestation(
                            attested_records(template),
                            lambda p: _blob(policy_dir, fetched, p),
                            lambda p: _blob(root, head, p),
                        )
                    except ValueError as exc:
                        mismatches, errors = [], [str(exc)]
                    for item in errors:
                        report.fail("attested files", item)
                    if mismatches and args.allow_protected:
                        report.note(f"attested files changed, allowed by {args.allow_protected}: " + "; ".join(mismatches))
                    elif mismatches:
                        for item in mismatches:
                            report.fail("attested files", item)
                    elif not errors:
                        report.ok("attested files match the policy repository")
                    report.note("records that apply only to named historical candidate commits (phase 7, phase 8, layer 3) are not checked")

    commands: list[str] = list(OFFLINE_COMMANDS)
    governance = list(COVERED_GOVERNANCE)
    if template is not None:
        try:
            runnable: list[str] = []
            for job in POLICY_JOBS:
                job_runnable, job_skipped = job_commands(template, job)
                runnable.extend(job_runnable)
                for item in job_skipped:
                    report.note(f"skipped (not run by the preflight): {item[:100]}")
            commands = runnable
            names = governance_commands(template)
            extra = [n for n in names if n not in COVERED_GOVERNANCE]
            if extra:
                report.note("governance commands in the policy job that the preflight does not run: " + ", ".join(extra))
            governance = [n for n in names if n in COVERED_GOVERNANCE]
        except ValueError as exc:
            report.fail("policy template", str(exc))
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as checkout_dir:
        ci_env: dict[str, str] | None = None
        if args.ci_like:
            home = Path(checkout_dir) / "home"
            home.mkdir()
            empty = home / "empty-gitconfig"
            empty.write_text("", encoding="utf-8")
            ci_env, removed = ci_like_environment(str(home), str(empty))
            report.note(
                f"ci-like environment: HOME={home}, GIT_CONFIG_GLOBAL and GIT_CONFIG_SYSTEM=empty file, GIT_CONFIG_NOSYSTEM=1, "
                f"protocol.file.allow=never, {len(removed)} variables removed ({', '.join(removed) or 'none'})"
            )
            report.note(f"ci-like cannot reproduce: {CI_LIKE_CANNOT}; it is not parity with the pipeline")
        work = Path(checkout_dir) / "head"
        added = _git(root, "worktree", "add", "--detach", str(work), head)
        if added.returncode != 0:
            report.fail("clean checkout of the head", _text(added.stderr))
        else:
            try:
                run_checks(report, work, base, head, commands, governance, contract, evidence, ci_env)
            finally:
                _git(root, "worktree", "remove", "--force", str(work))
                _git(root, "worktree", "prune")

    status = "FAILED" if report.failed else "ALL OK"
    print(f"head {head} base {base}; status: {status}")
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
