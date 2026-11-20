"""Presence tests for the approver's opening of the T2/T3 Task Contract (spec/AIDF-TASK-CONTRACT-OPENING-TASK-CONTRACT.md)."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEADINGS = ("Read this first", "Problem", "Why it matters", "The change", "Technical details", "What you need to decide")


def normal(path: str) -> str:
    return " ".join((ROOT / path).read_text(encoding="utf-8").split())


class OpeningTemplateTests(unittest.TestCase):
    def test_the_opening_comes_before_part_a(self) -> None:
        text = normal("templates/task-contract.md")
        self.assertIn("## Approver's opening (T2/T3 only", text)
        self.assertLess(text.index("## Approver's opening"), text.index("## Part A"))

    def test_the_six_headings_are_present_in_order(self) -> None:
        text = normal("templates/task-contract.md")
        block = text[text.index("## Approver's opening"):text.index("## Part A")]
        positions = [block.index(f"- **{name}**") for name in HEADINGS]
        self.assertEqual(positions, sorted(positions))

    def test_each_heading_carries_its_limit_or_guide(self) -> None:
        text = normal("templates/task-contract.md")
        block = text[text.index("## Approver's opening"):text.index("## Part A")]
        for needle in ("*(up to 6 lines)*", "*(up to 5 lines)*", "*(up to 3 sentences)*", "*(up to 10 lines)*", "*(as long as the change needs)*", "*(up to 15 lines)*"):
            self.assertIn(needle, block)

    def test_t0_t1_have_no_opening(self) -> None:
        text = normal("templates/task-contract.md")
        self.assertIn("T0/T1 contracts have no opening: three lines, inline", text)

    def test_breaking_is_defined(self) -> None:
        text = normal("templates/task-contract.md")
        self.assertIn("Mark **BREAKING** each behaviour change that a caller or consumer must react to", text)

    def test_part_a_and_part_b_control(self) -> None:
        text = normal("templates/task-contract.md")
        self.assertIn("Part A and Part B control", text)
        self.assertIn("adds no requirement, scope or criterion that Part A lacks", text)
        self.assertIn("The approver's decision is on the whole contract, not on the opening alone", text)

    def test_the_opening_is_not_shortened_or_waived(self) -> None:
        text = normal("templates/task-contract.md")
        self.assertIn("the author writes it, does not shorten it and does not leave a section out", text)

    def test_the_lifecycle_row_carries_the_new_form(self) -> None:
        text = normal("core/01-lifecycle.md")
        self.assertIn("| An approver's opening, then one screen (`templates/task-contract.md`) |", text)
        self.assertNotIn("| One screen (`templates/task-contract.md`) |", text)


if __name__ == "__main__":
    unittest.main()
