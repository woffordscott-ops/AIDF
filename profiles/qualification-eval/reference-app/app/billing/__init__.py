"""Integer-cent ledger and invoices (INV-4)."""
from app import idempotency, permissions, tenants, validate
from app.db import transaction
from app.errors import Conflict, Invalid, NotFound

MAX_AMOUNT_CENTS = 10**12  # per operation or invoice line
MAX_BALANCE_CENTS = 10**15  # per tenant; far below SQLite's signed 64-bit limit


def _cents(value):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise Invalid("amount must be a positive integer number of cents")
    if value > MAX_AMOUNT_CENTS:
        raise Invalid(f"amount must not exceed {MAX_AMOUNT_CENTS} cents")
    return value


def balance(db, principal):
    permissions.require(principal, "billing.read")
    return _balance(db, principal.tenant_id)


def _balance(db, tenant_id):
    row = db.execute(
        "SELECT COALESCE(SUM(amount_cents), 0) AS b FROM ledger WHERE tenant_id = ?",
        (tenant_id,),
    ).fetchone()
    return row["b"]


def credit(db, principal, amount_cents, idempotency_key):
    permissions.require(principal, "billing.write")
    amount = _cents(amount_cents)
    key = idempotency.check_key(idempotency_key)
    request_hash = idempotency.fingerprint("credit", amount_cents=amount)
    with transaction(db):
        tenants.require_live(db, principal, "billing.write")
        saved = idempotency.replay(db, principal, key, request_hash)
        if saved is not None:
            return saved  # this exact request was already applied: answer it again, write nothing
        new_balance = _balance(db, principal.tenant_id) + amount
        if new_balance > MAX_BALANCE_CENTS:
            raise Conflict("balance limit exceeded")
        db.execute(
            "INSERT INTO ledger (tenant_id, kind, amount_cents) VALUES (?, 'credit', ?)",
            (principal.tenant_id, amount),
        )
        idempotency.remember(db, principal, key, request_hash, new_balance)
    return new_balance  # computed under the lock: nothing is read after COMMIT that could fail


def debit(db, principal, amount_cents, idempotency_key):
    permissions.require(principal, "billing.write")
    amount = _cents(amount_cents)
    key = idempotency.check_key(idempotency_key)
    request_hash = idempotency.fingerprint("debit", amount_cents=amount)
    with transaction(db):  # check-and-write is one atomic step
        tenants.require_live(db, principal, "billing.write")
        saved = idempotency.replay(db, principal, key, request_hash)
        if saved is not None:
            return saved
        new_balance = _balance(db, principal.tenant_id) - amount
        if new_balance < 0:
            raise Conflict("insufficient balance")
        db.execute(
            "INSERT INTO ledger (tenant_id, kind, amount_cents) VALUES (?, 'debit', ?)",
            (principal.tenant_id, -amount),
        )
        idempotency.remember(db, principal, key, request_hash, new_balance)
    return new_balance  # computed under the lock: nothing is read after COMMIT that could fail


def create_invoice(db, principal, lines, idempotency_key):
    permissions.require(principal, "billing.write")
    key = idempotency.check_key(idempotency_key)
    if not isinstance(lines, list) or not lines:
        raise Invalid("an invoice needs at least one line")
    parsed = []
    for line in lines:
        if not isinstance(line, dict) or not isinstance(line.get("description"), str):
            raise Invalid("each line needs a description")
        parsed.append((validate.text(line["description"], "description"), _cents(line.get("amount_cents"))))
    total = sum(amount for _, amount in parsed)
    if total > MAX_BALANCE_CENTS:
        raise Invalid("invoice total is too large")
    request_hash = idempotency.fingerprint("invoice", lines=parsed)
    with transaction(db):  # the invoice and all its lines are stored together or not at all
        tenants.require_live(db, principal, "billing.write")
        saved = idempotency.replay(db, principal, key, request_hash)
        if saved is not None:
            return saved
        cur = db.execute(
            "INSERT INTO invoices (tenant_id, total_cents) VALUES (?, ?)",
            (principal.tenant_id, total),
        )
        invoice_id = cur.lastrowid
        for description, amount in parsed:
            db.execute(
                "INSERT INTO invoice_lines (invoice_id, description, amount_cents) VALUES (?, ?, ?)",
                (invoice_id, description, amount),
            )
        invoice = {  # built from what was just written, under the lock; no read after COMMIT
            "id": invoice_id,
            "total_cents": total,
            "lines": [{"description": d, "amount_cents": a} for d, a in parsed],
        }
        idempotency.remember(db, principal, key, request_hash, invoice)
    return invoice


def get_invoice(db, principal, invoice_id):
    permissions.require(principal, "billing.read")
    invoice_id = validate.db_id(invoice_id, "invoice_id")
    inv = db.execute(
        "SELECT id, total_cents FROM invoices WHERE id = ? AND tenant_id = ?",
        (invoice_id, principal.tenant_id),
    ).fetchone()
    if inv is None:
        raise NotFound("invoice not found")
    lines = db.execute(
        "SELECT description, amount_cents FROM invoice_lines WHERE invoice_id = ?",
        (invoice_id,),
    ).fetchall()
    return {
        "id": inv["id"],
        "total_cents": inv["total_cents"],
        "lines": [{"description": r["description"], "amount_cents": r["amount_cents"]} for r in lines],
    }
