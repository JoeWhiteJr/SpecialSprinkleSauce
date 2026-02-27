"""API Key authentication middleware for Wasden Watch."""
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str = Security(API_KEY_HEADER)):
    """Validate API key from X-API-Key header.

    If API_KEY is not configured (empty string), authentication is disabled
    to allow local development without keys.
    """
    if not settings.api_key:
        return None  # Auth disabled when no key configured
    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key
