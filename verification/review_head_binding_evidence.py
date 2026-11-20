"""Counterfactual evidence for the review-outcome-record comparison in core/05-review.md section 6.

This is evidence for spec/AIDF-REVIEW-HEAD-BINDING-TASK-CONTRACT.md, not a protected gate. compare() is the
comparison the section describes; main() builds throwaway repositories and shows that it accepts the shapes
the section allows and rejects, one by one, the shapes it must not allow. Standard library only, plus the
strict JSON loader of aidf_check.py so that this comparison and the repository's gates parse JSON the same way.
"""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aidf_check import _strict_json_loads

MAX_REPORT_BYTES = 1 << 20
SECURITY_EVIDENCE_FIELDS = ("status", "artifact", "artifact_sha256", "coverage_boundary")

DECL = {
    "review_reports": ["verification/x-verifier-report-round*.md", "verification/x-security-review-round*.md"],
    "security_reports": ["verification/x-security-review-round*.md"],
    "dispositions": "verification/x-dispositions.md",
    "pack": "verification/x-evidence-pack.json",
    "contract": "verification/x-task-contract.json",
}


def git(repo, *args, check=True, inp=None):
    done = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t",
                           "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", *args],
                          capture_output=True, input=inp, check=False)
    if check and done.returncode:
        raise RuntimeError(done.stderr.decode("utf-8", "replace"))
    return done


def text(done):
    return done.stdout.decode("utf-8").strip()


def blob(repo, sha):
    return git(repo, "cat-file", "blob", sha).stdout


def matches(path, patterns):
    """A declared pattern: '*' matches within one path segment; matching is case-sensitive."""
    return any(re.fullmatch("[^/]*".join(re.escape(part) for part in pattern.split("*")), path) for pattern in patterns)


def report_problem(data):
    if not data:
        return "is empty"
    if len(data) > MAX_REPORT_BYTES:
        return "is larger than the report size limit"
    if b"\0" in data:
        return "contains a NUL byte"
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return "is not UTF-8 text"
    return None


def canonical(value):
    """A form in which two parsed values are equal only if their JSON texts are equal up to object key order and
    whitespace: 1, 1.0 and true stay different, and array order is kept."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def parse(data):
    if len(data) > MAX_REPORT_BYTES:
        raise ValueError("larger than the size limit")
    doc = _strict_json_loads(data.decode("utf-8"))
    if not isinstance(doc, dict):
        raise TypeError("not a JSON object")
    return doc


def compare(repo, r, h, decl):
    """Differences between R and H that are not outcome records. An empty list means H is covered."""
    if git(repo, "merge-base", "--is-ancestor", r, h, check=False).returncode:
        return ["R is not an ancestor of H"]
    found = []
    added = {}
    modified = {}
    parts = git(repo, "diff-tree", "-r", "-z", "--no-renames", "--raw", r, h).stdout.split(b"\0")
    for meta, raw_path in zip(parts[0::2], parts[1::2]):
        old_mode, new_mode, old_sha, new_sha, status = meta.decode().lstrip(":").split(" ")
        path = raw_path.decode("utf-8", "surrogateescape")
        if status == "A" and matches(path, decl["review_reports"]):
            if new_mode != "100644":
                found.append(f"report {path} is not a regular file (mode {new_mode})")
                continue
            data = blob(repo, new_sha)
            problem = report_problem(data)
            if problem:
                found.append(f"report {path} {problem}")
            else:
                added[path] = data
        elif status == "M" and path in (decl["dispositions"], decl["pack"], decl["contract"]):
            if old_mode != "100644" or new_mode != "100644":
                found.append(f"mode change on {path}")
            else:
                modified[path] = (blob(repo, old_sha), blob(repo, new_sha))
        else:
            found.append(f"not an outcome record: {status} {path}")
    if decl["dispositions"] in modified:
        old, new = modified[decl["dispositions"]]
        if not new.startswith(old):
            found.append("dispositions file changes bytes before its end")
        elif old and not old.endswith(b"\n"):
            found.append("dispositions file did not end with a newline before the append")
        elif report_problem(new[len(old):]):
            found.append(f"appended dispositions bytes {report_problem(new[len(old):])}")
    if decl["pack"] in modified:
        found += compare_pack(modified[decl["pack"]], added, decl)
    if decl["contract"] in modified:
        found += compare_contract(modified[decl["contract"]], added)
    return found


def security_part(doc):
    section = doc.get("security_evidence")
    return section if isinstance(section, dict) else {}


def compare_pack(pair, added, decl):
    try:
        old, new = parse(pair[0]), parse(pair[1])
    except (TypeError, ValueError) as exc:
        return [f"evidence pack cannot be parsed strictly: {exc}"]
    fields_old = {k: security_part(old)[k] for k in SECURITY_EVIDENCE_FIELDS if k in security_part(old)}
    fields_new = {k: security_part(new)[k] for k in SECURITY_EVIDENCE_FIELDS if k in security_part(new)}
    for doc in (old, new):
        for key in SECURITY_EVIDENCE_FIELDS:
            security_part(doc).pop(key, None)
    if canonical(old) != canonical(new):
        return ["evidence pack changes outside the declared security_evidence fields"]
    if canonical(fields_old) == canonical(fields_new):
        return []
    found = []
    artifact = fields_new.get("artifact")
    if fields_new.get("status") != "passed":
        found.append("security_evidence.status is not passed")
    if not isinstance(artifact, str) or artifact not in added or not matches(artifact, decl["security_reports"]):
        found.append("security_evidence.artifact is not a security report added between R and H")
    elif fields_new.get("artifact_sha256") != hashlib.sha256(added[artifact]).hexdigest():
        found.append("security_evidence.artifact_sha256 is not the hash of that committed report")
    boundary = fields_new.get("coverage_boundary")
    if not isinstance(boundary, str) or not boundary.strip():
        found.append("security_evidence.coverage_boundary is empty")
    return found


def compare_contract(pair, added):
    try:
        old, new = parse(pair[0]), parse(pair[1])
    except (TypeError, ValueError) as exc:
        return [f"contract cannot be parsed strictly: {exc}"]
    scope_old, scope_new = old.pop("declared_scope", None), new.pop("declared_scope", None)
    found = []
    if canonical(old) != canonical(new):
        found.append("contract changes outside declared_scope")
    lists = isinstance(scope_old, list) and isinstance(scope_new, list)
    if not lists or not all(isinstance(entry, str) for entry in scope_old + scope_new) or len(set(scope_new)) != len(scope_new):
        return found + ["declared_scope is not a list of distinct strings"]
    if scope_new[:len(scope_old)] != scope_old:
        found.append("declared_scope entries were removed, changed or reordered")
    for entry in scope_new[len(scope_old):]:
        if entry not in added:
            found.append(f"declared_scope gains {entry!r}, which is not a report added between R and H")
    return found


def write(repo, rel, content, newline="\n"):
    path = Path(repo, rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline=newline)


def base_repo(tmp, dispositions="# Dispositions\n\nA-1 fixed.\n"):
    git(tmp, "init", "-q", "-b", "main")
    git(tmp, "config", "core.ignorecase", "false")
    pack = {"e3": {"artifact": "all mutants caught"}, "residual_risk": "limits", "n": 1, "flag": False,
            "security_evidence": {"status": "pending", "artifact": "none", "artifact_sha256": "", "coverage_boundary": "", "note": 1}}
    contract = {"schema_version": 1, "change_id": "x", "declared_scope": ["app/**", "lib/**"],
                "acceptance_criteria": [{"id": "AC1", "text": "t"}, {"id": "AC2", "text": "u"}]}
    write(tmp, "app.py", "print(1)\n")
    write(tmp, DECL["pack"], json.dumps(pack, indent=2) + "\n")
    write(tmp, DECL["contract"], json.dumps(contract, indent=2) + "\n")
    write(tmp, DECL["dispositions"], dispositions)
    write(tmp, "verification/x-verifier-report-round1.md", "report one\n")
    git(tmp, "add", "-A")
    git(tmp, "commit", "-q", "-m", "reviewed content")
    return text(git(tmp, "rev-parse", "HEAD"))


def read(tmp, rel):
    return Path(tmp, rel).read_text(encoding="utf-8")


def edit_json(tmp, rel, fn):
    doc = json.loads(read(tmp, rel))
    fn(doc)
    write(tmp, rel, json.dumps(doc, indent=2) + "\n")


SECURITY = "verification/x-security-review-round2.md"
SECURITY_TEXT = "security\n"
SECURITY_SHA = hashlib.sha256(SECURITY_TEXT.encode()).hexdigest()


def fill(doc, artifact=SECURITY, sha=SECURITY_SHA, status="passed", boundary="fixture"):
    doc["security_evidence"].update(status=status, artifact=artifact, artifact_sha256=sha, coverage_boundary=boundary)


def index_entry(tmp, mode, data, path):
    sha = text(git(tmp, "hash-object", "-w", "--stdin", inp=data)) if data is not None else "a" * 40
    git(tmp, "update-index", "--add", "--cacheinfo", f"{mode},{sha},{path}")


def report2(tmp):
    write(tmp, "verification/x-verifier-report-round2.md", "report two\n")


def full_set(tmp):
    write(tmp, SECURITY, SECURITY_TEXT)
    write(tmp, DECL["dispositions"], read(tmp, DECL["dispositions"]) + "A-2 fixed.\n")
    edit_json(tmp, DECL["pack"], fill)
    edit_json(tmp, DECL["contract"], lambda c: c["declared_scope"].append(SECURITY))


def with_security(tmp, mutate):
    write(tmp, SECURITY, SECURITY_TEXT)
    edit_json(tmp, DECL["pack"], mutate)


def pack_reordered(tmp):
    doc = json.loads(read(tmp, DECL["pack"]))
    write(tmp, DECL["pack"], json.dumps(dict(reversed(list(doc.items()))), indent=4) + "\n", newline="\r\n")


def raw_replace(tmp, rel, old, new):
    content = read(tmp, rel)
    assert old in content
    write(tmp, rel, content.replace(old, new, 1))


def stage_mode(path):
    return lambda tmp: git(tmp, "update-index", "--chmod=+x", path)


def stage_entry(mode, data, path):
    return lambda tmp: index_entry(tmp, mode, data, path)


def rename_onto_report(tmp):
    Path(tmp, "app.py").rename(Path(tmp, "verification/x-verifier-report-round2.md"))


def nothing(tmp):
    return None


def pack_edit(fn):
    return lambda tmp: edit_json(tmp, DECL["pack"], fn)


def contract_edit(fn):
    return lambda tmp: edit_json(tmp, DECL["contract"], fn)


def put(rel, content):
    return lambda tmp: write(tmp, rel, content)


# (name, working-tree step, covered?, index step after "git add -A")
SCENARIOS = [
    ("report file added by itself", report2, True, None),
    ("report + dispositions append + security_evidence fill + scope addition", full_set, True, None),
    ("pack rewritten with the same values: key order, indent, CRLF", pack_reordered, True, None),
    ("code changed", put("app.py", "print(2)\n"), False, None),
    ("existing pack sentence changed", pack_edit(lambda p: p["e3"].update(artifact="no mutant passed")), False, None),
    ("security_evidence fill plus another pack field", lambda t: with_security(t, lambda p: (fill(p), p.update(residual_risk="changed"))), False, None),
    ("extra key inside security_evidence", pack_edit(lambda p: p["security_evidence"].update(note="extra")), False, None),
    ("existing dispositions line changed", put(DECL["dispositions"], "# Dispositions\n\nA-1 not fixed.\n"), False, None),
    ("dispositions line deleted", put(DECL["dispositions"], "# Dispositions\n"), False, None),
    ("dispositions line inserted before an existing line", put(DECL["dispositions"], "# Dispositions\n\nINSERTED.\nA-1 fixed.\n"), False, None),
    ("dispositions line prepended", put(DECL["dispositions"], "INSERTED.\n# Dispositions\n\nA-1 fixed.\n"), False, None),
    ("dispositions file converted to CRLF", lambda t: write(t, DECL["dispositions"], read(t, DECL["dispositions"]), newline="\r\n"), False, None),
    ("extra file", put("notes.md", "note\n"), False, None),
    ("existing report file modified", put("verification/x-verifier-report-round1.md", "report one, edited\n"), False, None),
    ("report at an undeclared path", put("verification/other-report.md", "report\n"), False, None),
    ("report in a nested path below a declared pattern", put("verification/x-verifier-report-round2/not-a-report.md", "r\n"), False, None),
    ("empty report", put("verification/x-verifier-report-round2.md", ""), False, None),
    ("binary report", lambda t: Path(t, "verification/x-verifier-report-round2.md").write_bytes(b"\0\1\2binary"), False, None),
    ("report as a symlink", nothing, False, stage_entry("120000", b"app.py", "verification/x-verifier-report-round2.md")),
    ("report as a gitlink", nothing, False, stage_entry("160000", None, "verification/x-verifier-report-round2.md")),
    ("report path differing only in case", nothing, False, stage_entry("100644", b"report\n", "verification/X-VERIFIER-REPORT-ROUND2.MD")),
    ("report added as an executable", report2, False, stage_mode("verification/x-verifier-report-round2.md")),
    ("mode change on the dispositions file", nothing, False, stage_mode(DECL["dispositions"])),
    ("mode change on the evidence pack", nothing, False, stage_mode(DECL["pack"])),
    ("mode change on the contract", nothing, False, stage_mode(DECL["contract"])),
    ("duplicate key hides a changed pack sentence", lambda t: raw_replace(t, DECL["pack"], '"residual_risk": "limits"', '"residual_risk": "waived", "residual_risk": "limits"'), False, None),
    ("duplicate key hides a changed acceptance criterion", lambda t: raw_replace(t, DECL["contract"], '"text": "t"', '"text": "weaker", "text": "t"'), False, None),
    ("pack whose root is an array", put(DECL["pack"], "[]\n"), False, None),
    ("contract whose root is an array", put(DECL["contract"], "[]\n"), False, None),
    ("pack with a trailing comma", lambda t: raw_replace(t, DECL["pack"], '"residual_risk": "limits"', '"residual_risk": "limits",'), False, None),
    ("contract criterion changed", contract_edit(lambda c: c["acceptance_criteria"][0].update(text="weaker")), False, None),
    ("declared_scope entry removed", contract_edit(lambda c: c["declared_scope"].clear()), False, None),
    ("declared_scope reordered", contract_edit(lambda c: c["declared_scope"].reverse()), False, None),
    ("declared_scope reordered and a report path added", lambda t: (write(t, "verification/x-verifier-report-round2.md", "r"), edit_json(t, DECL["contract"], lambda c: (c["declared_scope"].reverse(), c["declared_scope"].append("verification/x-verifier-report-round2.md")))), False, None),
    ("declared_scope entry is an object", contract_edit(lambda c: c["declared_scope"].append({"a": 1})), False, None),
    ("pack value 1 becomes true", pack_edit(lambda p: p.update(n=True)), False, None),
    ("pack value 1 becomes 1.0", pack_edit(lambda p: p.update(n=1.0)), False, None),
    ("pack value false becomes 0", pack_edit(lambda p: p.update(flag=0)), False, None),
    ("security_evidence extra key 1 becomes true", pack_edit(lambda p: p["security_evidence"].update(note=True)), False, None),
    ("contract schema_version 1 becomes true", contract_edit(lambda c: c.update(schema_version=True)), False, None),
    ("contract schema_version 1 becomes 1.0", contract_edit(lambda c: c.update(schema_version=1.0)), False, None),
    ("contract acceptance criteria reordered", contract_edit(lambda c: c["acceptance_criteria"].reverse()), False, None),
    ("declared_scope gains KERNEL.md", contract_edit(lambda c: c["declared_scope"].append("KERNEL.md")), False, None),
    ("declared_scope gains a wildcard", contract_edit(lambda c: c["declared_scope"].append("**")), False, None),
    ("declared_scope gains a report path that was not added", contract_edit(lambda c: c["declared_scope"].append("verification/x-verifier-report-round9.md")), False, None),
    ("fill names a URL as the artifact", lambda t: with_security(t, lambda p: fill(p, artifact="https://example.invalid/r")), False, None),
    ("fill names app.py as the artifact", lambda t: with_security(t, lambda p: fill(p, artifact="app.py")), False, None),
    ("fill carries the wrong hash", lambda t: with_security(t, lambda p: fill(p, sha="a" * 64)), False, None),
    ("fill leaves status pending", lambda t: with_security(t, lambda p: fill(p, status="pending")), False, None),
    ("fill names a Verifier report as the Security artifact", pack_edit(lambda p: fill(p, artifact="verification/x-verifier-report-round1.md", sha=hashlib.sha256(b"report one\n").hexdigest())), False, None),
    ("fill with an empty coverage boundary", lambda t: with_security(t, lambda p: fill(p, boundary=" ")), False, None),
    ("file deleted", lambda t: Path(t, "app.py").unlink(), False, None),
    ("file renamed onto a report path", rename_onto_report, False, None),
]


def run_one(fn, stage, **base):
    with tempfile.TemporaryDirectory() as tmp:
        r = base_repo(tmp, **base)
        fn(tmp)
        git(tmp, "add", "-A")
        if stage:
            stage(tmp)
        git(tmp, "commit", "-q", "-m", "after review")
        return compare(tmp, r, text(git(tmp, "rev-parse", "HEAD")), DECL)


def commit(tmp, message):
    git(tmp, "add", "-A")
    git(tmp, "commit", "-q", "-m", message)


def run_chain():
    """R -> C1 (report) -> C2 (fill): both commits are outcome records, so R..C2 is covered."""
    with tempfile.TemporaryDirectory() as tmp:
        r = base_repo(tmp)
        write(tmp, SECURITY, SECURITY_TEXT)
        commit(tmp, "c1")
        edit_json(tmp, DECL["pack"], fill)
        commit(tmp, "c2")
        return compare(tmp, r, text(git(tmp, "rev-parse", "HEAD")), DECL)


def run_not_ancestor():
    with tempfile.TemporaryDirectory() as tmp:
        base_repo(tmp)
        git(tmp, "checkout", "-q", "-b", "side")
        report2(tmp)
        commit(tmp, "side")
        side = text(git(tmp, "rev-parse", "HEAD"))
        git(tmp, "checkout", "-q", "main")
        write(tmp, "verification/x-verifier-report-round3.md", "report three\n")
        commit(tmp, "main moves")
        return compare(tmp, side, text(git(tmp, "rev-parse", "HEAD")), DECL)


def run_merge(code_on_side):
    """A merge whose tree adds only a report is covered; one whose tree carries a code change is not."""
    with tempfile.TemporaryDirectory() as tmp:
        r = base_repo(tmp)
        git(tmp, "checkout", "-q", "-b", "side")
        if code_on_side:
            write(tmp, "app.py", "print(2)\n")
        else:
            report2(tmp)
        commit(tmp, "side")
        git(tmp, "checkout", "-q", "main")
        write(tmp, "verification/x-verifier-report-round3.md", "report three\n")
        commit(tmp, "main")
        git(tmp, "merge", "-q", "--no-ff", "-m", "merge", "side")
        return compare(tmp, r, text(git(tmp, "rev-parse", "HEAD")), DECL)


def run_exact_revert():
    """A code change followed by its exact revert leaves no code difference between R and H."""
    with tempfile.TemporaryDirectory() as tmp:
        r = base_repo(tmp)
        write(tmp, "app.py", "print(2)\n")
        commit(tmp, "code")
        write(tmp, "app.py", "print(1)\n")
        commit(tmp, "revert")
        report2(tmp)
        commit(tmp, "report")
        return compare(tmp, r, text(git(tmp, "rev-parse", "HEAD")), DECL)


def run_unterminated_append():
    """An append to a dispositions file whose last line had no newline would extend that line."""
    return run_one(put(DECL["dispositions"], "# Dispositions\n\nA-1 fixed.A-2.\n"), None,
                   dispositions="# Dispositions\n\nA-1 fixed.")


def leaves(value, path=()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from leaves(child, path + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from leaves(child, path + (index,))
    else:
        yield path, value


def variants(value):
    if isinstance(value, bool):
        return [int(value), str(value).lower(), None]
    if isinstance(value, int):
        return [bool(value), float(value), value + 1, str(value), None]
    if isinstance(value, float):
        return [int(value), value + 1.0, str(value), None]
    if value is None:
        return [0, False, "", "null"]
    return [value + "x", "", None, 0, True]


def set_at(doc, path, new):
    node = doc
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = new


def property_check():
    """Every leaf of a rich pack and contract, replaced by every variant of another type or value, must be refused;
    a pure reordering of object keys must be accepted. Returns (cases, wrong)."""
    pack = {"a": {"b": [1, 2.5, True, None, "s", {"c": 0}]}, "residual_risk": "r", "n": 1,
            "security_evidence": {"status": "pending", "artifact": "none", "artifact_sha256": "", "coverage_boundary": "",
                                  "note": 1, "list": [False]}}
    contract = {"schema_version": 1, "change_id": "x", "declared_scope": ["a/**"], "k": [1, [2, {"z": 3}]],
                "acceptance_criteria": [{"id": "AC1", "text": "t"}, {"id": "AC2", "text": "u"}]}
    cases = wrong = 0
    for name, doc, check in (("pack", pack, lambda o, n: compare_pack((o, n), {}, DECL)),
                             ("contract", contract, lambda o, n: compare_contract((o, n), {}))):
        old = json.dumps(doc).encode()
        for path, value in leaves(doc):
            if name == "pack" and path[0] == "security_evidence" and path[-1] in SECURITY_EVIDENCE_FIELDS:
                continue
            if name == "contract" and path[0] == "declared_scope":
                continue
            for variant in variants(value):
                changed = json.loads(old)
                set_at(changed, path, variant)
                cases += 1
                if not check(old, json.dumps(changed).encode()):
                    wrong += 1
                    print(f"WRONG {name} {path} {value!r} -> {variant!r} accepted")
        reordered = json.dumps(dict(reversed(list(doc.items())))).encode()
        cases += 1
        if check(old, reordered):
            wrong += 1
            print(f"WRONG {name} key reorder rejected")
    # a JSON null is not the same as an absent key, in either direction, for each security_evidence field
    for key in SECURITY_EVIDENCE_FIELDS:
        present = json.loads(json.dumps(pack))
        present["security_evidence"][key] = None
        absent = json.loads(json.dumps(pack))
        del absent["security_evidence"][key]
        for before, after in ((present, absent), (absent, present)):
            cases += 1
            if not compare_pack((json.dumps(before).encode(), json.dumps(after).encode()), {}, DECL):
                wrong += 1
                print(f"WRONG pack security_evidence.{key} null and absent treated as equal")
    return cases, wrong


def main():
    failures = 0
    results = [(name, run_one(fn, stage), covered) for name, fn, covered, stage in SCENARIOS]
    results += [("two successive outcome-record commits", run_chain(), True),
                ("merge whose tree adds only a report", run_merge(False), True),
                ("code change followed by its exact revert, then a report", run_exact_revert(), True),
                ("merge whose tree carries a code change", run_merge(True), False),
                ("append to a dispositions file with no final newline", run_unterminated_append(), False),
                ("R is not an ancestor of H", run_not_ancestor(), False)]
    for name, found, should_pass in results:
        ok = (not found) == should_pass
        failures += not ok
        print(f"{'OK   ' if ok else 'WRONG'} {'covered ' if not found else 'rejected'} {name}" + (f"  [{found[0]}]" if found else ""))
    cases, wrong = property_check()
    failures += wrong
    print(f"{cases} leaf-mutation cases over a rich pack and contract, {wrong} wrong")
    print(f"{len(results)} scenarios, {failures} wrong")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
