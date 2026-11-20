# Quickstart: Paginate the Items Listing

Validation guide for the items listing after the tasks in [tasks.md](./tasks.md) are implemented. This file does not implement the feature. The scenarios below were not run against a paged listing, because that behavior is not in the code yet.

Related detail: [items listing contract](./contracts/items-listing.md), [data model](./data-model.md).

## Prerequisites

- Repository root as the working directory.
- Python 3.10 or newer. This workspace has Python 3.14.7.
- No packages to install.

## Baseline already observed

On 2026-11-05, before any listing change:

```text
python -m unittest
```

reported `Ran 2 tests` and `OK`. `tests/test_api.py` still expects a no-parameter listing of 250 items. That is the current behavior, not the target.

## Validate

From the repository root, after implementation:

```text
python -m unittest
```

Expected: the suite reports `OK`.

The suite should then show at least the following outcomes. Call `inventory.api.get_items` with the `params` dictionary. Compare the `(status, body)` pair with the contract.

| Check | Call | Expected |
| --- | --- | --- |
| No parameters | `get_items({})` | Status 200. `len(body["items"])` is 20. `body["total"]` is 250. Skus are SKU-001 through SKU-020 in that order. |
| Later page | `get_items({"limit": "20", "offset": "40"})` | Status 200. Skus SKU-041 through SKU-060. `total` is 250. |
| Last partial page | `get_items({"limit": "20", "offset": "240"})` | Status 200. 10 items, SKU-241 through SKU-250. `total` is 250. |
| Past the end | `get_items({"offset": "250"})` | Status 200. `items` is empty. `total` is 250. |
| Bounds | `get_items({"limit": "1"})` and `get_items({"limit": "100"})` | Status 200. Page lengths 1 and 100. `total` is 250. |
| Bad page size | `get_items({"limit": "0"})`, `get_items({"limit": "101"})`, `get_items({"limit": "abc"})`, `get_items({"limit": ""})` | Status 400. `body["error"]` is `limit must be a whole number from 1 to 100`. No `items` key. |
| Bad skip | `get_items({"offset": "-1"})`, `get_items({"offset": "1.5"})` | Status 400. `body["error"]` is `offset must be a whole number from 0`. No `items` key. |
| Both bad | `get_items({"limit": "0", "offset": "-1"})` | Status 400. The error names `limit` and uses the `limit` sentence above. |
| Single item still works | `get_item({"sku": "SKU-001"})` and `get_item({"sku": "nope"})` | Status 200, then status 404 with `{"error": "no such item"}`. |

Walking `offset` 0, 20, 40, … 240 with `limit` 20 returns each of the 250 skus once, in order, and every response has `total` 250.

## Done when

- Every row above matches.
- `python -m unittest` passes.
- `get_item` outcomes are unchanged.
