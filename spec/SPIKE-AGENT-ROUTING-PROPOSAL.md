---
owner: framework-maintainer
load_when: reviewing this Spike's findings or drafting the follow-on Task Contract
max_length: 1 page
last_verified: 2026-09-29
---

# Spike Report — automatic, cost-aware multi-agent task routing

**Status: closed.** Run by Claude Sonnet 5 under Architect role, authorized by Scott Wofford, Change Owner, on 2026-09-29. Non-mergeable — this is a design answer, not code.

- **Question the spike answers:** Given two or more Layer-2-qualified agents with declared execution modes, what is the minimum decision logic that selects which agent handles which sub-task of a classified change — under a cost constraint, preserving T2+ separation-of-duties and clean-room context curation — without a human manually relaying every handoff?
- **Time-box:** Compressed to one session rather than the proposed one week, since the running Architect already held the needed context (the qualified-profile schema, `modes/execution-modes.md`, `core/02-authority.md`, and this session's own lived instance of the exact problem) rather than needing to reconstruct it cold.

- **What was tried:** Re-derived the routing requirement from this session's own transcript rather than designing abstractly: catalogued every point where a task moved between Claude and Codex, what each handoff's briefing actually contained, and what distinguished which agent ended up doing which kind of work. Cross-checked that distinction against the existing qualified-profile schema (`profiles/qualified/phase8-codex-gpt-5-6-sol/*.json`) and the "Required context" fields already specified per mode in `modes/execution-modes.md`, to find what's genuinely missing versus what already exists as unformalized prose.

- **Findings:**
  1. **The specialty split in this session was not a skill difference — it was access plus track record.** Codex operated the GitLab/policy-repo ceremony because it held push credentials and had the branch/tag history proving prior competence there; I did adversarial security analysis because I could spawn scoped subagents and had no conflicting access. A routing design that models "specialty" as a soft skill rating will misroute; it has to model **hard eligibility** (does this agent have the access/tooling the sub-task requires — binary, not a preference) separately from **ranked domain qualification** (evidence-backed track record within the eligible set).
  2. **The specialty dimension must be qualified the same way mode already is — empirically, not declared.** The original design critique (`spec/AIDF-v1.2.2-design-proposal.md` §1.1) already rejected capability tiers as marketing categories for exactly this reason. A `specialty` field that's self-reported by a model or asserted by a vendor repeats that mistake. It needs the same treatment mode qualification already gets: suite-based, fail-closed, evidence-bound.
  3. **The context-curation rule already exists — it just isn't generalized.** `core/05-review.md` §2 already specifies, in prose, exactly what a Verifier receives (requirement, class, invariants, diff, evidence pack — explicitly not the author's rationale) versus what a Security Reviewer receives (the same, plus Bugbot's findings and dispositions, in order). That's a real, working handoff-curation spec for one specific pair of roles. The gap isn't inventing curation — it's generalizing this pattern into a package generator that constructs the right curated slice for *any* role handoff, mechanically, instead of a human writing a bespoke prompt each time (which is what I did, by hand, all session).
  4. **The separation-of-duties rule constrains routing as a hard post-filter, not an input to ranking.** Whatever ranking a router produces, the same instance selected for Implementer must be excluded from Verifier/Security Reviewer on the same change, and at T3 at least one of Verifier/Security Reviewer must be independently-context-derived. This has to run *after* the router's ranking, as an exclusion, never blended into the score — otherwise a cost-optimizing router has a live incentive to erode it.

- **Blast radius / architectural impact discovered:** Touches `profiles/` (a new specialty-domain field alongside the existing mode dimension, itself qualified via suite evidence, not declared) and adds two new artifacts: a deterministic routing/selection function (same style as `verification/qualification_check.py` — fail-closed, evidence-bound) and a handoff-package generator that mechanizes what `core/05-review.md` §2 already specifies in prose for review handoffs, generalized to other role pairs. Does **not** require changing `core/02-authority.md`'s separation-of-duties rule — the third out-of-scope boundary held; the rule is enforced as a post-ranking filter, not renegotiated. Does not touch the locked Layer 1 kernel.

- **Resulting Spec Confidence:** Clear — sufficient to write acceptance criteria for a follow-on Task Contract without further clarification.

- **Resulting classification recommendation:** **T2** for building the routing function and handoff-package generator themselves. Recommend the same provisional-before-qualified pattern `modes/execution-modes.md` already uses for mode declarations: a router's role *assignment* for any T2+ task starts **provisional** — Architect-declared and recorded, same as a mode declaration today — rather than fully autonomous, until the router itself has a track record. Autonomous routing without that interim step would be the one path that could quietly erode separation-of-duties under cost pressure, which is exactly what finding 4 flags. This provisional requirement is why the change doesn't need to be T3 — it's a control on the *rollout*, not evidence the routing logic itself is trip-wired work.

- **Next step:** Proceed to Task Contract (T2), scoped to exactly the three artifacts in "blast radius" above, with the provisional-rollout requirement written into its acceptance criteria as a non-negotiable line item, not left implicit.

- **Branch:** None cut — investigation was conducted by direct analysis against `origin/main`, no throwaway code produced.
