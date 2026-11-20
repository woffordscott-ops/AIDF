"""Replay the record-text rule of core/05-review.md section 4 on the hand-labelled findings of the finding table
(findings blocking by label or named in a round's outcome; the `blocking` column itself is not read).

A report whose labelled blocking findings are all `record_text` would have had no blocking finding under the rule, apart from the
four exceptions the rule keeps (an overstated guarantee, a missing required artifact, a wrong SHA or digest a gate uses, a record
that contradicts code or tests). The replay does not apply the exceptions, so its count is an upper bound on the rounds avoided.

    python verification/review_rule_replay.py [verification/review-finding-table.csv]
"""

import collections
import csv
import pathlib
import sys

DEFAULT = pathlib.Path(__file__).with_name("review-finding-table.csv")


def replay(rows):
    """Return counts of labelled reports by band (rounds 1-2, 3+) and by whether every labelled finding is record text."""
    by_report = collections.defaultdict(list)
    for row in rows:
        label = row.get("type_checked", "")
        if label and label not in ("not_a_finding", "unsure"):
            by_report[(row["path"], int(row["round"]))].append(label)
    counts = collections.Counter()
    for (_path, rnd), labels in by_report.items():
        band = "3+" if rnd > 2 else "1-2"
        counts[(band, "record_only" if set(labels) == {"record_text"} else "other")] += 1
    return counts


def main(argv=None):
    path = pathlib.Path((argv or sys.argv[1:] or [DEFAULT])[0])
    with open(path, newline="", encoding="utf-8") as fh:
        counts = replay(csv.DictReader(fh))
    for band in ("1-2", "3+"):
        record_only, other = counts[(band, "record_only")], counts[(band, "other")]
        print(f"rounds {band}: {record_only + other} reports with labelled findings; {record_only} had only record text; {other} had other types")
    return 0


if __name__ == "__main__":
    sys.exit(main())
