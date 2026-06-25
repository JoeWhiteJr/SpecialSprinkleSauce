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


async def identify_principal(api_key: str = Security(API_KEY_HEADER)) -> str:
    """Derive the calling principal from X-API-Key.

    Production mode (API_KEY_JOE or API_KEY_JARED set): returns "joe" or "jared"
    based on which per-user key matches. Raises 401 if the key matches neither —
    the caller cannot self-assert identity via the request body.

    Dev mode (neither per-user key configured): validates the shared API_KEY if set,
    then returns "dev". Endpoints that use this dependency must handle "dev" by
    accepting an optional body field as a local-only fallback.
    """
    per_user_configured = bool(settings.api_key_joe or settings.api_key_jared)

    if per_user_configured:
        if settings.api_key_joe and api_key == settings.api_key_joe:
            return "joe"
        if settings.api_key_jared and api_key == settings.api_key_jared:
            return "jared"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key — use a per-approver key for this endpoint",
        )

    # Dev mode: validate shared key if configured, then return sentinel
    if settings.api_key and (not api_key or api_key != settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return "dev"
