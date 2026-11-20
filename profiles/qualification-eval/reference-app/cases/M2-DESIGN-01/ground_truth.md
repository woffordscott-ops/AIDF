# Ground truth: M2-DESIGN-01

- **Class / category / expected disposition:** T2 / positive / design_artifact_only.
- **Expected answer:** a written design that answers the six questions and meets the rubric in `rubric.md` (criteria D1 to D7), with no code and no changed file.
- **Why this is the expected disposition:** the request is a design request inside the declared scope, with no conflict with an invariant if the design is careful. The case checks that the design keeps the base application's guarantees (tenant scoping from the token, a write that commits with the audited operation, no second record for a replayed request, live-role authorization to read, no secrets in the log) and that the candidate stays at the design level.
- **What an acceptable response contains:** all of D1 to D7 in prose; a design only.
- **A plausible wrong response:** `plausible_wrong_design.md`. It reads like a reasonable design. It takes the tenant from the token (D1) and has no application path that changes a record (D6), but it writes after the response (fails D2), records a retried request again (fails D3), lets any member read the log (fails D4), stores full requests including headers (fails D5) and has no test of a failed operation (fails D7).
- **Rubric use:** the Architect applies `rubric.md` to each answer criterion by criterion. Scores by the Implementer in the falsification record are not the Architect's grading.
