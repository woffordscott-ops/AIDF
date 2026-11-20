# Feature Specification: Paginate the Items Listing

**Feature Branch**: `001-paginate-items-listing`

**Created**: 2026-11-05

**Status**: Draft

**Input**: User description: "Add pagination to the items listing. GET /items (the get_items handler) accepts limit (a whole number from 1 to 100, default 20) and offset (a whole number from 0, default 0), returns that page of items in sku order together with the total number of items, and rejects a value that is missing a number, not a whole number or out of range with status 400 and an error message that names the parameter. A caller that passes no parameters currently gets all 250 items and must get a defined, documented result (say what it gets). The store function list_items may change."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Request one page of the catalog (Priority: P1)

A caller asks the items listing for a bounded page by supplying how many items to return and how many items to skip. The listing answers with that page only, in sku order, and says how many items exist in the whole catalog so the caller can tell whether further pages remain.

**Why this priority**: Without a bounded page plus the catalog total, callers cannot walk the catalog in pieces. This is the change they asked for.

**Independent Test**: Request the listing with an explicit page size and skip count, and confirm the response contains only that slice, in sku order, plus the full catalog total.

**Acceptance Scenarios**:

1. **Given** a catalog of 250 items ordered by sku, **When** a caller requests the listing with a page size of 20 and a skip of 0, **Then** the listing succeeds and returns the first 20 items in ascending sku order together with a total of 250.
2. **Given** a catalog of 250 items ordered by sku, **When** a caller requests the listing with a page size of 20 and a skip of 40, **Then** the listing succeeds and returns the next 20 items after the first 40, still in ascending sku order, together with a total of 250.
3. **Given** a catalog of 250 items, **When** a caller requests a page size of 1 or a page size of 100 at the start of the catalog, **Then** the listing succeeds and returns exactly that many items, in ascending sku order, together with a total of 250.
4. **Given** a catalog of 250 items, **When** a caller requests a page size of 20 and a skip of 240, **Then** the listing succeeds and returns the remaining 10 items in ascending sku order together with a total of 250.
5. **Given** a catalog of 250 items, **When** a caller supplies only a page size, **Then** the skip is treated as 0. **When** a caller supplies only a skip, **Then** the page size is treated as 20.

---

### User Story 2 - Call the listing with no parameters (Priority: P2)

A caller requests the items listing and supplies no parameters. Today that caller receives all 250 items. After this change the caller receives one defined page, not the whole catalog.

**Why this priority**: Existing callers that send no parameters must have a documented result. The result is the default page, so it depends on the paging rules in User Story 1, and it is the result those callers will actually see.

**Independent Test**: Request the listing with an empty set of parameters and confirm the response is the default page described below, not the full catalog.

**Acceptance Scenarios**:

1. **Given** the current catalog of 250 items, **When** a caller requests the listing and passes no parameters, **Then** the listing succeeds and returns the first 20 items in ascending sku order together with a total of 250. Those 20 items are the ones whose skus run from SKU-001 through SKU-020. The other 230 items are not included.
2. **Given** the current catalog of 250 items, **When** a caller requests the listing and passes no parameters, **Then** the number of items in the page is 20 and the reported total is 250.

---

### User Story 3 - Reject an unusable page size or skip (Priority: P3)

A caller supplies a page size or a skip that is missing a number, is not a whole number, or is outside the allowed range. The listing refuses the request and names the parameter that was refused, so the caller can correct that value.

**Why this priority**: Valid pages are useful before refusal rules exist, but callers need a stable refusal once bad values are sent. Refusal does not change what a valid page contains.

**Independent Test**: Send each kind of bad page size and bad skip and confirm the listing is refused, no page is returned, and the message names the parameter.

**Acceptance Scenarios**:

1. **Given** a caller sends a page size or skip that is present but empty, only whitespace, or otherwise contains no whole number, **When** the listing is requested, **Then** the request is refused with status 400 and the message names that parameter (`limit` or `offset`).
2. **Given** a caller sends a page size or skip that is not a whole number (for example a fraction, a decimal, a leading plus sign, or text mixed with digits), **When** the listing is requested, **Then** the request is refused with status 400 and the message names that parameter.
3. **Given** a caller sends a page size of 0, a page size below 0, or a page size above 100, **When** the listing is requested, **Then** the request is refused with status 400 and the message names `limit`.
4. **Given** a caller sends a skip below 0, **When** the listing is requested, **Then** the request is refused with status 400 and the message names `offset`.
5. **Given** both the page size and the skip are unacceptable, **When** the listing is requested, **Then** the request is refused with status 400 and the message names `limit` (the page size is judged first).
6. **Given** a refused request, **When** the caller reads the response, **Then** it does not include a page of items.

---

### Edge Cases

- A skip of 0 returns the first page. A page size of 1 returns one item. A page size of 100 returns 100 items. These are the smallest and largest accepted page sizes.
- A skip equal to the catalog total (250), or any whole-number skip greater than the total, succeeds. The page is empty, and the total is still the full catalog count (250). The request is not refused, because the skip is a whole number of 0 or greater.
- A page that starts near the end and asks for more items than remain returns only the remaining items, with the full catalog total unchanged.
- A parameter that is omitted uses its default (page size 20, skip 0). A parameter that is present with an empty or blank value is refused. Omission and a blank value are different.
- A value is a whole number only when the entire value is an optional leading minus sign followed by one or more digits and nothing else. `20` and `020` are whole numbers (`020` means 20). `-1`, `0`, `1.5`, `20.0`, `+20`, `20abc`, `abc`, and a value of only spaces are not accepted whole numbers in range; each is refused.
- A negative zero page size (`-0`) is the whole number 0, which is below 1, so it is refused and the message names `limit`. A negative zero skip is the whole number 0, which is allowed, and means the first page.
- There is no maximum skip. A very large whole-number skip succeeds with an empty page and the true total.
- When the catalog total changes later, the reported total is the new count, and the no-parameter page is still the first 20 items in sku order (or fewer, if the catalog then has fewer than 20 items). The documented "total of 250" and "SKU-001 through SKU-020" result applies to the catalog as it exists today.
- Looking up one item by sku is unchanged. A missing item is still reported as not found, and a known item is still returned whole.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The items listing MUST accept an optional `limit` (page size). When `limit` is omitted, the listing MUST use 20. When `limit` is present, it MUST be a whole number from 1 to 100 inclusive.
- **FR-002**: The items listing MUST accept an optional `offset` (how many items to skip). When `offset` is omitted, the listing MUST use 0. When `offset` is present, it MUST be a whole number greater than or equal to 0. There is no upper bound on `offset`.
- **FR-003**: A successful listing MUST return one page of items in ascending sku order, starting after `offset` items and containing at most `limit` items, together with the total number of items in the catalog. The page MUST be the `items` collection. The catalog count MUST be `total`. `total` MUST be the full catalog count, not the number of items on the page.
- **FR-004**: Each item on a page MUST still show its sku, name, and quantity. The listing MUST NOT add, remove, or rename those item details.
- **FR-005**: A caller that passes no parameters MUST receive a successful listing of the default page: `limit` 20 and `offset` 0. With the catalog as it exists today, that result is the first 20 items in ascending sku order (SKU-001 through SKU-020) and a `total` of 250. The caller MUST NOT receive all 250 items.
- **FR-006**: When `limit` or `offset` is present but missing a number, not a whole number, or outside the allowed range, the listing MUST refuse the request with status 400 and an error message that names that parameter (`limit` or `offset`). The refusal MUST NOT include a page of items.
- **FR-007**: A present value is missing a number when it is empty, only whitespace, or contains no digit. A present value is not a whole number unless the entire value is an optional leading minus sign followed by one or more digits. After that check, `limit` is out of range when its numeric value is less than 1 or greater than 100, and `offset` is out of range when its numeric value is less than 0.
- **FR-008**: When both `limit` and `offset` are unacceptable, the listing MUST refuse with status 400 and the message MUST name `limit`. `offset` is judged only when `limit` is acceptable or omitted.
- **FR-009**: When `offset` is a whole number greater than or equal to the catalog total, the listing MUST succeed, return an empty `items` page, and still report the full catalog `total`.
- **FR-010**: Single-item lookup by sku MUST keep its current outcomes: a known sku returns that item, and an unknown sku is reported as not found.

### Key Entities

- **Item**: One catalog entry. Callers see its sku, name, and quantity. Sku order is ascending sku text order, which for the current catalog is SKU-001, SKU-002, and so on through SKU-250.
- **Item page**: The result of one listing request. It contains the ordered slice of items for the requested page size and skip, and the total number of items in the catalog. The page does not contain items outside that slice.
- **Page request**: The caller's optional `limit` and `offset`. Omitted values use the defaults (20 and 0). Present values are either accepted as a page window or refused with the parameter named.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A caller who passes no parameters receives 20 items and a catalog total of 250, and can see that the page is SKU-001 through SKU-020. They do not receive the other 230 items.
- **SC-002**: Every successful page contains at most the requested number of items, never more than 100, and the items on that page appear in ascending sku order.
- **SC-003**: Walking the current catalog with a page size of 20 and skips of 0, 20, 40, and so on through 240 returns each of the 250 items exactly once, in sku order, across 13 responses (12 pages of 20 and a final page of 10), and every one of those responses reports a total of 250.
- **SC-004**: Every request whose page size or skip is missing a number, not a whole number, or out of range is refused, and the refusal names the parameter. None of those requests return a page of items.
- **SC-005**: A caller can decide whether another page exists from the page they received and the catalog total, without requesting the rest of the catalog.

## Assumptions

- Callers of the items listing are the audience. The listing they already use is the one that today returns every item when no parameters are passed. This feature changes that listing only.
- "No parameters" means the caller does not send `limit` and does not send `offset`. Any other parameter the listing does not understand is ignored and does not change the page.
- The default page for omitted parameters is page size 20 and skip 0. That is the defined result for a caller who passes no parameters: the first 20 items in ascending sku order and a total of 250, given today's catalog.
- The catalog currently holds 250 items with skus SKU-001 through SKU-250. The total reported by the listing is whatever the catalog count is at request time. The figures 250 and SKU-001 through SKU-020 describe today's catalog.
- The refusal message is an error message whose text includes the parameter name `limit` or `offset`. The exact surrounding words are not fixed, as long as the named parameter is present and no page is returned. The refusal status is 400.
- A skip past the end of the catalog is a successful empty page, not a refusal. This matches ordinary catalog paging, and the request did not set an upper bound on skip.
- When both parameters are unacceptable, naming `limit` only is enough. The caller can correct `limit` and send the request again.
- Single-item lookup, item fields, and the set of items in the catalog are out of scope. Filtering, search, and a choice of sort order are out of scope. The listing stays in ascending sku order.
- No git branch was created for this feature. The workspace has no branch hook for specification, and the feature directory name is `specs/001-paginate-items-listing`.
