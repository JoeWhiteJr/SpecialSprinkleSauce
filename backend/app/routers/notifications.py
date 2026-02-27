"""
Notifications router — notification history, channels, test dispatch, and preferences.

Follows mock-first pattern: if settings.use_mock_data, returns mock data
without touching external services or database.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ---------------------------------------------------------------------------
# Request body models
# ---------------------------------------------------------------------------

class TestNotificationRequest(BaseModel):
    channel: str = "log"
    message: str = "Test notification from Wasden Watch dashboard"


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

def _mock_notifications() -> list[dict]:
    """Generate mock notification history."""
    base = datetime(2026, 2, 21, 14, 0, 0, tzinfo=timezone.utc)
    return [
        {
            "id": "notif-001",
            "timestamp": (base).isoformat(),
            "title": "Pipeline Complete: NVDA",
            "message": "Action: BUY. Strong quant composite with Wasden APPROVE.",
            "severity": "info",
            "channel": "log",
            "success": True,
        },
        {
            "id": "notif-002",
            "timestamp": (base - timedelta(hours=1)).isoformat(),
            "title": "Risk Alert: Position Size",
            "message": "[TSLA] Proposed position 15% exceeds MAX_POSITION_PCT 12%. (Rule: position_size)",
            "severity": "warning",
            "channel": "log",
            "success": True,
        },
        {
            "id": "notif-003",
            "timestamp": (base - timedelta(hours=3)).isoformat(),
            "title": "Consecutive Loss Streak",
            "message": "3 consecutive losses. Tickers: PYPL, NFLX, XOM. Entries active.",
            "severity": "warning",
            "channel": "log",
            "success": True,
        },
        {
            "id": "notif-004",
            "timestamp": (base - timedelta(days=1)).isoformat(),
            "title": "CIRCUIT BREAKER ACTIVATED",
            "message": "SPY 5-day return: -6.20%. Actions: Cut all positions by 50%, Increase cash target to 40%, Halt new entries, Alert both partners",
            "severity": "critical",
            "channel": "log",
            "success": True,
        },
        {
            "id": "notif-005",
            "timestamp": (base - timedelta(days=2)).isoformat(),
            "title": "Pipeline Complete: AAPL",
            "message": "Action: HOLD. Wasden NEUTRAL — insufficient coverage depth.",
            "severity": "info",
            "channel": "log",
            "success": True,
        },
    ]


def _mock_channels() -> list[dict]:
    """Generate mock channel status list."""
    return [
        {
            "name": "log",
            "enabled": True,
            "configured": True,
            "description": "Application logger (always active)",
        },
        {
            "name": "slack",
            "enabled": False,
            "configured": False,
            "description": "Slack webhook notifications",
        },
        {
            "name": "email",
            "enabled": False,
            "configured": False,
            "description": "Email (SMTP) notifications",
        },
    ]


def _mock_preferences() -> dict:
    """Generate mock notification preferences."""
    return {
        "risk_alerts": {
            "channels": ["log", "slack"],
            "min_severity": "warning",
            "description": "Risk engine alerts (position size, correlation, etc.)",
        },
        "circuit_breaker": {
            "channels": ["log", "slack", "email"],
            "min_severity": "critical",
            "description": "Circuit breaker activation/resolution",
        },
        "consecutive_losses": {
            "channels": ["log", "slack"],
            "min_severity": "warning",
            "description": "Consecutive loss streak warnings",
        },
        "pipeline_complete": {
            "channels": ["log"],
            "min_severity": "info",
            "description": "Pipeline run completion notices",
        },
        "screening_complete": {
            "channels": ["log"],
            "min_severity": "info",
            "description": "Screening funnel completion notices",
        },
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("")
async def list_notifications():
    """List recent notifications, most recent first."""
    if settings.use_mock_data:
        return _mock_notifications()

    from app.services.notifications.notification_service import get_notification_service

    service = get_notification_service()
    return service.get_history()


@router.get("/channels")
async def list_channels():
    """List configured notification channels and their status."""
    if settings.use_mock_data:
        return _mock_channels()

    from app.services.notifications.notification_service import get_notification_service

    service = get_notification_service()
    return service.get_channels()


@router.post("/test")
async def send_test_notification(body: TestNotificationRequest):
    """Send a test notification to verify channel configuration.

    Body:
        channel: Target channel ("slack", "email", "log").
        message: Message text to send.
    """
    if settings.use_mock_data:
        return {
            "id": "test-notif-mock",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "title": "Test Notification",
            "message": body.message,
            "severity": "info",
            "channel": body.channel,
            "success": True,
        }

    from app.services.notifications.notification_service import get_notification_service

    service = get_notification_service()
    result = service.send(
        title="Test Notification",
        message=body.message,
        severity="info",
        channel=body.channel,
    )
    return result


@router.get("/preferences")
async def get_preferences():
    """Get notification preferences — which events route to which channels."""
    if settings.use_mock_data:
        return _mock_preferences()

    # In production this would come from DB/settings; for now return defaults
    return _mock_preferences()
