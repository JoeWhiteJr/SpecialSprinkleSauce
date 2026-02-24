from supabase import create_client, Client
from app.config import settings


_client: Client | None = None


def get_supabase() -> Client:
    """Return a singleton Supabase client. Raises if credentials are missing."""
    global _client
    if _client is None:
        if not settings.supabase_url or not settings.supabase_service_key:
            raise RuntimeError(
                "Supabase credentials not configured. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env"
            )
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client


def check_connection() -> bool:
    """Quick connectivity check. Returns True if Supabase responds."""
    if settings.use_mock_data:
        return False
    try:
        client = get_supabase()
        # Simple query to verify connectivity
        client.table("system_settings").select("*").limit(1).execute()
        return True
    except Exception:
        return False
