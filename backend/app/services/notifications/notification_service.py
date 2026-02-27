"""
Notification Service — multi-channel notification dispatch for Wasden Watch.

Supports Slack (webhook), email (SMTP), and log fallback.
Graceful degradation: if a channel fails, falls back to logging.
All notifications are stored in an in-memory history for dashboard display.
"""

import logging
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Optional

from app.config import settings

logger = logging.getLogger("wasden_watch.notifications")


class NotificationService:
    """Multi-channel notification dispatcher with graceful degradation."""

    def __init__(self):
        self._history: list[dict] = []
        self._slack_webhook_url: str = getattr(settings, "slack_webhook_url", "")
        self._email_smtp_host: str = getattr(settings, "email_smtp_host", "")
        self._email_smtp_port: int = getattr(settings, "email_smtp_port", 587)
        self._email_from: str = getattr(settings, "email_from", "")
        self._email_recipients: list[str] = getattr(settings, "email_recipients", [])
        self._email_password: str = getattr(settings, "email_password", "")

    # ------------------------------------------------------------------
    # Core send method
    # ------------------------------------------------------------------

    def send(
        self,
        title: str,
        message: str,
        severity: str = "info",
        channel: str | None = None,
    ) -> dict:
        """Send a notification through the specified (or default) channel.

        Args:
            title: Notification title/subject.
            message: Notification body text.
            severity: One of "info", "warning", "critical".
            channel: Target channel ("slack", "email", "log", or None for auto).

        Returns:
            Dict with id, timestamp, title, message, severity, channel, success.
        """
        notification_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        success = False
        actual_channel = channel or self._default_channel()

        # Always log regardless of channel
        self._send_log(title, message, severity)

        # Route to channel handler
        if actual_channel == "slack":
            success = self._send_slack(title, message, severity)
        elif actual_channel == "email":
            success = self._send_email(
                title, message, severity, self._email_recipients
            )
        elif actual_channel == "log":
            # Already logged above
            success = True
        else:
            logger.warning(f"Unknown channel '{actual_channel}', falling back to log")
            actual_channel = "log"
            success = True

        # If the primary channel failed, mark log as fallback
        if not success:
            logger.warning(
                f"Channel '{actual_channel}' failed for notification '{title}'. "
                "Logged as fallback."
            )
            actual_channel = f"{actual_channel} (failed, logged)"

        record = {
            "id": notification_id,
            "timestamp": timestamp,
            "title": title,
            "message": message,
            "severity": severity,
            "channel": actual_channel,
            "success": success,
        }
        self._history.append(record)
        return record

    # ------------------------------------------------------------------
    # Channel handlers
    # ------------------------------------------------------------------

    def _send_slack(self, title: str, message: str, severity: str) -> bool:
        """Send notification via Slack webhook.

        Returns True on success, False on failure.
        """
        if not self._slack_webhook_url:
            logger.warning("Slack webhook URL not configured, cannot send")
            return False

        severity_emoji = {"critical": ":red_circle:", "warning": ":warning:", "info": ":information_source:"}.get(
            severity, ":information_source:"
        )
        payload = {
            "text": f"{severity_emoji} *{title}*\n{message}",
            "username": "Wasden Watch",
        }

        try:
            import httpx

            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    self._slack_webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code == 200:
                    logger.info(f"Slack notification sent: {title}")
                    return True
                else:
                    logger.error(
                        f"Slack webhook returned {response.status_code}: {response.text}"
                    )
                    return False
        except Exception as exc:
            logger.error(f"Slack send failed: {exc}")
            return False

    def _send_email(
        self,
        title: str,
        message: str,
        severity: str,
        recipients: list[str],
    ) -> bool:
        """Send notification via SMTP email.

        Returns True on success, False on failure.
        """
        if not self._email_smtp_host or not self._email_from or not recipients:
            logger.warning("Email not configured (missing host, from, or recipients)")
            return False

        severity_prefix = f"[{severity.upper()}] " if severity != "info" else ""
        subject = f"{severity_prefix}Wasden Watch: {title}"

        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = self._email_from
        msg["To"] = ", ".join(recipients)

        try:
            with smtplib.SMTP(self._email_smtp_host, self._email_smtp_port) as server:
                server.starttls()
                if self._email_password:
                    server.login(self._email_from, self._email_password)
                server.send_message(msg)
            logger.info(f"Email notification sent to {recipients}: {title}")
            return True
        except Exception as exc:
            logger.error(f"Email send failed: {exc}")
            return False

    def _send_log(self, title: str, message: str, severity: str) -> None:
        """Log the notification. Always succeeds."""
        log_message = f"NOTIFICATION [{severity.upper()}] {title}: {message}"
        if severity == "critical":
            logger.critical(log_message)
        elif severity == "warning":
            logger.warning(log_message)
        else:
            logger.info(log_message)

    # ------------------------------------------------------------------
    # Convenience methods for specific event types
    # ------------------------------------------------------------------

    def send_risk_alert(self, alert: dict) -> dict:
        """Send a formatted risk alert notification.

        Args:
            alert: Dict with keys like severity, title, message, rule_violated, ticker.
        """
        severity = alert.get("severity", "warning")
        title = alert.get("title", "Risk Alert")
        ticker = alert.get("ticker", "")
        rule = alert.get("rule_violated", "")
        message = alert.get("message", "")

        formatted_message = message
        if ticker:
            formatted_message = f"[{ticker}] {formatted_message}"
        if rule:
            formatted_message = f"{formatted_message} (Rule: {rule})"

        return self.send(
            title=title,
            message=formatted_message,
            severity=severity,
        )

    def send_circuit_breaker_alert(self, state: dict) -> dict:
        """Send a circuit breaker activation/resolution notification.

        Args:
            state: Dict from circuit_breaker_to_dict().
        """
        active = state.get("active", False)
        spy_return = state.get("spy_5day_return")
        actions = state.get("actions_taken", [])

        if active:
            spy_pct = f"{spy_return:.2%}" if spy_return is not None else "N/A"
            message = (
                f"SPY 5-day return: {spy_pct}. "
                f"Actions: {', '.join(actions) if actions else 'none'}"
            )
            return self.send(
                title="CIRCUIT BREAKER ACTIVATED",
                message=message,
                severity="critical",
            )
        else:
            resolved_by = state.get("resolved_by", "unknown")
            return self.send(
                title="Circuit Breaker Resolved",
                message=f"Circuit breaker deactivated by {resolved_by}.",
                severity="info",
            )

    def send_consecutive_loss_alert(self, state: dict) -> dict:
        """Send a consecutive loss streak notification.

        Args:
            state: Dict from consecutive_loss_to_dict().
        """
        streak = state.get("current_streak", 0)
        consecutive_losses = state.get("consecutive_losses", abs(streak) if streak < 0 else 0)
        tickers = state.get("streak_tickers", [])
        paused = state.get("entries_paused", False)

        severity = "critical" if paused else "warning"
        title = "Consecutive Loss Streak"
        message = (
            f"{consecutive_losses} consecutive losses. "
            f"Tickers: {', '.join(tickers[-5:]) if tickers else 'none'}. "
            f"Entries {'PAUSED' if paused else 'active'}."
        )

        return self.send(title=title, message=message, severity=severity)

    def send_pipeline_complete(
        self, ticker: str, action: str, reason: str
    ) -> dict:
        """Send a pipeline completion notification.

        Args:
            ticker: The ticker processed.
            action: Final action taken (BUY, SELL, HOLD, etc.).
            reason: Reason for the action.
        """
        return self.send(
            title=f"Pipeline Complete: {ticker}",
            message=f"Action: {action}. {reason}",
            severity="info",
        )

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_history(self) -> list[dict]:
        """Return notification history, most recent first."""
        return list(reversed(self._history))

    def get_channels(self) -> list[dict]:
        """Return configured notification channels with status."""
        channels = [
            {
                "name": "log",
                "enabled": True,
                "configured": True,
                "description": "Application logger (always active)",
            },
            {
                "name": "slack",
                "enabled": bool(self._slack_webhook_url),
                "configured": bool(self._slack_webhook_url),
                "description": "Slack webhook notifications",
            },
            {
                "name": "email",
                "enabled": bool(
                    self._email_smtp_host and self._email_from and self._email_recipients
                ),
                "configured": bool(self._email_smtp_host),
                "description": "Email (SMTP) notifications",
            },
        ]
        return channels

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _default_channel(self) -> str:
        """Determine default channel based on what is configured."""
        if self._slack_webhook_url:
            return "slack"
        if self._email_smtp_host and self._email_from and self._email_recipients:
            return "email"
        return "log"


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Return the singleton NotificationService instance."""
    global _service
    if _service is None:
        _service = NotificationService()
    return _service
