"""Password hashing and signed, expiring session tokens (INV-1, INV-5)."""
import base64
import hashlib
import hmac
import json
import math
import secrets
from dataclasses import dataclass

from app.errors import AuthError, Invalid

# Fixture-only constant. Never a real key.
TEST_SIGNING_KEY = b"reference-app-fixture-key-not-a-secret"
TOKEN_TTL_SECONDS = 3600
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


@dataclass(frozen=True)
class Principal:
    user_id: int
    tenant_id: int
    role: str


def hash_password(password):
    if not isinstance(password, str) or len(password) < 8:
        raise Invalid("password must be at least 8 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return salt.hex() + "$" + digest.hex()


def verify_password(password, stored):
    if not isinstance(password, str):
        return False
    try:
        salt_hex, digest_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    try:
        actual = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    except UnicodeEncodeError:  # a lone surrogate can never match a stored password
        return False
    return hmac.compare_digest(actual, expected)


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(key, body):
    return hmac.new(key, body.encode(), hashlib.sha256).hexdigest()


MAX_TIME = 10**15  # seconds; far beyond any real clock or lifetime, far below float limits


def _finite_number(value):
    """A real number that is finite and within +/- MAX_TIME. Compares without converting huge ints."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float) and not math.isfinite(value):
        return False
    return -MAX_TIME <= value <= MAX_TIME


def _reject_constant(name):
    raise ValueError(f"non-standard JSON constant {name}")


def issue_token(key, user_id, tenant_id, role, now, ttl=TOKEN_TTL_SECONDS):
    if not (_finite_number(now) and _finite_number(ttl) and ttl > 0):
        raise Invalid("token time and ttl must be finite numbers and ttl positive")
    payload = {"uid": user_id, "tid": tenant_id, "role": role, "exp": now + ttl}
    body = _b64(json.dumps(payload, sort_keys=True).encode())
    return body + "." + _sign(key, body)


def verify_token(key, token, now):
    """Return the Principal for a valid, unexpired token; raise AuthError otherwise."""
    if not isinstance(token, str) or token.count(".") != 1:
        raise AuthError("malformed token")
    body, signature = token.split(".")
    if not body.isascii():  # a valid body is base64url; never sign text that cannot be encoded
        raise AuthError("malformed token")
    if not _finite_number(now):
        raise AuthError("bad clock")
    if not signature.isascii() or not hmac.compare_digest(_sign(key, body), signature):
        raise AuthError("bad signature")
    try:
        payload = json.loads(_unb64(body), parse_constant=_reject_constant)
        user_id, tenant_id = payload["uid"], payload["tid"]
        role, expires = payload["role"], payload["exp"]
    except (ValueError, KeyError, TypeError) as exc:
        raise AuthError("malformed token") from exc
    if not _finite_number(expires) or now >= expires:
        raise AuthError("token expired")
    return Principal(user_id=user_id, tenant_id=tenant_id, role=role)


def authenticate(db, key, token, now):
    """Verify a token, then derive authority from the user's LIVE membership.

    The token proves who the caller is and which tenant they chose at login. Their role
    (and whether they still belong at all) is read from the database on every request, so
    a removed or demoted member cannot keep acting on a token issued earlier (INV-2).
    """
    claim = verify_token(key, token, now)
    row = db.execute(
        "SELECT role FROM memberships WHERE tenant_id = ? AND user_id = ? AND active = 1",
        (claim.tenant_id, claim.user_id),
    ).fetchone()
    if row is None:
        raise AuthError("membership revoked")
    return Principal(user_id=claim.user_id, tenant_id=claim.tenant_id, role=row["role"])


def _is_text(value):
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


_UNKNOWN_USER_HASH = hash_password("not-a-real-password")  # fixture-only; burns the same work for unknown emails


def _is_int(value):
    """A real integer that SQLite can bind (signed 64-bit); anything else is a login failure."""
    return isinstance(value, int) and not isinstance(value, bool) and -(2**63) <= value < 2**63


def login(db, key, email, password, tenant_id, now):
    """Authenticate and mint a token for one tenant the user actively belongs to."""
    if not (isinstance(email, str) and isinstance(password, str) and _is_int(tenant_id)):
        raise AuthError("invalid credentials")  # same answer as any other login failure
    if not (_is_text(email) and _is_text(password)):
        raise AuthError("invalid credentials")  # not storable text: no account can match
    user = db.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    # An unknown email still costs one scrypt, so neither the answer nor the time tells them apart.
    stored = user["password_hash"] if user is not None else _UNKNOWN_USER_HASH
    password_ok = verify_password(password, stored)
    if user is None or not password_ok:
        raise AuthError("invalid credentials")
    member = db.execute(
        "SELECT role FROM memberships WHERE tenant_id = ? AND user_id = ? AND active = 1",
        (tenant_id, user["id"]),
    ).fetchone()
    if member is None:
        raise AuthError("invalid credentials")
    return issue_token(key, user["id"], tenant_id, member["role"], now)
