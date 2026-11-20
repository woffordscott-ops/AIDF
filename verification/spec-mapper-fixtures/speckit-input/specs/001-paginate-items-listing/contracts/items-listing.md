# Contract: Items listing

Operation name: items listing (`GET /items`).

Implementation: `get_items(params: dict[str, str]) -> tuple[int, dict]` in `inventory/api.py`.

This project does not run an HTTP server. Callers pass a dictionary of string parameters and receive a status integer and a body dictionary. Keys other than `limit` and `offset` are ignored. Single-item lookup (`get_item`) is not part of this contract.

Catalog used in the examples: 250 items, skus SKU-001 through SKU-250, ascending sku order. See [data-model.md](../data-model.md).

## Request

| Parameter | Required | Default when the key is absent | Accepted value |
| --- | --- | --- | --- |
| `limit` | no | `20` | Whole number from 1 to 100 inclusive |
| `offset` | no | `0` | Whole number greater than or equal to 0 |

A present value is a whole number only when it fully matches `^-?[0-9]+$`. A present key is never replaced by the default, including when the value is empty or whitespace.

## Success

Status `200`.

```text
{
  "items": [ { "sku": string, "name": string, "quantity": integer }, ... ],
  "total": integer
}
```

- `items` is the page, in ascending sku order, starting after `offset` catalog items, with length at most `limit`.
- `total` is the number of items in the catalog, not the length of `items`.
- Each element has only `sku`, `name`, and `quantity`.

### Examples (today's catalog)

| `params` | `items` | `total` |
| --- | --- | --- |
| `{}` | SKU-001 through SKU-020 (20 items) | 250 |
| `{"limit": "20", "offset": "0"}` | SKU-001 through SKU-020 | 250 |
| `{"limit": "20", "offset": "40"}` | SKU-041 through SKU-060 | 250 |
| `{"limit": "1"}` | SKU-001 only | 250 |
| `{"limit": "100"}` | SKU-001 through SKU-100 | 250 |
| `{"limit": "20", "offset": "240"}` | SKU-241 through SKU-250 (10 items) | 250 |
| `{"offset": "250"}` | empty list | 250 |
| `{"offset": "1000"}` | empty list | 250 |
| `{"limit": "020", "offset": "0"}` | SKU-001 through SKU-020 | 250 |

## Refusal

Status `400`. The body is an error object and does not contain `items`.

| Condition | Body |
| --- | --- |
| `limit` is present and is not a whole number, or is outside 1 through 100 | `{"error": "limit must be a whole number from 1 to 100"}` |
| `limit` is absent or acceptable, and `offset` is present and is not a whole number, or is below 0 | `{"error": "offset must be a whole number from 0"}` |

When both values are unacceptable, the response is the `limit` error above.

Covered examples of refusal: `""`, `" "`, `"abc"`, `"20abc"`, `"1.5"`, `"20.0"`, `"+20"`, `"1e2"`, `limit` `"0"`, `limit` `"-1"`, `limit` `"-0"`, `limit` `"101"`, `offset` `"-1"`. `offset` `"-0"` is success (the integer 0), not a refusal.

## Out of scope

- `get_item`: a known sku still returns status 200 and that item; an unknown sku still returns status 404 and `{"error": "no such item"}`.
- Changing the catalog, item fields, or sort order.
