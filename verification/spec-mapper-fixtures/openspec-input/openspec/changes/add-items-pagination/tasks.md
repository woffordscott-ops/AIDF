# Tasks

## 1. Page the listing

- [ ] 1.1 Change `list_items` in `inventory/store.py` to `list_items(limit: int, offset: int) -> tuple[list[Item], int]`. Sort by sku as it does now, set `total` to the sorted length, and return `ordered[offset:offset + limit]` plus `total` (empty page when `offset` is past the end). Update `get_items` in `inventory/api.py` so a valid request maps that page to `{"items": [{"sku", "name", "quantity"}, ...], "total": total}` with status 200, using 20 and 0 when `limit` or `offset` is omitted. Update the `get_items` docstring so it no longer says every item is returned. Replace `test_all_items_are_listed` and add the success cases from `specs/items-listing/spec.md` (no parameters, only `limit`, only `offset`, second page, partial last page, offset 250, offset 1000000, first item fields, limit 1, limit 100, offset 0, leading zeros `01`/`000`, offset `-0`). Verify with `python -m unittest`: those cases pass, and `test_one_item` still returns 200 for `SKU-001` and 404 for `nope`.

## 2. Reject invalid parameters

- [ ] 2.1 In `get_items`, before calling the store, classify each present value as in `design.md`: no decimal digit is missing a number, anything other than `^-?\d+$` is not a whole number, then range-check `limit` (1 through 100) and `offset` (from 0, no maximum). Check `limit` before `offset` and stop at the first failure. Return status 400 and `{"error": "<message>"}` with no `items` key, using the four message templates in `design.md`. Ignore unrelated parameters. Add tests for empty `limit`, empty `offset`, `abc`, `1.5`, `20.0`, `1e1`, `+20`, ` 20`, `limit` `0`, `limit` `101`, `limit` `-1`, `offset` `-1`, both `limit` `0` and `offset` `-1` (error contains `limit`), and a request whose only extra key is `sku`. Verify with `python -m unittest`: the new 400 cases pass and the section 1 page tests still pass.

## 3. Suite check

- [ ] 3.1 Run `python -m unittest` from the repo root and confirm the whole module passes, including the unchanged single-item cases and every page and 400 case above.
