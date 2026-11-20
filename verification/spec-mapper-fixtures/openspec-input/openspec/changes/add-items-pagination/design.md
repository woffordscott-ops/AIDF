# Design

## Context

See proposal.md for why the listing must be paged. Today `get_items` ignores its parameter dict and returns every row from `list_items()`. `list_items()` takes no arguments, sorts `_ITEMS` by sku, and returns the full list (250 seeded items, `SKU-001` through `SKU-250`). `get_item` / `find_item` return one item or `{"error": "no such item"}` with status 404. Handlers take `dict[str, str]` and return `(status, body)`. Behavior for valid and invalid pages is in `specs/items-listing/spec.md`.

## Goals / Non-Goals

**Goals:**

- Parse and validate `limit` and `offset` in `get_items`, and page in `list_items`.
- Use one error object shape, `{"error": "<message>"}`, with the parameter name in the message.
- Make the no-parameter call the default page (limit 20, offset 0) so the old "all 250 items" result cannot happen by leaving the arguments off.

**Non-Goals:**

- Cursor or keyset pagination, filtering, or a different sort.
- Changing `get_item`, `find_item`, or the `Item` fields.
- A new dependency, an HTTP server, or a cap on how large an in-range `offset` may be.

## Decisions

### Validate in the handler, page in the store

`get_items` reads the string dict, applies defaults, and returns 400 before calling the store when a present value is invalid. `list_items` receives integers that are already in range and returns the page plus the total.

Alternative: slice the full list inside `get_items` and leave `list_items()` unchanged. Rejected. The store already owns sku order, it is the only caller (`get_items`), and the proposal allows `list_items` to change. Keeping paging in the handler would leave a no-argument `list_items()` that still means "everything", which is the behavior this change removes from the listing.

Alternative: add a second function and keep `list_items()` as the full dump. Rejected for the same reason. One function, new signature, so the old call does not still type-check as "return all".

### `list_items(limit: int, offset: int) -> tuple[list[Item], int]`

Sort by sku as today (`sorted(_ITEMS, key=lambda item: item.sku)`). `total` is the length of that sequence. The page is `ordered[offset:offset + limit]`. When `offset` is past the end, the slice is empty and `total` is unchanged. The store does not re-check ranges and does not interpret strings.

The handler maps each `Item` to `{"sku", "name", "quantity"}` and returns `200, {"items": page, "total": total}`.

### Classify the string, then convert

Do not use bare `int()` on the raw parameter. `int("+20")` and `int(" 20")` succeed, and `int("20.0")` fails, which does not match the spec.

For each of `limit` then `offset`:

1. Key absent: use 20 or 0. Do not treat absence as an error.
2. Present value with no decimal digit (empty string, whitespace, `abc`): missing a number.
3. Otherwise the whole value must match `^-?\d+$`. If it does not (`1.5`, `20.0`, `+20`, `1e1`, ` 20`): not a whole number.
4. Convert with `int` (so `01` is 1 and `-0` is 0). `limit` must be 1 through 100. `offset` must be greater than or equal to 0. Any other integer is out of range. There is no maximum `offset`.
5. Stop at the first failure. `limit` is checked before `offset`, so both invalid names `limit`.

Messages, which all contain the parameter name:

- missing a number: `"<name> is missing a number"`
- not a whole number: `"<name> must be a whole number"`
- `limit` out of range: `"limit must be a whole number from 1 to 100"`
- `offset` out of range: `"offset must be a whole number from 0"`

The 400 body is only `{"error": <message>}`. It has no `items` key. Other keys in the parameter dict are ignored.

### No-parameter result

`get_items({})` is limit 20 and offset 0. On the current seed that is status 200, `items` of SKU-001 through SKU-020 in that order, and `total` 250. It is not the 250-item list the current test expects.

## Risks / Trade-offs

- [Callers of `get_items({})` stop receiving 250 items] → Documented default page above. Update `test_all_items_are_listed` in the same change. No other callers are in this repo.
- [`list_items()` signature break] → Only `get_items` calls it. Update that call in the same change. `find_item` stays argument-compatible.
- [A huge digit string is still a valid `offset`] → Accepted. The spec allows any whole number from 0, including `1000000`, and Python `int` can parse it. The page is then empty. This sample catalog does not need a digit-length cap.
- [Bare `int()` would accept `+` and spaces] → The `^-?\d+$` check runs first.

## Migration Plan

1. Change `list_items` and `get_items` together so nothing keeps the old full-list call.
2. Replace the test that expects 250 items from `get_items({})` with the default-page, other-page, and 400 cases in the spec.
3. Rollback is reverting `inventory/api.py`, `inventory/store.py`, and `tests/test_api.py`. There is no stored data and no deploy step.

## Open Questions

None. Parsing, error text, the `list_items` signature, and the no-parameter page are decided above and match the spec.
