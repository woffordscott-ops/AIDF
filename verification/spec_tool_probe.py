"""Stage 1 of the spec-tool bake-off: can a headless agent drive Spec Kit or OpenSpec, and what does a run write?

For one tool the probe, in a scratch directory outside the repository: installs the pinned version into a scratch prefix, initialises a throwaway
project, starts `cursor-agent -p` once on a throwaway prompt that stops before the tool's apply step, and takes a file snapshot before and after each
step (verification/workspace_snapshot.py). It writes one redacted JSON record. No suite case is used and no scored run is made.

    python verification/spec_tool_probe.py TOOL --out-dir DIR [--dry-run] [--scratch DIR] [--model M] [--agent-executable PATH] [--keep]

TOOL is `speckit` or `openspec`. `--dry-run` prints the plan and runs nothing.
Contract: spec/AIDF-SPEC-TOOL-BAKEOFF-STAGES-0-1-TASK-CONTRACT.md (criteria 6 to 8). It is evidence tooling, not a gate.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def _load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


snapshots = _load("workspace_snapshot")
run_review = _load("run_review")

DEFAULT_MODEL = "gpt-5.6-sol-high"
UV_VERSION = "0.13.7"  # used only when uv is not installed: put into the scratch directory with pip, never globally
STEP_TIMEOUT = 900
AGENT_TIMEOUT = 1800
TAIL = 4000
TOOLS: dict[str, dict[str, Any]] = {
    "speckit": {
        "label": "Spec Kit",
        "tag": "v1.3.0",
        "commit": "34a0d388eac671d656eb05b125ad3ed6056168ed",
        "installer": "uv",
        "install": ["tool", "install", "specify-cli", "--from", "git+https://github.com/github/spec-kit.git@v1.3.0"],
        "binary": "specify",
        "init": ["init", "--here", "--force", "--non-interactive", "--integration", "cursor-agent"],  # found by the first probe: plain init asks a question and exits 0 when cancelled
        "flow": "specify, plan and tasks (the skills /speckit-specify, /speckit-plan, /speckit-tasks)",
        "environment": {"DO_NOT_TRACK": "1"},
        "artifact_roots": ["specs/"],
    },
    "openspec": {
        "label": "OpenSpec",
        "tag": "v1.16.0",
        "commit": "27c0515724decc633818c735ee596481eec78a8b",
        "installer": "npm",
        "install": ["install", "--no-audit", "--no-fund", "@fission-ai/openspec@1.16.0"],
        "binary": "openspec",
        "init": ["init", "--tools", "cursor"],
        "flow": "propose (the command /opsx:propose)",
        "environment": {"OPENSPEC_TELEMETRY": "0", "DO_NOT_TRACK": "1"},
        "artifact_roots": ["openspec/changes/"],
    },
    # A0 of the bake-off: no tool, the framework documents are copied into the workspace (as the measurement harness does for Arm A)
    "aidf": {
        "label": "AIDF",
        "tag": None,
        "commit": None,
        "installer": None,
        "flow": "classify the change as the lifecycle requires and write its Task Contract to task-contract.md",
        "environment": {},
        "artifact_roots": ["task-contract.md"],
    },
}
AIDF_DOCS = ["KERNEL.md", "core/01-lifecycle.md", "core/04-verification.md", "core/05-review.md", "templates/task-contract.md", "templates/evidence-pack.md"]
# What the stop summary calls a code file: these suffixes outside the tools' own scaffold directories. Another suffix is not reported.
CODE_SUFFIXES = (".py", ".js", ".jsx", ".mjs", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".rb", ".php", ".sh", ".ps1", ".bat", ".cmd", ".cs", ".c", ".h", ".cpp", ".hpp", ".swift", ".sql")
SCAFFOLD_PREFIXES = (".specify/", ".cursor/", "openspec/", "aidf/")
DEFAULT_CHANGE = "add a function `slugify(title)` to slug.py that lowercases the title and replaces runs of spaces with single hyphens."
SAMPLE_FILES = {
    "README.md": "# sample\n\nA throwaway project for a probe.\n",
    "slug.py": '"""Text helpers."""\n\n\ndef shout(text: str) -> str:\n    return text.upper()\n',
}
HEAD = """This is a throwaway project used to see how {label} behaves under a headless agent. It is not a real task.

Change to propose: {change}

"""
TOOL_PROMPT = """Use {label} to produce its planning artifacts for this change: {flow}. The tool is already installed and initialised in this directory; use the project's own command definitions, or its command line.

STOP before the tool's apply or implement step. Do not write or change any code file. When the artifacts exist, reply with: the exact commands or skills you used, the files you created, and anything that blocked you. Say what you did not do. Do not claim a result you did not see.
"""
AIDF_PROMPT = """Work under the AI Development Framework (AIDF); its documents are in aidf/ in this directory (read KERNEL.md, core/01-lifecycle.md and templates/task-contract.md). {flow}. Fill the parts of the template that the class requires.

STOP before implementing. Do not write or change any code file. When the contract exists, reply with: the class you chose and why in one sentence, the files you created, and anything that blocked you. Say what you did not do. Do not claim a result you did not see.
"""


def build_prompt(tool: str, change: str = DEFAULT_CHANGE, extra: str = "") -> str:
    """The prompt of one arm. `extra` is a further instruction appended at the end (used to try a different shape of the artifact)."""
    spec = TOOLS[tool]
    body = AIDF_PROMPT if tool == "aidf" else TOOL_PROMPT
    text = (HEAD + body).format(label=spec["label"], flow=spec["flow"], change=change)
    return text + ("\n" + extra.strip() + "\n" if extra.strip() else "")


def child_environment(source: dict[str, str], tool: str, scratch: Path) -> dict[str, str]:
    """An allowlist environment (the one run_review.py gives a reviewer), with the tool's caches and prefixes in the scratch directory and its telemetry off."""
    base, _ = run_review.reviewer_environment(source, [], scratch / "caches")
    environment: dict[str, str] = dict(base)
    bin_dirs = [str(scratch / "uv-bin"), str(scratch / "npm" / "node_modules" / ".bin"), str(scratch / "npm")]
    path_key = next((key for key in environment if key.upper() == "PATH"), "PATH")
    environment[path_key] = os.pathsep.join(bin_dirs + [environment.get(path_key, "")])
    environment.update({
        "UV_TOOL_DIR": str(scratch / "uv-tools"), "UV_TOOL_BIN_DIR": str(scratch / "uv-bin"), "UV_CACHE_DIR": str(scratch / "uv-cache"),
        "NPM_CONFIG_PREFIX": str(scratch / "npm"), "NPM_CONFIG_CACHE": str(scratch / "npm-cache"), "NPM_CONFIG_UPDATE_NOTIFIER": "false",
    })
    environment.update(TOOLS[tool]["environment"])
    if TOOLS[tool]["installer"] == "uv":
        environment["PYTHONPATH"] = str(scratch / "uv-boot")  # only used when uv is bootstrapped into the scratch directory
    return environment


def agent_argv(executable: str, model: str, sandbox: bool) -> list[str]:
    """The agent command. The prompt goes in on standard input (as the measurement harness does), so a .cmd launcher never has to quote it."""
    argv = [executable, "-p", "--output-format", "text", "--trust", "--force", "--model", model]
    if sandbox:
        argv += ["--sandbox", "enabled"]
    return argv


def plan(tool: str, scratch: Path, model: str, agent_executable: str, have_uv: bool = True, change: str = DEFAULT_CHANGE,
         extra: str = "") -> list[dict[str, Any]]:
    """The steps of one probe, as data: nothing is run by building it. Without uv on the machine, a pinned uv is first put into the scratch directory."""
    spec = TOOLS[tool]
    workspace = scratch / "workspace"
    prompt = build_prompt(tool, change, extra)
    sandbox = sys.platform != "win32"
    steps: list[dict[str, Any]] = []
    agent_step = {"name": "agent", "argv": agent_argv(agent_executable, model, sandbox), "cwd": str(workspace), "timeout": AGENT_TIMEOUT, "input": prompt}
    if spec["installer"] is None:
        return [agent_step]
    installer = [spec["installer"]]
    if spec["installer"] == "uv" and not have_uv:
        steps.append({"name": "bootstrap-uv", "argv": [sys.executable, "-m", "pip", "install", "--target", str(scratch / "uv-boot"), f"uv=={UV_VERSION}"],
                      "cwd": str(scratch), "timeout": STEP_TIMEOUT})
        installer = [sys.executable, "-m", "uv"]
    install = [*spec["install"]]
    if spec["installer"] == "npm":
        install[1:1] = ["--prefix", str(scratch / "npm")]  # the binary lands in <prefix>/node_modules/.bin, which child_environment puts on PATH
    steps += [
        {"name": "install", "argv": [*installer, *install], "cwd": str(scratch), "timeout": STEP_TIMEOUT},
        {"name": "version", "argv": [spec["binary"], "--version"], "cwd": str(workspace), "timeout": 120},
        {"name": "init", "argv": [spec["binary"], *spec["init"]], "cwd": str(workspace), "timeout": STEP_TIMEOUT},
        agent_step,
    ]
    return steps


def make_workspace(scratch: Path, tool: str = "", sample: Path | None = None) -> Path:
    """The throwaway project: the built-in two files, or a copy of `sample`. For the aidf mode the framework documents are copied into aidf/."""
    workspace = scratch / "workspace"
    workspace.mkdir(parents=True)
    if sample is None:
        for name, text in SAMPLE_FILES.items():
            (workspace / name).write_text(text, encoding="utf-8", newline="\n")
    else:
        shutil.copytree(sample, workspace, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", ".git"))
    if tool == "aidf":
        for name in AIDF_DOCS:
            target = workspace / "aidf" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(HERE.parent / name, target)
    return workspace


def _under_root(rel: str, roots: tuple[str, ...]) -> bool:
    """A root that ends in a slash is a directory (a prefix match); any other root is one file (an exact match)."""
    return any(rel.startswith(root) if root.endswith("/") else rel == root for root in roots)


def collect_artifacts(tool: str, workspace: Path, added: list[str], out: Path) -> list[str]:
    """Copy the planning artifacts the agent step added (the tool's artifact roots only, not the scaffold) to out/<tool>/, redacting local paths. A link (symbolic or junction) or a directory is skipped."""
    roots = tuple(TOOLS[tool]["artifact_roots"])
    copied = []
    for rel in sorted(added):
        if not _under_root(rel, roots):
            continue
        source = workspace / rel
        if snapshots._is_link(source) or not source.is_file():
            continue  # a link (symbolic or junction) is recorded by the snapshot, never read; a directory has no text
        target = out / tool / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        text = source.read_text(encoding="utf-8", errors="replace")
        target.write_text(snapshots.redact(text, workspace.parent), encoding="utf-8", newline="\n")
        copied.append(rel)
    return copied


def run_step(argv: list[str], cwd: Path, env: dict[str, str], timeout: int, input_text: str | None = None) -> dict[str, Any]:
    """Run one command and return what happened. A missing program or a timeout is an answer, not a crash."""
    start = time.time()
    exe = shutil.which(argv[0], path=env.get("PATH") or env.get("Path")) or argv[0]
    try:
        done = subprocess.run([exe, *argv[1:]], cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=timeout, check=False, input=input_text)
        result: dict[str, Any] = {"exit": done.returncode, "stdout": done.stdout, "stderr": done.stderr}
    except FileNotFoundError:
        result = {"exit": None, "stdout": "", "stderr": "", "error": f"program not found: {argv[0]}"}
    except subprocess.TimeoutExpired:
        result = {"exit": None, "stdout": "", "stderr": "", "error": f"timed out after {timeout} s"}
    result["seconds"] = round(time.time() - start, 1)
    return result


def _tail(text: str) -> str:
    return text if len(text) <= TAIL else "[...]" + text[-TAIL:]


def run_probe(tool: str, scratch: Path, model: str, agent_executable: str, source_env: dict[str, str], runner: Any = run_step,
              change: str = DEFAULT_CHANGE, sample: Path | None = None, collect: Path | None = None, extra: str = "") -> dict[str, Any]:
    """Run the plan and return the record (not yet redacted). With `collect`, the planning artifacts are copied there before the scratch directory goes."""
    workspace = make_workspace(scratch, tool, sample)
    env = child_environment(source_env, tool, scratch)
    record: dict[str, Any] = {
        "tool": tool, "pinned": {"tag": TOOLS[tool]["tag"], "commit": TOOLS[tool]["commit"]}, "model": model, "platform": sys.platform,
        "sandbox": "enabled" if sys.platform != "win32" else "none: the agent CLI supports its sandbox only on macOS and Linux",
        "telemetry_settings": TOOLS[tool]["environment"], "environment_names": sorted(env), "steps": [],
    }
    before = snapshots.snapshot(workspace)
    for step in plan(tool, scratch, model, agent_executable, shutil.which("uv") is not None, change, extra):
        result = runner(step["argv"], Path(step["cwd"]), env, step["timeout"], step.get("input"))
        after = snapshots.snapshot(workspace)
        entry = {
            "name": step["name"], "argv": step["argv"], "prompt_on_stdin": "input" in step,
            "exit": result["exit"], "seconds": result["seconds"], "error": result.get("error"),
            "stdout_tail": _tail(result["stdout"]), "stderr_tail": _tail(result["stderr"]),
            "writes": snapshots.compare(before, after),
        }
        record["steps"].append(entry)
        before = after
        if step["name"] in ("bootstrap-uv", "install") and result["exit"] != 0:
            record["stopped"] = "the install did not succeed; later steps were not run"
            break
        if step["name"] == "init" and result["exit"] != 0:
            record["stopped"] = "init did not succeed; the agent was not started"
            break
    agent_writes = next((s["writes"] for s in record["steps"] if s["name"] == "agent"), None)
    if collect is not None and agent_writes is not None:
        record["collected"] = collect_artifacts(tool, workspace, agent_writes["added"], collect)
    record["answers"] = answers(record)
    return record


def answers(record: dict[str, Any]) -> dict[str, str]:
    """The six questions of criterion 7, each answered from the steps or marked not answered."""
    steps = {s["name"]: s for s in record["steps"]}

    def ok(name: str) -> bool:
        return name in steps and steps[name]["exit"] == 0

    out: dict[str, str] = {}
    if TOOLS[record["tool"]]["installer"] is None:
        out["a_install"] = out["b_init_writes"] = "not applicable: no tool in this arm"
    else:
        failed = (steps.get("bootstrap-uv") if "bootstrap-uv" in steps and not ok("bootstrap-uv") else steps.get("install")) or {}
        out["a_install"] = ("yes: installed into a scratch prefix" + (" (uv itself was put there first)" if "bootstrap-uv" in steps else "")) if ok("install") else "no: " + (failed.get("error") or "the install exited non-zero or was not run")
        init = steps.get("init")
        if init is None:
            out["b_init_writes"] = "not answered: init was not run"
        else:
            w = init["writes"]
            out["b_init_writes"] = f"exit {init['exit']}; added {len(w['added'])} files, changed {len(w['changed'])}: " + ", ".join(w["added"][:40])
    agent = steps.get("agent")
    if agent is None:
        out["c_headless_flow"] = out["d_writes_and_stop"] = "not answered: the agent was not started"
    else:
        out["c_headless_flow"] = f"agent exit {agent['exit']}" + (f" ({agent['error']})" if agent["error"] else "") + "; see the reply tail and the files added"
        w = agent["writes"]
        code = [p for p in w["added"] + w["changed"] if p.endswith(CODE_SUFFIXES) and not p.startswith(SCAFFOLD_PREFIXES)]
        out["d_writes_and_stop"] = f"added {len(w['added'])}, changed {len(w['changed'])}, removed {len(w['removed'])}; code files written: {code or 'none'}"
    out["e_telemetry"] = "the setting was applied to the child's environment (" + ", ".join(f"{k}={v}" for k, v in record["telemetry_settings"].items()) + "); its effect was not observed"
    out["f_time_and_calls"] = ", ".join(f"{s['name']} {s['seconds']} s" for s in record["steps"]) + "; agent calls: " + ("1" if agent else "0")
    return out


def write_probe_record(record: dict[str, Any], out_dir: Path, scratch: Path, repo: Path) -> Path:
    text = snapshots.redact(json.dumps(record, indent=2, ensure_ascii=False) + "\n", scratch)
    text = re.sub(re.escape(str(repo)), "<repo>", text)
    out_dir = out_dir.resolve()
    if out_dir == scratch.resolve() or scratch.resolve() in out_dir.parents:
        raise SystemExit("--out-dir may not be inside the scratch directory")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{record['tool']}-probe.json"
    if target.is_file() and target.stat().st_nlink > 1:
        raise SystemExit("the record path is a file with more than one link; it may be a hard link to another file")
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tool", choices=sorted(TOOLS))
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--scratch", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--agent-executable", default=shutil.which("cursor-agent") or "cursor-agent")
    parser.add_argument("--change-file", type=Path, help="a text file holding the change to propose (default: the slugify change)")
    parser.add_argument("--sample", type=Path, help="a directory copied in as the throwaway project (default: two small files)")
    parser.add_argument("--collect", type=Path, help="copy the planning artifacts the agent adds to this directory (redacted)")
    parser.add_argument("--prompt-extra", type=Path, help="a text file appended to the prompt (for example a different shape for the artifact)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep", action="store_true", help="keep the scratch directory after the record is written")
    args = parser.parse_args(argv)
    repo = HERE.parent
    change = args.change_file.read_text(encoding="utf-8").strip() if args.change_file else DEFAULT_CHANGE
    extra = args.prompt_extra.read_text(encoding="utf-8") if args.prompt_extra else ""
    scratch = (args.scratch or (Path(tempfile.gettempdir()) / "aidf-probe-dry" if args.dry_run else Path(tempfile.mkdtemp(prefix="aidf-probe-")))).resolve()
    if scratch == repo or repo in scratch.parents:
        print("probe: the scratch directory may not be inside the repository", file=sys.stderr)
        return 1
    if args.dry_run:
        for step in plan(args.tool, scratch, args.model, args.agent_executable, shutil.which("uv") is not None, change, extra):
            print(step["name"], step["argv"], "in", snapshots.redact(step["cwd"], scratch), "(prompt on stdin)" if "input" in step else "")
        print("environment names:", ", ".join(sorted(child_environment(dict(os.environ), args.tool, scratch))))
        return 0
    try:
        record = run_probe(args.tool, scratch, args.model, args.agent_executable, dict(os.environ), change=change, sample=args.sample, collect=args.collect, extra=extra)
        target = write_probe_record(record, args.out_dir, scratch, repo)
    finally:
        if not args.keep:
            shutil.rmtree(scratch, ignore_errors=True)
    print("record:", target.name)
    for key, value in record["answers"].items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
