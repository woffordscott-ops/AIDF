# Data Model: Paginate the Items Listing

The catalog is the existing in-memory list. This feature does not add storage, identifiers, or a lifecycle. A listing is a pure read.

## Item

Already stored. Unchanged by this feature.

| Field | Type | Rules |
| --- | --- | --- |
| sku | string | Required. Unique in the current catalog. Today's values are `SKU-001` through `SKU-250`. |
| name | string | Required. Today's value is `Item {n}` for the same `n` as the sku. |
| quantity | integer | Required. Today's value is `n % 7`. |

**Ordering**: Ascending sku text. For the current zero-padded skus, that order is SKU-001, SKU-002, … SKU-250.

**Relationships**: An item appears on a page only as an element of that page's `items` slice. Lookup by sku (`find_item`) is a separate read and is unchanged.

## ItemPage

New result of `list_items`. Not stored.

| Field | Type | Rules |
| --- | --- | --- |
| items | list of Item | The contiguous sku-ordered slice starting after `offset` items and containing at most `limit` items. Length is 0 when `offset` is greater than or equal to the catalog count, or when the catalog is empty. Length is never greater than `limit`. |
| total | integer | Count of every item in the catalog, not the length of `items`. Today's catalog count is 250. `total` is greater than or equal to 0. |

**Relationships**: `items` is a slice of the sku-ordered catalog. `total` is `len` of that full ordered catalog, computed on the same read as the slice.

**Validation (enforced before the store builds a page)**:

- `limit` is a whole number from 1 to 100 inclusive. When `limit` is omitted, use 20.
- `offset` is a whole number greater than or equal to 0. There is no upper bound. When `offset` is omitted, use 0.
- The store receives those integers only after they have passed the rules above. It does not invent a status code.

## Page request

Not stored. The two optional inputs to the listing.

| Field | Type | Rules |
| --- | --- | --- |
| limit | whole number, or absent | Absent means 20. Present means the entire value matches `^-?[0-9]+$`, then the integer is from 1 to 100 inclusive. Otherwise the listing is refused and the message names `limit`. |
| offset | whole number, or absent | Absent means 0. Present means the entire value matches `^-?[0-9]+$`, then the integer is greater than or equal to 0. Otherwise the listing is refused and the message names `offset`. |

A whole number is an optional leading `-` followed by one or more ASCII digits `0-9` and nothing else. `020` means 20. `-0` means 0 (refused for `limit`, accepted for `offset`). Empty, whitespace, `+20`, `20.0`, `1.5`, `20abc`, and `abc` are refusals.

If both present values are unacceptable, the refusal names `limit` and does not need to name `offset`.

## State transitions

None. Items are not created, updated, or deleted by this feature. Each listing reads the current catalog and returns one `ItemPage`.
