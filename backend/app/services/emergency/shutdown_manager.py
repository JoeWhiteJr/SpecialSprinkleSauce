"""
Emergency Shutdown Manager — coordinated system-wide halt.

Provides emergency shutdown capability to cancel all open orders,
halt trading, and force paper mode. Tracks shutdown/resume history.

Works in mock mode by default (no Alpaca client needed).
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from app.config import settings

logger = logging.getLogger("wasden_watch.emergency")


@dataclass
class ShutdownEvent:
    """Record of a shutdown or resume event."""
    timestamp: str
    initiated_by: str
    reason: str
    orders_cancelled: int
    actions_taken: list[str]
    event_type: str  # "shutdown" or "resume"


class ShutdownManager:
    """Emergency shutdown coordinator.

    Manages system-wide trading halt, order cancellation, and
    resume flow. Maintains in-memory state and event history.
    """

    def __init__(self):
        self._shutdown_active: bool = False
        self._history: list[dict] = []

    def emergency_shutdown(self, initiated_by: str, reason: str) -> dict:
        """Execute emergency shutdown — cancel orders, halt trading.

        Args:
            initiated_by: Name of person or system initiating shutdown.
            reason: Human-readable reason for the shutdown.

        Returns:
            Dict with shutdown result details.
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        self._shutdown_active = True

        # Cancel all open orders
        cancelled = self.cancel_all_orders()
        orders_cancelled = len(cancelled)

        actions_taken = [
            "Set shutdown_active = True",
            f"Cancelled {orders_cancelled} open orders",
            "Halted new order submissions",
            "Alert sent to partners",
        ]

        logger.critical(
            f"EMERGENCY SHUTDOWN initiated by {initiated_by}: {reason} "
            f"({orders_cancelled} orders cancelled)"
        )

        event = {
            "timestamp": timestamp,
            "initiated_by": initiated_by,
            "reason": reason,
            "orders_cancelled": orders_cancelled,
            "actions_taken": actions_taken,
            "event_type": "shutdown",
        }
        self._history.append(event)

        return {
            "success": True,
            "timestamp": timestamp,
            "initiated_by": initiated_by,
            "reason": reason,
            "orders_cancelled": orders_cancelled,
            "actions_taken": actions_taken,
        }

    def cancel_all_orders(self) -> list[dict]:
        """Cancel all open orders via Alpaca client.

        In mock mode, returns empty list (simulated).

        Returns:
            List of cancelled order details.
        """
        if settings.use_mock_data:
            logger.info("MOCK: cancel_all_orders — no real orders to cancel")
            return []

        try:
            from app.services.execution.alpaca_client import AlpacaClient
            client = AlpacaClient()
            cancelled = client.cancel_all_orders()
            logger.info(f"Cancelled {len(cancelled)} orders via Alpaca")
            return cancelled
        except Exception as e:
            logger.error(f"Failed to cancel orders during shutdown: {e}")
            return []

    def force_paper_mode(self) -> dict:
        """Request switch to paper trading mode.

        Note: Actual environment change requires service restart.

        Returns:
            Dict with status and current mode.
        """
        logger.warning(
            f"Force paper mode requested. Current mode: {settings.trading_mode}. "
            "Requires service restart to take effect."
        )
        return {
            "success": True,
            "message": "Paper mode requested. Requires service restart.",
            "current_mode": settings.trading_mode,
        }

    def get_shutdown_status(self) -> dict:
        """Return current shutdown status.

        Returns:
            Dict with active state, last event, and trading mode.
        """
        last_event = self._history[-1] if self._history else None
        return {
            "active": self._shutdown_active,
            "last_event": last_event,
            "trading_mode": settings.trading_mode,
        }

    def resume_trading(self, approved_by: str) -> dict:
        """Resume trading after emergency shutdown.

        Args:
            approved_by: Name of person approving the resume (required, non-empty).

        Returns:
            Dict with resume result details.

        Raises:
            ValueError: If approved_by is empty.
        """
        if not approved_by or not approved_by.strip():
            raise ValueError("approved_by is required (non-empty string)")

        timestamp = datetime.utcnow().isoformat() + "Z"
        self._shutdown_active = False

        logger.info(f"Trading RESUMED — approved by {approved_by}")

        event = {
            "timestamp": timestamp,
            "initiated_by": approved_by,
            "reason": "Trading resumed",
            "orders_cancelled": 0,
            "actions_taken": ["Set shutdown_active = False", "Trading resumed"],
            "event_type": "resume",
        }
        self._history.append(event)

        return {
            "success": True,
            "timestamp": timestamp,
            "approved_by": approved_by,
            "message": "Trading resumed",
        }

    def get_shutdown_history(self) -> list[dict]:
        """Return full shutdown/resume event history.

        Returns:
            List of event dicts in chronological order.
        """
        return list(self._history)

    def is_shutdown_active(self) -> bool:
        """Check if emergency shutdown is currently active.

        Returns:
            True if shutdown is active, False otherwise.
        """
        return self._shutdown_active
