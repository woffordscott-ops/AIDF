"""Presence and citation tests for instantiation/spec-tools.md (spec/AIDF-SPEC-TOOLS-INTEROP-GUIDE-TASK-CONTRACT.md)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE = "instantiation/spec-tools.md"
SETUP = "instantiation/set-up-aidf.md"
ARTIFACTS = "verification/spec-tool-bakeoff/reading-test/artifacts/"
STAGE0 = "strategy/AIDF-SPEC-TOOL-BAKEOFF-STAGE0.md"
SECTIONS = (
    "## 1. What this guide is based on, and what it is not",
    "## 2. What a tool can feed into a Task Contract",
    "## 3. The order of steps",
    "## 4. Facts to plan for",
    "## 5. What stays AIDF's",
    "## 6. Declared scope",
    "## 7. No converter exists",
    "## 8. Drafting a Task Contract with the mapper",
)


def text(path: str = GUIDE) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def flat(path: str = GUIDE) -> str:
    return " ".join(text(path).split())


def run_checker(project: Path) -> str:
    done = subprocess.run([sys.executable, str(ROOT / "instantiation" / "check_context_pack.py"), "--project-root", str(project), "--manifest", "project-context-pack.json"],
                          cwd=project, capture_output=True, text=True, encoding="utf-8", check=False, env={**os.environ, "PYTHONUTF8": "1"})
    return done.stdout.split(":")[0] if done.stdout.startswith("PASS") else done.stdout + done.stderr


def _git_show(commit: str, path: str) -> str:
    try:
        done = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)
    except FileNotFoundError:
        return ", including slug.py."
    return done.stdout if done.returncode == 0 else ", including slug.py."  # a shallow clone has no such commit: the claim is then not tested


def table_rows() -> list[list[str]]:
    rows = []
    for line in text().splitlines():
        match = re.match(r"^\| (\d+) \| (.+) \|$", line)
        if match:
            rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


class GuideTests(unittest.TestCase):
    def test_the_front_matter_is_present(self) -> None:
        head = text().split("---")[1]
        for key in ("owner:", "load_when:", "max_length:", "last_verified:"):
            self.assertIn(key, head)

    def test_the_sections_are_present_in_order(self) -> None:
        body = text()
        positions = [body.index(heading) for heading in SECTIONS]
        self.assertEqual(positions, sorted(positions))

    def test_the_scope_of_the_evidence_is_stated(self) -> None:
        body = flat()
        for needle in ("OpenSpec v1.16.0", "Spec Kit v1.3.0", "each run once", "`grok-4.7-high`", "on Windows, without a sandbox",
                       "No saving was shown", "AIDF does not certify a tool"):
            self.assertIn(needle, body)

    def test_the_field_table_has_the_18_fields_and_the_stage_0_counts(self) -> None:
        rows = table_rows()
        self.assertEqual([int(row[0]) for row in rows], list(range(1, 19)))
        self.assertIn("**supplied 2, partly 4, AIDF-only 12**", flat())
        supplied = [r for r in rows if r[2].startswith("supplied") and r[3].startswith("supplied")]
        partly = [r for r in rows if r[2].startswith("partly") and r[3].startswith("partly")]
        only = [r for r in rows if r[2] == "AIDF-only" and r[3] == "AIDF-only"]
        self.assertEqual((len(supplied), len(partly), len(only)), (2, 4, 12))
        self.assertEqual(len(supplied) + len(partly) + len(only), 18)

    def test_the_field_table_agrees_with_the_stage_0_document(self) -> None:
        stage0 = {}
        for line in text(STAGE0).splitlines():
            match = re.match(r"^\| (\d+) \| (.+?) \| (.+?) \| (.+?) \|$", line)
            if match:
                stage0[int(match.group(1))] = (match.group(2), match.group(3), match.group(4))
        self.assertEqual(sorted(stage0), list(range(1, 19)))
        for row in table_rows():
            number = int(row[0])

            def kind(cell: str) -> str:
                cell = cell.replace("*", "")
                return "supplied" if cell.startswith("supplied") else "partly" if cell.startswith("partly") else "AIDF-only"

            self.assertEqual(kind(row[2]), kind(stage0[number][1]), f"OpenSpec, field {number}")
            self.assertEqual(kind(row[3]), kind(stage0[number][2]), f"Spec Kit, field {number}")

    def test_the_apply_step_runs_after_the_approval(self) -> None:
        full = text()
        section = " ".join(full[full.index("## 3. The order of steps"):full.index("## 4. Facts to plan for")].split())
        self.assertIn("only after the contract is Approved does the tool's apply step run", section)
        for command in ("`/opsx:apply`", "`/speckit-implement`", "`/speckit-converge`"):
            self.assertIn(command, section)
        self.assertIn("is not that approval", section)
        start = full[full.index("## Start here"):full.index("## A worked example")]
        step5 = " ".join(start[start.index("5. **Now run the tool's apply step:**"):start.index("6. **Verify and review")].split())
        for command in ("`/opsx:apply`", "`/speckit-implement`", "`/speckit-converge`"):
            self.assertIn(command, step5)

    def test_start_here_gives_the_actions_before_section_1(self) -> None:
        body = text()
        start = body[body.index("## Start here"):body.index(SECTIONS[0])]
        for step in ("1. **Classify the change**", "2. **Ask your agent to run only the tool's planning step", "3. **Write the Task Contract**",
                     "4. **A human approves the Task Contract.**", "5. **Now run the tool's apply step:**", "6. **Verify and review as AIDF says:**"):
            self.assertIn(step, start)
        positions = [start.index(n) for n in ("1. **", "2. **", "3. **", "4. **", "5. **", "6. **")]
        self.assertEqual(positions, sorted(positions))
        for command in ("`/opsx:propose`", "`/speckit-specify`", "`/speckit-plan`", "`/speckit-tasks`", "STOP before the tool's apply or implement step"):
            self.assertIn(command, start)
        self.assertIn("A human approves the Task Contract.", start)

    def test_start_here_says_what_must_not_happen_and_what_is_not_promised(self) -> None:
        body = text()
        start = body[body.index("## Start here"):body.index(SECTIONS[0])]
        must_not = start[start.index("**What must not happen before the Task Contract is Approved.**"):start.index("**What this guide does not promise.**")]
        for needle in ("apply, implement or converge step is not run", "No code file is written or changed", "is not counted as the approval", "Nothing from the tool is treated as evidence"):
            self.assertIn(needle, must_not)
        not_promised = start[start.index("**What this guide does not promise.**"):]
        for needle in ("another release of either tool", "saves time or effort", "AIDF certifies, supports or tests a tool", "A converter"):
            self.assertIn(needle, not_promised)

    def test_start_here_links_the_setup_how_to_and_says_why(self) -> None:
        body = text()
        start = body[body.index("## Start here"):body.index(SECTIONS[0])]
        self.assertIn("[how to set up AIDF in a project](set-up-aidf.md)", start)
        self.assertIn("**Why do it.**", body[:body.index("## Start here")])
        self.assertIn("nothing here is a reason to start", body)

    def test_the_setup_how_to_gives_the_steps_in_order(self) -> None:
        body = text(SETUP)
        steps = ("## Before you begin: what you need", "## Step 1. Get AIDF and check that it runs", "## Step 2. Name the two people", "## Step 3. Read the kernel",
                 "## Step 4. Build the project context pack", "## Step 5. Record how your agent may work", "## Step 6. Start your first change")
        positions = [body.index(step) for step in steps]
        self.assertEqual(positions, sorted(positions))
        for needle in ("`git --version`", "Python 3.12 or newer", "If you see `FAILED` or `Error`, stop", "python3 --version", "python --version", "git clone https://github.com/woffordscott-ops/AIDF.git aidf", "It is a public repository: anyone can clone it and you do not need an account", "if it still fails, ask the person who gave you AIDF",
                       "python3 -m unittest discover -s verification/tests", "python -m unittest discover -s verification/tests",
                       "cp -r <AIDF>/instantiation/starter/. .", "Copy-Item -Recurse -Force <AIDF>\\instantiation\\starter\\* .",
                       "check_context_pack.py --project-root . --manifest project-context-pack.json",
                       "PASS: context-pack structural checks (human architecture approval still required)",
                       "Change Owner: <full name>", "Architect: <full name>", "`core/02-authority.md` section 1", "`modes/execution-modes.md`",
                       "templates/task-contract.md", "continue with `instantiation/spec-tools.md`", "Do not change any code until a human has approved the Task Contract"):
            self.assertIn(needle, body)

    def test_step_5_explains_the_modes_and_gives_examples(self) -> None:
        body = text(SETUP)
        step = body[body.index("## Step 5."):body.index("## Step 6.")]
        for mode in ("**M0 Constrained execution**", "**M1 Supervised implementation**", "**M2 Design and synthesis**", "**M3 Adversarial verification**"):
            self.assertIn(mode, step)
        for needle in ("Use it when", "What the agent may do", "What it must not do", "**The one rule to remember.**", "**Why you declare.**",
                       "**How to choose.**", "*Example A: one person, one agent.*", "*Example B: a team with two agents.*",
                       "*Example C: a team that plans with OpenSpec or Spec Kit.*", "Provisional mode declarations (made by the Architect)",
                       "`core/02-authority.md` section 3", "a third, separate session also acts as security reviewer", "does not lower any bar"):
            self.assertIn(needle, step)
        self.assertEqual(step.count("Provisional mode declarations (made by the Architect)"), 3)

    def test_the_starter_passes_the_checker_for_a_new_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            shutil.copytree(ROOT / "instantiation" / "starter", project)
            self.assertEqual(run_checker(project), "PASS")

    def test_the_documented_script_makes_a_pack_for_an_existing_project_that_passes(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git is not installed")
        script = re.search(r"```python\n(.*?)```", text(SETUP), re.DOTALL)
        self.assertIsNotNone(script)
        assert script is not None
        self.assertFalse(any(line.startswith(" ") and line.strip().startswith("import") for line in script.group(1).splitlines()))
        self.assertTrue(script.group(1).startswith("import json, re, subprocess"))
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            environment = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
            (project / "app.py").write_text("x = 1\n", encoding="utf-8")
            (project / "sub").mkdir()
            (project / "sub" / "né file.txt").write_text("y\n", encoding="utf-8")
            for command in (["git", "init", "-q", "."], ["git", "add", "-A"], ["git", "commit", "-q", "-m", "init"]):
                subprocess.run(command, cwd=project, env=environment, check=True, capture_output=True)
            shutil.copytree(ROOT / "instantiation" / "starter", project, dirs_exist_ok=True)
            helper = Path(tmp) / "make_pack.py"
            helper.write_text(script.group(1), encoding="utf-8")
            subprocess.run([sys.executable, str(helper)], cwd=project, env=environment, check=True, capture_output=True)
            manifest = json.loads((project / "project-context-pack.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["entry_path"], "existing")
            self.assertEqual(sorted(manifest["repository_map"]["paths"]), ["app.py", "sub/né file.txt"])
            self.assertEqual(run_checker(project), "PASS")

    def test_the_starter_files_carry_the_front_matter_and_a_prompt_to_write(self) -> None:
        for path in sorted((ROOT / "instantiation" / "starter" / "context").glob("*.md")):
            body = path.read_text(encoding="utf-8")
            for key in ("owner:", "load_when:", "max_length:", "last_verified:"):
                self.assertIn(key, body.split("---")[1], path.name)
            if path.name != "repository-map.md":
                self.assertIn("To be written by you (the Architect).", body, path.name)

    def test_the_worked_example_cites_files_that_exist_and_maps_the_parts(self) -> None:
        body = text()
        example = body[body.index("## A worked example"):body.index(SECTIONS[0])]
        for name in ("openspec/changes/add-items-pagination/proposal.md", "openspec/changes/add-items-pagination/design.md",
                     "openspec/changes/add-items-pagination/specs/items-listing/spec.md", "openspec/changes/add-items-pagination/tasks.md",
                     "specs/001-paginate-items-listing/spec.md", "specs/001-paginate-items-listing/plan.md", "specs/001-paginate-items-listing/tasks.md",
                     "specs/001-paginate-items-listing/contracts/items-listing.md"):
            tool = "openspec" if name.startswith("openspec") else "speckit"
            self.assertTrue((ROOT / ARTIFACTS / tool / name).is_file(), name)
        for needle in ("Class, trip-wires, evidence strategy, recovery, review budget, status", "nothing", "2,647 words", "7,784 words", "1,539 words", "**BREAKING**"):
            self.assertIn(needle, example)
        for named in ("`proposal.md`", "`design.md` (decisions and rejected alternatives)", "`specs/items-listing/spec.md`", "`tasks.md` (a checklist)", "`spec.md` (user stories",
                      "`plan.md`", "`contracts/items-listing.md`", "`checklists/requirements.md`"):
            self.assertIn(named, example)

    def test_the_how_to_repeats_the_authority_and_class_rules_as_the_core_documents_state_them(self) -> None:
        body = flat(SETUP)
        authority = flat("core/02-authority.md")
        lifecycle = flat("core/01-lifecycle.md")
        self.assertIn("the only party who can waive a non-trip-wire control", authority)
        self.assertIn("the only party who can waive a control that is not a trip-wire (a trip-wire cannot be waived)", body)
        self.assertIn("T2: human under Architect authority. T3: same, approved before implementation", authority)
        self.assertIn("approves Task Contracts at class T2 and T3", body)
        self.assertIn("A second, separate session satisfies it (`core/02-authority.md` section 3)", body)
        self.assertIn("changing the model inside the same session does not count", body)
        self.assertIn("a third, separate session also acts as security reviewer", body)
        gloss = ("**T0** mechanical and verifiable by construction (formatting, regenerating generated code, a documentation typo, a mechanical rename); "
                 "**T1** contained: a behaviour change inside one ownership boundary and within existing contracts, reversible, with the requirement fully clear, using a pattern that is authorised for T1; "
                 "**T2** structural: it crosses ownership boundaries, changes an interface or contract, is a real design decision, or has meaningful blast radius; "
                 "**T3** critical: a kernel trip-wire fires (a security boundary, an effect that cannot be undone, high operational or financial consequence).")
        self.assertIn(gloss, body)
        for phrase in ("Behavior change inside one ownership boundary, within existing contracts, reversible, Spec Confidence Clear",
                       "Crosses ownership boundaries, changes an interface/contract", "high operational/financial consequence"):
            self.assertIn(phrase, lifecycle)

    def test_step_4_gives_its_six_parts_in_order_and_the_failure_help_matches_the_checker(self) -> None:
        body = text(SETUP)
        step = body[body.index("## Step 4."):body.index("## Step 5.")]
        parts = ("1. **Copy the starter into your project root.**", "2. **Name the project.**", "3. **If your project already has code (and only then), record its files.**",
                 "4. **Run the checker.**", "5. **Write the content.**", "6. **Commit**")
        positions = [step.index(part) for part in parts]
        self.assertEqual(positions, sorted(positions))
        checker = (ROOT / "instantiation" / "check_context_pack.py").read_text(encoding="utf-8")
        for message in ("invalid project identifier", "artifact could not be opened safely", "invalid frontmatter field", "platform cannot bind Git validation to the project root"):
            self.assertIn(message, checker)
            self.assertIn(f"FAIL: {message}", step)
        self.assertIn("**macOS:**", step)
        self.assertIn("AIDF has not been tested on macOS", step)
        self.assertIn("For a new project (no code yet) the checker is expected to work on macOS, but that has not been tried", step)
        self.assertIn("Run it *before* you commit the new `context/` folder", step)
        self.assertIn("each markdown file in `context/` except `repository-map.md`", step.lower())
        self.assertIn("git add -A", body)
        self.assertIn("If it prints `fatal: not a git repository`, run `git init` in the project folder first.", flat(SETUP))
        self.assertIn("If the commit stops with `Author identity unknown`", flat(SETUP))
        self.assertIn("`git config --global user.name \"Your Name\"` and `git config --global user.email \"you@example.com\"`", flat(SETUP))

    def test_the_three_mode_examples_carry_their_declaration_lines(self) -> None:
        body = text(SETUP)
        step = body[body.index("## Step 5."):body.index("## Step 6.")]
        lines = ("2026-11-06 | Tool A with Model X | M1 (implement) for T0 to T3; M2 (plan) for T2 and T3",
                 "2026-11-06 | Tool A with Model X, a new session | M3 (review) for T2; for T3 also a third session as security reviewer. Never the session that built the change",
                 "2026-11-06 | Tool A with Model X | M1 (implement) and M0 (mechanical changes)",
                 "2026-11-06 | Tool B with Model Y | M3 (review) for T2 and T3, as a separate session from the one that built the change",
                 "2026-11-06 | Tool B with Model Y | M2 (plan) for T2 and T3",
                 "M2 (plan) only; its apply step is not run until the Task Contract is Approved",
                 "2026-11-06 | Tool A with Model X, after approval | M1 (implement)")
        for line in lines:
            self.assertIn(line, step)

    def test_the_stage_1_facts_in_the_guide_match_the_probe_source_and_the_dispositions(self) -> None:
        guide = flat()
        self.assertIn("whose agent step added 38 files in all", guide)
        record = json.loads((ROOT / "verification" / "spec-tool-bakeoff" / "probe" / "speckit-probe.json").read_text(encoding="utf-8"))
        added = [len(step["writes"]["added"]) for step in record["steps"] if step["name"] == "agent"]
        self.assertEqual(added, [38])
        self.assertIn("`TOOL_PROMPT` in `verification/spec_tool_probe.py`", guide)
        stop = "STOP before the tool's apply or implement step. Do not write or change any code file."
        self.assertIn(stop, (ROOT / "verification" / "spec_tool_probe.py").read_text(encoding="utf-8"))
        self.assertIn(stop, guide)
        self.assertIn("the stage 1 runs were given the same sentence with \", including slug.py\" (a file of their throwaway project) added after \"code file\"", guide)
        self.assertIn(", including slug.py.", _git_show("1e54ee79", "verification/spec_tool_probe.py"))
        self.assertIn("`instantiation/set-up-aidf.md`, `instantiation/starter/`", flat("CHANGELOG.md"))

    def test_the_example_word_counts_match_the_dispositions(self) -> None:
        dispositions = flat("verification/spec-tool-bakeoff-stages-0-1-verifier-dispositions.md")
        for count in ("2,647", "7,784", "1,539"):
            self.assertIn(count, dispositions)

    def test_the_safety_facts_are_stated(self) -> None:
        body = flat()
        for needle in ("`--allow-steering-files`", "12 files for OpenSpec", "9 skills under `.cursor/skills/` for Spec Kit",
                       "can create git branches in a git checkout", "still exits 0 with nothing written", "`OPENSPEC_TELEMETRY=0`",
                       "Neither README shows one"):
            self.assertIn(needle, body)

    def test_what_stays_aidfs(self) -> None:
        body = flat()
        self.assertIn("is an input and is never evidence", body)
        self.assertIn("It may not restate or override `KERNEL.md`", body)
        self.assertIn("a file outside it is a scope change", body)

    def test_no_converter_is_offered(self) -> None:
        body = flat()
        self.assertIn("AIDF has no converter: no tool turns an OpenSpec change folder or a Spec Kit feature directory into a finished Task Contract.", body)
        self.assertIn("Section 8 describes a draft generator", body)
        self.assertIn("a team that names the format it uses and asks for it", body)

    def test_every_cited_repository_path_exists(self) -> None:
        # The worked example cites the sample project's and the tools' files; its own test checks those.
        for source in (GUIDE, SETUP):
            body = text(source)
            if source == GUIDE:
                body = body[:body.index("## A worked example")] + body[body.index(SECTIONS[0]):]
            cited = set(re.findall(r"`([A-Za-z0-9_./-]+\.(?:md|py|json))`", body))
            if source == SETUP:
                cited -= {"context/repository-map.md", "docs/AIDF-ROLES.md"}  # files of the reader's own project
            cited |= set(re.findall(r"\]\(([A-Za-z0-9_./-]+\.md)\)", body))
            self.assertTrue(cited)
            missing = []
            for path in sorted(cited):
                if "/" not in path:
                    continue
                if not ((ROOT / path).exists() or (ROOT / "instantiation" / path).exists()):
                    missing.append(path)
            self.assertEqual(missing, [], source)

    def test_the_instantiation_readme_points_to_the_guide_and_the_how_to(self) -> None:
        self.assertIn("[using OpenSpec or Spec Kit with AIDF](spec-tools.md)", flat("instantiation/README.md"))
        self.assertIn("[how to set up AIDF in a project](set-up-aidf.md)", flat("instantiation/README.md"))

    def test_the_customer_dry_run_fixes_stay_in_the_guides(self) -> None:
        setup, guide = flat(SETUP), flat(GUIDE)
        for needle in ("saves UTF-8 without a byte-order mark", "`FAIL: Unexpected UTF-8 BOM`", "The four you are most likely to meet",
                       "run the tool's planning step first", "AIDF does not fix where the files go", "The *Verifier* named in `core/05-review.md`"):
            self.assertIn(needle, setup)
        for needle in ("`node --version`", "`npm install --prefix .tools @fission-ai/openspec@1.16.0`", "init --tools claude --no-animation",
                       "Add `.tools/` to your `.gitignore`"):
            self.assertIn(needle, guide)

    def test_the_recorded_pin_matches_the_stage_0_document(self) -> None:
        stage0 = flat(STAGE0)
        for value in re.findall(r"`(v?\d+\.\d+\.\d+)`|\b([0-9a-f]{40})\b", flat()):
            token = value[0] or value[1]
            if len(token) == 40:
                self.assertIn(token, stage0)


if __name__ == "__main__":
    unittest.main()
