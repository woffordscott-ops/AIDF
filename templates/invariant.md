---
owner: framework-maintainer
load_when: the Invariants Register is created or amended, as part of your project's Layer 3 architecture governance
max_length: 1 row per invariant
last_verified: 2026-10-06
---

# Invariant Record

`ID · statement · rationale · scope · enforcement · owner · status`

| Field | Value |
|---|---|
| ID | |
| Statement | |
| Rationale | |
| Scope | |
| Enforcement | `GENERATED` \| `CI-ENFORCED` \| `TEST-ENFORCED` \| `PROSE-ONLY` |
| Owner | |
| Status | Active \| Superseded |

`enforcement` is descending order of trust: `GENERATED` (violation impossible by construction) → `CI-ENFORCED` (a check fails the build) → `TEST-ENFORCED` (a specific test asserts it) → `PROSE-ONLY` (nothing enforces this — labeled explicitly so no one mistakes aspiration for guarantee).

**Status:** this schema is defined from the start, because classification and evidence work reference invariants by ID. The Invariants Register itself — and therefore any populated rows — doesn't exist until your project completes its own Layer 3 architecture-governance pass (`core/03-architecture.md`, via `instantiation/`). Do not treat an empty or missing register as zero invariants; treat it as not yet instantiated for your project.
