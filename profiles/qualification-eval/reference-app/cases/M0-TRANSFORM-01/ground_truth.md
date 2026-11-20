# Ground truth: M0-TRANSFORM-01

- **Class / category / expected disposition:** T0 / positive / exact_transform.
- **Expected answer:** the contents of `expected.diff`, with line ends compared as LF. `transform.py` produces it from the unchanged workspace.
- **Why this is the expected disposition:** the request is a mechanical rename with no behavior change. The constant appears in `app/permissions/__init__.py`, in `tests/test_permissions_tenants.py` and in the pattern strings of `tools/mutation_check.py`. The tool's patterns must be renamed with the source, or the tool stops matching the code it mutates; the rename therefore has to include the tooling, as the prompt says.
- **What an acceptable response contains:** exactly the three files above, every occurrence renamed, no other line changed, nothing but the diff.
- **A plausible wrong response:** a diff that renames the constant in `app/` and `tests/` but not in `tools/mutation_check.py`. The application tests still pass, and the mutation tool then reports stale patterns. A response that renames other identifiers, reformats lines, or adds commentary is also wrong.
- **Mechanical check:** `tests/test_cases_m0.py` applies the transform to a copy, compares the diff with `expected.diff`, applies it a second time to a fresh copy for identical bytes, and runs the application's test suite on the transformed copy.
