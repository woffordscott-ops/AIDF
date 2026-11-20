---
owner: framework-maintainer
load_when: lifecycle stage 6 (Task Contract), before implementation
max_length: an approver's opening, then 1 screen (T2/T3); 3 lines (T0/T1)
last_verified: 2026-11-05
---

# Task Contract

`core/01-lifecycle.md` §4. T0/T1: fill Part A only, inline in the task/PR description — no separate document required. T2/T3: fill Part A and Part B; status must be **Approved** by a human under Architect authority before implementation begins.

## Approver's opening (T2/T3 only; write it first, before Part A)

For the human who must approve this contract and has not seen the request. T0/T1 contracts have no opening: three lines, inline. The opening is part of the T2/T3 form: the author writes it, does not shorten it and does not leave a section out (a section with nothing to say says "none"). It is a summary, and Part A and Part B control: the opening adds no requirement, scope or criterion that Part A lacks and states no fact that the parts below do not support. The approver's decision is on the whole contract, not on the opening alone. Mark **BREAKING** each behaviour change that a caller or consumer must react to (a changed result for an existing call, a removed or renamed name, a stricter check). Use plain words.

- **Read this first** *(up to 6 lines)*: what this document is, the decision you are asked to make, and the order to read the rest in.
- **Problem** *(up to 5 lines)*: what is wrong or missing today.
- **Why it matters** *(up to 3 sentences)*: why this is an issue.
- **The change** *(up to 10 lines)*: what will be different afterwards, in plain language, with each BREAKING change marked.
- **Technical details** *(as long as the change needs)*: what will change, concrete enough to check against the code: files, functions, behaviour, error cases and their exact results.
- **What you need to decide** *(up to 15 lines)*: the assumptions made, any open question, what is out of scope, how it will be tested, the class proposed and why, and the main risk.

## Part A — Minimal (all classes)

- **Intended outcome:**
- **Acceptance criteria:** *(end with `Spec Confidence: [intake state] → Clear via [clarification/Spike reference]`; use `Clear at intake` when no re-evaluation was needed)*
- **Declared scope** (files/modules in scope):
- **Outcome records** *(optional; T2/T3. To opt in to `core/05-review.md` section 6 outcome records, add an acceptance criterion that lists the report path patterns and the dispositions file. Omit it to keep the default rule.)*:

## Part B — Plan (T2/T3 only)

- **Approach:**
- **Invariants touched:**
- **Evidence strategy** (counterfactual mechanism(s) planned — see `templates/evidence-pack.md`):
- **Protected files touched** *(T2/T3; files attested by the protected policy repository, found by `python verification/preflight.py`. `none`, or the paths and the cross-repository T3 change that updates their attestation. An edit to an attested file fails the pipeline job `aidf-governance`.)*:
- **Recovery / reversal approach** (per locked spec §10.4.1; operational form in `core/04-verification.md`):
- **New rule or checker** *(only when the change adds one; keep as a checklist)*: name the existing records it must still accept and run it over them before review; walk the rule through the lifecycle of the change that introduces it; search the locked documents for the limit it touches; do not edit an approved contract without asking the Change Owner; call a waiver a waiver, with its condition named; when a reviewer reproduces one shape of a check that enumerates, close the class (parse, do not pattern-match) or state in the pack the shapes that still pass, and write no guarantee about the class, because closing one reported shape is not a fix (`core/05-review.md` §2).
- **Review budget** *(T2/T3; `core/05-review.md` §2 and §5. Default T2: 2 Verifier rounds; T3: 2 Verifier and 2 Security rounds; a declared budget is at most 2 rounds per layer. When the last budgeted round does not pass, the Change Owner chooses and records: merge with advisories, accept a named residual, split, stop, or one more round (only for a rank-1 finding in code, tests or security posture). The Change Owner may also pre-authorise here, for each named layer and naming the number, up to 2 further rounds after that layer's last budgeted round; each starts only after a round of that layer that did not pass and found a rank-1 finding in code, tests or security posture, recorded in the dispositions first (`core/05-review.md` §2 and §5). The cap and the default are unchanged. Omit it to keep the two-round maximum.)*:

## Status (T2/T3; T0/T1 status is implicit in the author-established three-line Part A)

- **State:** Established | Approved
- **Established by** (author):
- **Approved by** (human, T2/T3 only — role: Architect):
- **Date:**
- **Class:** T0 | T1 | T2 | T3
- **Spec Confidence at intake:** Clear | Partial | Vague
- **Re-evaluated to Clear by:** clarification output or Spike report reference | N/A — Clear at intake

Spec Confidence must be `Clear` before implementation at every class. Recording `Clear` is not a substitute for recording the re-evaluation when the task entered as `Partial` or `Vague`.

Changes outside declared scope are re-declared here or split into a separate Task Contract — never absorbed silently.
