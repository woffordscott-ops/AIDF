# Research: Paginate the Items Listing

## 1. Where the page is cut

**Decision**: Change `list_items` in `inventory/store.py` so it accepts `limit` and `offset` and returns the sku-ordered slice plus the full catalog count. `get_items` in `inventory/api.py` remains the only caller and is the place that applies defaults and refusals.

**Rationale**: The store already owns sku order (`sorted` by `item.sku`). The only caller is `get_items`. The request allows `list_items` to change. Keeping the slice next to the sort prevents the handler from re-ordering items. Status 400 stays in the handler because the store does not currently know about status codes (`get_item` is what returns 404).

**Alternatives considered**: Slice inside `get_items` and leave `list_items()` returning every item. That works, and it avoids a signature change, but it leaves two places that know about order if the handler sorts again, or it trusts the handler to remember that `list_items` is already ordered. A separate paging function beside an unchanged `list_items` adds a second entry point nobody else calls. Cursor-style paging was rejected because the request specifies `limit` and `offset`.

## 2. Result shape

**Decision**: Add a frozen dataclass `ItemPage` with `items: list[Item]` and `total: int`. `get_items` maps a successful page to `{"items": [{"sku", "name", "quantity"}, ...], "total": total}`.

**Rationale**: `Item` is already a frozen dataclass. A named result keeps `total` (the catalog count) distinct from the length of `items`. The response key `items` matches the body the current handler returns, so existing readers of that key still find the page there. `total` is the new catalog count.

**Alternatives considered**: Return a tuple `(list[Item], int)`. Shorter, but easy to confuse with the handler's `(status, body)` tuple. Put `total` only in the handler by calling `len` on a full list. That keeps the store return type stable, but then the store cannot be the single place that knows the catalog size once it returns a slice.

## 3. What a caller with no parameters receives

**Decision**: Omitted `limit` means 20. Omitted `offset` means 0. The successful body is the first 20 items in ascending sku order and `"total": 250`. With today's catalog those skus are SKU-001 through SKU-020.

**Rationale**: The request defines those defaults and asks for a documented result for callers who currently receive all 250 items. The catalog is built as `SKU-{n:03d}` for `n` from 1 to 250, then sorted by sku text. Zero-padded skus sort in that same order. Observed baseline: `python -m unittest` on 2026-11-05 ran 2 tests and passed, including `test_all_items_are_listed`, which still expects 250 items. That expectation is the behavior this change replaces. It was not changed in this planning step.

**Alternatives considered**: Keep returning all 250 items when both parameters are omitted, and page only when a parameter is present. That preserves today's callers, but it contradicts the requested defaults and the requirement to define the no-parameter result as a page.

## 4. Which strings are whole numbers

**Decision**: A present value is a whole number only when the entire string matches `^-?[0-9]+$`. Interpret it with `int`. Then apply the range: `limit` from 1 to 100 inclusive, `offset` greater than or equal to 0. Use ASCII digits `[0-9]`, not a Unicode digit class. `020` is the integer 20 and is in range for both parameters. `-0` is 0: refused for `limit`, accepted for `offset`.

**Rationale**: The specification treats a whole number as an optional leading minus and digits, with no other characters. `int("20.0")` and `int("1e2")` are the wrong checks because they reject some of those strings only by accident and accept others that the spec rejects (`+20` is accepted by `int` and rejected by this rule). A Unicode `\d` match would accept digits the spec does not list.

**Alternatives considered**: `str.lstrip("-").isdigit()` which rejects an empty remainder but still needs a separate check that the minus appears at most once. `int()` inside `try`/`except`, which accepts `+20` and leading or trailing whitespace is not accepted by `int` for a space-padded string, but `int("+20")` succeeds. Float parsing, which would accept `20.0`.

## 5. Omitted versus blank, and two bad values

**Decision**: A missing key uses the default. A present key, including `""` or whitespace, is validated and never defaults. If `limit` is present and unacceptable, return that refusal even when `offset` is also unacceptable. Judge `offset` only when `limit` is absent or acceptable.

**Rationale**: The specification separates omission from a blank value, and it says the page size is judged first.

**Alternatives considered**: Treat blank as omitted. That hides a caller mistake. Return both parameter names in one message. The specification only requires that `limit` be named when both are unacceptable.

## 6. Refusal body

**Decision**: Status 400 and `{"error": "limit must be a whole number from 1 to 100"}` or `{"error": "offset must be a whole number from 0"}`. The same message covers a missing number, a non-whole number, and an out-of-range number for that parameter. No `items` key on a refusal.

**Rationale**: `get_item` already returns `{"error": "no such item"}`. Reusing an `error` string keeps one failure shape. Each chosen sentence contains the parameter name, which is the testable requirement. One sentence per parameter avoids a matrix of wordings the specification left unfixed.

**Alternatives considered**: Different sentences for "not a number" and "out of range". More precise, and not required. A list of field errors. Heavier than the existing error string.

## 7. Skip at or past the end

**Decision**: `offset` greater than or equal to the catalog count returns status 200, `"items": []`, and the real `total`. The store slices the ordered catalog with `ordered[offset:offset + limit]` after the handler has guaranteed `offset >= 0` and `limit >= 1`.

**Rationale**: Python slicing already yields an empty list when the start is past the end, including a very large `offset`. The specification says this is success, not a refusal, and that there is no maximum skip.

**Alternatives considered**: Refuse an `offset` greater than or equal to `total` with status 400. That invents an upper bound the request does not set. Clamp the offset back to the last page. That would return items the caller did not ask for.

## 8. Parameters the listing does not use

**Decision**: `get_items` reads only `limit` and `offset`. Any other key is ignored. `get_item` and `find_item` are not modified.

**Rationale**: The specification assumes unknown parameters do not change the page, and it places single-item lookup out of scope.

**Alternatives considered**: Reject unknown keys with status 400. Stricter, and it would change callers that send extra keys for no current effect.

## 9. Dependencies and platform

**Decision**: Add no package and no service. Stay on the standard library and on `unittest`.

**Rationale**: `inventory/api.py` and `inventory/store.py` import only the standard library. The handler contract is a dict in and a `(status, body)` pair out. Introducing an HTTP framework would invent a server the sample does not have.

**Alternatives considered**: Define an OpenAPI server and a query-string parser. The project never receives a raw query string; `params` is already `dict[str, str]`. The contract is documented as that function contract instead.
