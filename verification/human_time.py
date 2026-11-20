"""Sum the human-time fields of a dispositions file (metrics/definitions.md, "Human minutes, computation").

A request is a `Requested (UTC)` line followed by an `Answered (UTC)` line, optionally with an `Active minutes (manual)` line
before the next request. The elapsed time is an upper bound on waiting, not on effort. A request without both timestamps, or
with one that does not parse, is counted as unknown and adds nothing to any total.

    python verification/human_time.py <dispositions file> [more files]
"""

import argparse
import datetime
import pathlib
import re
import sys

FIELD = re.compile(r"^\W*(Requested \(UTC\)|Answered \(UTC\)|Active minutes \(manual\))\W*:\W*(?P<value>.*?)\s*$", re.IGNORECASE)
KEYS = {"requested (utc)": "requested", "answered (utc)": "answered", "active minutes (manual)": "manual"}


def parse_time(text):
    try:
        value = datetime.datetime.fromisoformat(text.strip().strip("*` ").replace("Z", "+00:00"))
    except ValueError:
        return None
    return value if value.tzinfo is not None else None


def requests_of(text):
    """Return one dict per request: requested, answered, manual (each None when absent or unparsable)."""
    found = []
    seen = []  # the field names already read for each request
    for line in text.splitlines():
        match = FIELD.match(line.replace("**", ""))
        if not match:
            continue
        key = KEYS[match.group(1).lower()]
        value = match.group("value")
        if key == "requested":
            found.append({"requested": parse_time(value), "answered": None, "manual": None, "manual_given": False})
            seen.append({"requested"})
            continue
        if not found or key in seen[-1]:
            # an answer or minutes with no open request is a request whose start is unknown
            found.append({"requested": None, "answered": None, "manual": None, "manual_given": False})
            seen.append(set())
        seen[-1].add(key)
        if key == "answered":
            found[-1]["answered"] = parse_time(value)
        else:
            found[-1]["manual_given"] = True
            found[-1]["manual"] = float(value) if re.fullmatch(r"\d+(?:\.\d+)?", value) else None
    return found


def summarize(requests):
    known = [r for r in requests if r["requested"] and r["answered"] and r["answered"] >= r["requested"]]
    upper = sum((r["answered"] - r["requested"]).total_seconds() for r in known) / 60
    manual = [r["manual"] for r in requests if r["manual"] is not None]
    return {
        "requests": len(requests),
        "unknown": len(requests) - len(known),
        "upper_bound_minutes": round(upper, 1),
        "manual_minutes": round(sum(manual), 1),
        "manual_reported": len(manual),
        "manual_unreadable": sum(1 for r in requests if r["manual_given"] and r["manual"] is None),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+")
    args = parser.parse_args(argv)
    requests = []
    for name in args.files:
        requests.extend(requests_of(pathlib.Path(name).read_text(encoding="utf-8")))
    total = summarize(requests)
    print(
        f"requests {total['requests']}; unknown {total['unknown']}; upper bound {total['upper_bound_minutes']} min "
        f"(waiting, not effort); manual {total['manual_minutes']} min over {total['manual_reported']} requests; "
        f"{total['manual_unreadable']} manual values unreadable or unknown"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
