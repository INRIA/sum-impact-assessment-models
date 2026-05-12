"""
HTTP error translation utilities for FastAPI route handlers.
"""
import functools

from fastapi import HTTPException


def translate_errors(func):
    """
    Decorator that converts unhandled exceptions in route handlers to HTTP 500 responses.

    ``HTTPException`` instances are re-raised unchanged so that explicit status
    codes (404, 409, …) are not accidentally promoted to 500.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return wrapper
