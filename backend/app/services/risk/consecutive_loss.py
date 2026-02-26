"""
Consecutive loss counter — per PROJECT_STANDARDS_v2.md Section 8.

At 7 consecutive losses: alert, pause entries, await human decision.
System explains what it is doing, why, and suggests possible shutdown.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.services.risk.constants import CONSECUTIVE_LOSS_WARNING

logger = logging.getLogger("wasden_watch.consecutive_loss")


@dataclass
class ConsecutiveLossState:
    """Tracks consecutive wins/losses."""
    current_streak: int = 0  # positive = wins, negative = losses
    streak_tickers: list[str] = field(default_factory=list)
    last_result_date: Optional[str] = None
    warning_active: bool = False
    entries_paused: bool = False
    paused_at: Optional[str] = None
    resumed_by: Optional[str] = None
    resumed_at: Optional[str] = None


# In-memory state (backed by DB via migration 009)
_state = ConsecutiveLossState()


def record_trade_result(ticker: str, is_win: bool) -> ConsecutiveLossState:
    """Record a trade result and update the streak.

    Args:
        ticker: The ticker that closed.
        is_win: True if trade was profitable, False if loss.

    Returns:
        Updated ConsecutiveLossState.
    """
    global _state
    now = datetime.utcnow().isoformat() + "Z"

    if is_win:
        if _state.current_streak < 0:
            # Reset losing streak
            _state.current_streak = 1
            _state.streak_tickers = [ticker]
        else:
            _state.current_streak += 1
            _state.streak_tickers.append(ticker)
        _state.warning_active = False
        _state.entries_paused = False
        logger.info(f"WIN recorded for {ticker}. Streak: +{_state.current_streak}")
    else:
        if _state.current_streak > 0:
            # Reset winning streak
            _state.current_streak = -1
            _state.streak_tickers = [ticker]
        else:
            _state.current_streak -= 1
            _state.streak_tickers.append(ticker)
        logger.info(f"LOSS recorded for {ticker}. Streak: {_state.current_streak}")

        # Check warning threshold
        consecutive_losses = abs(_state.current_streak)
        if consecutive_losses >= CONSECUTIVE_LOSS_WARNING:
            _state.warning_active = True
            _state.entries_paused = True
            _state.paused_at = now
            logger.critical(
                f"CONSECUTIVE LOSS WARNING: {consecutive_losses} consecutive losses "
                f"(threshold: {CONSECUTIVE_LOSS_WARNING}). "
                f"Entries PAUSED. Awaiting human decision."
            )

    _state.last_result_date = now
    return _state


def get_current_streak() -> ConsecutiveLossState:
    """Return current streak state."""
    return _state


def resume_after_human_decision(approved_by: str) -> ConsecutiveLossState:
    """Resume trading after human reviews the loss streak.

    Args:
        approved_by: Name of person approving the resume (Joe or Jared).

    Returns:
        Updated state with entries unpaused.
    """
    global _state

    if not _state.entries_paused:
        logger.info("Entries not paused, nothing to resume")
        return _state

    logger.info(f"Trading RESUMED after human decision by {approved_by}")
    _state.entries_paused = False
    _state.resumed_by = approved_by
    _state.resumed_at = datetime.utcnow().isoformat() + "Z"
    return _state


def consecutive_loss_to_dict(state: ConsecutiveLossState) -> dict:
    """Convert to API-friendly dict."""
    consecutive_losses = abs(state.current_streak) if state.current_streak < 0 else 0
    return {
        "current_streak": state.current_streak,
        "consecutive_losses": consecutive_losses,
        "warning_threshold": CONSECUTIVE_LOSS_WARNING,
        "warning_active": state.warning_active,
        "entries_paused": state.entries_paused,
        "paused_at": state.paused_at,
        "streak_tickers": state.streak_tickers,
        "last_result_date": state.last_result_date,
        "resumed_by": state.resumed_by,
        "resumed_at": state.resumed_at,
    }
