"""Verify the facts of an evidence pack that the repository can answer (core/05-review.md section 4, templates/evidence-pack.md).

    python verification/pack_facts.py --evidence <pack.json> [--root .] [--head HEAD]

It is a separate file, not a command of aidf_check.py, because aidf_check.py is attested by the protected policy repository.
Exit status 0 means no finding. It is run by the Implementer, is not a pipeline job, and is not a security control.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aidf_check import (
    MAX_DIFF_BYTES,
    Finding,
    _safe_repo_path,
    _valid_git_revision,
    load_json,
)


def _git_bytes(root: Path, args: list[str]) -> bytes | None:
    """Raw stdout of a git command, or None when git fails or times out (an absent object is a normal answer)."""
    try:
        result = subprocess.run(
            ["git", "-c", f"safe.directory={root.as_posix()}", *args],
            cwd=root,
            check=False,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 and len(result.stdout) <= MAX_DIFF_BYTES else None


def _strings_of(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings_of(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings_of(item)


PACK_FACT_SHA = re.compile(r"\b[0-9a-fA-F]{7,40}\b")
PACK_FACT_TEST = re.compile(r"\btest_[A-Za-z0-9_]{1,}\b(?!\.py)")
PACK_FACT_DIGEST_CONTEXT = re.compile(r"(?:digest|sha-?256)\W{0,3}$")
PACK_FACT_PATH_LIKE = re.compile(r"\.(?:md|json|txt|py|yml|yaml|csv)$")
PACK_FACT_PATH = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]*")


def check_pack_facts(evidence: dict[str, Any], root: Path, head: str = "HEAD") -> list[Finding]:
    """Verify the facts of an evidence pack that the repository can answer: no argument, no reviewer pass.

    Closed list: (1) a security_evidence artifact that is a bare repository path names a blob at ``head`` whose SHA-256
    equals artifact_sha256; (2) every commit SHA cited (7 to 40 hex digits with at least one digit and one letter)
    resolves to a git object (a commit or a blob); (3) every ``test_*`` name cited is defined as ``def test_*`` in a tracked Python file at ``head``.
    Free-text artifacts, paths cited in prose and the truth of any sentence are not checked.
    """
    findings: list[Finding] = []
    if not _valid_git_revision(head) and head != "HEAD":
        return [Finding("pack-facts", "--head must be HEAD or a hexadecimal revision")]
    security = evidence.get("security_evidence")
    if isinstance(security, dict):
        artifact = security.get("artifact")
        claimed = security.get("artifact_sha256")
        if isinstance(artifact, str) and artifact.strip():
            whole = artifact.strip()
            lead = whole.split(None, 1)[0].strip("(),;:`'\"")
            for candidate in dict.fromkeys((whole, lead)):
                if PACK_FACT_PATH.fullmatch(candidate) and _safe_repo_path(candidate):
                    blob = _git_bytes(root, ["cat-file", "blob", f"{head}:{candidate}"])
                    if blob is not None:
                        if hashlib.sha256(blob).hexdigest() != claimed:
                            findings.append(Finding("pack-facts", f"security_evidence.artifact_sha256 does not match the committed blob of {candidate!r}"))
                        break
            else:
                if re.search(r"[/\\]", lead) or PACK_FACT_PATH_LIKE.search(lead) or PACK_FACT_PATH_LIKE.search(whole) or (
                    not re.search(r"\s", whole) and "." in whole
                ):
                    findings.append(Finding("pack-facts", f"security_evidence.artifact {artifact!r} looks like a file but names no committed file at {head} that can be verified"))
    text = "\n".join(_strings_of(evidence))
    shas = set()
    for match in PACK_FACT_SHA.finditer(text):
        token = match.group(0)
        before = text[max(0, match.start() - 12) : match.start()].lower()
        if re.search(r"\d", token) and re.search(r"[a-fA-F]", token) and not PACK_FACT_DIGEST_CONTEXT.search(before):
            shas.add(token.lower())
    for sha in sorted(shas):
        if _git_bytes(root, ["rev-parse", "--verify", "--quiet", f"{sha}^{{object}}"]) is None:
            findings.append(Finding("pack-facts", f"cited hexadecimal string {sha} does not resolve to a git object"))
    names = sorted(set(PACK_FACT_TEST.findall(text)))
    if names:
        listing = _git_bytes(root, ["grep", "-h", "-o", "-E", r"def test_[A-Za-z0-9_]+", head, "--", "*.py"])
        defined = {line.split()[-1] for line in listing.decode("utf-8", "replace").splitlines()} if listing else set()
        files = _git_bytes(root, ["ls-tree", "-r", "--name-only", head])
        modules = {Path(line).stem for line in files.decode("utf-8", "replace").splitlines() if line.endswith(".py")} if files else set()
        defined |= modules
        for name in names:
            if name not in defined:
                findings.append(Finding("pack-facts", f"cited test {name} is not defined in a tracked Python file at {head}"))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        evidence = load_json(root, args.evidence)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"FAIL [input] {exc}")
        return 1
    findings = check_pack_facts(evidence, root, args.head)
    for finding in findings:
        print(f"FAIL [{finding.check}] {finding.message}")
    if findings:
        return 1
    print("PASS: requested AIDF checks completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
