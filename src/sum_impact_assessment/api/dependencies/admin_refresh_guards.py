"""
Guard helpers for admin full refresh endpoints.
"""
from __future__ import annotations

import time
from threading import Lock
from typing import Dict, Optional, Tuple

from fastapi import Depends, Header, HTTPException, Request, status

from ...config.settings import settings
from .auth import verify_admin_refresh_api_key

_rate_limit_store: Dict[str, float] = {}
_idempotency_store: Dict[str, Tuple[str, float]] = {}
_rate_limit_lock = Lock()
_idempotency_lock = Lock()


def _prune_rate_limit_store(now: float) -> None:
    expired_keys = [
        api_key for api_key, timestamp in _rate_limit_store.items()
        if now - timestamp >= settings.REFRESH_RATE_LIMIT_SECONDS
    ]
    for api_key in expired_keys:
        _rate_limit_store.pop(api_key, None)


def _prune_idempotency_store(now: float) -> None:
    expired_keys = [
        key for key, (_, timestamp) in _idempotency_store.items()
        if now - timestamp >= settings.REFRESH_IDEMPOTENCY_WINDOW_SECONDS
    ]
    for key in expired_keys:
        _idempotency_store.pop(key, None)


def enforce_ip_allowlist(request: Request) -> None:
    """
    Restrict admin refresh requests to allowed client hosts.
    """
    if not settings.ADMIN_REFRESH_ALLOWED_IPS:
        return

    client_host = request.client.host if request.client else None
    if client_host not in settings.ADMIN_REFRESH_ALLOWED_IPS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Request origin is not allowed"
        )


def enforce_rate_limit(api_key: str = Depends(verify_admin_refresh_api_key)) -> str:
    """
    Reject refresh requests that arrive inside the configured rate-limit window.
    """
    check_rate_limit(api_key)
    return api_key


def check_rate_limit(api_key: str) -> None:
    """
    Reject refresh requests that arrive inside the configured rate-limit window.
    """
    now = time.time()

    with _rate_limit_lock:
        _prune_rate_limit_store(now)
        previous_timestamp = _rate_limit_store.get(api_key)
        if previous_timestamp is not None:
            retry_after = max(
                1,
                int(settings.REFRESH_RATE_LIMIT_SECONDS - (now - previous_timestamp))
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limited",
                    "retry_after_seconds": retry_after
                }
            )


def validate_idempotency_key(
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key")
) -> Optional[str]:
    """
    Reject duplicate idempotent refresh requests inside the configured time window.
    """
    if not idempotency_key:
        return None

    now = time.time()
    with _idempotency_lock:
        _prune_idempotency_store(now)
        existing = _idempotency_store.get(idempotency_key)
        if existing is not None:
            original_run_id, _ = existing
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "duplicate_request",
                    "original_run_id": original_run_id
                }
            )

    return idempotency_key


def mark_rate_limit(api_key: str) -> None:
    """
    Store the timestamp of a successfully accepted refresh trigger.
    """
    with _rate_limit_lock:
        _rate_limit_store[api_key] = time.time()


def remember_idempotency_key(idempotency_key: Optional[str], run_id: str) -> None:
    """
    Store the accepted run id for a given idempotency key.
    """
    if not idempotency_key:
        return

    with _idempotency_lock:
        _idempotency_store[idempotency_key] = (run_id, time.time())


def reset_admin_refresh_guards_state() -> None:
    """
    Reset in-memory guard state for tests.
    """
    with _rate_limit_lock:
        _rate_limit_store.clear()

    with _idempotency_lock:
        _idempotency_store.clear()