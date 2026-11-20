# Spec Delta

## Purpose

Returns one sku-ordered page of inventory items for GET /items, including the catalog total, and rejects invalid limit and offset values.

## ADDED Requirements

### Requirement: Omitted parameters use defaults
An items listing that omits `limit` MUST use 20. An items listing that omits `offset` MUST use 0. The response MUST be the page those defaults select.

#### Scenario: No parameters on the seeded catalog
- **WHEN** the items listing is requested with no parameters and the catalog is the 250 seeded items SKU-001 through SKU-250
- **THEN** the status is 200, `items` contains SKU-001 through SKU-020 in that order, and `total` is 250

#### Scenario: Only limit is sent
- **WHEN** `limit` is `5` and `offset` is omitted on the seeded catalog
- **THEN** the status is 200, `items` contains SKU-001 through SKU-005 in that order, and `total` is 250

#### Scenario: Only offset is sent
- **WHEN** `offset` is `5` and `limit` is omitted on the seeded catalog
- **THEN** the status is 200, `items` contains SKU-006 through SKU-025 in that order, and `total` is 250

### Requirement: Page content and total
The listing MUST answer a valid request with status 200. The body MUST include `items` and `total`. `items` MUST be the contiguous slice of the catalog in ascending sku order, starting at `offset`, with at most `limit` items. `total` MUST be the full catalog size and MUST NOT change with the page. Each item MUST include `sku`, `name`, and `quantity` from the catalog.

#### Scenario: Second page
- **WHEN** `limit` is `20` and `offset` is `20` on the seeded catalog
- **THEN** the status is 200, `items` contains SKU-021 through SKU-040 in that order, and `total` is 250

#### Scenario: Partial last page
- **WHEN** `limit` is `20` and `offset` is `240` on the seeded catalog
- **THEN** the status is 200, `items` contains SKU-241 through SKU-250 in that order, and `total` is 250

#### Scenario: Offset at the catalog size
- **WHEN** `limit` is `20` and `offset` is `250` on the seeded catalog
- **THEN** the status is 200, `items` is an empty array, and `total` is 250

#### Scenario: Offset far past the end
- **WHEN** `limit` is `20` and `offset` is `1000000` on the seeded catalog
- **THEN** the status is 200, `items` is an empty array, and `total` is 250

#### Scenario: First seeded item keeps its fields
- **WHEN** the items listing is requested with no parameters on the seeded catalog
- **THEN** the first item has `sku` `SKU-001`, `name` `Item 1`, and `quantity` 1

### Requirement: Inclusive page bounds
`limit` MUST be accepted for the whole numbers 1 and 100. `offset` MUST be accepted for the whole number 0. An accepted `offset` past the last item MUST still return status 200 and an empty `items` array.

#### Scenario: Smallest limit
- **WHEN** `limit` is `1` and `offset` is `0` on the seeded catalog
- **THEN** the status is 200, `items` contains only SKU-001, and `total` is 250

#### Scenario: Largest limit
- **WHEN** `limit` is `100` and `offset` is `0` on the seeded catalog
- **THEN** the status is 200, `items` contains SKU-001 through SKU-100 in that order, and `total` is 250

#### Scenario: Zero offset
- **WHEN** `limit` is `20` and `offset` is `0` on the seeded catalog
- **THEN** the status is 200 and the first item is SKU-001

### Requirement: Whole-number values
A present `limit` or `offset` is a whole number only when the entire value is an optional leading `-` followed by one or more decimal digits. Leading zeros MUST be accepted and MUST NOT change the integer value. A present value with no decimal digit MUST be treated as missing a number. Any other present value MUST be treated as not a whole number.

#### Scenario: Leading zeros are the same integer
- **WHEN** `limit` is `01` and `offset` is `000` on the seeded catalog
- **THEN** the status is 200, `items` contains only SKU-001, and `total` is 250

#### Scenario: Empty limit is missing a number
- **WHEN** `limit` is an empty string
- **THEN** the status is 400 and the `error` string contains `limit`

#### Scenario: Empty offset is missing a number
- **WHEN** `offset` is an empty string
- **THEN** the status is 400 and the `error` string contains `offset`

#### Scenario: Letters are missing a number
- **WHEN** `offset` is `abc`
- **THEN** the status is 400 and the `error` string contains `offset`

#### Scenario: Fractional limit is not a whole number
- **WHEN** `limit` is `1.5`
- **THEN** the status is 400 and the `error` string contains `limit`

#### Scenario: Trailing decimal is not a whole number
- **WHEN** `limit` is `20.0`
- **THEN** the status is 400 and the `error` string contains `limit`

#### Scenario: Exponent and sign and space are not whole numbers
- **WHEN** `limit` is `1e1`, or `limit` is `+20`, or `offset` is ` 20`
- **THEN** the status is 400 and the `error` string contains the rejected parameter's name

### Requirement: Out-of-range values
`limit` MUST be rejected when its whole-number value is less than 1 or greater than 100. `offset` MUST be rejected when its whole-number value is less than 0. There is no maximum `offset`. The rejection MUST use status 400, and the `error` string MUST contain that parameter's name.

#### Scenario: Limit below 1
- **WHEN** `limit` is `0`
- **THEN** the status is 400 and the `error` string contains `limit`

#### Scenario: Limit above 100
- **WHEN** `limit` is `101`
- **THEN** the status is 400 and the `error` string contains `limit`

#### Scenario: Negative limit
- **WHEN** `limit` is `-1`
- **THEN** the status is 400 and the `error` string contains `limit`

#### Scenario: Negative offset
- **WHEN** `offset` is `-1`
- **THEN** the status is 400 and the `error` string contains `offset`

#### Scenario: Negative zero offset is zero
- **WHEN** `offset` is `-0` and `limit` is omitted on the seeded catalog
- **THEN** the status is 200, `items` contains SKU-001 through SKU-020 in that order, and `total` is 250

### Requirement: One error names the parameter
A rejected listing MUST return a body that is an object with an `error` string and MUST NOT return `items`. When both `limit` and `offset` are invalid, the `error` string MUST contain `limit`. Parameters other than `limit` and `offset` MUST NOT change the page and MUST NOT by themselves cause a 400.

#### Scenario: Both parameters invalid
- **WHEN** `limit` is `0` and `offset` is `-1`
- **THEN** the status is 400 and the `error` string contains `limit`

#### Scenario: Unrelated parameter is ignored
- **WHEN** the request includes `sku` set to `SKU-001` and omits `limit` and `offset` on the seeded catalog
- **THEN** the status is 200, `items` contains SKU-001 through SKU-020 in that order, and `total` is 250
