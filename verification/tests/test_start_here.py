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
    "authorization-no-code-only": "If the project already has code, do not write an authorization",
    "authorization-no-registry-entry": "with no registry entry (the checker refuses one in a project with no code)",
    "authorization-expiry": "the expiry 90 days from today",
    "authorization-unsigned": "the status left Inactive, and the grantor and the date left pending for me to fill by editing those lines",
    "authorization-t2-either-way": "my first change is T2 whether or not I sign it",
    "authorization-later-changes-only": "only if it stays inside the tool's existing commands and file format and changes no contract",
    "lighter-keeps-class": "the lighter start does not lower the class of my first change",
    "done-checklist": "Show me this checklist for the first change",
    "self-test-only-on-request": "Do not run the AIDF self-test (the checks of set-up-aidf.md Step 1) unless I ask you to; if I ask, run it once and tell me its result once, when it has finished.",
    "restart-note": "tell me that its slash commands load only in a new session, and that until then you run the same steps through its command line",
    "review-route-choice": "make verification/run_review.py refuse to start a review, and that I choose between reviewing a commit of the project without them and passing --allow-steering-files knowingly (the log records that). Recommend neither, and never run the review tool yourself.",
    "confirmation-recorded-once": "the confirmation is recorded once, in docs/AIDF-ROLES.md",
    "confirmation-only-place": "that is the only place I confirm the context pack",
    "read-only-commands": "plus read-only commands that inspect (listing or reading files, git status, git log, git diff)",
    "approval-one-block": "every line to change and the words to write, all in one block",
    "no-open-question": "In the first Task Contract leave no open question",
    "iso-dates": "Write every date as YYYY-MM-DD",
    "review-records-in-scope": "docs/reviews/, docs/AIDF-ROLES.md and the contract's own file, and it has an Outcome records criterion",
    "simplest-design": "Propose the simplest design that meets the invariants I stated, and name what it leaves out.",
    "git-local-identity": "use only a repository-local identity (git config without --global) and never change my machine-wide settings",
    "local-publishes-nothing": "a local repository publishes nothing",
    "branch-and-local-merge": 'where the project has no remote, "merged" means merged into the main branch locally after the review has passed at a named commit',
    "language-version-asked": "which version of the language",
    "checklist-confirmation": "the context pack is read and confirmed by me in docs/AIDF-ROLES.md",
    "checklist-merged": "[ ] the change is merged (with no remote: into the main branch locally, after the review passed)",
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
# rules, the size question and the lighter start in the prompt, one sentence in the README section. Updated 2026-11-24 again for the small-project rule: the lighter start writes an unsigned
# standing authorization for a project with no code (the clause of core/01-lifecycle.md section 7 that lets it describe its own pattern). Digest of the text with white space collapsed.
# Updated 2026-11-25 for the friction follow-ups: rules 16 to 18 (the self-test only on request, the restart note for a planning tool, the review-route choice).
# Updated 2026-11-27 for friction-followups-2: the first change is T2 whether or not the standing authorization is signed, question e asks the language version, rule 5 (one confirmation record), rule 8 (read-only commands), rule 12 (one block), rule 18 (a commit, not a copy), rules 19 and 20 (the first contract, Git), the roles confirmation line and the checklist wording.
PROMPT_SHA256 = "f0b7e89a0e6c99955067ae2b7848e1ab059c7d38100130e4bed1a9cd0e985c24"
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

    def test_the_lighter_start_writes_three_context_files_and_an_unsigned_authorization_for_a_project_without_code(self):
        flat_prompt = flat(self.prompt)
        for needle in (
            "write drafts of only context/architecture-overview.md, context/testing-strategy.md and context/conventions.md and leave every other context file as shipped",
            "usually T2",
            "context/repository-map.md is not left as shipped",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, flat_prompt)
        # The checker refuses a PROVISIONAL pattern entry in a project with no code (found by the rehearsal of the clarity change), so the
        # authorization describes its pattern itself and the prompt writes no registry entry.
        for word in ("PROVISIONAL", "pattern-registry.json"):
            with self.subTest(absent=word):
                self.assertNotIn(word, self.prompt)
        self.assertIn("aidf/templates/standing-authorization.md", self.prompt)
        self.assertTrue((ROOT / "templates" / "standing-authorization.md").is_file())

    def test_no_shell_command_is_given_for_approval(self):
        self.assertIsNone(re.search(r"\bsed\s+-", self.prompt))
        self.assertNotIn("sed -i", self.prompt)
        self.assertNotIn("! cd", self.prompt)

    def test_the_checklist_names_each_box(self):
        flat_prompt = flat(self.prompt)
        for box in ("the Task Contract is approved by me", "the change is built with its tests", "a separate session has reviewed it", "docs/reviews/", "the context pack is read and confirmed by me", "the change is merged", "if a standing authorization was written, it is signed by me"):
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


class SmallProjectRuleTests(unittest.TestCase):
    """The core rule that lets a standing authorization describe its own pattern in a project with no code (Task Contract
    spec/AIDF-SMALL-PROJECT-RULE-TASK-CONTRACT.md). Every other condition of Route 2 stays."""

    def test_route_2_carries_the_clause_and_keeps_its_conditions(self):
        text = flat(read("core/01-lifecycle.md"))
        self.assertIn("or, in a project with no code yet, a pattern the authorization itself describes", text)
        self.assertIn("In a project with no code yet there is no incumbent pattern for a `PROVISIONAL` entry to record, so the authorization describes the pattern itself; every other condition of Route 2 applies unchanged.", text)
        for kept in (
            "**Route 2 never becomes Route 1 by use or by age.**",
            "**No precedent.** Permission to execute this pattern under T1 controls, for a stated scope, until a stated expiry.",
            "approved by a human under Architect authority and recorded (pattern · scope · expiry · grantor)",
            "work under it reverts to minimum T2 until ratified",
            "No precedent, no covering standing authorization, precedent that doesn't fit the context, or a `PROVISIONAL` entry with no covering authorization → **minimum T2.**",
            "**De-escalation requires the authority of the higher class**",
        ):
            with self.subTest(kept=kept):
                self.assertIn(kept, text)

    def test_the_authority_document_and_the_template_say_the_same(self):
        authority = flat(read("core/02-authority.md"))
        self.assertIn("In a project with no code yet, where there is no incumbent pattern to enter in the registry, the authorization describes the pattern in its own text; the human grantor, the scope and the mandatory expiry are unchanged.", authority)
        template = read("templates/standing-authorization.md")
        self.assertIn("in a project with no code yet, describe the pattern here instead", template)
        for field in ("**Scope**", "**Expiry** (date — mandatory)", "**Grantor** (human, Architect authority)"):
            with self.subTest(field=field):
                self.assertIn(field, template)

    def test_the_trip_wires_and_the_dependency_gate_are_not_touched_by_the_rule(self):
        kernel = flat(read("KERNEL.md"))
        self.assertIn("any one forces T3, non-negotiable, cannot be waived by an agent", kernel)
        self.assertIn("any new third-party dependency or license change requires human approval regardless of class", kernel)
        prompt = flat(prompt_of(read("instantiation/start-here.md")))
        self.assertIn("is still T3 and a new dependency still needs my approval", prompt)


class FrictionFollowupsTests(unittest.TestCase):
    """Task Contract spec/AIDF-FRICTION-FOLLOWUPS-TASK-CONTRACT.md: the self-test is optional, a planning tool's commands need a new
    session, and the user is told before the first review what can stop the review tool."""

    def test_the_prompt_does_not_carry_the_test_command_and_names_the_flag_without_running_it(self):
        prompt = prompt_of(read("instantiation/start-here.md"))
        self.assertNotIn("unittest", prompt)
        self.assertIn("--allow-steering-files", prompt)
        self.assertNotIn("python verification/run_review.py", prompt)

    def test_set_up_marks_the_self_test_optional_and_keeps_the_stop_on_failure_sentence(self):
        setup = flat(read("instantiation/set-up-aidf.md"))
        self.assertIn("4. Optional: run its checks, to confirm your copy; skip this step if you are told not to or do not need it.", setup)
        self.assertIn("5. If you ran the checks, read the last lines.", setup)
        self.assertIn("If you see `FAILED` or `Error`, stop and ask the person who gave you AIDF: do not continue on a copy that fails its own checks.", setup)

    def test_the_human_page_says_the_self_test_is_not_run_unasked(self):
        text = flat(read("instantiation/start-here.md"))
        self.assertIn("It does not run AIDF's own self-test unless you ask", text)


class FrictionFollowups2Tests(unittest.TestCase):
    """Task Contract spec/AIDF-FRICTION-FOLLOWUPS-2-TASK-CONTRACT.md: what the first change's class depends on is stated truthfully, the
    first contract is approvable in one pass, the context pack has one confirmation record, and Git settings stay local."""

    def setUp(self):
        self.text = read("instantiation/start-here.md")
        self.prompt = flat(prompt_of(self.text))
        self.setup = flat(read("instantiation/set-up-aidf.md"))

    def test_the_over_promise_about_the_first_change_is_gone_from_prompt_and_note(self):
        page = flat(self.text)
        for old in ("my first change is T2 until I have signed it", "until you sign it the first change is T2", "lets your first changes in its scope run under the lighter T1 controls"):
            with self.subTest(old=old):
                self.assertNotIn(old, page)

    def test_the_note_says_the_first_change_is_t2_either_way(self):
        note = flat(self.text.split("## The prompt")[0])
        self.assertIn("does not lower your first change, which is T2 either way", note)
        self.assertIn("only if that change stays within the tool's existing commands and file format and changes no contract", note)

    def test_the_prompt_names_the_confirmation_lines_and_does_not_ask_for_per_file_edits(self):
        self.assertIn('a line "Context pack confirmed by (Architect): pending" and a line "Date: pending"', self.prompt)
        self.assertIn("never ask me to edit it file by file", self.prompt)

    def test_the_prompt_never_has_the_agent_set_global_git_settings(self):
        self.assertNotIn("git config --global", self.prompt)

    def test_set_up_uses_a_repository_local_identity_and_names_the_confirmation_record(self):
        self.assertNotIn("git config --global", self.setup)
        self.assertIn('run these inside the project folder, without `--global`', self.setup)
        self.assertIn("Context pack confirmed by (Architect): <full name, written by the Architect>", self.setup)
        self.assertIn("This one line is the confirmation of the whole context pack", self.setup)

    def test_set_up_defines_merged_for_a_project_with_no_remote(self):
        self.assertIn("if the project has no remote, merged means merged into the main branch locally after the review passed at a named commit", self.setup)

    def test_the_old_wording_of_rule_18_is_gone(self):
        self.assertNotIn("reviewing a copy of the project", self.prompt)


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
