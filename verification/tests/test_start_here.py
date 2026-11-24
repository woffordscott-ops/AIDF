"""The guided start: README Getting started and the prompt in instantiation/start-here.md.

Pins the three actions of the README, the rules the prompt carries (the agent proposes and a human approves; roles, approvals and mode
declarations stay with the human; nothing is written before a confirmed summary; nothing outside the project; the builder is not the only
reviewer; the prompt stops at the first Task Contract), that every path the prompt names exists, and that the manual path is kept.
"""
import hashlib
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Each rule: a label and a phrase the prompt must contain. Removing the phrase must be noticed (see test_removing_any_rule_is_noticed).
RULES = {
    "propose-human-approves": "You propose; a human approves.",
    "no-guessing-roles": "Never choose, guess or invent who the Change Owner or the Architect is.",
    "no-approvals": "Never set a Task Contract, a context pack or any record to Approved",
    "no-unconfirmed-declarations": "Never write a mode declaration (which tool and model may work in which mode) that I have not confirmed line by line.",
    "draft-marks": "Draft, to be confirmed by the Architect",
    "unknowns-stated": "Unknown: to be decided by the Architect",
    "one-question": "Ask one question at a time",
    "summary-before-writing": "Write no file until you have shown me a summary of my answers and I have said yes to it.",
    "stay-in-project": "write only inside this project folder",
    "no-install-no-commit": "do not commit, merge or push unless I tell you to",
    "separate-reviewer": "may not be its only reviewer",
    "stop-at-contract": "Stop after the first Task Contract is written and shown to me.",
    "no-code-change": "Do not change any code or start the first change.",
    "no-automatic-t3": "a \"yes\" does not by itself make a change T3.",
    "same-session-below-t2": "at T0 and T1 the same session may check it",
    "next-required-step": 'End every reply with one line, "Next required step: ..."',
    "approve-by-editing": "approving in chat does not count because the file must change",
    "no-shell-approval": "Never suggest a sed command or any other shell one-liner for this.",
    "records-default": "review reports and dispositions go in docs/reviews/ in this project",
    "plain-decisions": "Put every decision you ask of me in one plain sentence",
    "lighter-conditional": "Offer the lighter start of question g only when I say the project is small and my answer to every part of question f was no.",
    "lighter-never-unasked": "Never apply it unasked.",
    "yes-cancels-lighter": "A yes to any part of f cancels it.",
    "t3-and-dependency-stay": "is still T3 and a new dependency still needs my approval",
    "lighter-existing-map": "if the project already has code, record its files with the script of Step 4.3 exactly as in the step above, so that context/repository-map.md is not left as shipped",
    "lighter-keeps-class": "the lighter start does not lower the class of my first change",
    "done-checklist": "Show me this checklist for the first change",
}

INTERVIEW = (
    "a. Who is the Change Owner",
    "b. Is this a new project",
    "c. What is the project's name",
    "d. In a few sentences",
    "e. What language and tools",
    "f. Does it handle any of these",
    "g. Only if every part of my answer to f was no",
    "h. Which agent tool and model",
    "i. What is the first change",
)

# The phrases above say what each rule is; they cannot see a sentence added next to them that reverses them. So the prompt and the README
# section are also pinned whole: any edit fails the test until the editor reads the rules again (the Verifier of the first round showed six
# edits that kept every phrase and changed what an agent does) and updates the digest here. Updated 2026-11-24 for the clarity change: five new
# rules, the size question and the lighter start in the prompt, one sentence in the README section. Digest of the text with white space collapsed.
PROMPT_SHA256 = "2bb28564dd83ed7ecb0dea7885ac475c92e58871cb553b431092dfe4c0745b46"
README_SECTION_SHA256 = "09ba404a082160aff891ce355d16f38ea22a79329777aa8f98bac0717ea58edf"

CLONE = "git clone https://github.com/woffordscott-ops/AIDF.git aidf"


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def flat(text):
    return re.sub(r"\s+", " ", text)


def prompt_of(text):
    blocks = re.findall(r"```\n(.*?)```", text, re.DOTALL)
    assert len(blocks) == 1, "start-here.md must hold exactly one code block (the prompt)"
    return blocks[0]


def missing_rules(prompt):
    flat_prompt = flat(prompt)
    return [label for label, phrase in RULES.items() if flat(phrase) not in flat_prompt]


def getting_started(text):
    start = text.index("## Getting started")
    end = text.index("## The locked three-layer model")
    return text[start:end]


class ReadmeGettingStartedTests(unittest.TestCase):
    def setUp(self):
        self.section = getting_started(read("README.md"))

    def test_the_section_is_pinned_whole(self):
        digest = hashlib.sha256(flat(self.section).strip().encode("utf-8")).hexdigest()
        self.assertEqual(digest, README_SECTION_SHA256, "the Getting started section changed: re-read it, then update README_SECTION_SHA256 and say why in the dispositions")

    def test_three_actions_in_order(self):
        positions = [self.section.index(marker) for marker in (
            "**1. Check your tools and clone AIDF.**",
            "**2. Open your coding agent in your project folder.**",
            "**3. Paste the prompt.**",
        )]
        self.assertEqual(positions, sorted(positions))

    def test_the_clone_command_and_prerequisites_are_given(self):
        self.assertIn(CLONE, self.section)
        for needle in ("git --version", "python3 --version", "python --version", "Python 3.12", "No account is needed"):
            self.assertIn(needle, self.section)

    def test_the_suite_run_is_optional(self):
        flat_section = flat(self.section)
        self.assertIn("Optional: to check your copy", flat_section)
        self.assertLess(self.section.index(CLONE), self.section.index("unittest discover"))
        self.assertLess(self.section.index("**3. Paste the prompt.**"), self.section.index("After your first change:"))
        self.assertNotIn("unittest discover", self.section[self.section.index("**2. Open"):])

    def test_it_links_the_prompt_and_the_manual_path_and_keeps_the_later_steps(self):
        self.assertIn("(instantiation/start-here.md)", self.section)
        self.assertIn("(instantiation/set-up-aidf.md)", self.section)
        later = self.section[self.section.index("After your first change:"):]
        self.assertIn("**Qualify your own tool/model**", later)
        self.assertIn("**Run day to day under `core/01-lifecycle.md`**", later)

    def test_the_human_keeps_the_decisions_in_the_readme_too(self):
        flat_section = flat(self.section)
        self.assertIn("It proposes and you decide", flat_section)
        self.assertIn("You must name a **Change Owner** and an **Architect**", flat_section)


class StartHerePromptTests(unittest.TestCase):
    def setUp(self):
        self.text = read("instantiation/start-here.md")
        self.prompt = prompt_of(self.text)

    def test_the_prompt_carries_every_rule(self):
        self.assertEqual(missing_rules(self.prompt), [])

    def test_the_prompt_is_pinned_whole(self):
        digest = hashlib.sha256(flat(self.prompt).strip().encode("utf-8")).hexdigest()
        self.assertEqual(digest, PROMPT_SHA256, "the prompt changed: re-read every rule, then update PROMPT_SHA256 and say why in the dispositions")

    def test_removing_any_rule_is_noticed(self):
        for label, phrase in RULES.items():
            with self.subTest(rule=label):
                self.assertEqual(self.prompt.count(phrase) >= 1, True)
                weakened = self.prompt.replace(phrase, "")
                self.assertEqual(missing_rules(weakened), [label])

    def test_the_interview_is_in_order(self):
        positions = [self.prompt.index(question) for question in INTERVIEW]
        self.assertEqual(positions, sorted(positions))

    def test_the_summary_is_confirmed_before_files_are_written(self):
        self.assertLess(self.prompt.index("Then show me a short summary"), self.prompt.index("After I say yes:"))
        self.assertLess(self.prompt.index("After I say yes:"), self.prompt.index("Write docs/AIDF-ROLES.md"))

    def test_the_lighter_start_comes_after_the_context_pack_and_before_the_classification(self):
        positions = [self.prompt.index(marker) for marker in (
            "- Build the context pack as set-up-aidf.md Step 4 describes",
            "- If I chose the lighter start",
            "- Classify my first change",
            "- Show me this checklist",
            "- End by telling me",
        )]
        self.assertEqual(positions, sorted(positions))

    def test_the_lighter_start_writes_three_context_files_and_promises_no_lower_class(self):
        flat_prompt = flat(self.prompt)
        for needle in (
            "write drafts of only context/architecture-overview.md, context/testing-strategy.md and context/conventions.md and leave every other context file as shipped",
            "usually T2",
            "context/repository-map.md is not left as shipped",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, flat_prompt)
        # The first rehearsal showed the checker refuses a PROVISIONAL pattern entry in a project with no code, so Route 2 cannot serve a new
        # project: the prompt must not promise T1 through a standing authorization.
        for word in ("standing authorization", "PROVISIONAL", "Route 2", "pattern-registry.json"):
            with self.subTest(absent=word):
                self.assertNotIn(word, self.prompt)

    def test_no_shell_command_is_given_for_approval(self):
        self.assertIsNone(re.search(r"\bsed\s+-", self.prompt))
        self.assertNotIn("sed -i", self.prompt)
        self.assertNotIn("! cd", self.prompt)

    def test_the_checklist_names_each_box(self):
        flat_prompt = flat(self.prompt)
        for box in ("the Task Contract is approved by me", "the change is built with its tests", "a separate session has reviewed it", "docs/reviews/", "the context pack is read and confirmed by me", "the change is merged"):
            with self.subTest(box=box):
                self.assertIn(box, flat_prompt)

    def test_the_contract_is_left_unapproved(self):
        flat_prompt = flat(self.prompt)
        self.assertIn("State Established and the approval fields pending", flat_prompt)
        self.assertIn("the Architect approves the Task Contract by setting its State to Approved", flat_prompt)

    def test_every_aidf_path_the_prompt_names_exists(self):
        names = set(re.findall(r"aidf/([A-Za-z0-9_./-]+\.(?:md|json|py))", self.prompt))
        self.assertTrue(names)
        for name in names:
            with self.subTest(path=name):
                self.assertTrue((ROOT / name).is_file(), name)

    def test_the_steps_and_sections_it_refers_to_exist(self):
        setup = read("instantiation/set-up-aidf.md")
        for heading in ("## Step 2.", "## Step 4.", "## Step 5.", "## Step 6."):
            self.assertIn(heading, setup)
        self.assertIn("## The script for step 4.3", setup)
        self.assertIn("Provisional mode declarations", setup)

    def test_the_human_page_says_what_the_agent_will_not_do(self):
        flat_text = flat(self.text)
        for needle in ("What the agent will not do", "What you must still do yourself", "instantiation/set-up-aidf.md"):
            self.assertIn(needle, flat_text)

    def test_it_asks_for_nothing_secret(self):
        lowered = self.prompt.lower()
        for word in ("password", "api key", "token", "secret key"):
            self.assertNotIn(word, lowered)


class ManualPathKeptTests(unittest.TestCase):
    def test_set_up_aidf_points_to_the_prompt_and_keeps_its_steps(self):
        text = read("instantiation/set-up-aidf.md")
        self.assertIn("(start-here.md)", text)
        for heading in ("## Step 1.", "## Step 2.", "## Step 3.", "## Step 4.", "## Step 5.", "## Step 6.", "## The script for step 4.3"):
            self.assertIn(heading, text)

    def test_the_instantiation_index_links_both(self):
        text = flat(read("instantiation/README.md"))
        self.assertIn("(start-here.md)", text)
        self.assertIn("(set-up-aidf.md)", text)


if __name__ == "__main__":
    unittest.main()
