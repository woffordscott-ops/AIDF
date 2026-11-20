---
owner: framework-maintainer
load_when: lifecycle stage 8 (Self-verification), every class
max_length: 1 page; class-aware — only fields the class's required level demands
last_verified: 2026-10-14
---

# Evidence Pack

One page. This template is class-aware — fields above the class's required evidence level are marked `not required for this class` or omitted. Order: falsification first, evidence next, gaps and residual risk last. This pack is evidence of falsifiable correctness only; it carries no claim about requirement fitness, design quality, or risk acceptability (jurisdiction rule, `KERNEL.md`).

**Content rules.** The pack states the current state of the change. It carries
no review history and no round labels (reports are separate files that
the pack may name by path and committed-blob hash). Every claim names the
command, test, file or report it rests on. A universal word (every, all, both,
each) is used only with the set it covers listed; otherwise it is not used. A sentence that guarantees behaviour over an open set (fails closed,
cannot, never, always, every other, any other) names the test that fails when the guarantee is false; with no such test it is written as a
limit ("passes silently for X") or removed.
`python verification/pack_facts.py --evidence <pack>` verifies three things against the repository: the committed-blob SHA-256 of a
`security_evidence.artifact` that names a committed file (alone, or as its first word followed by prose; an artifact that looks like a file and names none is reported); that a cited hexadecimal string of 7 to 40 characters (with a digit and a letter, and not
directly after `digest`, `SHA-256` or `SHA256`, and not inside a longer word) resolves to a git object; and that a cited `test_` name is defined in a tracked Python file. Reviewers do not
argue those three. Every other cited fact is reviewed as before. The Implementer runs the check and records its output in the dispositions; it is not
yet a pipeline job. A narrative, count or history sentence is advisory in review (`core/05-review.md` §4).

- **Class:** T0 | T1 | T2 | T3
- **What would falsify this change:**
- **Jurisdiction:** This evidence addresses falsifiable correctness only; it does not establish requirement fitness, design quality, or acceptable risk.

## T0 (E0–E2) — all classes fill this section

- **E0 — Build:** artifact/command + result, or explicit `not applicable` reason
- **E1 — Static checks:** artifact/command + result for types/lint, secret scan, dependency/SCA; architecture-lint remains unavailable until your project's architecture governance (`core/03-architecture.md`) supplies boundary rules
- **E2 — Existing suite:** artifact/command + result + coverage boundary; use `unavailable` when no suite exists, never a manufactured pass

## T1+ (E0–E3)

- **E3 — Counterfactual mechanism used:** (reversion test | before/after reproduction | failure reproduction | mutation testing | baseline comparison | contract comparison | performance benchmark | architecture/invariant check | other falsifiable mechanism)
- **E3 artifact:**
- **The counterfactual, in one sentence** (what would have to be different for this evidence to fail):
- **What was not tested, and why:**
- **Exemption ID** (if E3 not satisfied): reference exactly one Open, unexpired registry record whose change ID and class match this pack — see `templates/exemption.md`. Not applicable at T0. No exemption exists at T3.

## T2+ (E0–E6)

- **E4 — Acceptance-criteria traceability** (each executable criterion → executing check + `passed` status + exact artifact; pending prose is invalid):
- **E5 — Negative / boundary / abuse coverage:**
- **E6 — Invariants touched + contract diff:**

## T3 (E0–E7)

- **E7 — Operation classification:** reversible | destructive but recoverable | truly irreversible
- **E7 — Status:** `passed` only after the applicable operational and recovery artifacts have executed
- **E7 — Operational behavior:** perf/load evidence where relevant, otherwise an explicit not-applicable reason
- **E7 — Failure observability:** the signal produced when this change fails
- **E7 — Flag / kill-switch:** executed control where applicable, otherwise an explicit not-applicable reason
- **E7 — Unrecoverable effects:** explicit accounting, including `none identified` where true
- **E7 — Reversible:** executed rollback artifact
- **E7 — Destructive but recoverable:** executed restore artifact · representative dataset · measured recovery time
- **E7 — Truly irreversible:** execution artifact · verified recovery point · restore path · irrecoverable effects and consequence · pre-execution human acceptance
- **Security evidence:** `passed` status · exact artifact · artifact SHA-256 · explicit coverage boundary (including ignored or dynamically sourced findings)

## Residual risk

The limits that remain, each as a plain fact: what was not tested, not run, or
not covered, and why. A review report is named by path and committed-blob hash.
