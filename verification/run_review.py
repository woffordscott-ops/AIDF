"""Run one reviewer round: pin the head, build a clean clone, run the preflight, start the reviewer CLI with a reduced environment, keep its answer byte for byte and commit it alone.

The human starts this tool; it does not decide anything about the review and is not a security boundary (spec/AIDF-REVIEW-RUN-REVIEW-TASK-CONTRACT.md).
"""

from __future__ import annotations

import argparse
import atexit
import base64
import contextlib
import datetime
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
from collections.abc import Iterator
from pathlib import Path
from typing import Any

OUTCOMES = ("Outcome: PASS", "Outcome: PASS_WITH_ADVISORIES", "Outcome: BLOCKED")
ALLOWED_ENVIRONMENT = (
    "PATH", "PATHEXT", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "TEMP", "TMP", "HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH",
    "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "USERNAME", "LANG", "LC_ALL", "TERM",
)
FIXED_ENVIRONMENT = {"PYTHONDONTWRITEBYTECODE": "1"}
SECRET_VARIABLE = re.compile(r"token|proxy|password|passwd|secret|credential|api_?key|private_?key|jwt|bearer|^ssh_|docker_auth|_auth(?:_|$)|mysql_pwd|passphrase|signing_key(?!_id)|database_url|dsn$", re.IGNORECASE)
NOT_A_SECRET = re.compile(r"^(?:ci_commit_(?:short_)?sha|ci_commit_before_sha|no_proxy|(?:feature|ldap)_auth|odbc_dsn)$|_key_id$|_auth_server_url$", re.IGNORECASE)
MIN_SECRET_LENGTH = 8
# Variables that point git at another repository, index or object store: never given to a git call of this tool.
GIT_REDIRECTS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR", "GIT_NAMESPACE", "GIT_EXEC_PATH")
# Files that steer an agent that is started in a checkout (the CLI is started with --trust).
# A path that can steer an agent: a name or a directory that agent CLIs read (the list of the installed cursor-agent: .cursor .agents .claude .codex
# .grok, AGENTS.md, CLAUDE.md, CLAUDE.local.md), any other directory whose name starts with a dot (.git, .github/workflows, .gitlab and .gitea/workflows excepted),
# any AGENT, CLAUDE or GEMINI markdown file, and any path with a control character in it. Symbolic links are noted by their mode (see steering_paths).
AGENT_CONFIGURATION = re.compile(
    r"(?:^|/)(?:(?:AGENTS|CLAUDE|GEMINI)(?:\.[A-Za-z]+)?\.(?:md|mdc)|\.(?!git/|github/workflows/|gitlab/|gitea/workflows/)[^/]*/.*|\.cursor[^/]*|\.mcp\.json|\.github/copilot-instructions\.md)$"
    r"|[\x00-\x1f\x7f]",
    re.IGNORECASE,
)
# The matches that a human must always see: the locations the installed agent CLI reads, links and names with a control character.
FIRST_RANK = re.compile(
    r"(?:^|/)(?:\.(?:cursor|agents|claude|codex|grok)(?:/|$)|(?:AGENTS|CLAUDE)(?:\.local|\.override)?\.md$|GEMINI\.md$|\.cursor(?:ignore|indexingignore|rules)$|\.mcp\.json$)"
    r"|\.github/copilot-instructions\.md$|[\x00-\x1f\x7f]",
    re.IGNORECASE,
)
SAFE_ARGUMENT = re.compile(r"[A-Za-z0-9 _.,:/\\=+@-]+")
DEFAULT_TIMEOUT = 3600
KILL_WAIT = 10
MAX_ANSWER_BYTES = 1024 * 1024
MINIMUM_PYTHON = (3, 12)
REPORT_NAME = re.compile(r"[A-Za-z0-9._-]+-(?:verifier|security-review)-report[A-Za-z0-9._-]*\.md")
GIT_TIMEOUT = 120
BRIEF_INSTRUCTION = "Follow the instructions in the file {brief_file}. Print your complete report as your final reply."
def default_profile(platform: str) -> list[str]:
    """cursor-agent's profile. --sandbox enabled where the CLI supports it (macOS, Linux); on Windows the CLI exits with "Sandbox requires macOS or Linux"."""
    sandbox = [] if platform == "win32" else ["--sandbox", "enabled"]
    return ["{executable}", "-p", "--output-format", "text", "--trust", "--force", *sandbox, "--model", "{model}", BRIEF_INSTRUCTION]


DEFAULT_PROFILE = default_profile(sys.platform)


class Refusal(Exception):
    """The run stops here; the message says why. Nothing further is done."""


class Interrupted(BaseException):
    """The tool was asked to stop (SIGTERM, SIGHUP or SIGQUIT) at any point of the run."""


_NO_HOOKS: Path | None = None


def no_hooks_dir() -> Path:
    """An empty directory used as core.hooksPath: no repository, template or global hook runs on a git call of this tool."""
    global _NO_HOOKS
    if _NO_HOOKS is None or not _NO_HOOKS.is_dir():
        _NO_HOOKS = Path(tempfile.mkdtemp(prefix="aidf-no-hooks-"))
        atexit.register(shutil.rmtree, _NO_HOOKS, True)
    if any(_NO_HOOKS.iterdir()):
        raise Refusal("the empty hooks directory of this run is no longer empty (something wrote into it); nothing further is run")
    return _NO_HOOKS


_UNTRUSTED: list[Path] = []


def steering_summary(listing: str) -> tuple[list[str], list[str]]:
    """Paths of `git ls-tree -r -z` output (mode, type, object, tab, name; entries ended by NUL) that can steer an agent started in the checkout:
    names matching AGENT_CONFIGURATION, and every symbolic link (a link can make any location resolve into a steering directory). Returns the
    first-rank matches (FIRST_RANK, links) and the others, each in path order, so that ordinary files can never push the first-rank ones out."""
    first: list[str] = []
    rest: list[str] = []
    for entry in listing.split("\0"):
        meta, _, name = entry.partition("\t")
        link = meta.startswith("120000")
        if name and (link or AGENT_CONFIGURATION.search(name)):
            text = clean(name) + (" (symbolic link)" if link else "")
            (first if link or FIRST_RANK.search(name) else rest).append(text)
    return first, rest


def steering_paths(listing: str) -> list[str]:
    first, rest = steering_summary(listing)
    return first + rest


def plain(path: str) -> str:
    """A Windows path without the \\\\?\\ prefix and without the administrative-share spelling of a drive (\\\\localhost\\C$\\...)."""
    if path.startswith("\\\\?\\UNC\\"):
        path = "\\\\" + path[8:]
    elif re.match(r"\\\\\?\\[A-Za-z]:\\", path):
        path = path[4:]
    share = re.match(r"\\\\(?:localhost|127\.0\.0\.1)\\([A-Za-z])\$(\\.*)?$", path, re.IGNORECASE)
    return f"{share[1]}:{share[2] or chr(92)}" if share else path


def is_inside(path: str | Path, bases: list[Path]) -> bool:
    """The path is one of the bases or lies below one, whatever its spelling: compared after the prefix and share spellings are removed and links, junctions and short names are resolved, and by file identity."""
    resolved = Path(os.path.realpath(plain(str(path))))
    for candidate in (resolved, *resolved.parents):
        for base in bases:
            if candidate == base:
                return True
            try:
                if os.path.samefile(candidate, base):  # any other spelling of the same directory (a machine-name share, for example)
                    return True
            except OSError:
                if os.path.exists(base) and os.path.exists(candidate):
                    return True  # both exist and still cannot be compared: treated as inside
    return False


def distrust(*paths: Path) -> None:
    """Directories from which the tool runs no program: the repository under review, the clone, the output directory."""
    _UNTRUSTED[:] = [Path(os.path.realpath(plain(str(path)))) for path in paths]


def tool(name: str) -> str:
    """The absolute path of a program the tool starts by name (git, taskkill). On Windows the current directory is never searched, and a program
    that lies in the repository under review, the clone or the output directory is refused."""
    if sys.platform == "win32":
        os.environ["NoDefaultCurrentDirectoryInExePath"] = "1"
    found = shutil.which(name)
    if found is None:
        raise Refusal(f"{name} was not found on PATH")
    resolved = Path(os.path.realpath(plain(found)))
    if is_inside(resolved, _UNTRUSTED):
        raise Refusal(f"{name} resolves to {resolved}, which lies inside the repository, the clone or the output directory; the tool will not run it")
    return str(resolved)


def reviewer_program(name: str) -> str:
    """The absolute path of the reviewer program (SR2-B1): never a name that a launcher, CreateProcess or cmd.exe could resolve against the clone.
    A name with a directory part must be absolute; a bare name is looked up on PATH (the current directory is not searched on Windows)."""
    if any(separator in name for separator in ("/", "\\")) and not os.path.isabs(name):
        raise Refusal(f"the reviewer program {name!r} is a relative path; give an absolute path or a name on PATH")
    if os.path.isabs(name):
        found: str | None = name if os.path.exists(name) else None
    else:
        found = tool_lookup(name)
    if found is None:
        raise Refusal(f"the reviewer program {name!r} was not found")
    resolved = Path(os.path.realpath(plain(found)))
    if is_inside(resolved, _UNTRUSTED):
        raise Refusal(f"the reviewer program {resolved} lies inside the repository, the clone or the output directory; the tool will not run it")
    return str(resolved)


def tool_lookup(name: str) -> str | None:
    if sys.platform == "win32":
        os.environ["NoDefaultCurrentDirectoryInExePath"] = "1"
    return shutil.which(name)


def git_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    """The tool's environment without the variables that redirect git, plus extra."""
    environment = {key: value for key, value in os.environ.items() if key.upper() not in GIT_REDIRECTS}
    environment.update(extra or {})
    return environment


def git_config_flags() -> list[str]:
    return ["-c", f"core.hooksPath={no_hooks_dir().as_posix()}", "-c", "core.fsmonitor=false"]


ISOLATED_FLAGS = (subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW) if sys.platform == "win32" else 0


def git(
    root: Path, *args: str, check: bool = True, data: bytes | None = None, env: dict[str, str] | None = None, isolated: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    """Run git in root with no hook and no fsmonitor command (core.hooksPath is an empty directory).

    isolated: on Windows the program is created in a process group of its own and with a console of its own (CREATE_NO_WINDOW: no window is shown),
    so neither a console Ctrl-C nor a console Ctrl-Break of the tool's console is delivered to it (a process group alone shields from Ctrl-C only);
    it is used for the git programs that run while the report moves (commit_report), where the tool holds the signal itself. On POSIX it changes nothing.
    """
    done = subprocess.run(
        [tool("git"), "-C", str(root), "-c", f"safe.directory={root.as_posix()}", *git_config_flags(), *args],
        capture_output=True, check=False, timeout=GIT_TIMEOUT, input=data, env=git_environment(env),
        creationflags=ISOLATED_FLAGS if isolated and sys.platform == "win32" else 0,
    )
    if check and done.returncode != 0:
        raise Refusal(f"git {' '.join(args[:3])} failed: {clean(done.stderr.decode('utf-8', 'replace').strip(), 300)}")
    return done


def git_text(root: Path, *args: str, isolated: bool = False) -> str:
    return git(root, *args, isolated=isolated).stdout.decode("utf-8", "replace").strip()


def snapshot(root: Path) -> tuple[str, str, str]:
    """Where the repository stands: HEAD, every ref, and the tracked and staged changes."""
    return (
        git_text(root, "rev-parse", "HEAD"),
        git_text(root, "for-each-ref", "--format=%(refname) %(objectname)"),
        git_text(root, "status", "--porcelain", "--untracked-files=no"),
    )


def reviewer_environment(source: dict[str, str], passed: list[str], cache: Path | None = None) -> tuple[dict[str, str], list[str]]:
    """An allowlist environment. Returns it and the names that were passed explicitly. With `cache`, the caches of ruff, mypy, Python and pytest are
    pointed into that directory (outside the checkout), so that a reviewer who runs the checks does not leave files in the clone."""
    allowed = {name.upper() for name in ALLOWED_ENVIRONMENT}
    wanted = {name.upper() for name in passed}
    for name in passed:
        if name.upper().startswith("GIT_"):
            raise Refusal(f"--pass-env {name}: GIT_ variables are never passed")
    environment = {key: value for key, value in source.items() if key.upper() in allowed or key.upper() in wanted}
    environment.update(FIXED_ENVIRONMENT)
    if cache is not None:
        environment.update({
            "RUFF_CACHE_DIR": str(cache / "ruff"), "MYPY_CACHE_DIR": str(cache / "mypy"), "PYTHONPYCACHEPREFIX": str(cache / "pycache"),
            "PYTEST_ADDOPTS": "-p no:cacheprovider",
        })
    if sys.platform == "win32":
        # cmd.exe, which runs a .cmd launcher, reads this from the reviewer's environment: without it, a program the launcher names without a
        # path (npm's node, for example) is looked for in the clone first.
        environment["NoDefaultCurrentDirectoryInExePath"] = "1"
    missing = sorted(name for name in passed if name.upper() not in {key.upper() for key in source})
    if missing:
        raise Refusal("--pass-env names a variable that is not set: " + ", ".join(missing))
    return environment, sorted(passed)


def secret_values(source: dict[str, str], passed: list[str]) -> dict[str, str]:
    """Values of the tool's own secret-looking variables and of the passed ones, by name."""
    found = {k: v for k, v in source.items() if SECRET_VARIABLE.search(k) and not NOT_A_SECRET.search(k) and len(v) >= MIN_SECRET_LENGTH}
    for name in passed:
        for key, value in source.items():
            if key.upper() == name.upper() and len(value) >= MIN_SECRET_LENGTH:
                found[key] = value
    return found


def redact(text: str, secrets: dict[str, str]) -> str:
    for value in sorted(secrets.values(), key=len, reverse=True):
        text = text.replace(value, "<redacted>")
    return text


_ACTIVE_SECRETS: dict[str, str] = {}


def clean(text: str, limit: int | None = None, lines: bool = False) -> str:
    """Text that came from the reviewer or from git, made safe to print or log: secret values redacted (before any cut to limit characters, so a
    value is never cut in half), control characters shown escaped (line breaks kept when lines is set)."""
    text = redact(text, _ACTIVE_SECRETS)
    if lines:
        text = text.replace("\r\n", "\n")
    if limit is not None:
        text = text[:limit]
    keep = " \n" if lines else " "
    return "".join(character if character.isprintable() or character in keep else repr(character)[1:-1] for character in text)


def encodings(value: str) -> list[bytes]:
    """The forms in which a value is looked for in an answer: as is, UTF-16, percent-encoded, JSON-escaped, hex and base64 (any alignment)."""
    raw = value.encode("utf-8")
    forms = [
        raw, value.encode("utf-16-le"), value.encode("utf-16-be"), urllib.parse.quote(value, safe="").encode("ascii"),
        json.dumps(value)[1:-1].encode("ascii"), raw.hex().encode("ascii"), raw.hex().upper().encode("ascii"),
    ]
    for offset, skip in ((0, 0), (1, 2), (2, 3)):
        text = base64.b64encode(b"\0" * offset + raw).decode("ascii").rstrip("=")[skip:]
        if (offset + len(raw)) % 3:
            text = text[:-1]
        forms += [text.encode("ascii"), text.replace("+", "-").replace("/", "_").encode("ascii")]
    return [form for form in forms if form]


def find_secret(answer: bytes, secrets: dict[str, str]) -> str | None:
    squeezed = re.sub(rb"\s+", b"", answer)
    for name, value in sorted(secrets.items()):
        squeezed_value = re.sub(r"\s+", "", value)
        for form in encodings(value) + (encodings(squeezed_value) if len(squeezed_value) >= MIN_SECRET_LENGTH else []):
            if form in answer or form in squeezed:
                return name
    return None


def outcome_line(answer: bytes) -> tuple[str | None, str]:
    """The outcome word if the last non-empty line is exactly one of the three and no other line is; otherwise None and the reason."""
    try:
        text = answer.decode("utf-8")
    except UnicodeDecodeError:
        return None, "the answer is not UTF-8"
    lines = [line.rstrip("\r") for line in text.split("\n")]
    while lines and lines[-1].strip() == "":
        lines.pop()
    if not lines:
        return None, "the answer is empty"
    if lines[-1] in OUTCOMES:
        for number, line in enumerate(lines[:-1], 1):
            if line in OUTCOMES:
                return None, f"line {number} is also an Outcome line ({line!r}) and only the last line may be one"
        return lines[-1][len("Outcome: "):], ""
    return None, f"the last non-empty line is not an Outcome line: {lines[-1][:80]!r}"


def scope_pattern(pattern: str) -> re.Pattern[str]:
    out = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile(out)


def plain_relative_path(path: str) -> bool:
    """A repository path written the way git writes it: forward slashes, no dot segments, no drive or root."""
    if not path or path.startswith("/") or "\\" in path or ":" in path or "\0" in path:
        return False
    return all(part not in ("", ".", "..") and part == part.rstrip(" .") for part in path.split("/"))


def report_in_scope(contract: dict[str, object], path: str) -> bool:
    """The path is a report path (the naming of core/05-review.md section 6) and is listed in declared_scope, literally or by a pattern."""
    scope = contract.get("declared_scope")
    if not isinstance(scope, list) or not plain_relative_path(path):
        return False
    if REPORT_NAME.fullmatch(path.rsplit("/", 1)[-1]) is None:
        return False
    return any(isinstance(item, str) and (item == path or ("*" in item and scope_pattern(item).fullmatch(path) is not None)) for item in scope)


def is_batch_launcher(executable: str) -> bool:
    """A .cmd or .bat file, also when Windows would drop trailing dots and spaces from the name."""
    return Path(executable.rstrip(" .")).suffix.lower() in (".cmd", ".bat")


def unsafe_for_batch_launcher(arguments: list[str]) -> str | None:
    for item in arguments:
        if SAFE_ARGUMENT.fullmatch(item) is None:
            return item
    return None


def build_command(profile: list[str], values: dict[str, str]) -> list[str]:
    command = []
    for item in profile:
        for key, value in values.items():
            item = item.replace("{" + key + "}", value)
        command.append(item)
    return command


def kill_tree(process: subprocess.Popen[bytes]) -> None:
    """Windows: kill the reviewer and the processes it started. (POSIX ends the reviewer through the Lifeline.)"""
    if sys.platform == "win32":
        subprocess.run([tool("taskkill"), "/F", "/T", "/PID", str(process.pid)], capture_output=True, check=False)
    process.kill()


HELD_SIGNALS = ("SIGINT", "SIGTERM", "SIGHUP", "SIGQUIT")


def _interrupt(signum: int, _frame: object) -> None:
    raise Interrupted(signum)


def install_signal_handlers() -> list[tuple[int, Any]]:
    """For the whole run: SIGTERM, SIGHUP and SIGQUIT raise Interrupted, as SIGINT raises KeyboardInterrupt. Returns what to restore."""
    saved: list[tuple[int, Any]] = []
    if sys.platform != "win32" and threading.current_thread() is threading.main_thread():
        for number in (signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT):
            saved.append((number, signal.signal(number, _interrupt)))
    return saved


@contextlib.contextmanager
def signals_deferred() -> Iterator[None]:
    """Hold SIGINT, SIGTERM, SIGHUP and SIGQUIT back (POSIX; SIGINT and SIGBREAK on Windows) while the report moves, or the reviewer starts.

    A signal held back is raised when the block ends (on Windows: a Ctrl-C or a Ctrl-Break becomes a KeyboardInterrupt then, also when the block
    ends with another exception, which becomes its cause). On Windows a closing console, a logoff and a shutdown are not held.
    """
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    if sys.platform == "win32":
        pending: list[int] = []
        previous_handlers: dict[int, Any] = {}

        def restore() -> None:
            for number, handler in previous_handlers.items():
                signal.signal(number, handler)

        try:
            for number in (signal.SIGINT, signal.SIGBREAK):
                previous_handlers[number] = signal.signal(number, lambda held, _frame: pending.append(held))
            yield
        except BaseException as failure:
            restore()
            if pending and not isinstance(failure, KeyboardInterrupt):
                raise KeyboardInterrupt from failure
            raise
        restore()
        if pending:
            raise KeyboardInterrupt
        return
    held = {getattr(signal, name) for name in HELD_SIGNALS}
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, held)
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


# POSIX: the reviewer is started by this small program, which leads a session. The reviewer leads a session of its own below it. The program holds the
# read end of a pipe whose write end only the tool holds. When the pipe closes (the tool ended, however it ended, or asked for the end) or when the
# reviewer exits, it kills the reviewer's whole group and leaves. Nothing is sent over the pipe: closing it is the only message.
WATCHDOG = r"""
import json, os, signal, subprocess, sys, threading
descriptor = int(sys.argv[1])
try:
    child = subprocess.Popen(json.loads(sys.argv[2]), stdin=subprocess.DEVNULL, start_new_session=True)
except OSError as error:
    sys.stderr.write("cannot start the reviewer: %s\n" % error)
    sys.stderr.flush()
    os._exit(127)
def end(code):
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except OSError:
        pass
    os._exit(code)
def watch():
    while True:
        try:
            data = os.read(descriptor, 1)
        except OSError:
            data = b""
        if data == b"":
            end(137)
try:
    threading.Thread(target=watch, daemon=True).start()
except BaseException:
    end(1)
code = child.wait()
end(code if code >= 0 else 128 - code)
"""


def _windows_job() -> Any:
    """A job object that kills every process in it when its last handle closes (the tool ending, however it ends)."""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class Counters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in ("r", "w", "o", "rt", "wt", "ot")]

    class Basic(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64), ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t), ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD),
        ]

    class Extended(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", Basic), ("IoInfo", Counters), ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    job = kernel32.CreateJobObjectW(None, None)
    info = Extended()
    info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not job or not kernel32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
        raise OSError("cannot create the job object that ties the reviewer to the tool")
    ntdll = ctypes.WinDLL("ntdll")
    ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]
    return job, kernel32, ntdll


CREATE_SUSPENDED = 0x00000004


class Lifeline:
    """Ties the reviewer's life to the tool's: on POSIX through a watchdog and a pipe, on Windows through a job object."""

    def __init__(self) -> None:
        self.write_end: int | None = None
        self.job: Any = None

    def start(self, command: list[str], cwd: Path, environment: dict[str, str]) -> subprocess.Popen[bytes]:
        if sys.platform == "win32":
            self.job = _windows_job()
            job, kernel32, ntdll = self.job
            # A Ctrl-C is held back from before the reviewer exists until it is inside the job and running; it is raised after that, and the job
            # (closed by finish) then kills the reviewer. Otherwise a suspended reviewer outside the job could be left behind.
            with signals_deferred():
                process = subprocess.Popen(
                    command, cwd=cwd, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    creationflags=CREATE_SUSPENDED,
                )
                try:
                    handle = int(process._handle)  # type: ignore[attr-defined]
                    if not kernel32.AssignProcessToJobObject(job, handle):
                        raise OSError("cannot put the reviewer into the job object")
                    if ntdll.NtResumeProcess(handle) != 0:
                        raise OSError("cannot resume the reviewer")
                except BaseException:
                    kill_tree(process)
                    raise
            return process
        read_end, self.write_end = os.pipe()
        read_end = self._above_standard(read_end)
        self.write_end = self._above_standard(self.write_end)
        try:
            process = subprocess.Popen(
                [sys.executable, "-I", "-c", WATCHDOG, str(read_end), json.dumps(command)], cwd=cwd, env=environment,
                pass_fds=(read_end,), start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
        finally:
            os.close(read_end)
        return process

    def release(self) -> None:
        """POSIX: close the write end. The watchdog reads end of file, kills the reviewer's group and leaves."""
        descriptor, self.write_end = self.write_end, None
        if descriptor is not None:
            os.close(descriptor)

    @staticmethod
    def _above_standard(descriptor: int) -> int:
        """A pipe end must not be 0, 1 or 2 (when the tool was started with a standard stream closed): the reviewer's own streams are those."""
        if descriptor > 2:
            return descriptor
        taken = []
        while descriptor <= 2:
            taken.append(descriptor)
            descriptor = os.dup(descriptor)
        for low in taken:
            os.close(low)
        return descriptor

    def stop(self, process: subprocess.Popen[bytes]) -> None:
        """End the reviewer and its children now."""
        if sys.platform == "win32":
            kill_tree(process)
            return
        self.release()
        try:
            process.wait(timeout=KILL_WAIT)
        except subprocess.TimeoutExpired:
            process.kill()

    def finish(self) -> None:
        """The run is over: close the pipe (the watchdog has left or kills what is left) or close the job (Windows kills what is left)."""
        self.release()
        if self.job is not None:
            job, kernel32, _ntdll = self.job
            kernel32.CloseHandle(job)
            self.job = None


def run_reviewer(command: list[str], cwd: Path, environment: dict[str, str], timeout: int) -> tuple[int | None, bytes, bytes]:
    """Returns (exit status or None on timeout, stdout, stderr). No shell, no standard input.

    The reviewer lives only as long as the tool: whatever ends the tool (an exception here, a signal, a kill) closes the pipe or the job and the
    reviewer's whole group or job is killed. Limits (residual_risk in the evidence pack): on Windows a kill of the tool before the reviewer is
    assigned to the job; on POSIX a process that leaves the reviewer's group, or a watchdog that is itself killed. A reviewer ended by a signal N is reported as 128 + N on POSIX.
    """
    lifeline = Lifeline()
    try:
        process = lifeline.start(command, cwd, environment)
        try:
            out, err = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            lifeline.stop(process)
            try:
                out, err = process.communicate(timeout=KILL_WAIT)
            except subprocess.TimeoutExpired:
                out, err = b"", b""
            return None, out, err
        except BaseException:
            lifeline.stop(process)
            raise
    finally:
        lifeline.finish()
    return process.returncode, out, err


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_clone(root: Path, head: str, out: Path) -> Path:
    """A new repository with the pinned head and its history and nothing else: no remote, no other refs, no hooks. It is built from git's own
    built-in commands (init, pack-objects, checkout) and not with `git clone`, which starts the external helper git-upload-pack: on some
    installations (the CI image's, for one) that helper is not found and every clone fails."""
    clone = out / "checkout"
    made = subprocess.run(
        [tool("git"), *git_config_flags(), "init", "--quiet", f"--template={no_hooks_dir().as_posix()}", str(clone)],
        capture_output=True, check=False, timeout=GIT_TIMEOUT, env=git_environment(),
    )
    if made.returncode != 0:
        raise Refusal("cannot create the checkout repository: " + clean(made.stderr.decode("utf-8", "replace").strip(), 300))
    try:
        name = git(root, "pack-objects", "--revs", "--quiet", str(out / "transfer"), data=(head + "\n").encode("ascii")).stdout.decode("ascii").strip()
        packs = clone / ".git" / "objects" / "pack"
        packs.mkdir(parents=True, exist_ok=True)
        for part in sorted(out.glob(f"transfer-{name}.*")):  # .pack, .idx and, in newer git, .rev
            shutil.move(str(part), str(packs / f"pack-{name}{part.suffix}"))
    except (Refusal, OSError) as exc:
        raise Refusal("cannot copy the repository's objects: " + clean(str(exc), 300)) from exc
    git(clone, "checkout", "--quiet", "--detach", head)
    return clone


def clone_state(clone: Path) -> dict[str, str]:
    """What the clone holds, read without running git in it (the reviewer controls its configuration): every file and link outside .git by
    content, and the clone's HEAD (its other refs are its own)."""
    state: dict[str, str] = {}
    for directory, names, files in os.walk(clone, followlinks=False):
        here = Path(directory)
        if here == clone:
            names[:] = [name for name in names if name != ".git"]
        for name in list(names):
            path = here / name
            key = path.relative_to(clone).as_posix()
            if path.is_symlink() or os.path.isjunction(path):
                state[key] = "link " + os.readlink(path)  # a link to a directory is recorded, never followed
                names.remove(name)
            else:
                state[key + "/"] = "directory"
        for name in files:
            path = here / name
            key = path.relative_to(clone).as_posix()
            if path.is_symlink():
                state[key] = "link " + os.readlink(path)
                continue
            mode = path.lstat().st_mode
            if not stat.S_ISREG(mode):
                state[key] = f"special {stat.S_IFMT(mode):o}"  # a FIFO or device is never opened
                continue
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(chunk)
            state[key] = f"{digest.hexdigest()} {stat.S_IMODE(mode):o}"
    head_file = clone / ".git" / "HEAD"
    state[".git/HEAD"] = head_file.read_text(encoding="utf-8", errors="replace") if head_file.is_file() else "absent"
    return state


def clone_changes(clone: Path, before: dict[str, str]) -> list[str]:
    after = clone_state(clone)
    problems = []
    if after.get(".git/HEAD") != before.get(".git/HEAD"):
        problems.append("the clone's HEAD moved")
    for key in sorted(set(before) | set(after)):
        if key != ".git/HEAD" and before.get(key) != after.get(key):
            problems.append("changed in the clone: " + key)
    return problems[:20]


def configuration_state(root: Path) -> dict[str, bytes | None]:
    """The repository files that decide which commands git runs for the tool (read before the reviewer starts and again after it ended)."""
    common = Path(git_text(root, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    own = Path(git_text(root, "rev-parse", "--path-format=absolute", "--git-dir"))
    homes = {Path(os.path.expanduser("~"))}
    homes |= {Path(os.environ[name]) for name in ("HOME", "USERPROFILE") if os.environ.get(name)}
    if os.environ.get("HOMEDRIVE") and os.environ.get("HOMEPATH"):
        homes.add(Path(os.environ["HOMEDRIVE"] + os.environ["HOMEPATH"]))
    configs = {home / ".config" for home in homes}
    if os.environ.get("XDG_CONFIG_HOME"):
        configs.add(Path(os.environ["XDG_CONFIG_HOME"]))
    files = [common / "config", common / "info/attributes", common / "config.worktree", own / "config.worktree", own / "info/attributes"]
    for home in sorted(homes):
        files.append(home / ".gitconfig")
    for config in sorted(configs):
        files += [config / "git/config", config / "git/attributes", config / "git/ignore"]
    for variable in ("GIT_CONFIG_GLOBAL", "GIT_ATTR_GLOBAL"):  # git 2.42 and later says where it looks
        asked = git(root, "var", variable, check=False).stdout.decode("utf-8", "replace").split("\n")
        files += [Path(line.strip()) for line in asked if line.strip()]
    files += [Path(os.environ[name]) for name in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM") if os.environ.get(name)]
    attributes = git(root, "config", "--path", "--get", "core.attributesFile", check=False).stdout.decode("utf-8", "replace").strip()
    if attributes:
        files.append(Path(attributes))
    files = [path if path.is_absolute() else root / path for path in files]  # git reads a relative path against the repository, not the tool's directory
    return {str(path): path.read_bytes() if path.is_file() else None for path in files}


_OUT_IDENTITY: list[tuple[int, int]] = []


def remember_out(out: Path) -> None:
    status = out.stat()
    _OUT_IDENTITY[:] = [(status.st_dev, status.st_ino)]


def out_unchanged(out: Path) -> bool:
    """The output directory is still the directory the run started with (not a link, not moved aside and replaced by the reviewer)."""
    try:
        status = out.stat()
        return not (out.is_symlink() or os.path.isjunction(out)) and [(status.st_dev, status.st_ino)] == _OUT_IDENTITY
    except OSError:
        return False


def write_new(path: Path, data: bytes) -> None:
    """Write a file that must not exist yet and is not followed through a link (the reviewer could have planted one in the output directory)."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    with os.fdopen(os.open(path, flags, 0o644), "wb") as handle:
        handle.write(data)


def write_brief(path: Path, header: dict[str, str], preflight_output: str, brief: str) -> None:
    lines = ["# Review run header (computed by verification/run_review.py)", ""]
    lines += [f"- **{key}:** {value}" for key, value in header.items()]
    lines += ["", "## Preflight output", "", "```", preflight_output.rstrip(), "```", "", "## Brief", "", brief.rstrip(), ""]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def commit_report(root: Path, relative: str, answer: bytes, head: str, message: str) -> str:
    """Commit the report alone, on top of the pinned head, byte for byte. Returns the new commit.

    The commit is built from objects (no clean filters, no .gitattributes) and every git call of this tool runs with an empty hooks directory,
    so no repository hook runs. It is checked, and only then written: the file, then the index entry, then the branch last; HEAD is checked again.
    """
    if git_text(root, "rev-parse", "HEAD") != head:
        raise Refusal("HEAD moved since the head was pinned; the report is not committed")
    if git_text(root, "diff", "--cached", "--name-only"):
        raise Refusal("the index has staged changes; the report must be committed alone")
    target = root / relative
    real_parent = target.parent.resolve()
    if real_parent != root.resolve() and root.resolve() not in real_parent.parents:
        raise Refusal(f"{relative} would be written outside the repository (a directory on its path is a link); nothing committed")
    if os.path.lexists(target) or git(root, "cat-file", "-e", f"HEAD:{relative}", check=False).returncode == 0:
        raise Refusal(f"{relative} already exists (or is a link); a report is never overwritten")
    with tempfile.TemporaryDirectory() as scratch:
        blob = git(root, "hash-object", "-w", "--no-filters", "--stdin", data=answer).stdout.decode().strip()
        env = {}
        env["GIT_INDEX_FILE"] = str(Path(scratch) / "index")
        git(root, "read-tree", head, env=env)
        git(root, "update-index", "--add", "--cacheinfo", f"100644,{blob},{relative}", env=env)
        tree = git(root, "write-tree", env=env).stdout.decode().strip()
        changed = git(root, "diff-tree", "-r", "--no-renames", "--name-status", head, tree).stdout.decode().split()
        if changed != ["A", relative]:
            raise Refusal(f"the commit would change more than the report: {changed[:6]}; nothing committed")
        stored = git(root, "cat-file", "blob", f"{tree}:{relative}").stdout
        if hashlib.sha256(stored).hexdigest() != hashlib.sha256(answer).hexdigest():
            raise Refusal(f"the stored blob of {relative} differs from the answer; nothing committed")
        commit = git(root, "commit-tree", tree, "-p", head, "-m", message).stdout.decode().strip()
        with signals_deferred():
            # The file comes first, then the index entry, and the branch moves last. An end of the tool after the file and before the index
            # entry leaves an untracked file; after the entry, a staged report; both are visible and not silently deleted by the next commit.
            # If the branch has moved, the file and the entry stay: they belong to the commit.
            created = False
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
                descriptor = os.open(target, flags, 0o644)
                created = True
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(answer)
                git(root, "update-index", "--add", "--cacheinfo", f"100644,{blob},{relative}", isolated=True)
                git(root, "update-ref", "-m", "run_review: report", "HEAD", commit, head, isolated=True)
            except BaseException:
                # Roll back only while the branch is still at the pinned head. If it has moved (or cannot be read), the report commit exists and
                # the file and the index entry belong to it: removing them would make the next commit delete the report.
                try:
                    unmoved = git_text(root, "rev-parse", "HEAD", isolated=True) == head
                except (Refusal, OSError, subprocess.SubprocessError):
                    unmoved = False
                if unmoved:
                    if created:
                        with contextlib.suppress(Exception):
                            target.unlink()
                    with contextlib.suppress(Exception):
                        git(root, "update-index", "--force-remove", "--", relative, check=False, isolated=True)
                raise
            git(root, "update-index", "--refresh", check=False, isolated=True)
    if git_text(root, "rev-parse", "HEAD") != commit:
        raise Refusal("HEAD is not the report commit after the update; check the repository (git log, git status)")
    return commit


def prepare_out(root: Path, out: Path) -> None:
    """The output directory is new or empty and outside the repository; nothing is written to a directory that fails this."""
    if out == root or root in out.parents:
        raise Refusal("--out must be outside the repository")
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise Refusal(f"--out {out} is not an empty directory")
    out.mkdir(parents=True, exist_ok=True)


USAGE_NOTE = """Before the first run:
  * A reviewer CLI that is not on PATH is named with --reviewer-executable and its full path. On Windows cursor-agent is a .cmd launcher in the
    user's local application directory (...\\AppData\\Local\\cursor-agent\\cursor-agent.cmd).
  * The report path (--report) must be named by an entry of the contract's declared_scope, a path or a pattern, before the run; otherwise the tool
    refuses before it starts the reviewer.
  * --out must be a new or empty directory. A refused start leaves its log there: clear the directory before the next start.
  * The tool refuses to start the reviewer when the head holds files that can steer it (AGENTS.md, CLAUDE.md, .cursor, .agents, .claude, .codex,
    .grok, symbolic links, names with a control character); --allow-steering-files starts it anyway and the log records that.
  * The reviewer's ruff, mypy, Python and pytest caches are pointed into <out>/reviewer-cache; any other file it leaves in the checkout makes the run invalid.
  * An answer with an Outcome line anywhere but its last line is not committed; it is kept as <out>/answer.rejected.
  * The tool commits the report alone on top of the pinned HEAD, moves the branch you are on to it (on a detached HEAD only HEAD moves), and never pushes.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None, epilog=USAGE_NOTE, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=".")
    parser.add_argument("--head", default="HEAD", help="must resolve to the current HEAD")
    parser.add_argument("--previous", help="the previously reviewed head (a confirmation round covers the delta)")
    parser.add_argument("--contract", required=True, help="the change's JSON Task Contract (declared_scope names the allowed report paths)")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--brief", required=True, help="the round's brief file prepared by the Implementer")
    parser.add_argument("--report", required=True, help="repository path of the report to commit")
    parser.add_argument("--role", choices=("verifier", "security"), default="verifier")
    parser.add_argument("--round", type=int, default=1)
    parser.add_argument("--model", default="")
    parser.add_argument("--out", help="a new or empty directory outside the repository (default: a temporary one)")
    parser.add_argument("--pass-env", action="append", default=[], metavar="NAME")
    parser.add_argument("--reviewer-command", help="JSON list replacing the default profile; {executable} {model} {brief_file} {checkout} are replaced")
    parser.add_argument("--reviewer-executable")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--preflight-arg", action="append", default=[], help="passed to verification/preflight.py")
    parser.add_argument("--skip-preflight", metavar="REASON")
    parser.add_argument("--accept-nonconforming", metavar="REASON")
    parser.add_argument("--allow-steering-files", action="store_true", help="start the reviewer although the head holds files that can steer it (see --help, the note)")
    parser.add_argument("--message")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    clock = time.monotonic()
    log: dict[str, object] = {"started": now(), "role": args.role, "round": args.round, "model": args.model, "passed_variables": sorted(args.pass_env)}
    out = Path(tempfile.mkdtemp(prefix="aidf-review-run-")).resolve() if args.out is None else Path(args.out).resolve()
    log_path = out / "review-run.json"
    status = 1
    prepared = False
    handlers = install_signal_handlers()
    try:
        if sys.version_info < MINIMUM_PYTHON:
            raise Refusal(f"Python {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]} or later is required")
        prepare_out(root, out)
        remember_out(out)
        prepared = True
        status = run(args, root, out, log)
    except Refusal as exc:
        print(f"REFUSED  {clean(str(exc))}")
        log["refused"] = clean(str(exc))
    except (KeyboardInterrupt, Interrupted):
        log["interrupted"] = True
        status = 130
        try:
            now_head = git_text(root, "rev-parse", "HEAD")
        except (Refusal, OSError, subprocess.SubprocessError):
            now_head = ""
        pinned = log.get("head")
        if pinned and now_head and now_head != pinned:
            log["head_after_interrupt"] = now_head
            print(f"INTERRUPTED  HEAD is {now_head}, not the pinned head {pinned}: the report may have been committed; check git log and git status")
        else:
            print("INTERRUPTED  the tool ended; its lifeline kills a reviewer that was running; the branch did not move")
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        print(f"REFUSED  {clean(str(exc))}")
        log["refused"] = clean(str(exc))
    for number, handler in handlers:
        signal.signal(number, handler)
    log["finished"] = now()
    log["duration_seconds"] = round(time.monotonic() - clock)
    log["exit_status"] = status
    if prepared and not out_unchanged(out):
        print(f"the log was not written: {out} is no longer the directory the run started with")
    elif prepared:
        try:
            write_new(log_path, (json.dumps(log, indent=2, sort_keys=True) + "\n").encode("utf-8"))
            print(f"log      {log_path}")
        except OSError as exc:
            print(f"the log could not be written to {log_path}: {clean(str(exc))}")
    print(json.dumps(log, indent=2, sort_keys=True))
    return status


def run(args: argparse.Namespace, root: Path, out: Path, log: dict[str, object]) -> int:
    distrust(root, out)
    secrets = secret_values(dict(os.environ), args.pass_env)
    _ACTIVE_SECRETS.clear()
    _ACTIVE_SECRETS.update(secrets)
    head = git_text(root, "rev-parse", "--verify", f"{args.head}^{{commit}}")
    current = git_text(root, "rev-parse", "HEAD")
    if head != current:
        raise Refusal(f"--head resolves to {head}, not the current HEAD {current}; check out the head to review (the report is committed on top of it)")
    if git_text(root, "status", "--porcelain", "--untracked-files=no"):
        raise Refusal("uncommitted tracked changes: commit first, the reviewer reads the committed head")
    previous = None
    if args.previous:
        previous = git_text(root, "rev-parse", "--verify", f"{args.previous}^{{commit}}")
        if git(root, "merge-base", "--is-ancestor", previous, head, check=False).returncode != 0:
            raise Refusal("--previous is not an ancestor of the head")
    print(f"head     {head}")
    log.update({"head": head, "previous_head": previous})
    try:
        contract = json.loads(git(root, "show", f"{head}:{args.contract.replace(os.sep, '/')}").stdout.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise Refusal(f"the contract at the head is not JSON: {exc}") from exc
    relative = args.report.replace(os.sep, "/")
    if not isinstance(contract, dict) or not report_in_scope(contract, relative):
        raise Refusal(f"{relative} does not match a report pattern in the declared_scope of {args.contract}")
    if os.path.lexists(root / relative) or git(root, "cat-file", "-e", f"HEAD:{relative}", check=False).returncode == 0:
        raise Refusal(f"{relative} already exists (or is a link); a report is never overwritten")

    preflight_text = "not run"
    if args.skip_preflight:
        preflight_text = f"SKIPPED by the human: {args.skip_preflight}"
        log["preflight_skipped"] = args.skip_preflight
        print(f"preflight skipped: {args.skip_preflight}")
    else:
        done = subprocess.run(
            [sys.executable, "verification/preflight.py", "--root", str(root), "--contract", args.contract, "--evidence", args.evidence, *args.preflight_arg],
            cwd=root, capture_output=True, check=False, timeout=3600, env=git_environment(),
        )
        preflight_text = (done.stdout + done.stderr).decode("utf-8", "replace")
        log["preflight_exit"] = done.returncode
        if done.returncode != 0:
            print(clean(preflight_text, lines=True))
            raise Refusal("the preflight failed: fix what it reports; the reviewer was not started")
        print(clean(preflight_text, lines=True).rstrip())
        print("preflight ok")

    before = snapshot(root)
    configuration = configuration_state(root)
    clone = make_clone(root, head, out)
    distrust(root, out, clone)
    clone_before = clone_state(clone)
    first, rest = steering_summary(git(root, "ls-tree", "-r", "-z", head).stdout.decode("utf-8", "replace"))
    log["steering_files_allowed"] = bool(args.allow_steering_files)
    if first or rest:
        log["agent_configuration_in_head"] = first[:200] + rest[:20]
        log["agent_configuration_total"] = len(first) + len(rest)
        if first and not args.allow_steering_files:
            raise Refusal(
                f"the reviewed head holds {len(first)} paths that can steer the reviewer (it is started with --trust): " + ", ".join(first[:20])
                + (" ..." if len(first) > 20 else "")
                + "; review a head without them, or pass --allow-steering-files to start the reviewer anyway. Nothing was started"
            )
        print(
            f"NOTE     the reviewed head holds {len(first) + len(rest)} files that can steer an agent started in it (the CLI is started with --trust); "
            f"{len(first)} at the locations the CLI reads or as links: " + ", ".join(first[:20]) + ("" if first else "none")
            + ("; others, first 5: " + ", ".join(rest[:5]) if rest else "")
        )
    base = git(root, "rev-parse", "--verify", "origin/main^{commit}", check=False).stdout.decode().strip() or "not resolvable"
    brief_path = out / "brief.md"
    header = {
        "Role and layer": f"{'independent Verifier' if args.role == 'verifier' else 'Security reviewer layer'}, round {args.round}",
        "Reviewed head": head,
        "Previous reviewed head": previous or "none (first round)",
        "Delta": f"git diff {previous} {head}" if previous else "the whole change against the base",
        "Base (origin/main)": base,
        "Checkout (read-only)": str(clone),
        "Outcome line": "the last line of your reply must be exactly one of: " + ", ".join(OUTCOMES),
    }
    write_brief(brief_path, header, preflight_text, Path(args.brief).read_text(encoding="utf-8"))
    log["brief"] = str(brief_path)

    if not args.reviewer_command and not args.model:
        raise Refusal("--model is required for the default profile")
    executable = args.reviewer_executable or (tool("cursor-agent") if tool_lookup("cursor-agent") else "")
    profile = json.loads(args.reviewer_command) if args.reviewer_command else default_profile(sys.platform)
    if not args.reviewer_command and "--sandbox" not in profile:
        log["sandbox"] = "none: cursor-agent supports its sandbox only on macOS and Linux"
        print("NOTE     no sandbox is in effect: cursor-agent supports --sandbox only on macOS and Linux; the reviewer can read and write what this account can")
    if not isinstance(profile, list) or not all(isinstance(item, str) for item in profile):
        raise Refusal("--reviewer-command must be a JSON list of strings")
    command = build_command(profile, {"executable": executable, "model": args.model, "brief_file": str(brief_path), "checkout": str(clone)})
    if not command[0]:
        raise Refusal("the reviewer CLI was not found: pass --reviewer-executable or --reviewer-command")
    if is_batch_launcher(command[0]):
        bad = unsafe_for_batch_launcher(command[1:])
        if bad is not None:
            raise Refusal(f"a .cmd or .bat launcher passes its arguments through cmd.exe; this argument has characters the tool will not pass: {bad[:60]!r}")
    command[0] = reviewer_program(command[0])
    if is_batch_launcher(command[0]) and (re.search(r'[%!^&|<>"]', command[0]) or (re.search(r"[(),;=]", command[0]) and not re.search(r"\s", command[0]))):
        raise Refusal(f"the .cmd or .bat launcher '{clean(command[0])}' has a character in its path that cmd.exe interprets (% ! ^ & | < > \" and, in a path without a space, ( ) , ; =); install it elsewhere or use a launcher without one")
    if is_batch_launcher(command[0]):  # a name without its extension is resolved to a .cmd or .bat file only now
        bad = unsafe_for_batch_launcher(command[1:])
        if bad is not None:
            raise Refusal(f"a .cmd or .bat launcher passes its arguments through cmd.exe; this argument has characters the tool will not pass: {clean(bad[:60])!r}")
    cache = out / "reviewer-cache"
    cache.mkdir()
    environment, _passed = reviewer_environment(dict(os.environ), args.pass_env, cache)
    log["reviewer_command"] = [redact(item, secrets) for item in profile]
    log["environment_names"] = sorted(environment)
    print("environment names passed to the reviewer: " + ", ".join(sorted(environment)))

    started = now()
    code, answer, err = run_reviewer(command, clone, environment, args.timeout)
    log["reviewer_started"] = started
    log["reviewer_finished"] = now()
    if not out_unchanged(out):
        raise Refusal("the output directory is no longer the directory the run started with (the reviewer replaced it); nothing was written to it and nothing is committed")
    write_new(out / "reviewer.err", err)
    write_new(out / "answer.bin", answer)
    log["answer_sha256"] = hashlib.sha256(answer).hexdigest()
    log["answer_bytes"] = len(answer)
    if code is None:
        raise Refusal(f"the reviewer ran past the timeout of {args.timeout} s and was killed; nothing committed")
    log["reviewer_exit"] = code
    if code == 127 and err.startswith(b"cannot start the reviewer"):
        raise Refusal(clean(err.decode("utf-8", "replace").strip(), 300))
    if code != 0:
        raise Refusal(f"the reviewer exited with status {code}; nothing committed (standard output is in {out / 'answer.bin'}, standard error in reviewer.err)")
    print(f"answer   {len(answer)} bytes, sha256 {log['answer_sha256']}, reviewer exit {code}")

    problems = clone_changes(clone, clone_before)
    if configuration_state(root) != configuration:
        raise Refusal("the repository configuration (config, config.worktree, attributes, the global configuration) changed while the reviewer ran; nothing committed")
    if snapshot(root) != before:
        problems.append("the repository the tool ran in changed (HEAD, a ref or a tracked change)")
    if problems:
        log["invalid_run"] = [clean(problem) for problem in problems]
        raise Refusal("the run is invalid, nothing committed: " + "; ".join(problems))
    leaked = find_secret(answer, secrets)
    if leaked:
        raise Refusal(f"the answer contains the value of the variable {leaked}; nothing committed (the answer is in {out / 'answer.bin'}: do not share it)")
    if len(answer) > MAX_ANSWER_BYTES or b"\0" in answer or not answer.strip():
        raise Refusal(f"the answer is empty, larger than {MAX_ANSWER_BYTES} bytes or holds a NUL byte; it is not an outcome record and is never committed")
    word, reason = outcome_line(answer)
    log["outcome"] = word
    if word is None:
        rejected = out / "answer.rejected"
        (out / "answer.bin").replace(rejected)
        if not args.accept_nonconforming:
            raise Refusal(f"{reason}; the answer is kept as {rejected}, nothing committed")
        if reason == "the answer is not UTF-8":
            raise Refusal("the answer is not UTF-8; --accept-nonconforming does not cover that")
        log["accepted_nonconforming"] = args.accept_nonconforming
        print(f"WAIVER   committed although {reason}; reason: {args.accept_nonconforming} (a waiver of the Implementer's own rule, not of a review rule)")
    message = args.message or f"docs(review): {args.role} round {args.round} report, committed verbatim"
    log["report_commit"] = commit_report(root, relative, answer, head, message)
    print(f"committed {relative} as {log['report_commit']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
