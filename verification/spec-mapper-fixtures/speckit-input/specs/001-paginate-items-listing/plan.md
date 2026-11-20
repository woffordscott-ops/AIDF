# Implementation Plan: Paginate the Items Listing

**Branch**: `001-paginate-items-listing` | **Date**: 2026-11-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-paginate-items-listing/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Callers of the items listing can ask for one page. `limit` is a whole number from 1 to 100 and defaults to 20. `offset` is a whole number from 0 and defaults to 0. A successful response returns that sku-ordered slice in `items` and the full catalog count in `total`. A caller who passes no parameters gets the first 20 items (SKU-001 through SKU-020) and a total of 250, not all 250 items. A present value that is missing a number, not a whole number, or out of range is refused with status 400 and an error message that names the parameter.

The handler in `inventory/api.py` validates the parameters. `list_items` in `inventory/store.py` may change so that it returns the ordered page and the total. Single-item lookup stays as it is.

## Technical Context

**Language/Version**: Python 3.10 or newer. The package already uses `list[Item]`, `dict[str, str]`, and `Item | None`. This workspace runs Python 3.14.7. There is no dependency manifest and no version pin file.

**Primary Dependencies**: Python standard library only (`dataclasses` in the store, `unittest` in the tests). No web framework. The listing is a function, `get_items(params) -> (status, body)`, not a listening server.

**Storage**: In-memory tuple of 250 `Item` values in `inventory/store.py`. No database.

**Testing**: `unittest`, run as `python -m unittest` from the repository root. The current suite is `tests/test_api.py` (2 tests). Observed on 2026-11-05: `python -m unittest` reported `Ran 2 tests` and `OK`. Those tests still expect the unpaged listing.

**Target Platform**: Local Python process on the developer machine. The sample is not deployed.

**Project Type**: In-process request handlers (a small library). `GET /items` is the name of the listing operation implemented by `get_items`.

**Performance Goals**: Correct pages over the existing 250-item catalog. Each listing sorts that catalog and slices one page. No separate throughput target.

**Constraints**: `limit` 1 through 100 inclusive, default 20. `offset` greater than or equal to 0, no upper bound, default 0. Success includes `items` and `total`. Refusal is status 400 and a message that names `limit` or `offset`. Item fields stay sku, name, and quantity. `get_item` stays unchanged. No new dependency, service, or storage.

**Scale/Scope**: One catalog of 250 items. Two production modules (`inventory/api.py`, `inventory/store.py`) and one test module (`tests/test_api.py`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is the stock template. Principle titles, principle text, the extra sections, and the governance block are still placeholders (`[PRINCIPLE_1_NAME]` through `[GOVERNANCE_RULES]`, unfilled version and dates). The commented examples (library-first, a CLI, test-first) are not adopted rules, so they are not gates.

**Before Phase 0**: PASS. There is no ratified principle to violate. The change stays inside the existing inventory package, adds no dependency, and adds no storage.

**After Phase 1**: PASS. The design adds one result value, `ItemPage`, next to the existing `Item` dataclass, and keeps validation in the handler that already returns status codes. No extra project, repository layer, or service is introduced. Complexity Tracking does not apply.

## Project Structure

### Documentation (this feature)

```text
specs/001-paginate-items-listing/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── items-listing.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
inventory/
├── __init__.py          # unchanged
├── api.py               # get_items validates limit and offset; get_item unchanged
└── store.py             # Item, ItemPage, list_items, find_item

tests/
├── __init__.py          # unchanged
└── test_api.py          # listing expectations updated when the feature is implemented
```

**Structure Decision**: Use the existing single package. The listing change belongs in `inventory/store.py` (ordered page and total) and `inventory/api.py` (defaults, whole-number checks, status, and response body). Tests stay in `tests/test_api.py`. No `src/` tree, no frontend, and no new package.

## Complexity Tracking

No constitution violations. This section does not apply.
