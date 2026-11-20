"""Build the finding-level table of the committed review reports (strategy/AIDF-REVIEW-EFFICIENCY-PROPOSAL.md, "How we would know it worked").

Reads the committed blobs of a revision (default HEAD) and writes one row per finding that a report numbers. Everything is a
pattern match on the report text. Nothing is interpreted by hand: the columns marked "method" say how a value was obtained, and
a row the patterns could not classify says so. Use the table to count, and read the report line before relying on one row.

    python verification/review_finding_table.py --out verification/review-finding-table.csv [--rev HEAD] [--summary]
"""

import argparse
import collections
import csv
import json
import pathlib
import re
import subprocess
import sys

NAME = re.compile(
    r"^(?P<change>.+?)-(?P<kind>verifier-report|security-review|security-report|distinct-security-review)"
    r"(?:-round(?P<round>\d+))?\.md$"
)
START = re.compile(
    r"^\s*(?:[#>*\-|]+\s*)*(?:\*\*)?`?(?P<id>[A-Z]{1,4}\d{0,3}-\d{2,3}\b|Finding \d+|Blocker \d+)"
)
BARE = re.compile(r"^\s*(?:#{1,6}\s+|\|\s*|\*\*|-\s+\*\*)`?(?P<id>[A-Z]{1,3}\d{1,2})\b(?![-/])")
HEADING = re.compile(r"^#{1,6}\s+(?P<text>.+)$")
CARRY = re.compile(r"status of|previous|prior|earlier|carried|round \d+ finding|disposition|re-?check", re.IGNORECASE)
CLOSED = re.compile(r"\b(closed|fixed|resolved|confirmed_fixed|still open|unresolved|withdrawn)\b", re.IGNORECASE)
IGNORED_PREFIXES = ("SHA", "MR", "RFC", "CWE", "TLS", "UTF", "PEM")
ID_ANYWHERE = re.compile(r"\b[A-Z]{1,4}\d{0,3}-\d{2,3}\b")
RECORD_WORDS = re.compile(
    r"evidence[- ]pack|disposition|\bclaims?\b|wording|history|stale|inaccurate|overstat|misstat|prose|sentence|narrative",
    re.IGNORECASE,
)
OUTCOME = re.compile(r"\b(outcome|verdict|blocked|blocking|blocker)\b", re.IGNORECASE)
PATH = re.compile(r"[\w./-]+\.(?:py|md|json|yml|yaml|sh|csv|toml)\b")
SEVERITY = re.compile(
    r"\b(non-blocking|advisory|blocker|blocking|critical|high|major|medium|minor|low|rank[- ]?[1-4])\b", re.IGNORECASE
)
NOT_BLOCKING = re.compile(r"non-blocking|advisory|\blow\b|minor", re.IGNORECASE)
BLOCKING = re.compile(r"blocker|blocking|critical|\bhigh\b|major|rank[- ]?[12]\b", re.IGNORECASE)
COLUMNS = [
    "change",
    "role",
    "round",
    "path",
    "finding_id",
    "line",
    "section",
    "carry_over",
    "severity_word",
    "blocking",
    "in_outcome",
    "type_auto",
    "type_method",
    "type_checked",
    "paths_cited",
    "title",
]


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8").stdout


TRACKED = ()
# Titles quote report text, which may name a private host or show how a test splits a literal to hide one; neither is kept.
PRIVATE_HOST = re.compile(r"\b[\w.-]+\.home\b")
SPLIT_LITERAL = re.compile(r"""(["'])[^"']{0,24}\1(?:\s*\+\s*(["'])[^"']{0,24}\2)+""")
LOCAL_PATH = re.compile(r"[A-Za-z]:[\\/]+\S*|\b[Uu]sers/\w+/\S*|/(?:home|Users)/\w+/\S*")


def resolve(found):
    """Map the file names a finding cites to tracked repository paths; a name that is not a tracked file is dropped."""
    names = {p.strip("./") for p in found}
    return sorted({t for t in TRACKED for n in names if n and (t == n or t.endswith("/" + n) or n.endswith("/" + t))})


def scrub(text):
    """One line of title text, with local file-system paths replaced."""
    text = LOCAL_PATH.sub("[local path]", re.sub(r"\s+", " ", text))
    text = SPLIT_LITERAL.sub("[split string]", text)
    return PRIVATE_HOST.sub("[private host]", text)[:160]


def classify(paths):
    """Return (type, method) from the file names a finding cites."""
    if not paths:
        return "unclassified", "no file name cited"
    tests = [p for p in paths if "/tests/" in p or p.rsplit("/", 1)[-1].startswith("test_")]
    code = [p for p in paths if p.endswith((".py", ".sh", ".yml", ".yaml", ".toml")) and p not in tests]
    if code:
        return "code", "cites a non-test source file"
    if tests:
        return "tests", "cites a test file"
    return "record_text", "cites only documents, records or data files"


def json_findings(text):
    """Findings from canonical JSON records: a line that is a JSON array or object with "id" keys."""
    out = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.lstrip().startswith(("[{", "{\"")):
            continue
        try:
            data = json.loads(line)
        except ValueError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if not isinstance(item, dict) or "id" not in item:
                continue
            blocking = item.get("blocking")
            paths = resolve(PATH.findall(json.dumps(item)))
            kind, method = classify(paths)
            out.append(
                {
                    "finding_id": str(item["id"]),
                    "line": number,
                    "section": "canonical JSON record",
                    "carry_over": "no",
                    "severity_word": str(item.get("severity") or item.get("rank") or ""),
                    "blocking": {True: "yes", False: "no"}.get(blocking, "unknown"),
                    "type_auto": kind,
                    "type_method": method + " (canonical record)",
                    "paths_cited": ";".join(paths[:6]),
                    "title": scrub(str(item.get("title") or item.get("basis") or "")),
                }
            )
    return out


def carried(fid, head, section, round_no):
    """A numbered finding of an earlier round, or one the line reports as closed."""
    prefix = re.match(r"(?:R|SR)(\d+)-", fid)
    if prefix and round_no and int(prefix.group(1)) != round_no:
        return True
    status = head[head.find(fid) + len(fid) :][:60]
    return bool(CARRY.search(section) or CLOSED.search(status))


def findings_of(text, round_no=0):
    """Yield one dict per first occurrence of a finding id at the start of a line."""
    records = json_findings(text)
    if records:
        yield from records
        return
    lines = text.splitlines()
    section = ""
    starts = []
    seen = set()
    for number, line in enumerate(lines, 1):
        heading = HEADING.match(line)
        if heading:
            section = heading["text"].strip()
        match = START.match(line) or BARE.match(line)
        if match and (match["id"].startswith(IGNORED_PREFIXES) or len(set(ID_ANYWHERE.findall(line))) >= 3):
            match = None
        if match and match["id"] not in seen:
            seen.add(match["id"])
            starts.append((number, match["id"], section))
    for index, (number, fid, section) in enumerate(starts):
        end = starts[index + 1][0] - 1 if index + 1 < len(starts) else len(lines)
        for probe in range(number, end):
            if HEADING.match(lines[probe]) and probe + 1 > number:
                end = probe
                break
        block = "\n".join(lines[number - 1 : end])
        head = lines[number - 1].strip()
        near = " ".join(lines[number - 1 : number + 2])
        severity = SEVERITY.search(near)
        word = severity.group(1).lower() if severity else ""
        if NOT_BLOCKING.search(word):
            blocking = "no"
        elif BLOCKING.search(word):
            blocking = "yes"
        else:
            blocking = "unknown"
        paths = resolve(PATH.findall(block))
        kind, method = classify(paths)
        if RECORD_WORDS.search(head):
            kind, method = "record_text", "title names a pack, claim, wording or record"
        outside = [ln for i, ln in enumerate(lines, 1) if not number <= i < end]
        named = any(fid in ln and OUTCOME.search(ln) for ln in outside)
        yield {
            "in_outcome": "yes" if named else "no",
            "finding_id": fid,
            "line": number,
            "section": section,
            "carry_over": "yes" if carried(fid, head, section, round_no) else "no",
            "severity_word": word,
            "blocking": blocking,
            "type_auto": kind,
            "type_method": method,
            "paths_cited": ";".join(paths[:6]),
            "title": scrub(head),
        }


def rows_for(repo, rev):
    global TRACKED
    TRACKED = tuple(git(repo, "ls-tree", "-r", "--name-only", rev).splitlines())
    rows = []
    for rel in git(repo, "ls-files", "verification").splitlines():
        base = rel.rsplit("/", 1)[-1]
        match = NAME.match(base)
        if not match or not rel.endswith(".md") or "review-evidence" in rel:
            continue
        text = git(repo, "show", f"{rev}:{rel}")
        role = "verifier" if "verifier" in match["kind"] else "security"
        rnd = int(match["round"] or 1)
        found = list(findings_of(text, rnd))
        if not found:
            rows.append(
                {
                    "change": match["change"],
                    "role": role,
                    "round": rnd,
                    "path": rel,
                    "finding_id": "",
                    "type_auto": "none_found",
                    "type_method": "no numbered finding matched",
                }
            )
        for item in found:
            rows.append({"change": match["change"], "role": role, "round": rnd, "path": rel, **item})
    rows.sort(key=lambda r: (r["change"], r["role"], r["round"], r.get("line", 0)))
    return rows


def load_labels(path):
    """Hand labels: a CSV with path, finding_id and label columns. A missing file means no labels."""
    path = pathlib.Path(path)
    if not path.is_file():
        return {}
    with open(path, newline="", encoding="utf-8") as fh:
        return {(r["path"], r["finding_id"]): r["label"] for r in csv.DictReader(fh)}


def apply_labels(rows, labels):
    for row in rows:
        row["type_checked"] = labels.get((row["path"], row["finding_id"]), "") if row["finding_id"] else ""


def write(rows, out):
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, restval="", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def summary(rows):
    reports = {r["path"] for r in rows}
    own = [r for r in rows if r["finding_id"] and r["carry_over"] != "yes"]
    lines = [f"reports: {len(reports)}; finding rows: {len(rows)}; excluding carry-overs and empty reports: {len(own)}"]
    for label, pick in (("round 1-2", lambda r: r["round"] <= 2), ("round 3+", lambda r: r["round"] > 2)):
        part = [r for r in own if pick(r)]
        count = collections.Counter(r["type_auto"] for r in part)
        lines.append(f"{label}: {len(part)} findings; " + ", ".join(f"{k} {v}" for k, v in sorted(count.items())))
    for label, pick in (("round 1-2", lambda r: r["round"] <= 2), ("round 3+", lambda r: r["round"] > 2)):
        count = collections.Counter(r["type_checked"] for r in own if r["type_checked"] and pick(r))
        lines.append(f"hand-labelled {label}: " + ", ".join(f"{k} {v}" for k, v in sorted(count.items())))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=".")
    parser.add_argument("--rev", default="HEAD")
    parser.add_argument("--out", required=True)
    parser.add_argument("--labels", default=str(pathlib.Path(__file__).with_name("review-finding-labels.csv")))
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)
    rows = rows_for(args.repo, args.rev)
    apply_labels(rows, load_labels(args.labels))
    write(rows, pathlib.Path(args.out))
    print(f"wrote {len(rows)} rows to {args.out}")
    if args.summary:
        print(summary(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
