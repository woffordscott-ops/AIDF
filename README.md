---
owner: framework-maintainer
load_when: onboarding to the framework, or orienting a new contributor/agent
max_length: 2 pages
last_verified: 2026-10-20
---

# AI-Assisted Development Framework (AIDF)

AIDF is a governance framework for AI-assisted software development: a lifecycle, a task-classification model, execution-mode definitions, a role/authority model, and a verification and review model, sized so that routine work stays light and risky work gets real human control. The goal is calibration, not uniform caution — a formatting fix and a change to authentication logic don't get the same process; what scales with risk is the amount of ceremony, not the amount of code.

It exists because AI-generated defects fail differently than human-written ones: they tend to look plausible rather than obviously wrong — syntactically clean, locally reasonable, passing the tests written for the happy path, and still wrong on the case that matters. That makes review-by-reading weak as a primary control no matter how careful the reviewer is, which is why AIDF treats executable evidence (tests that fail before a fix and pass after, counterfactual checks that prove a control blocks what it claims to block) and clear human authority boundaries — who can accept risk, who can waive a control, who signs off — as the things actually doing the work. Adopting it means AI-assisted development's speed doesn't come bundled with its most dangerous failure mode by default.

This is orientation, not a policy document. Policy lives in `KERNEL.md` and `core/`.

## Getting started

Clone this repository and run `python3 -m unittest discover -s verification/tests` — it should finish with `OK` (some tests are skipped on some platforms). That's the entire verification suite; there's nothing to install beyond Python 3, and no server to start.

Before anything else: name a **Change Owner** and an **Architect** for your project (`core/02-authority.md` §1). One person can hold both — solo operation is explicitly supported — but every later gate assumes these roles exist and are held by *someone*. Then:

1. **Read `KERNEL.md`** (≤2 pages) — jurisdiction and the control-selection ladder; `core/` elaborates on it one topic per file.
2. **Produce your project context pack** (Layer 3) — `instantiation/bootstrap-new.md` if you're starting before code exists, or `instantiation/onboard-existing.md` if you already have a codebase. Output: an architecture overview, invariants register, contracts, and security model, checked structurally by `instantiation/check_context_pack.py`.
3. **Qualify your own tool/model** (Layer 2) — `profiles/qualification-protocol-v1.1.md`. Output: a profile scoped to your exact repository, revision, tool, model, and environment. This repository's own example profile doesn't transfer to your project. To run a qualification without a private project, use the public reference suite (`profiles/qualification-eval/suite-v2.json`, digest `91c8d1eefb846aa44d3af8dec9a34ccbfe72979cbd37ae236af661ffd63710e6`), which also needs `profiles/qualification-protocol-v1.2.md` (an additive amendment to v1.1 for suites other than the private pilot's). It pins revision `6d647332048862bfa464d11374f53ea6d9cdcfbd` of the project's private history, which a published copy of this repository does not contain: in a published copy, read the case material and the suite file from the commit you checked out and record that commit in your profile (`profiles/README.md` says why the pin is not changed here). Give a fresh instance of your tool and model only each case's prompt and starting workspace, never its ground truth, rubric, hidden tests or reference solution. M0 is graded byte-exactly against an expected diff for the transform case and by an evaluator against an expected disposition and ground truth for the other three; M1 by hidden tests plus plausible-wrong implementations for the three implementation cases and by expected disposition against ground truth for the five others; M2 by the Architect's frozen rubric; M3 by ground truth and rubric. It is a partial suite (16 of the 21 cases the parent contract planned) and its answer key is public, so a result says nothing about a candidate that had access to it; read `profiles/qualification-eval/REFERENCE-SUITE.md` first.
4. **Run day to day under `core/01-lifecycle.md`** — every unit of work from here on gets classified T0–T3 and gated accordingly.

## The locked three-layer model

| Layer | Name | Contents | Status |
|---|---|---|---|
| **Layer 1** | Core Governance | Principles, lifecycle, classification, execution modes, roles, authority, architecture governance, verification, review, context, cost. | V1.2.2 is the immutable architecture baseline; the evidence-grounded v1.3.0 Phase 6 revision is formally closed. |
| **Layer 2** | Tool/Model Qualification | The qualification eval and the resulting model→mode profile. | This repository's own example profile (`codex-cli` / `gpt-5.6-sol`) was qualified for M0–M3 against its own pilot's suite until its per-mode expiries of 2026-10-09, which have passed, so it is not currently eligible and requalification is required — evidence, not something adopters inherit. See `profiles/README.md` for the expiries and the Assignment rule; a published copy of this repository does not contain that profile. |
| **Layer 3** | Project Instantiation | The project context pack, via existing-project discovery or greenfield bootstrap. | Protected-integrated and formally exited: merged to protected main, passed exact-head Linux CI and separated review, accepted by the Change Owner on 2026-09-28. |

For the exact commits, pipelines, and Change Owner approval dates behind the status above — and this framework's own build history in full — see `IMPLEMENTATION-STATUS.md`.

## Repository structure

```
ai-development-framework/
├── README.md                 this file
├── KERNEL.md                 ★ always loaded, ≤2pp — the behavior-changing core
├── IMPLEMENTATION-STATUS.md  traceability ledger: specified vs. implemented vs. enforced
├── LICENSE / NOTICE          Apache License 2.0
├── core/
│   ├── 01-lifecycle.md       stages, gate matrix, classification, Task Contract, Pattern Registry
│   ├── 02-authority.md       roles, authority levels, gates, separation of duties
│   ├── 03-architecture.md    architecture governance (overview, invariants, contracts, ADRs)
│   ├── 04-verification.md    evidence ladder, counterfactuals, recovery, test integrity
│   ├── 05-review.md          separated review, findings, dispositions, precision
│   └── 06-context-and-cost.md  context-loading triggers and cost controls
├── modes/
│   └── execution-modes.md    M0–M3 definitions and the declared/qualified rule
├── templates/                 11 Phase-1 templates — the artifacts agents fill in day to day
├── profiles/                  Layer 2 protocol, suite, environments, and qualification records (active)
├── instantiation/              Layer 3 implementation, protected-integrated
├── metrics/                    metric definitions and classification-audit procedure
├── verification/               deterministic checks, policy, records, and fixtures
└── spec/                       the locked architecture spec and the Phase 1 implementation brief
```

`CHANGELOG.md` tracks locked-spec version changes (currently `v1.3.0`), not every merged capability — see `IMPLEMENTATION-STATUS.md` for the latter.

## Contributing and reporting a security problem

See `CONTRIBUTING.md` (external contributions are not accepted yet) and `SECURITY.md` (how to report a defect in the framework or its checkers).

## Evidence archives

The `verification/` and `profiles/qualification-runs/` folders hold the evidence behind this framework's own build and its example qualification, recorded as it happened. That evidence still carries the original private pilot's identifiers (the maintainer's workstation username, an internal hostname and the pilot project's path). They were left in place on purpose: the archives are bound by SHA-256 digests, and redacting them would break the proofs. You do not need these folders to adopt AIDF, and a distribution can leave them out.

## What is intentionally not implemented yet

None of these block adopting AIDF today — each describes a manual process you can run yourself (the same way the original private pilot did), just not yet packaged as reusable, automatically-enforced tooling other projects can drop in. Building generalized versions of this before a second real adopter exists to prove what "reusable" needs to mean would be guessing, so none of it has been built yet:

- **Architecture-lint enforcement** — Layer 3 defines the invariants, contracts, and ADRs your project produces, but AIDF doesn't ship a CI gate that automatically checks your code against them. One exists, but only for the original pilot's specific codebase; it doesn't generalize.
- **Metric reporting** — `metrics/` defines what to measure and how to audit it; the only metrics actually collected so far are the pilot's own project-local numbers. There's no shipped collection or reporting tool beyond the schema.
- **Review-provenance enforcement as reusable guidance** — `core/05-review.md` makes separated review operational, and a CI gate exists that stops an author from faking review history — again, only wired into the original pilot's own CI policy. Whether this becomes general framework guidance for other adopters is still an open design question.

Two unrelated, narrower gaps:

- **Qualification of Claude Code or Cursor** — only `codex-cli` / `gpt-5.6-sol` has ever been qualified, because exact, reproducible runtime/model identities for Claude Code and Cursor were unavailable to run the qualification suite against — not a judgment that they're unsuitable.
- **A pre-built routing authorization mapping** — the trust mapping automatic routing requires is deliberately not shipped. Building your own is optional and its own governed task; see `instantiation/README.md`'s "After Layer 3" section and `profiles/README.md`'s "Specialty dimension and automatic routing" section.

## Where the locked architecture specification lives

`spec/AIDF-v1.2.2-design-proposal.md` — Layer 1, locked at V1.2.2. This is the authoritative specification; nothing in this repository overrides it, and this repository does not modify it — including its own header, which still reads "Draft for review," leftover from before this revision was locked (see `IMPLEMENTATION-STATUS.md`'s Implementation Conflicts, item 3). Where an implementation artifact and the spec appear to disagree, the spec wins and the disagreement is recorded in `IMPLEMENTATION-STATUS.md` under Implementation Conflicts. The Phase 1 implementation assignment that produced this repository is `spec/PHASE1-IMPLEMENTATION-BRIEF.md`.

## License

Licensed under the Apache License, Version 2.0 — see `LICENSE` and `NOTICE`.
Free to use, modify, and redistribute, including commercially. This license
covers this repository's content (the method, policy schema, evaluation
suite, and reference CLI); it says nothing about and does not restrict any
separately operated hosted service, managed qualification offering, or
support engagement.
