# Task Contract (DRAFT, not approved)

Drafted by `spec_mapper` with the mapping `speckit`. A draft is not an approval, a classification or evidence: a person fills each TODO, chooses the class and has it approved before any implementation.
Every line copied from a planning file sits in a quotation under its source file; nothing else in this draft comes from the sources.

- **Change id:** `001-paginate-items-listing` (the name of the folder that holds `specs/001-paginate-items-listing/spec.md`)
- **Files read:** `specs/001-paginate-items-listing/plan.md`, `specs/001-paginate-items-listing/spec.md`, `specs/001-paginate-items-listing/tasks.md`
- **Parts copied from the source:** 5 of 17. **Parts left as TODO:** 12.

## Approver's opening

- **Read this first:** TODO(author)
- **Problem:** TODO(author)
- **Why it matters:** TODO(author)
- **The change:** TODO(author)
- **Technical details:** TODO(author)
- **What you need to decide:** TODO(author)

## Part A: Minimal

- **Intended outcome:**
  - Source: `specs/001-paginate-items-listing/spec.md` (blocks)
    > ### User Story 1 - Request one page of the catalog (Priority: P1)
    >
    > A caller asks the items listing for a bounded page by supplying how many items to return and how many items to skip. The listing answers with that page only, in sku order, and says how many items exist in the whole catalog so the caller can tell whether further pages remain.
    >
    > **Why this priority**: Without a bounded page plus the catalog total, callers cannot walk the catalog in pieces. This is the change they asked for.
    >
    > **Independent Test**: Request the listing with an explicit page size and skip count, and confirm the response contains only that slice, in sku order, plus the full catalog total.
    >
    > **Acceptance Scenarios**:
    >
    > 1. **Given** a catalog of 250 items ordered by sku, **When** a caller requests the listing with a page size of 20 and a skip of 0, **Then** the listing succeeds and returns the first 20 items in ascending sku order together with a total of 250.
    > 2. **Given** a catalog of 250 items ordered by sku, **When** a caller requests the listing with a page size of 20 and a skip of 40, **Then** the listing succeeds and returns the next 20 items after the first 40, still in ascending sku order, together with a total of 250.
    > 3. **Given** a catalog of 250 items, **When** a caller requests a page size of 1 or a page size of 100 at the start of the catalog, **Then** the listing succeeds and returns exactly that many items, in ascending sku order, together with a total of 250.
    > 4. **Given** a catalog of 250 items, **When** a caller requests a page size of 20 and a skip of 240, **Then** the listing succeeds and returns the remaining 10 items in ascending sku order together with a total of 250.
    > 5. **Given** a catalog of 250 items, **When** a caller supplies only a page size, **Then** the skip is treated as 0. **When** a caller supplies only a skip, **Then** the page size is treated as 20.
    >
    > ---
    >
    > ### User Story 2 - Call the listing with no parameters (Priority: P2)
    >
    > A caller requests the items listing and supplies no parameters. Today that caller receives all 250 items. After this change the caller receives one defined page, not the whole catalog.
    >
    > **Why this priority**: Existing callers that send no parameters must have a documented result. The result is the default page, so it depends on the paging rules in User Story 1, and it is the result those callers will actually see.
    >
    > **Independent Test**: Request the listing with an empty set of parameters and confirm the response is the default page described below, not the full catalog.
    >
    > **Acceptance Scenarios**:
    >
    > 1. **Given** the current catalog of 250 items, **When** a caller requests the listing and passes no parameters, **Then** the listing succeeds and returns the first 20 items in ascending sku order together with a total of 250. Those 20 items are the ones whose skus run from SKU-001 through SKU-020. The other 230 items are not included.
    > 2. **Given** the current catalog of 250 items, **When** a caller requests the listing and passes no parameters, **Then** the number of items in the page is 20 and the reported total is 250.
    >
    > ---
    >
    > ### User Story 3 - Reject an unusable page size or skip (Priority: P3)
    >
    > A caller supplies a page size or a skip that is missing a number, is not a whole number, or is outside the allowed range. The listing refuses the request and names the parameter that was refused, so the caller can correct that value.
    >
    > **Why this priority**: Valid pages are useful before refusal rules exist, but callers need a stable refusal once bad values are sent. Refusal does not change what a valid page contains.
    >
    > **Independent Test**: Send each kind of bad page size and bad skip and confirm the listing is refused, no page is returned, and the message names the parameter.
    >
    > **Acceptance Scenarios**:
    >
    > 1. **Given** a caller sends a page size or skip that is present but empty, only whitespace, or otherwise contains no whole number, **When** the listing is requested, **Then** the request is refused with status 400 and the message names that parameter (`limit` or `offset`).
    > 2. **Given** a caller sends a page size or skip that is not a whole number (for example a fraction, a decimal, a leading plus sign, or text mixed with digits), **When** the listing is requested, **Then** the request is refused with status 400 and the message names that parameter.
    > 3. **Given** a caller sends a page size of 0, a page size below 0, or a page size above 100, **When** the listing is requested, **Then** the request is refused with status 400 and the message names `limit`.
    > 4. **Given** a caller sends a skip below 0, **When** the listing is requested, **Then** the request is refused with status 400 and the message names `offset`.
    > 5. **Given** both the page size and the skip are unacceptable, **When** the listing is requested, **Then** the request is refused with status 400 and the message names `limit` (the page size is judged first).
    > 6. **Given** a refused request, **When** the caller reads the response, **Then** it does not include a page of items.
    >
    > ---
- **Acceptance criteria:**
  - Source: `specs/001-paginate-items-listing/spec.md` (section)
    > ## Requirements *(mandatory)*
    >
    > ### Functional Requirements
    >
    > - **FR-001**: The items listing MUST accept an optional `limit` (page size). When `limit` is omitted, the listing MUST use 20. When `limit` is present, it MUST be a whole number from 1 to 100 inclusive.
    > - **FR-002**: The items listing MUST accept an optional `offset` (how many items to skip). When `offset` is omitted, the listing MUST use 0. When `offset` is present, it MUST be a whole number greater than or equal to 0. There is no upper bound on `offset`.
    > - **FR-003**: A successful listing MUST return one page of items in ascending sku order, starting after `offset` items and containing at most `limit` items, together with the total number of items in the catalog. The page MUST be the `items` collection. The catalog count MUST be `total`. `total` MUST be the full catalog count, not the number of items on the page.
    > - **FR-004**: Each item on a page MUST still show its sku, name, and quantity. The listing MUST NOT add, remove, or rename those item details.
    > - **FR-005**: A caller that passes no parameters MUST receive a successful listing of the default page: `limit` 20 and `offset` 0. With the catalog as it exists today, that result is the first 20 items in ascending sku order (SKU-001 through SKU-020) and a `total` of 250. The caller MUST NOT receive all 250 items.
    > - **FR-006**: When `limit` or `offset` is present but missing a number, not a whole number, or outside the allowed range, the listing MUST refuse the request with status 400 and an error message that names that parameter (`limit` or `offset`). The refusal MUST NOT include a page of items.
    > - **FR-007**: A present value is missing a number when it is empty, only whitespace, or contains no digit. A present value is not a whole number unless the entire value is an optional leading minus sign followed by one or more digits. After that check, `limit` is out of range when its numeric value is less than 1 or greater than 100, and `offset` is out of range when its numeric value is less than 0.
    > - **FR-008**: When both `limit` and `offset` are unacceptable, the listing MUST refuse with status 400 and the message MUST name `limit`. `offset` is judged only when `limit` is acceptable or omitted.
    > - **FR-009**: When `offset` is a whole number greater than or equal to the catalog total, the listing MUST succeed, return an empty `items` page, and still report the full catalog `total`.
    > - **FR-010**: Single-item lookup by sku MUST keep its current outcomes: a known sku returns that item, and an unknown sku is reported as not found.
    >
    > ### Key Entities
    >
    > - **Item**: One catalog entry. Callers see its sku, name, and quantity. Sku order is ascending sku text order, which for the current catalog is SKU-001, SKU-002, and so on through SKU-250.
    > - **Item page**: The result of one listing request. It contains the ordered slice of items for the requested page size and skip, and the total number of items in the catalog. The page does not contain items outside that slice.
    > - **Page request**: The caller's optional `limit` and `offset`. Omitted values use the defaults (20 and 0). Present values are either accepted as a page window or refused with the parameter named.
  - Source: `specs/001-paginate-items-listing/spec.md` (section)
    > ## Success Criteria *(mandatory)*
    >
    > ### Measurable Outcomes
    >
    > - **SC-001**: A caller who passes no parameters receives 20 items and a catalog total of 250, and can see that the page is SKU-001 through SKU-020. They do not receive the other 230 items.
    > - **SC-002**: Every successful page contains at most the requested number of items, never more than 100, and the items on that page appear in ascending sku order.
    > - **SC-003**: Walking the current catalog with a page size of 20 and skips of 0, 20, 40, and so on through 240 returns each of the 250 items exactly once, in sku order, across 13 responses (12 pages of 20 and a final page of 10), and every one of those responses reports a total of 250.
    > - **SC-004**: Every request whose page size or skip is missing a number, not a whole number, or out of range is refused, and the refusal names the parameter. None of those requests return a page of items.
    > - **SC-005**: A caller can decide whether another page exists from the page they received and the catalog total, without requesting the rest of the catalog.
- **Declared scope:**
  - Source: `specs/001-paginate-items-listing/tasks.md` (checklist)
    > - [ ] T001 Confirm `python -m unittest` runs from the repository root, and leave `inventory/__init__.py` and `tests/__init__.py` unchanged per `specs/001-paginate-items-listing/plan.md`
    > - [ ] T002 Add a frozen dataclass `ItemPage` in `inventory/store.py` with `items` (list of `Item`) and `total` (int). `total` is the count of every item in the catalog, not the length of `items`. The length of `items` is never greater than `limit`, and it is 0 when `offset` is greater than or equal to the catalog count.
    > - [ ] T003 Change `list_items` in `inventory/store.py` to `list_items(limit: int = 20, offset: int = 0) -> ItemPage`. Sort the catalog by sku ascending, set `total` to the length of that full ordered catalog, and set `items` to `ordered[offset:offset + limit]`. Callers pass a `limit` that is a whole number from 1 to 100 inclusive (default 20) and an `offset` that is a whole number greater than or equal to 0 with no upper bound (default 0). This function does not return a status code.
    > - [ ] T004 [P] [US1] Add success-page checks in `tests/test_api.py` for `get_items`: `{"limit": "20", "offset": "0"}` returns SKU-001 through SKU-020 and `total` 250; `{"limit": "20", "offset": "40"}` returns SKU-041 through SKU-060 and `total` 250; `{"limit": "1"}` returns one item (SKU-001) and `total` 250; `{"limit": "100"}` returns 100 items and `total` 250; `{"limit": "20", "offset": "240"}` returns SKU-241 through SKU-250 (10 items) and `total` 250; `{"offset": "250"}` and `{"offset": "1000"}` return an empty `items` list and `total` 250; `{"limit": "020", "offset": "0"}` returns SKU-001 through SKU-020 and `total` 250. Each item has only `sku`, `name`, and `quantity`.
    > - [ ] T005 [P] [US1] In `get_items` in `inventory/api.py`, when at least one of `limit` and `offset` is present and every present value fully matches `^-?[0-9]+$` and is in range (`limit` from 1 to 100 inclusive, `offset` greater than or equal to 0), fill an absent `limit` with 20 and an absent `offset` with 0, call `list_items`, and return status 200 with `items` (sku, name, quantity, ascending sku order) and `total` (full catalog count). Ignore keys other than `limit` and `offset`. Leave a call that passes neither key returning the full catalog until T007.
    > - [ ] T006 [P] [US2] Change `test_all_items_are_listed` in `tests/test_api.py` so `get_items({})` expects status 200, 20 items, skus SKU-001 through SKU-020 in that order, and `total` 250, not a list of 250 items
    > - [ ] T007 [P] [US2] In `get_items` in `inventory/api.py`, when neither `limit` nor `offset` is present, use `limit` 20 and `offset` 0 and return the same status-200 body as a valid page (`items` plus `total`). A caller who passes no parameters receives SKU-001 through SKU-020 and `total` 250.
    > - [ ] T008 [P] [US3] Add refusal checks in `tests/test_api.py`: present `limit` values `""`, `" "`, `"abc"`, `"20abc"`, `"1.5"`, `"20.0"`, `"+20"`, `"1e2"`, `"0"`, `"-1"`, `"-0"`, and `"101"` return status 400, `{"error": "limit must be a whole number from 1 to 100"}`, and no `items` key; present `offset` values `"-1"`, `"1.5"`, and `""` with an acceptable or absent `limit` return status 400, `{"error": "offset must be a whole number from 0"}`, and no `items` key; `{"limit": "0", "offset": "-1"}` returns the `limit` error. `{"offset": "-0"}` stays success (integer 0, default `limit` 20).
    > - [ ] T009 [P] [US3] In `get_items` in `inventory/api.py`, judge a present `limit` before a present `offset`. If `limit` is present and the entire value does not match `^-?[0-9]+$` (ASCII digits only), or the integer is less than 1 or greater than 100, return status 400 and `{"error": "limit must be a whole number from 1 to 100"}` with no `items` key. Otherwise, if `offset` is present and the entire value does not match `^-?[0-9]+$`, or the integer is less than 0, return status 400 and `{"error": "offset must be a whole number from 0"}` with no `items` key. A missing key is not a refusal. `-0` is the integer 0.
    > - [ ] T010 Leave `get_item` in `inventory/api.py` and `find_item` in `inventory/store.py` unchanged, and keep `test_one_item` in `tests/test_api.py` expecting status 200 for sku `SKU-001` and status 404 with `{"error": "no such item"}` for sku `nope`
    > - [ ] T011 Run `python -m unittest` from the repository root and check every row in `specs/001-paginate-items-listing/quickstart.md`
- **Outcome records:** TODO(AIDF)

## Part B: Plan

- **Approach:**
  - Source: `specs/001-paginate-items-listing/plan.md` (section)
    > ## Summary
    >
    > Callers of the items listing can ask for one page. `limit` is a whole number from 1 to 100 and defaults to 20. `offset` is a whole number from 0 and defaults to 0. A successful response returns that sku-ordered slice in `items` and the full catalog count in `total`. A caller who passes no parameters gets the first 20 items (SKU-001 through SKU-020) and a total of 250, not all 250 items. A present value that is missing a number, not a whole number, or out of range is refused with status 400 and an error message that names the parameter.
    >
    > The handler in `inventory/api.py` validates the parameters. `list_items` in `inventory/store.py` may change so that it returns the ordered page and the total. Single-item lookup stays as it is.
- **Invariants touched:** TODO(AIDF)
- **Evidence strategy:** TODO(AIDF)
- **Protected files touched:** TODO(AIDF)
- **Recovery / reversal approach:** TODO(AIDF)
- **Review budget:** TODO(AIDF)
- **Dependency changes:**
  - Source: `specs/001-paginate-items-listing/plan.md` (section)
    > ## Technical Context
    >
    > **Language/Version**: Python 3.10 or newer. The package already uses `list[Item]`, `dict[str, str]`, and `Item | None`. This workspace runs Python 3.14.7. There is no dependency manifest and no version pin file.
    >
    > **Primary Dependencies**: Python standard library only (`dataclasses` in the store, `unittest` in the tests). No web framework. The listing is a function, `get_items(params) -> (status, body)`, not a listening server.
    >
    > **Storage**: In-memory tuple of 250 `Item` values in `inventory/store.py`. No database.
    >
    > **Testing**: `unittest`, run as `python -m unittest` from the repository root. The current suite is `tests/test_api.py` (2 tests). Observed on 2026-11-05: `python -m unittest` reported `Ran 2 tests` and `OK`. Those tests still expect the unpaged listing.
    >
    > **Target Platform**: Local Python process on the developer machine. The sample is not deployed.
    >
    > **Project Type**: In-process request handlers (a small library). `GET /items` is the name of the listing operation implemented by `get_items`.
    >
    > **Performance Goals**: Correct pages over the existing 250-item catalog. Each listing sorts that catalog and slices one page. No separate throughput target.
    >
    > **Constraints**: `limit` 1 through 100 inclusive, default 20. `offset` greater than or equal to 0, no upper bound, default 0. Success includes `items` and `total`. Refusal is status 400 and a message that names `limit` or `offset`. Item fields stay sku, name, and quantity. `get_item` stays unchanged. No new dependency, service, or storage.
    >
    > **Scale/Scope**: One catalog of 250 items. Two production modules (`inventory/api.py`, `inventory/store.py`) and one test module (`tests/test_api.py`).

## Status

- **State:** Established
- **Established by (author):** TODO(author)
- **Approved by (human, T2/T3 only, role: Architect):** none
- **Date:** TODO(author)
- **Class:** TODO(AIDF)
- **Spec Confidence at intake:** TODO(AIDF)
- **Re-evaluated to Clear by:** TODO(AIDF)
