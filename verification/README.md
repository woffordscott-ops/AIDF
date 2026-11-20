---
owner: framework-maintainer
load_when: configuring or running mechanical verification controls
max_length: 3 pages
last_verified: 2026-10-06
---

# Mechanical Verification Checks

`aidf_check.py` is a dependency-free Python 3 checker for the controls this framework can settle mechanically. It reads strict JSON records, examines a bounded Git diff, and fails closed when required input is missing or malformed.

## Inputs

- **Task Contract JSON:** `schema_version`, `change_id`, `class`, `spec_confidence`, `intended_outcome`, `acceptance_criteria`, `declared_scope`, `tripwires`, approval fields for T2/T3, and any `dependency_changes`. Each dependency approval binds an exact path and immutable reference; a path-only approval is insufficient.
- **Evidence Pack JSON:** class-aware E0–E7 records. T1+ requires E3 or an `exemption_id` linked to exactly one valid registry record; T2+ requires E4–E6; T3 requires E7, recovery classification, and security evidence. E1 must pass rather than representing missing static/security coverage as green.
- **Policy JSON:** project-owned path rules for trip-wires and dependency manifests. Policy patterns are data, not executable expressions. Content exclusions must be narrow, versioned, and reviewed; this framework excludes its own governance prose so words describing a risk do not claim that the implementation performs it.
- **Automation policy JSON:** a protected, expiring project selection of a risk
  threshold and human-involvement profile. It uses a separate closed schema and
  semantic validator; invalid input never creates authority.
- **Diff:** either `--base` plus `--head`, or bounded fixture files supplied with `--changed-files` and `--diff-file`.

All referenced files must resolve beneath `--root`. JSON inputs are limited to 256 KiB and diff input to 10 MiB. Unknown top-level fields are rejected so misspellings cannot silently disable a control.

## Commands

```text
python3 verification/aidf_check.py all \
  --contract path/to/your-task-contract.json \
  --evidence path/to/your-evidence-pack.json \
  --policy verification/policy.json \
  --base <merge-request-diff-base> --head <commit>

python3 -m unittest discover -s verification/tests -v

python3 verification/aidf_check.py automation-policy \
  --automation-policy verification/fixtures/positive/automation-policy-expanded-streamlined.json \
  --expected-project-id your-namespace/your-project \
  --expected-policy-sha256 <protected-canonical-policy-sha256>
```

`all` runs contract/evidence completeness, exemption-registry integrity, declared scope, trip-wire classification, exact dependency approval, added-line secret scanning, and assertion/coverage inspection. Blocking failures exit non-zero and identify remediation. Assertion or coverage decline prints `NOTICE` and exits successfully; it is deliberately an inspection trigger, never proof that test intent was preserved or violated.

`automation-policy` validates the profile independently. `all` also validates it
when `--automation-policy` or `--automation-policy-b64` is supplied, preserving
backward compatibility for projects that have not adopted profiles. Consumers
must supply the expected project identity and canonical policy SHA-256 from a
protected source independent of the author-controlled policy record. They may
also supply a closed-schema task override, which is accepted only if it tightens
every project ceiling. Consumers
must treat a validation failure as `conservative` + `guided`, with autonomous
merge disabled; `resolve_automation_policy` provides that normalized fallback.

## Project adaptation

Copy or reference the framework as a pinned submodule, create project-specific contract/evidence JSON records, and version a project policy. Start with narrow path rules and expand them only from observed misses. Never weaken a rule merely to make CI green; change classification, obtain the required human approval, or correct the declared scope.

The checker does not claim architecture quality, requirement fitness, acceptable risk, or complete secret detection. Those remain in their proper jurisdictions.
