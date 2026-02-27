"""Audit logging for sensitive operations."""
import logging
from datetime import datetime, timezone

audit_logger = logging.getLogger("wasden_watch.audit")
audit_logger.setLevel(logging.INFO)

# Add a file handler if one doesn't exist
if not audit_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | AUDIT | %(message)s"
    ))
    audit_logger.addHandler(handler)


def log_action(action: str, endpoint: str, initiated_by: str = "unknown", details: str = ""):
    """Log a sensitive action to the audit trail."""
    audit_logger.info(
        f"action={action} endpoint={endpoint} initiated_by={initiated_by} "
        f"details={details} timestamp={datetime.now(timezone.utc).isoformat()}"
    )
