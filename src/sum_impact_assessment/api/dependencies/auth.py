"""
Authentication dependencies for API routes.
"""
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from ...config.settings import settings


api_key_header = APIKeyHeader(name="X-Internal-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> None:
    """
    Verify internal API key sent in request headers.
    """
    if not api_key or api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
