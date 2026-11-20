---
description: "Tasks for paginating the items listing"
---

# Tasks: Paginate the Items Listing

**Input**: Design documents from `/specs/001-paginate-items-listing/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: The specification does not request a test-first program. `tests/test_api.py` already exists and currently expects a no-parameter listing of 250 items. Each story below updates that file so the story can be checked with `python -m unittest`. Write the new assertions before the matching behavior so those new assertions fail until that story is implemented.

**Organization**: Tasks are grouped by user story so each story can be implemented and checked on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Existing package: `inventory/` and `tests/` at the repository root
- Feature docs: `specs/001-paginate-items-listing/`
- Paths below match `specs/001-paginate-items-listing/plan.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Stay inside the existing package. No new project and no new dependency.

- [ ] T001 Confirm `python -m unittest` runs from the repository root, and leave `inventory/__init__.py` and `tests/__init__.py` unchanged per `specs/001-paginate-items-listing/plan.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The page result and the sku-ordered slice that every story returns

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T002 Add a frozen dataclass `ItemPage` in `inventory/store.py` with `items` (list of `Item`) and `total` (int). `total` is the count of every item in the catalog, not the length of `items`. The length of `items` is never greater than `limit`, and it is 0 when `offset` is greater than or equal to the catalog count.
- [ ] T003 Change `list_items` in `inventory/store.py` to `list_items(limit: int = 20, offset: int = 0) -> ItemPage`. Sort the catalog by sku ascending, set `total` to the length of that full ordered catalog, and set `items` to `ordered[offset:offset + limit]`. Callers pass a `limit` that is a whole number from 1 to 100 inclusive (default 20) and an `offset` that is a whole number greater than or equal to 0 with no upper bound (default 0). This function does not return a status code.

**Checkpoint**: `list_items(20, 0)` yields 20 items and a total of 250; `list_items(20, 250)` yields an empty item list and a total of 250

---

## Phase 3: User Story 1 - Request one page of the catalog (Priority: P1) 🎯 MVP

**Goal**: A caller who sends a valid `limit`, a valid `offset`, or both receives that sku-ordered page and the catalog total

**Independent Test**: Call `get_items` with an explicit valid window (for example `{"limit": "20", "offset": "40"}`) and confirm status 200, the matching sku slice, and `total` 250. A call that passes neither parameter still returns all 250 items until User Story 2.

### Tests for User Story 1

- [ ] T004 [P] [US1] Add success-page checks in `tests/test_api.py` for `get_items`: `{"limit": "20", "offset": "0"}` returns SKU-001 through SKU-020 and `total` 250; `{"limit": "20", "offset": "40"}` returns SKU-041 through SKU-060 and `total` 250; `{"limit": "1"}` returns one item (SKU-001) and `total` 250; `{"limit": "100"}` returns 100 items and `total` 250; `{"limit": "20", "offset": "240"}` returns SKU-241 through SKU-250 (10 items) and `total` 250; `{"offset": "250"}` and `{"offset": "1000"}` return an empty `items` list and `total` 250; `{"limit": "020", "offset": "0"}` returns SKU-001 through SKU-020 and `total` 250. Each item has only `sku`, `name`, and `quantity`.

### Implementation for User Story 1

- [ ] T005 [P] [US1] In `get_items` in `inventory/api.py`, when at least one of `limit` and `offset` is present and every present value fully matches `^-?[0-9]+$` and is in range (`limit` from 1 to 100 inclusive, `offset` greater than or equal to 0), fill an absent `limit` with 20 and an absent `offset` with 0, call `list_items`, and return status 200 with `items` (sku, name, quantity, ascending sku order) and `total` (full catalog count). Ignore keys other than `limit` and `offset`. Leave a call that passes neither key returning the full catalog until T007.

**Checkpoint**: Explicit valid pages match `specs/001-paginate-items-listing/contracts/items-listing.md`. The no-parameter call is still the old full catalog.

---

## Phase 4: User Story 2 - Call the listing with no parameters (Priority: P2)

**Goal**: A caller who passes no parameters receives the first 20 items and a total of 250

**Independent Test**: Call `get_items({})` and confirm status 200, 20 items, skus SKU-001 through SKU-020, and `total` 250

### Tests for User Story 2

- [ ] T006 [P] [US2] Change `test_all_items_are_listed` in `tests/test_api.py` so `get_items({})` expects status 200, 20 items, skus SKU-001 through SKU-020 in that order, and `total` 250, not a list of 250 items

### Implementation for User Story 2

- [ ] T007 [P] [US2] In `get_items` in `inventory/api.py`, when neither `limit` nor `offset` is present, use `limit` 20 and `offset` 0 and return the same status-200 body as a valid page (`items` plus `total`). A caller who passes no parameters receives SKU-001 through SKU-020 and `total` 250.

**Checkpoint**: No-parameter listing matches User Story 2. Explicit pages from User Story 1 still match.

---

## Phase 5: User Story 3 - Reject an unusable page size or skip (Priority: P3)

**Goal**: A present value that is missing a number, not a whole number, or out of range is refused with status 400 and a message that names the parameter

**Independent Test**: Call `get_items` with a bad `limit` and a bad `offset` and confirm status 400, the error sentence names that parameter, and the body has no `items`

### Tests for User Story 3

- [ ] T008 [P] [US3] Add refusal checks in `tests/test_api.py`: present `limit` values `""`, `" "`, `"abc"`, `"20abc"`, `"1.5"`, `"20.0"`, `"+20"`, `"1e2"`, `"0"`, `"-1"`, `"-0"`, and `"101"` return status 400, `{"error": "limit must be a whole number from 1 to 100"}`, and no `items` key; present `offset` values `"-1"`, `"1.5"`, and `""` with an acceptable or absent `limit` return status 400, `{"error": "offset must be a whole number from 0"}`, and no `items` key; `{"limit": "0", "offset": "-1"}` returns the `limit` error. `{"offset": "-0"}` stays success (integer 0, default `limit` 20).

### Implementation for User Story 3

- [ ] T009 [P] [US3] In `get_items` in `inventory/api.py`, judge a present `limit` before a present `offset`. If `limit` is present and the entire value does not match `^-?[0-9]+$` (ASCII digits only), or the integer is less than 1 or greater than 100, return status 400 and `{"error": "limit must be a whole number from 1 to 100"}` with no `items` key. Otherwise, if `offset` is present and the entire value does not match `^-?[0-9]+$`, or the integer is less than 0, return status 400 and `{"error": "offset must be a whole number from 0"}` with no `items` key. A missing key is not a refusal. `-0` is the integer 0.

**Checkpoint**: Refusals match the contract, and the valid pages from User Stories 1 and 2 still succeed

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Keep single-item lookup as it is, and run the quickstart checks

- [ ] T010 Leave `get_item` in `inventory/api.py` and `find_item` in `inventory/store.py` unchanged, and keep `test_one_item` in `tests/test_api.py` expecting status 200 for sku `SKU-001` and status 404 with `{"error": "no such item"}` for sku `nope`
- [ ] T011 Run `python -m unittest` from the repository root and check every row in `specs/001-paginate-items-listing/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup. Blocks every user story
- **User Stories (Phase 3+)**: Depend on Foundational. Do them in order P1 → P2 → P3 because User Stories 1, 2, and 3 all edit `inventory/api.py` and `tests/test_api.py`
- **Polish (Phase 6)**: Depends on the user stories that are in scope

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Foundational. No dependency on User Stories 2 or 3
- **User Story 2 (P2)**: Starts after Foundational. Follows User Story 1 so the two edits to `get_items` do not collide. The no-parameter result is the story that replaces today's 250-item response
- **User Story 3 (P3)**: Starts after Foundational. Follows User Story 2 so the refusal branches are added to the finished success path

### Within Each User Story

- Update `tests/test_api.py` before the matching `inventory/api.py` behavior when working in task-id order
- `ItemPage` and `list_items` (Phase 2) are already in place before story work
- The story checkpoint is the independent test for that story

### Parallel Opportunities

- T004 and T005 touch different files and can run together
- T006 and T007 touch different files and can run together
- T008 and T009 touch different files and can run together
- T002 and T003 both edit `inventory/store.py`, so they stay sequential
- User Stories 1, 2, and 3 are not a parallel set: they share `inventory/api.py` and `tests/test_api.py`

---

## Parallel Example: User Story 1

```text
Task T004: Add success-page checks in tests/test_api.py
Task T005: Return the valid page from get_items in inventory/api.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Explicit valid pages return the sku slice and `total` 250
5. A caller who passes no parameters still receives all 250 items at this stop. The requested no-parameter result is User Story 2

### Incremental Delivery

1. Setup + Foundational → `list_items` can return a page and a total
2. User Story 1 → explicit `limit` / `offset` pages
3. User Story 2 → no-parameter call returns SKU-001 through SKU-020 and `total` 250
4. User Story 3 → bad `limit` and `offset` values are refused with status 400 and the parameter name
5. Polish → `get_item` still behaves as before, and `python -m unittest` matches the quickstart

### Parallel Team Strategy

One implementer should take the stories in priority order. Two people can split a story's test file and `inventory/api.py` (the [P] pairs above). They should not split User Stories 1, 2, and 3 across people at the same time.

---

## Notes

- [P] tasks = different files, no dependencies on an incomplete task
- [US1], [US2], and [US3] map to the user stories in `specs/001-paginate-items-listing/spec.md`
- Refusal sentences and the whole-number rule are fixed in `specs/001-paginate-items-listing/contracts/items-listing.md` and `specs/001-paginate-items-listing/research.md`
- Stop after any story checkpoint to check that story on its own
- The practical slice that meets the request (a defined no-parameter page, plus explicit pages) is User Story 1 followed by User Story 2. User Story 3 adds the refusals
