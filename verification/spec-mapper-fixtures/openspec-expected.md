# Task Contract (DRAFT, not approved)

Drafted by `spec_mapper` with the mapping `openspec`. A draft is not an approval, a classification or evidence: a person fills each TODO, chooses the class and has it approved before any implementation.
Every line copied from a planning file sits in a quotation under its source file; nothing else in this draft comes from the sources.

- **Change id:** `add-items-pagination` (the name of the folder that holds `openspec/changes/add-items-pagination/proposal.md`)
- **Files read:** `openspec/changes/add-items-pagination/design.md`, `openspec/changes/add-items-pagination/proposal.md`, `openspec/changes/add-items-pagination/specs/items-listing/spec.md`, `openspec/changes/add-items-pagination/tasks.md`
- **Parts copied from the source:** 8 of 17. **Parts left as TODO:** 9.

## Approver's opening

- **Read this first:** TODO(author)
- **Problem:**
  - Source: `openspec/changes/add-items-pagination/proposal.md` (section)
    > ## Why
    >
    > `GET /items` returns the entire catalog on every call. The in-memory store already holds 250 items, and `get_items` ignores its query parameters, so every caller pays for a full sku-ordered dump. Listing needs a bounded page so callers can walk the catalog without taking all of it at once.
- **Why it matters:** TODO(author)
- **The change:**
  - Source: `openspec/changes/add-items-pagination/proposal.md` (section)
    > ## Capabilities
    >
    > ### New Capabilities
    >
    > - `items-listing`: Paginated `GET /items` — page bounds, sku order, the total count, the no-parameter default page, and 400 responses that name `limit` or `offset`.
    >
    > ### Modified Capabilities
    >
    > - None. The project has no existing specs (`openspec list --specs` reported no specs).
- **Technical details:**
  - Source: `openspec/changes/add-items-pagination/design.md` (section)
    > ## Decisions
    >
    > ### Validate in the handler, page in the store
    >
    > `get_items` reads the string dict, applies defaults, and returns 400 before calling the store when a present value is invalid. `list_items` receives integers that are already in range and returns the page plus the total.
    >
    > Alternative: slice the full list inside `get_items` and leave `list_items()` unchanged. Rejected. The store already owns sku order, it is the only caller (`get_items`), and the proposal allows `list_items` to change. Keeping paging in the handler would leave a no-argument `list_items()` that still means "everything", which is the behavior this change removes from the listing.
    >
    > Alternative: add a second function and keep `list_items()` as the full dump. Rejected for the same reason. One function, new signature, so the old call does not still type-check as "return all".
    >
    > ### `list_items(limit: int, offset: int) -> tuple[list[Item], int]`
    >
    > Sort by sku as today (`sorted(_ITEMS, key=lambda item: item.sku)`). `total` is the length of that sequence. The page is `ordered[offset:offset + limit]`. When `offset` is past the end, the slice is empty and `total` is unchanged. The store does not re-check ranges and does not interpret strings.
    >
    > The handler maps each `Item` to `{"sku", "name", "quantity"}` and returns `200, {"items": page, "total": total}`.
    >
    > ### Classify the string, then convert
    >
    > Do not use bare `int()` on the raw parameter. `int("+20")` and `int(" 20")` succeed, and `int("20.0")` fails, which does not match the spec.
    >
    > For each of `limit` then `offset`:
    >
    > 1. Key absent: use 20 or 0. Do not treat absence as an error.
    > 2. Present value with no decimal digit (empty string, whitespace, `abc`): missing a number.
    > 3. Otherwise the whole value must match `^-?\d+$`. If it does not (`1.5`, `20.0`, `+20`, `1e1`, ` 20`): not a whole number.
    > 4. Convert with `int` (so `01` is 1 and `-0` is 0). `limit` must be 1 through 100. `offset` must be greater than or equal to 0. Any other integer is out of range. There is no maximum `offset`.
    > 5. Stop at the first failure. `limit` is checked before `offset`, so both invalid names `limit`.
    >
    > Messages, which all contain the parameter name:
    >
    > - missing a number: `"<name> is missing a number"`
    > - not a whole number: `"<name> must be a whole number"`
    > - `limit` out of range: `"limit must be a whole number from 1 to 100"`
    > - `offset` out of range: `"offset must be a whole number from 0"`
    >
    > The 400 body is only `{"error": <message>}`. It has no `items` key. Other keys in the parameter dict are ignored.
    >
    > ### No-parameter result
    >
    > `get_items({})` is limit 20 and offset 0. On the current seed that is status 200, `items` of SKU-001 through SKU-020 in that order, and `total` 250. It is not the 250-item list the current test expects.
- **What you need to decide:** TODO(author)

## Part A: Minimal

- **Intended outcome:**
  - Source: `openspec/changes/add-items-pagination/proposal.md` (section)
    > ## What Changes
    >
    > - `GET /items` (`get_items`) accepts `limit` and `offset` and returns one page of items in sku order plus the total number of items.
    > - `limit` is a whole number from 1 to 100 and defaults to 20. `offset` is a whole number from 0 and defaults to 0. There is no upper bound on `offset`.
    > - A value that is missing a number, is not a whole number, or is out of range is rejected with status 400 and an error message that names the parameter.
    > - **BREAKING**: a caller that passes no parameters currently receives all 250 items and no total. That call becomes the default page: the first 20 items in sku order and `total` 250 (with the current seed). It no longer receives the full catalog.
    > - `list_items` may change so the store applies sku order, `limit`, and `offset` and reports the total. `GET /items/<sku>` (`get_item`) stays as it is.
- **Acceptance criteria:**
  - Source: `openspec/changes/add-items-pagination/specs/items-listing/spec.md` (blocks)
    > ### Requirement: Omitted parameters use defaults
    > An items listing that omits `limit` MUST use 20. An items listing that omits `offset` MUST use 0. The response MUST be the page those defaults select.
    >
    > #### Scenario: No parameters on the seeded catalog
    > - **WHEN** the items listing is requested with no parameters and the catalog is the 250 seeded items SKU-001 through SKU-250
    > - **THEN** the status is 200, `items` contains SKU-001 through SKU-020 in that order, and `total` is 250
    >
    > #### Scenario: Only limit is sent
    > - **WHEN** `limit` is `5` and `offset` is omitted on the seeded catalog
    > - **THEN** the status is 200, `items` contains SKU-001 through SKU-005 in that order, and `total` is 250
    >
    > #### Scenario: Only offset is sent
    > - **WHEN** `offset` is `5` and `limit` is omitted on the seeded catalog
    > - **THEN** the status is 200, `items` contains SKU-006 through SKU-025 in that order, and `total` is 250
    >
    > ### Requirement: Page content and total
    > The listing MUST answer a valid request with status 200. The body MUST include `items` and `total`. `items` MUST be the contiguous slice of the catalog in ascending sku order, starting at `offset`, with at most `limit` items. `total` MUST be the full catalog size and MUST NOT change with the page. Each item MUST include `sku`, `name`, and `quantity` from the catalog.
    >
    > #### Scenario: Second page
    > - **WHEN** `limit` is `20` and `offset` is `20` on the seeded catalog
    > - **THEN** the status is 200, `items` contains SKU-021 through SKU-040 in that order, and `total` is 250
    >
    > #### Scenario: Partial last page
    > - **WHEN** `limit` is `20` and `offset` is `240` on the seeded catalog
    > - **THEN** the status is 200, `items` contains SKU-241 through SKU-250 in that order, and `total` is 250
    >
    > #### Scenario: Offset at the catalog size
    > - **WHEN** `limit` is `20` and `offset` is `250` on the seeded catalog
    > - **THEN** the status is 200, `items` is an empty array, and `total` is 250
    >
    > #### Scenario: Offset far past the end
    > - **WHEN** `limit` is `20` and `offset` is `1000000` on the seeded catalog
    > - **THEN** the status is 200, `items` is an empty array, and `total` is 250
    >
    > #### Scenario: First seeded item keeps its fields
    > - **WHEN** the items listing is requested with no parameters on the seeded catalog
    > - **THEN** the first item has `sku` `SKU-001`, `name` `Item 1`, and `quantity` 1
    >
    > ### Requirement: Inclusive page bounds
    > `limit` MUST be accepted for the whole numbers 1 and 100. `offset` MUST be accepted for the whole number 0. An accepted `offset` past the last item MUST still return status 200 and an empty `items` array.
    >
    > #### Scenario: Smallest limit
    > - **WHEN** `limit` is `1` and `offset` is `0` on the seeded catalog
    > - **THEN** the status is 200, `items` contains only SKU-001, and `total` is 250
    >
    > #### Scenario: Largest limit
    > - **WHEN** `limit` is `100` and `offset` is `0` on the seeded catalog
    > - **THEN** the status is 200, `items` contains SKU-001 through SKU-100 in that order, and `total` is 250
    >
    > #### Scenario: Zero offset
    > - **WHEN** `limit` is `20` and `offset` is `0` on the seeded catalog
    > - **THEN** the status is 200 and the first item is SKU-001
    >
    > ### Requirement: Whole-number values
    > A present `limit` or `offset` is a whole number only when the entire value is an optional leading `-` followed by one or more decimal digits. Leading zeros MUST be accepted and MUST NOT change the integer value. A present value with no decimal digit MUST be treated as missing a number. Any other present value MUST be treated as not a whole number.
    >
    > #### Scenario: Leading zeros are the same integer
    > - **WHEN** `limit` is `01` and `offset` is `000` on the seeded catalog
    > - **THEN** the status is 200, `items` contains only SKU-001, and `total` is 250
    >
    > #### Scenario: Empty limit is missing a number
    > - **WHEN** `limit` is an empty string
    > - **THEN** the status is 400 and the `error` string contains `limit`
    >
    > #### Scenario: Empty offset is missing a number
    > - **WHEN** `offset` is an empty string
    > - **THEN** the status is 400 and the `error` string contains `offset`
    >
    > #### Scenario: Letters are missing a number
    > - **WHEN** `offset` is `abc`
    > - **THEN** the status is 400 and the `error` string contains `offset`
    >
    > #### Scenario: Fractional limit is not a whole number
    > - **WHEN** `limit` is `1.5`
    > - **THEN** the status is 400 and the `error` string contains `limit`
    >
    > #### Scenario: Trailing decimal is not a whole number
    > - **WHEN** `limit` is `20.0`
    > - **THEN** the status is 400 and the `error` string contains `limit`
    >
    > #### Scenario: Exponent and sign and space are not whole numbers
    > - **WHEN** `limit` is `1e1`, or `limit` is `+20`, or `offset` is ` 20`
    > - **THEN** the status is 400 and the `error` string contains the rejected parameter's name
    >
    > ### Requirement: Out-of-range values
    > `limit` MUST be rejected when its whole-number value is less than 1 or greater than 100. `offset` MUST be rejected when its whole-number value is less than 0. There is no maximum `offset`. The rejection MUST use status 400, and the `error` string MUST contain that parameter's name.
    >
    > #### Scenario: Limit below 1
    > - **WHEN** `limit` is `0`
    > - **THEN** the status is 400 and the `error` string contains `limit`
    >
    > #### Scenario: Limit above 100
    > - **WHEN** `limit` is `101`
    > - **THEN** the status is 400 and the `error` string contains `limit`
    >
    > #### Scenario: Negative limit
    > - **WHEN** `limit` is `-1`
    > - **THEN** the status is 400 and the `error` string contains `limit`
    >
    > #### Scenario: Negative offset
    > - **WHEN** `offset` is `-1`
    > - **THEN** the status is 400 and the `error` string contains `offset`
    >
    > #### Scenario: Negative zero offset is zero
    > - **WHEN** `offset` is `-0` and `limit` is omitted on the seeded catalog
    > - **THEN** the status is 200, `items` contains SKU-001 through SKU-020 in that order, and `total` is 250
    >
    > ### Requirement: One error names the parameter
    > A rejected listing MUST return a body that is an object with an `error` string and MUST NOT return `items`. When both `limit` and `offset` are invalid, the `error` string MUST contain `limit`. Parameters other than `limit` and `offset` MUST NOT change the page and MUST NOT by themselves cause a 400.
    >
    > #### Scenario: Both parameters invalid
    > - **WHEN** `limit` is `0` and `offset` is `-1`
    > - **THEN** the status is 400 and the `error` string contains `limit`
    >
    > #### Scenario: Unrelated parameter is ignored
    > - **WHEN** the request includes `sku` set to `SKU-001` and omits `limit` and `offset` on the seeded catalog
    > - **THEN** the status is 200, `items` contains SKU-001 through SKU-020 in that order, and `total` is 250
- **Declared scope:**
  - Source: `openspec/changes/add-items-pagination/tasks.md` (checklist)
    > - [ ] 1.1 Change `list_items` in `inventory/store.py` to `list_items(limit: int, offset: int) -> tuple[list[Item], int]`. Sort by sku as it does now, set `total` to the sorted length, and return `ordered[offset:offset + limit]` plus `total` (empty page when `offset` is past the end). Update `get_items` in `inventory/api.py` so a valid request maps that page to `{"items": [{"sku", "name", "quantity"}, ...], "total": total}` with status 200, using 20 and 0 when `limit` or `offset` is omitted. Update the `get_items` docstring so it no longer says every item is returned. Replace `test_all_items_are_listed` and add the success cases from `specs/items-listing/spec.md` (no parameters, only `limit`, only `offset`, second page, partial last page, offset 250, offset 1000000, first item fields, limit 1, limit 100, offset 0, leading zeros `01`/`000`, offset `-0`). Verify with `python -m unittest`: those cases pass, and `test_one_item` still returns 200 for `SKU-001` and 404 for `nope`.
    > - [ ] 2.1 In `get_items`, before calling the store, classify each present value as in `design.md`: no decimal digit is missing a number, anything other than `^-?\d+$` is not a whole number, then range-check `limit` (1 through 100) and `offset` (from 0, no maximum). Check `limit` before `offset` and stop at the first failure. Return status 400 and `{"error": "<message>"}` with no `items` key, using the four message templates in `design.md`. Ignore unrelated parameters. Add tests for empty `limit`, empty `offset`, `abc`, `1.5`, `20.0`, `1e1`, `+20`, ` 20`, `limit` `0`, `limit` `101`, `limit` `-1`, `offset` `-1`, both `limit` `0` and `offset` `-1` (error contains `limit`), and a request whose only extra key is `sku`. Verify with `python -m unittest`: the new 400 cases pass and the section 1 page tests still pass.
    > - [ ] 3.1 Run `python -m unittest` from the repo root and confirm the whole module passes, including the unchanged single-item cases and every page and 400 case above.
- **Outcome records:** TODO(AIDF)

## Part B: Plan

- **Approach:**
  - Source: `openspec/changes/add-items-pagination/design.md` (file)
    > # Design
    >
    > ## Context
    >
    > See proposal.md for why the listing must be paged. Today `get_items` ignores its parameter dict and returns every row from `list_items()`. `list_items()` takes no arguments, sorts `_ITEMS` by sku, and returns the full list (250 seeded items, `SKU-001` through `SKU-250`). `get_item` / `find_item` return one item or `{"error": "no such item"}` with status 404. Handlers take `dict[str, str]` and return `(status, body)`. Behavior for valid and invalid pages is in `specs/items-listing/spec.md`.
    >
    > ## Goals / Non-Goals
    >
    > **Goals:**
    >
    > - Parse and validate `limit` and `offset` in `get_items`, and page in `list_items`.
    > - Use one error object shape, `{"error": "<message>"}`, with the parameter name in the message.
    > - Make the no-parameter call the default page (limit 20, offset 0) so the old "all 250 items" result cannot happen by leaving the arguments off.
    >
    > **Non-Goals:**
    >
    > - Cursor or keyset pagination, filtering, or a different sort.
    > - Changing `get_item`, `find_item`, or the `Item` fields.
    > - A new dependency, an HTTP server, or a cap on how large an in-range `offset` may be.
    >
    > ## Decisions
    >
    > ### Validate in the handler, page in the store
    >
    > `get_items` reads the string dict, applies defaults, and returns 400 before calling the store when a present value is invalid. `list_items` receives integers that are already in range and returns the page plus the total.
    >
    > Alternative: slice the full list inside `get_items` and leave `list_items()` unchanged. Rejected. The store already owns sku order, it is the only caller (`get_items`), and the proposal allows `list_items` to change. Keeping paging in the handler would leave a no-argument `list_items()` that still means "everything", which is the behavior this change removes from the listing.
    >
    > Alternative: add a second function and keep `list_items()` as the full dump. Rejected for the same reason. One function, new signature, so the old call does not still type-check as "return all".
    >
    > ### `list_items(limit: int, offset: int) -> tuple[list[Item], int]`
    >
    > Sort by sku as today (`sorted(_ITEMS, key=lambda item: item.sku)`). `total` is the length of that sequence. The page is `ordered[offset:offset + limit]`. When `offset` is past the end, the slice is empty and `total` is unchanged. The store does not re-check ranges and does not interpret strings.
    >
    > The handler maps each `Item` to `{"sku", "name", "quantity"}` and returns `200, {"items": page, "total": total}`.
    >
    > ### Classify the string, then convert
    >
    > Do not use bare `int()` on the raw parameter. `int("+20")` and `int(" 20")` succeed, and `int("20.0")` fails, which does not match the spec.
    >
    > For each of `limit` then `offset`:
    >
    > 1. Key absent: use 20 or 0. Do not treat absence as an error.
    > 2. Present value with no decimal digit (empty string, whitespace, `abc`): missing a number.
    > 3. Otherwise the whole value must match `^-?\d+$`. If it does not (`1.5`, `20.0`, `+20`, `1e1`, ` 20`): not a whole number.
    > 4. Convert with `int` (so `01` is 1 and `-0` is 0). `limit` must be 1 through 100. `offset` must be greater than or equal to 0. Any other integer is out of range. There is no maximum `offset`.
    > 5. Stop at the first failure. `limit` is checked before `offset`, so both invalid names `limit`.
    >
    > Messages, which all contain the parameter name:
    >
    > - missing a number: `"<name> is missing a number"`
    > - not a whole number: `"<name> must be a whole number"`
    > - `limit` out of range: `"limit must be a whole number from 1 to 100"`
    > - `offset` out of range: `"offset must be a whole number from 0"`
    >
    > The 400 body is only `{"error": <message>}`. It has no `items` key. Other keys in the parameter dict are ignored.
    >
    > ### No-parameter result
    >
    > `get_items({})` is limit 20 and offset 0. On the current seed that is status 200, `items` of SKU-001 through SKU-020 in that order, and `total` 250. It is not the 250-item list the current test expects.
    >
    > ## Risks / Trade-offs
    >
    > - [Callers of `get_items({})` stop receiving 250 items] → Documented default page above. Update `test_all_items_are_listed` in the same change. No other callers are in this repo.
    > - [`list_items()` signature break] → Only `get_items` calls it. Update that call in the same change. `find_item` stays argument-compatible.
    > - [A huge digit string is still a valid `offset`] → Accepted. The spec allows any whole number from 0, including `1000000`, and Python `int` can parse it. The page is then empty. This sample catalog does not need a digit-length cap.
    > - [Bare `int()` would accept `+` and spaces] → The `^-?\d+$` check runs first.
    >
    > ## Migration Plan
    >
    > 1. Change `list_items` and `get_items` together so nothing keeps the old full-list call.
    > 2. Replace the test that expects 250 items from `get_items({})` with the default-page, other-page, and 400 cases in the spec.
    > 3. Rollback is reverting `inventory/api.py`, `inventory/store.py`, and `tests/test_api.py`. There is no stored data and no deploy step.
    >
    > ## Open Questions
    >
    > None. Parsing, error text, the `list_items` signature, and the no-parameter page are decided above and match the spec.
- **Invariants touched:** TODO(AIDF)
- **Evidence strategy:** TODO(AIDF)
- **Protected files touched:** TODO(AIDF)
- **Recovery / reversal approach:** TODO(AIDF)
- **Review budget:** TODO(AIDF)
- **Dependency changes:**
  - Source: `openspec/changes/add-items-pagination/proposal.md` (section)
    > ## Impact
    >
    > - `inventory/api.py`: `get_items` today returns `200` and `{"items": [...]}` for every item from `store.list_items()`, which sorts the full 250-item seed by sku. The handler must read `limit` and `offset`, validate them, and return a page plus `total`.
    > - `inventory/store.py`: `list_items()` currently takes no arguments and returns every item ordered by sku. Its signature and return value may change to serve a page and a total. `find_item` is unchanged.
    > - `tests/test_api.py`: `test_all_items_are_listed` calls `get_items({})` and asserts 250 items. That assertion no longer matches the default page and must be replaced with coverage for the default page, other pages, and 400 validation.
    > - No new dependencies. Item objects stay `{sku, name, quantity}`.

## Status

- **State:** Established
- **Established by (author):** TODO(author)
- **Approved by (human, T2/T3 only, role: Architect):** none
- **Date:** TODO(author)
- **Class:** TODO(AIDF)
- **Spec Confidence at intake:** TODO(AIDF)
- **Re-evaluated to Clear by:** TODO(AIDF)
