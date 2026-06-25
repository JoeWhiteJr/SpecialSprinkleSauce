"""Audit logging for sensitive operations.

Writes to two sinks:
  1. stdout (always) — immediate, zero latency impact
  2. Supabase audit_log table (when configured) — durable, survives restarts

The Supabase write is fire-and-forget (daemon thread). A failure there never
blocks the calling endpoint or loses the stdout record.
"""
import logging
import threading
from datetime import datetime, timezone

audit_logger = logging.getLogger("wasden_watch.audit")
audit_logger.setLevel(logging.INFO)

if not audit_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | AUDIT | %(message)s"
    ))
    audit_logger.addHandler(handler)


def _write_to_supabase(payload: dict) -> None:
    """Insert one audit row. Runs in a daemon thread — never raises."""
    try:
        from app.services.supabase_client import get_supabase
        get_supabase().table("audit_log").insert(payload).execute()
    except Exception as exc:
        audit_logger.warning("Supabase audit write failed: %s", exc)


def log_action(
    action: str,
    endpoint: str,
    initiated_by: str = "unknown",
    details: str = "",
) -> None:
    """Log a sensitive action to stdout and (if configured) Supabase."""
    ts = datetime.now(timezone.utc).isoformat()

    # Sink 1: stdout — always written, zero latency
    audit_logger.info(
        "action=%s endpoint=%s initiated_by=%s details=%s timestamp=%s",
        action, endpoint, initiated_by, details, ts,
    )

    # Sink 2: Supabase — best-effort, non-blocking
    from app.config import settings
    if not settings.use_mock_data and settings.supabase_url and settings.supabase_service_key:
        payload = {
            "action": action,
            "endpoint": endpoint,
            "principal": initiated_by,
            "details": details,
            "created_at": ts,
        }
        t = threading.Thread(target=_write_to_supabase, args=(payload,), daemon=True)
        t.start()
