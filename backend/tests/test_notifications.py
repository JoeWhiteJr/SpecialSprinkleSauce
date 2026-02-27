"""Unit tests for the Notification Service.

Tests notification dispatch, channel handling, formatting, history,
and graceful degradation when channels are unconfigured.
"""

import os

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

import logging  # noqa: E402
from app.services.notifications.notification_service import NotificationService  # noqa: E402


def _fresh_service() -> NotificationService:
    """Create a fresh NotificationService with no external channels configured."""
    return NotificationService()


# ---------------------------------------------------------------------------
# test_notification_mock_mode — send stores in history
# ---------------------------------------------------------------------------

def test_notification_mock_mode():
    """Sending a notification stores it in history with correct fields."""
    svc = _fresh_service()
    result = svc.send(title="Test", message="Hello world", severity="info")

    assert result["title"] == "Test"
    assert result["message"] == "Hello world"
    assert result["severity"] == "info"
    assert result["success"] is True
    assert "id" in result
    assert "timestamp" in result
    assert "channel" in result

    # Should appear in history
    history = svc.get_history()
    assert len(history) == 1
    assert history[0]["id"] == result["id"]


# ---------------------------------------------------------------------------
# test_notification_channels_unconfigured — graceful when no Slack/email
# ---------------------------------------------------------------------------

def test_notification_channels_unconfigured():
    """When no Slack/email is configured, notifications fall back to log and succeed."""
    svc = _fresh_service()

    # With no webhook URL, Slack should fail gracefully
    result_slack = svc.send(title="Slack Test", message="test", channel="slack")
    # Channel failed but logged as fallback
    assert "failed" in result_slack["channel"] or result_slack["success"] is False

    # With no SMTP config, email should fail gracefully
    result_email = svc.send(title="Email Test", message="test", channel="email")
    assert "failed" in result_email["channel"] or result_email["success"] is False

    # Log channel always works
    result_log = svc.send(title="Log Test", message="test", channel="log")
    assert result_log["success"] is True
    assert result_log["channel"] == "log"


# ---------------------------------------------------------------------------
# test_risk_alert_formatting — correct title/message format
# ---------------------------------------------------------------------------

def test_risk_alert_formatting():
    """Risk alert notification formats ticker and rule into the message."""
    svc = _fresh_service()
    alert = {
        "severity": "warning",
        "title": "Position Size Exceeded",
        "message": "Proposed 15% exceeds limit",
        "rule_violated": "position_size",
        "ticker": "TSLA",
    }
    result = svc.send_risk_alert(alert)

    assert result["title"] == "Position Size Exceeded"
    assert "TSLA" in result["message"]
    assert "position_size" in result["message"]
    assert result["severity"] == "warning"
    assert result["success"] is True  # falls back to log


# ---------------------------------------------------------------------------
# test_circuit_breaker_notification — formats CB state correctly
# ---------------------------------------------------------------------------

def test_circuit_breaker_notification():
    """Circuit breaker alert formats SPY return and actions."""
    svc = _fresh_service()

    # Active circuit breaker
    cb_state = {
        "active": True,
        "triggered_at": "2026-02-21T14:00:00Z",
        "spy_5day_return": -0.062,
        "actions_taken": [
            "Cut all positions by 50%",
            "Increase cash target to 40%",
            "Halt new entries",
            "Alert both partners",
        ],
        "resolved_at": None,
        "resolved_by": None,
    }
    result = svc.send_circuit_breaker_alert(cb_state)

    assert result["title"] == "CIRCUIT BREAKER ACTIVATED"
    assert result["severity"] == "critical"
    assert "-6.20%" in result["message"]
    assert "Cut all positions by 50%" in result["message"]

    # Resolved circuit breaker
    cb_resolved = {
        "active": False,
        "resolved_by": "Joe",
    }
    result2 = svc.send_circuit_breaker_alert(cb_resolved)
    assert result2["title"] == "Circuit Breaker Resolved"
    assert result2["severity"] == "info"
    assert "Joe" in result2["message"]


# ---------------------------------------------------------------------------
# test_consecutive_loss_notification — formats loss streak
# ---------------------------------------------------------------------------

def test_consecutive_loss_notification():
    """Consecutive loss alert formats streak count and ticker list."""
    svc = _fresh_service()
    loss_state = {
        "current_streak": -5,
        "consecutive_losses": 5,
        "warning_active": False,
        "entries_paused": False,
        "streak_tickers": ["PYPL", "NFLX", "XOM", "TSLA", "AMD"],
    }
    result = svc.send_consecutive_loss_alert(loss_state)

    assert result["title"] == "Consecutive Loss Streak"
    assert "5 consecutive losses" in result["message"]
    assert "PYPL" in result["message"]
    assert result["severity"] == "warning"

    # Paused state should be critical
    paused_state = {
        "current_streak": -7,
        "consecutive_losses": 7,
        "warning_active": True,
        "entries_paused": True,
        "streak_tickers": ["PYPL", "NFLX", "XOM", "TSLA", "AMD", "AAPL", "MSFT"],
    }
    result2 = svc.send_consecutive_loss_alert(paused_state)
    assert result2["severity"] == "critical"
    assert "PAUSED" in result2["message"]


# ---------------------------------------------------------------------------
# test_notification_history — history accumulates
# ---------------------------------------------------------------------------

def test_notification_history():
    """Notification history accumulates in order, most recent first."""
    svc = _fresh_service()

    svc.send(title="First", message="1st", severity="info")
    svc.send(title="Second", message="2nd", severity="warning")
    svc.send(title="Third", message="3rd", severity="critical")

    history = svc.get_history()
    assert len(history) == 3
    # Most recent first
    assert history[0]["title"] == "Third"
    assert history[1]["title"] == "Second"
    assert history[2]["title"] == "First"


# ---------------------------------------------------------------------------
# test_fallback_to_log — always logs even if other channels fail
# ---------------------------------------------------------------------------

def test_fallback_to_log(caplog):
    """Notifications are always logged regardless of channel success/failure."""
    svc = _fresh_service()

    with caplog.at_level(logging.INFO, logger="wasden_watch.notifications"):
        svc.send(title="Log Fallback Test", message="Should be logged", severity="info")

    assert "Log Fallback Test" in caplog.text
    assert "Should be logged" in caplog.text


# ---------------------------------------------------------------------------
# test_get_channels — returns channel list with status
# ---------------------------------------------------------------------------

def test_get_channels():
    """get_channels returns all three channels with correct status."""
    svc = _fresh_service()
    channels = svc.get_channels()

    assert len(channels) == 3

    channel_names = [c["name"] for c in channels]
    assert "log" in channel_names
    assert "slack" in channel_names
    assert "email" in channel_names

    # Log is always enabled
    log_ch = next(c for c in channels if c["name"] == "log")
    assert log_ch["enabled"] is True
    assert log_ch["configured"] is True

    # Slack and email are not configured by default
    slack_ch = next(c for c in channels if c["name"] == "slack")
    assert slack_ch["enabled"] is False
    assert slack_ch["configured"] is False

    email_ch = next(c for c in channels if c["name"] == "email")
    assert email_ch["enabled"] is False

    # All channels have descriptions
    for ch in channels:
        assert "description" in ch
        assert len(ch["description"]) > 0
