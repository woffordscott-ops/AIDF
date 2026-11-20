"""Tests for verification/pack_facts.py, the rule text of the review-efficiency core change, and the outcome-record declaration."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "verification"))
SPEC = importlib.util.spec_from_file_location("pack_facts", ROOT / "verification" / "pack_facts.py")
assert SPEC and SPEC.loader
pack_facts = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pack_facts
SPEC.loader.exec_module(pack_facts)


def git(repo, *args):
    done = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8")
    return done.stdout.strip()


# The text that speaks of rounds, budgets and pre-authorisation, block by block (a paragraph, or one item of a list), as reviewed. A block is pinned
# by the first 16 hex digits of the SHA-256 of its whitespace-normalised text. When a rule is changed on purpose, the failure prints the new block and
# the digest to put here; a block added anywhere in these three documents that uses one of the words in RULE_VOCABULARY fails until it is pinned.
RULE_VOCABULARY = re.compile(r"pre-authoris|\brounds?\b|budget|\bfour\b|\b4\b|\bextra\b", re.IGNORECASE)
PINNED_BLOCKS = {
    "core/05-review.md": ["1976eb304088bc42", "1f77134850a6b14e", "201bef4ddf5aab0f", "29350f0f6b849f59", "4174b103aa2754d9", "41b602c71cc10aba", "59ac09112a4c034c", "5d4b270b3d8f23e6", "6e84aca70862802e", "7a2271d487eaed8c", "7be44c2656b20321", "934585b99514b620", "96fd1eb384bda783", "97f84d069776d01e", "a0f47882dec3f0a8", "c7ff362b31495281", "ca39eccfc9f2cc10", "cde33fce184ebb15", "eb8d74a66321a24a", "ff87df782ae0f9f4"],
    "templates/task-contract.md": ["2ac1522a2f3691c8", "9e1d6561b99e984e", "b982848aa21d03d3"],
    "spec/adr/review-stop-rule.md": ["0b931078e06eea46", "1e7dbe7368fdccd0", "375c416da80c95fb", "41c6ae3a24ffdc33", "4d0794a34fa45e2e", "77fed72b549bf5bd", "86084de3090b16b2", "862d60cb1e34ba59", "889ae1a9dde4aa0d", "8f8673e187db845b", "a42f1389aadb598a", "d33faa78543265b1", "dcf74b1aa2817ad0", "f43cfa9daa1fc5df", "f7df6aa9616527ad", "ff36029a17f4fa6b"],
}


def rule_blocks(text: str) -> list[str]:
    found = []
    for paragraph in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        for item in re.split(r"(?m)^(?=\s*(?:[-*] |\d+\. ))", paragraph):
            item = " ".join(item.split())
            if item and RULE_VOCABULARY.search(item):
                found.append(item)
    return found


class RuleTextPresenceTests(unittest.TestCase):
    """The prose rules have no behaviour to test. These tests fail on the previous text; they show a rule is written, not that it is right."""

    def read(self, name):
        return (ROOT / name).read_text(encoding="utf-8")

    def test_review_budget_and_stop_menu_are_in_core_05_review(self):
        text = " ".join(self.read("core/05-review.md").split())
        for phrase in (
            "### Review budget",
            "merge with the listed advisories; accept a named residual",
            "split the change; stop; or allow one more round",
            "a rank-1 finding in code, tests or security posture",
            "A contract without a declared budget has a budget of two rounds",
            "A declared budget is at most two rounds per layer",
            "repeats only on the same condition",
            "The append is made before merge",
            "otherwise the append changes the head and section 7 applies",
            "Accepting a named residual is not a waiver of a control",
            "named, scoped residual risk and records the reason",
            "never accepts a rank-1 behavior defect that has a reproducing case",
        ):
            self.assertIn(phrase, text)

    def test_the_preauthorisation_of_further_rounds_is_written_and_the_cap_did_not_move(self):
        text = " ".join(self.read("core/05-review.md").split())
        for phrase in (
            "up to two further rounds per layer, after the layer's last budgeted round, naming the layer and the number",
            "A pre-authorisation is a human decision recorded in advance, not a larger budget.",
            "The default and the maximum of a declared budget stay at two rounds per layer,",
            "A pre-authorised round starts only if the round before it, of the same layer, did not pass and found a rank-1 finding in code, tests or security posture.",
            "Before the round starts, the dispositions record the pre-authorisation (contract and criterion), the finding that meets the condition and the date.",
            "for up to two further rounds of the layer it names.",
            "If no such finding exists the round is not started and the menu above applies.",
            "it does not carry to another layer or to another change, and a rebase or a merge-base refresh of the change does not end it.",
            # the cap and the default stay as they were
            "The default is two Verifier rounds at T2, and two Verifier and two Security rounds at T3",
            "A declared budget is at most two rounds per layer",
            "A contract without a declared budget has a budget of two rounds",
        ):
            self.assertIn(phrase, text)

    def test_no_count_above_two_is_the_default_or_the_maximum(self):
        """The cap is two. The only place the text may say four is the parenthesis that counts the pre-authorised rounds of a budget of two."""
        text = " ".join(self.read("core/05-review.md").split())
        budget = text[text.index("### Review budget"):text.index("### Controls that enumerate")]
        self.assertEqual(1, budget.count("four"), budget)
        self.assertIn("(for a budget of two, four rounds of that layer in all)", budget)
        disposition = text[text.index("## 5. Disposition and false positives"):text.index("## 6. Re-review triggers")]
        self.assertNotIn("four", disposition)
        self.assertNotIn("any number of", budget + disposition)
        self.assertNotIn("any number of", text[text.index("A pre-authorisation (section 2)"):text.index("## 6. Re-review triggers")])
        template = " ".join(self.read("templates/task-contract.md").split())
        line = template[template.index("**Review budget**"):]
        line = line[:line.index("## Status")]
        self.assertNotIn("four", line)
        self.assertIsNone(re.search(r"\b4\b", line), line)

    def test_every_block_that_speaks_of_rounds_or_budgets_is_the_reviewed_text(self):
        """A closed check over a vocabulary: it does not look for known-bad wording, it refuses any change to, or any addition of, a block that uses
        one of the words. It does not see a rewording that avoids all of them (RULE_VOCABULARY)."""
        for name, pinned in PINNED_BLOCKS.items():
            found = {hashlib.sha256(block.encode("utf-8")).hexdigest()[:16]: block for block in rule_blocks(self.read(name))}
            unpinned = {digest: block for digest, block in found.items() if digest not in pinned}
            missing = [digest for digest in pinned if digest not in found]
            self.assertFalse(unpinned or missing, f"{name}: new or changed blocks {unpinned}; pinned blocks no longer present {missing}")
            self.assertEqual(len(pinned), len(rule_blocks(self.read(name))), name)

    def test_template_and_adr_carry_the_preauthorisation(self):
        template = " ".join(self.read("templates/task-contract.md").split())
        self.assertIn("pre-authorise here, for each named layer and naming the number, up to 2 further rounds after that layer's last budgeted round", template)
        self.assertIn("The cap and the default are unchanged", template)
        adr = " ".join(self.read("spec/adr/review-stop-rule.md").split())
        for phrase in (
            "4. The Change Owner may pre-authorise, in the approved Task Contract, the decision that follows the cap",
            "a decision the human records in advance, conditioned on a rank-1 finding in code, tests or security posture in the round before, is a human decision after two rounds",
            "**A default of four rounds per layer.** It contradicts the locked [REQ] of section 11.3",
            "(Decision 4 gives the form in which that decision is taken in advance)",
            "**Decision 4 adds no round by itself.**",
            '"approved as drafted, go ahead", on `spec/AIDF-REVIEW-BUDGET-PREAUTHORISATION-TASK-CONTRACT.md`',
        ):
            self.assertIn(phrase, adr)

    def test_record_text_rule_and_its_four_exceptions_are_in_core_05_review(self):
        text = " ".join(self.read("core/05-review.md").split())
        for phrase in (
            "### Findings about record text",
            "is advisory, whatever its rank",
            "a sentence that overstates a guarantee a consumer relies on",
            "a required artifact, rehearsal or acceptance that is missing",
            "a SHA, digest or hash that a gate or a consumer uses and that is wrong",
            "a record that contradicts the code or tests it describes",
        ):
            self.assertIn(phrase, text)

    def test_templates_and_metric_carry_the_new_fields(self):
        self.assertIn("**Review budget**", self.read("templates/task-contract.md"))
        approval = self.read("templates/approval-request.md")
        for field in ("**Requested (UTC):**", "**Answered (UTC):**", "**Active minutes (manual):**"):
            self.assertIn(field, approval)
        self.assertIn("verification/pack_facts.py", self.read("templates/evidence-pack.md"))
        self.assertIn("Human minutes, computation", self.read("metrics/definitions.md"))


class OutcomeRecordDeclarationTests(unittest.TestCase):
    """The declaration in AC8 of this change's contract, tried against the comparison that section 6 names."""

    def setUp(self):
        spec = importlib.util.spec_from_file_location("binding", ROOT / "verification" / "review_head_binding_evidence.py")
        assert spec and spec.loader
        self.binding = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.binding
        spec.loader.exec_module(self.binding)
        contract = json.loads((ROOT / "verification" / "review-efficiency-core-task-contract.json").read_text(encoding="utf-8"))
        text = next(c["text"] for c in contract["acceptance_criteria"] if c["id"] == "AC8")
        import re

        report = re.search(r"report patterns are (\S+\.md);", text)
        dispositions = re.search(r"dispositions file is (\S+\.md)\.", text)
        assert report and dispositions
        self.decl = {
            "review_reports": [report.group(1)],
            "security_reports": [],
            "dispositions": dispositions.group(1),
            "pack": "verification/review-efficiency-core-evidence-pack.json",
            "contract": "verification/review-efficiency-core-task-contract.json",
        }
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@example.invalid")
        git(self.repo, "config", "user.name", "t")
        (self.repo / "verification").mkdir()
        for key in ("pack", "contract"):
            (self.repo / self.decl[key]).write_text((ROOT / self.decl[key]).read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
        (self.repo / self.decl["dispositions"]).write_text("# Dispositions\n\nEntry one.\n", encoding="utf-8", newline="\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "reviewed head")
        self.reviewed = git(self.repo, "rev-parse", "HEAD")

    def test_the_declared_paths_cover_a_report_and_a_dispositions_append(self):
        (self.repo / "verification" / "review-efficiency-core-verifier-report-round3.md").write_text("# Report\nOutcome: PASS\n", encoding="utf-8", newline="\n")
        with open(self.repo / self.decl["dispositions"], "a", encoding="utf-8", newline="\n") as fh:
            fh.write("\nEntry two.\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "outcome records")
        self.assertEqual([], self.binding.compare(str(self.repo), self.reviewed, "HEAD", self.decl))

    def test_a_later_pack_edit_is_not_an_outcome_record(self):
        pack = self.repo / self.decl["pack"]
        document = json.loads(pack.read_text(encoding="utf-8"))
        document["e4"][-1]["status"] = "pending_outcome"
        pack.write_text(json.dumps(document, indent=2), encoding="utf-8", newline="\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "pack edit")
        self.assertTrue(self.binding.compare(str(self.repo), self.reviewed, "HEAD", self.decl))


class PackFactsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@example.invalid")
        git(self.repo, "config", "user.name", "t")
        (self.repo / "verification").mkdir()
        self.report = self.repo / "verification" / "x-verifier-report.md"
        self.report.write_bytes(b"# Report\r\nPASS\r\n")
        (self.repo / "tests").mkdir()
        (self.repo / "tests" / "test_widget.py").write_text("class T:\n    def test_widget_works(self):\n        pass\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "c1")
        self.sha = git(self.repo, "rev-parse", "HEAD")
        self.blob_sha256 = hashlib.sha256(git_blob(self.repo, "verification/x-verifier-report.md")).hexdigest()

    def pack(self, **security):
        base = {"artifact": "verification/x-verifier-report.md", "artifact_sha256": self.blob_sha256, "status": "passed"}
        base.update(security)
        return {"residual_risk": f"Reviewed at commit {self.sha[:10]}; test_widget_works covers it.", "security_evidence": base}

    def messages(self, pack, head="HEAD"):
        return [f.message for f in pack_facts.check_pack_facts(pack, self.repo, head)]

    def test_true_facts_pass(self):
        self.assertEqual([], self.messages(self.pack()))

    def test_wrong_report_hash_fails(self):
        wrong = self.messages(self.pack(artifact_sha256="0" * 64))
        self.assertTrue(any("does not match the committed blob" in m for m in wrong))

    def test_hash_is_of_the_committed_blob_not_the_working_copy(self):
        self.report.write_bytes(b"changed in the working tree only\n")
        self.assertEqual([], self.messages(self.pack()))

    def test_missing_report_file_fails(self):
        missing = self.messages(self.pack(artifact="verification/absent-report.md"))
        self.assertTrue(any("names no committed file" in m for m in missing))

    def test_unknown_commit_fails_and_known_commit_passes(self):
        pack = self.pack()
        pack["residual_risk"] = "Reviewed at commit 1234abc and at " + self.sha[:12] + "."
        found = self.messages(pack)
        self.assertEqual(["cited hexadecimal string 1234abc does not resolve to a git object"], found)

    def test_a_digest_prefix_is_not_taken_for_a_commit(self):
        pack = self.pack()
        pack["residual_risk"] = "The suite digest 91c8d1ee is accepted; SHA-256 4f0a9b13c2 too."
        self.assertEqual([], self.messages(pack))

    def test_undefined_test_name_fails_and_module_names_pass(self):
        pack = self.pack()
        pack["residual_risk"] = "Covered by test_widget_works, test_widget (module) and test_missing_case."
        self.assertEqual(["cited test test_missing_case is not defined in a tracked Python file at HEAD"], self.messages(pack))

    def test_root_level_artifact_and_one_character_test_names_are_checked(self):
        missing = self.messages(self.pack(artifact="missing.md"))
        self.assertTrue(any("names no committed file" in m for m in missing))
        pack = self.pack()
        pack["residual_risk"] = "Covered by test_x."
        self.assertEqual(["cited test test_x is not defined in a tracked Python file at HEAD"], self.messages(pack))

    def test_a_sha_with_no_digit_or_no_letter_is_not_checked(self):
        pack = self.pack()
        pack["residual_risk"] = "Words such as deadbee and numbers such as 1234567 are not commit citations."
        self.assertEqual([], self.messages(pack))

    def test_an_annotated_path_is_verified_against_its_leading_file(self):
        zeros = "0" * 64
        path = "verification/x-verifier-report.md"
        for artifact in (f"{path} -- the report", f"{path} (committed)", f"{path} ", f"{path}, and the CI job", f"({path})"):
            wrong = self.messages(self.pack(artifact=artifact, artifact_sha256=zeros))
            self.assertTrue(any("does not match the committed blob" in m for m in wrong), artifact)
            self.assertEqual([], self.messages(self.pack(artifact=artifact)), artifact)

    def test_the_repositorys_own_annotated_packs_fail_with_a_wrong_hash(self):
        for name in ("phase9-ci-gate-integration-evidence-pack.json", "phase9-ci-policy-transition-evidence-pack.json"):
            with self.subTest(name):
                pack = json.loads((ROOT / "verification" / name).read_text(encoding="utf-8"))
                cited = pack["security_evidence"]["artifact"].split()[0]
                if not (ROOT / cited).is_file():
                    # The public tree leaves out the security review these packs cite (verification/public-export-manifest.json), so the check cannot run there.
                    self.skipTest(f"{cited} is not in this tree")
                own = [f.message for f in pack_facts.check_pack_facts(pack, ROOT) if "artifact_sha256" in f.message]
                self.assertEqual([], own, name)
                pack["security_evidence"]["artifact_sha256"] = "0" * 64
                wrong = [f.message for f in pack_facts.check_pack_facts(pack, ROOT) if "artifact_sha256" in f.message]
                self.assertEqual(1, len(wrong), name)

    def test_a_path_shaped_artifact_that_cannot_be_checked_is_a_finding(self):
        zeros = "0" * 64
        for shape in ("verification/my report.md", "verification" + chr(92) + "s.md", "../outside.md", "verification/s.md:HEAD"):
            found = self.messages(self.pack(artifact=shape, artifact_sha256=zeros))
            self.assertTrue(any("looks like a file but names no committed file" in m for m in found), shape)

    def test_hash_or_blob_words_do_not_hide_a_commit_citation_and_case_is_ignored(self):
        for sentence in ("commit hash 1234abc", "blob of commit 1234abc", "Reviewed at 1234ABCD."):
            pack = self.pack()
            pack["residual_risk"] = sentence
            self.assertEqual(1, len(self.messages(pack)), sentence)

    def test_free_text_artifact_is_not_checked(self):
        self.assertEqual([], self.messages(self.pack(artifact="CI job 79 archive", artifact_sha256="0" * 64)))

    def test_head_must_be_head_or_hex(self):
        self.assertEqual(["--head must be HEAD or a hexadecimal revision"], self.messages(self.pack(), head="main; rm"))

    def test_command_line_exit_status(self):
        pack_file = self.repo / "pack.json"
        pack_file.write_text(json.dumps(self.pack()), encoding="utf-8")
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(0, pack_facts.main(["--root", str(self.repo), "--evidence", "pack.json"]))
        pack_file.write_text(json.dumps(self.pack(artifact_sha256="1" * 64)), encoding="utf-8")
        with redirect_stdout(out):
            self.assertEqual(1, pack_facts.main(["--root", str(self.repo), "--evidence", "pack.json"]))
        self.assertIn("FAIL [pack-facts]", out.getvalue())


def git_blob(repo, path):
    return subprocess.run(["git", "cat-file", "blob", f"HEAD:{path}"], cwd=repo, check=True, capture_output=True).stdout


if __name__ == "__main__":
    unittest.main()
