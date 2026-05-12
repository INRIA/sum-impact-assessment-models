"""
UTC time helper — replaces deprecated ``datetime.utcnow()``.
"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current UTC time as a naive datetime (DB-compatible)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
