# Proposal

## Why

`GET /items` returns the entire catalog on every call. The in-memory store already holds 250 items, and `get_items` ignores its query parameters, so every caller pays for a full sku-ordered dump. Listing needs a bounded page so callers can walk the catalog without taking all of it at once.

## What Changes

- `GET /items` (`get_items`) accepts `limit` and `offset` and returns one page of items in sku order plus the total number of items.
- `limit` is a whole number from 1 to 100 and defaults to 20. `offset` is a whole number from 0 and defaults to 0. There is no upper bound on `offset`.
- A value that is missing a number, is not a whole number, or is out of range is rejected with status 400 and an error message that names the parameter.
- **BREAKING**: a caller that passes no parameters currently receives all 250 items and no total. That call becomes the default page: the first 20 items in sku order and `total` 250 (with the current seed). It no longer receives the full catalog.
- `list_items` may change so the store applies sku order, `limit`, and `offset` and reports the total. `GET /items/<sku>` (`get_item`) stays as it is.

## Capabilities

### New Capabilities

- `items-listing`: Paginated `GET /items` — page bounds, sku order, the total count, the no-parameter default page, and 400 responses that name `limit` or `offset`.

### Modified Capabilities

- None. The project has no existing specs (`openspec list --specs` reported no specs).

## Impact

- `inventory/api.py`: `get_items` today returns `200` and `{"items": [...]}` for every item from `store.list_items()`, which sorts the full 250-item seed by sku. The handler must read `limit` and `offset`, validate them, and return a page plus `total`.
- `inventory/store.py`: `list_items()` currently takes no arguments and returns every item ordered by sku. Its signature and return value may change to serve a page and a total. `find_item` is unchanged.
- `tests/test_api.py`: `test_all_items_are_listed` calls `get_items({})` and asserts 250 items. That assertion no longer matches the default page and must be replaced with coverage for the default page, other pages, and 400 validation.
- No new dependencies. Item objects stay `{sku, name, quantity}`.
