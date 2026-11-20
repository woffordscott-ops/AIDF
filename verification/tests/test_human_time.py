"""Tests for verification/human_time.py."""

import importlib.util
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SPEC = importlib.util.spec_from_file_location("human_time", ROOT / "verification" / "human_time.py")
H = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(H)

TEXT = """## Approval 1
- **Requested (UTC):** 2026-10-30T10:00:00Z
- **Answered (UTC):** 2026-10-30T10:30:00Z
- **Active minutes (manual):** 5

## Approval 2
- **Requested (UTC):** 2026-10-30T12:00:00Z
- **Answered (UTC):** 2026-10-30T12:10:00+00:00

## Approval 3
- **Requested (UTC):** 2026-10-30T14:00:00Z
- **Requested (UTC):** not a time
- **Answered (UTC):** 2026-10-30T14:05:00Z
- **Active minutes (manual):** about ten
"""


class HumanTimeTests(unittest.TestCase):
    def test_upper_bound_and_manual_minutes(self):
        total = H.summarize(H.requests_of(TEXT)[:2])
        self.assertEqual(total["requests"], 2)
        self.assertEqual(total["unknown"], 0)
        self.assertEqual(total["upper_bound_minutes"], 40.0)
        self.assertEqual((total["manual_minutes"], total["manual_reported"]), (5.0, 1))

    def test_missing_or_unparsable_values_are_unknown_not_zero(self):
        requests = H.requests_of(TEXT)
        self.assertEqual(len(requests), 4)  # approval 3 has two Requested lines, so it is two requests
        total = H.summarize(requests)
        self.assertEqual(total["unknown"], 2)
        self.assertEqual(total["upper_bound_minutes"], 40.0)

    def test_naive_timestamps_and_reversed_order_are_unknown(self):
        naive = "Requested (UTC): 2026-10-30T10:00:00\nAnswered (UTC): 2026-10-30T10:30:00Z\n"
        self.assertEqual(H.summarize(H.requests_of(naive))["unknown"], 1)
        reversed_ = "Requested (UTC): 2026-10-30T10:30:00Z\nAnswered (UTC): 2026-10-30T10:00:00Z\n"
        self.assertEqual(H.summarize(H.requests_of(reversed_))["unknown"], 1)

    def test_an_answer_with_no_request_is_one_unknown_request(self):
        found = H.requests_of("Answered (UTC): 2026-10-30T10:30:00Z\n")
        self.assertEqual((H.summarize(found)["requests"], H.summarize(found)["unknown"]), (1, 1))
        twice = H.requests_of("Requested (UTC): 2026-10-30T10:00:00Z\nAnswered (UTC): 2026-10-30T10:10:00Z\nAnswered (UTC): 2026-10-30T11:00:00Z\n")
        self.assertEqual((H.summarize(twice)["requests"], H.summarize(twice)["unknown"]), (2, 1))

    def test_unreadable_manual_values_are_reported_not_dropped(self):
        text = (
            "Requested (UTC): 2026-10-30T10:00:00Z\nActive minutes (manual): 2.5 min\n"
            "Requested (UTC): 2026-10-30T11:00:00Z\nActive minutes (manual): 3\n"
            "Requested (UTC): 2026-10-30T12:00:00Z\nActive minutes (manual): about 3\n"
        )
        total = H.summarize(H.requests_of(text))
        self.assertEqual((total["manual_minutes"], total["manual_reported"], total["manual_unreadable"]), (3.0, 1, 2))

    def test_command_line_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "d.md"
            path.write_text(TEXT, encoding="utf-8")
            out = StringIO()
            with redirect_stdout(out):
                self.assertEqual(H.main([str(path)]), 0)
        self.assertIn("upper bound 40.0 min", out.getvalue())
        self.assertIn("waiting, not effort", out.getvalue())


if __name__ == "__main__":
    unittest.main()
