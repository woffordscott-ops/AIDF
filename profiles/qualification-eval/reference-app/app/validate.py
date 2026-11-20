"""Shared validation of untrusted values before they reach the database or a dictionary."""
from app.errors import Invalid

MAX_DB_INT = 2**63 - 1  # the largest integer SQLite can bind


def text(value, name="value"):
    """A string that can be stored: a lone UTF-16 surrogate cannot be encoded as UTF-8."""
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise Invalid(f"{name} must be valid text") from None
    return value


def db_id(value, name="id"):
    """A positive integer SQLite can bind; anything else is a client error, never an exception."""
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= MAX_DB_INT:
        raise Invalid(f"{name} must be a positive integer")
    return value
