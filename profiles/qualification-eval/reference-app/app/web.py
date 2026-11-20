"""Minimal WSGI layer. The tenant always comes from the verified token (INV-1)."""
import json
import logging
import re
import time

from app import auth, billing, tenants, tickets
from app.errors import AppError, AuthError, Invalid, NotFound, TooLarge

_ROUTES = []
log = logging.getLogger(__name__)
MAX_BODY_BYTES = 64 * 1024


def route(method, pattern):
    def register(fn):
        _ROUTES.append((method, re.compile("^" + pattern + "$"), fn))
        return fn

    return register


def _principal(db, key, environ, now):
    header = environ.get("HTTP_AUTHORIZATION", "")
    if not header.startswith("Bearer "):
        raise AuthError("missing bearer token")
    return auth.authenticate(db, key, header[len("Bearer "):], now)


@route("POST", r"/tickets")
def _create_ticket(ctx, p, body):
    return 201, tickets.create_ticket(ctx.db, p, body.get("title"), body.get("idempotency_key"))


@route("GET", r"/tickets/([0-9]{1,18})")
def _get_ticket(ctx, p, body, tid):
    return 200, tickets.get_ticket(ctx.db, p, int(tid))


@route("POST", r"/tickets/([0-9]{1,18})/assign")
def _assign(ctx, p, body, tid):
    return 200, tickets.assign_ticket(ctx.db, p, int(tid), body.get("assignee_id"))


@route("POST", r"/members")
def _add_member(ctx, p, body):
    tenants.add_member(ctx.db, p, body.get("user_id"), body.get("role"))
    return 201, {"ok": True}


@route("DELETE", r"/members/([0-9]{1,18})")
def _remove_member(ctx, p, body, uid):
    tenants.remove_member(ctx.db, p, int(uid))
    return 200, {"ok": True}


@route("GET", r"/billing/balance")
def _balance(ctx, p, body):
    return 200, {"balance_cents": billing.balance(ctx.db, p)}


@route("POST", r"/billing/credit")
def _credit(ctx, p, body):
    return 200, {"balance_cents": billing.credit(ctx.db, p, body.get("amount_cents"), body.get("idempotency_key"))}


@route("POST", r"/billing/debit")
def _debit(ctx, p, body):
    return 200, {"balance_cents": billing.debit(ctx.db, p, body.get("amount_cents"), body.get("idempotency_key"))}


def _reject_constant(name):
    raise ValueError(f"non-standard JSON constant {name}")


class App:
    def __init__(self, db, key=auth.TEST_SIGNING_KEY, clock=time.time):
        self.db, self.key, self.clock = db, key, clock

    def __call__(self, environ, start_response):
        try:
            status, payload = self._dispatch(environ)
        except AppError as exc:
            status, payload = exc.status, {"error": str(exc)}
        except Exception:  # last resort: never let a failure escape the WSGI boundary or leak detail
            log.exception("unhandled error while serving %s %s", environ.get("REQUEST_METHOD"), environ.get("PATH_INFO"))
            status, payload = 500, {"error": "internal error"}
        data = json.dumps(payload).encode()
        start_response(
            f"{status} -",
            [("Content-Type", "application/json"), ("Content-Length", str(len(data)))],
        )
        return [data]

    def _dispatch(self, environ):
        method, path = environ["REQUEST_METHOD"], environ["PATH_INFO"]
        body = self._body(environ)
        now = self.clock()
        if method == "POST" and path == "/login":
            token = auth.login(
                self.db, self.key, body.get("email"), body.get("password"),
                body.get("tenant_id"), now,
            )
            return 200, {"token": token}
        for m, pattern, fn in _ROUTES:
            match = pattern.match(path)
            if m == method and match:
                principal = _principal(self.db, self.key, environ, now)
                return fn(self, principal, body, *match.groups())
        raise NotFound("no such route")

    @staticmethod
    def _body(environ):
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            raise Invalid("bad content length") from None
        if length < 0:
            raise Invalid("bad content length")
        if length > MAX_BODY_BYTES:
            raise TooLarge(f"request body must not exceed {MAX_BODY_BYTES} bytes")
        if length == 0:
            return {}
        try:
            parsed = json.loads(environ["wsgi.input"].read(length), parse_constant=_reject_constant)
        except (ValueError, RecursionError):  # not JSON, non-standard constant, or nested too deeply
            raise Invalid("body must be JSON") from None
        if not isinstance(parsed, dict):
            raise Invalid("body must be a JSON object")
        return parsed
