"""Goal Progress Tracker — tracks cumulative P&L toward the financial target."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .goal_state import GOAL_STATUS_ACHIEVED, GOAL_STATUS_FAILED, GoalState

logger = logging.getLogger("wasden_watch.pipeline.goal.progress")

# Re-evaluation thresholds
DEVIATION_TRIGGER_PCT = 0.30  # Re-evaluate if P&L deviates >30% from plan
TIME_PROGRESS_TRIGGER = 0.50  # >50% of timeframe elapsed
TARGET_PROGRESS_TRIGGER = 0.30  # <30% of target achieved
PACE_TOLERANCE = 0.20  # Within 20% of linear pace = "on track"


@dataclass
class GoalProgressUpdate:
    """Result of recording a trade result against the goal."""

    cumulative_pnl: float
    cumulative_pnl_pct: float
    remaining_target_pct: float
    remaining_capital: float
    remaining_days: int
    daily_target_pct: float
    on_track: bool
    pace: str  # "ahead", "on_track", "behind", "achieved"
    loss_limit_hit: bool
    should_re_evaluate: bool


class GoalProgressTracker:
    """Tracks cumulative P&L across multiple trades toward the goal."""

    def __init__(self, goal_state: GoalState):
        self._state = goal_state

    def record_trade_result(
        self,
        ticker: str,
        pnl: float,
        pnl_pct: float,
    ) -> GoalProgressUpdate:
        """Record a completed trade and update progress.

        Args:
            ticker: The ticker that was traded.
            pnl: Dollar P&L from the trade.
            pnl_pct: Percentage P&L from the trade.

        Returns:
            GoalProgressUpdate with current progress and re-evaluation flag.
        """
        config = self._state.config
        if config is None:
            raise ValueError("GoalState.config must be set")

        # Update cumulative P&L
        self._state.cumulative_pnl += pnl
        self._state.cumulative_pnl_pct += pnl_pct

        # Update remaining
        self._state.remaining_target_pct = config.target_return_pct - self._state.cumulative_pnl_pct
        self._state.remaining_capital += pnl  # Add back profits (or subtract losses)

        # Check if goal achieved
        if self._state.cumulative_pnl_pct >= config.target_return_pct:
            self._state.status = GOAL_STATUS_ACHIEVED

        # Check loss limit
        loss_limit_hit = self.check_loss_limit()
        if loss_limit_hit:
            self._state.status = GOAL_STATUS_FAILED

        remaining = self.get_remaining_target()

        return GoalProgressUpdate(
            cumulative_pnl=self._state.cumulative_pnl,
            cumulative_pnl_pct=self._state.cumulative_pnl_pct,
            remaining_target_pct=remaining["remaining_pct"],
            remaining_capital=self._state.remaining_capital,
            remaining_days=remaining["remaining_days"],
            daily_target_pct=remaining["daily_target_pct"],
            on_track=remaining["on_track"],
            pace=remaining["pace"],
            loss_limit_hit=loss_limit_hit,
            should_re_evaluate=self.should_re_evaluate(),
        )

    def should_re_evaluate(self) -> bool:
        """Determine if remaining trades need re-planning.

        Re-evaluate when:
            1. Cumulative P&L deviates >30% from linear pace
            2. A trade was BLOCKED or failed (checked externally)
            3. >50% of timeframe elapsed with <30% of target achieved
        """
        config = self._state.config
        if config is None:
            return False

        days_elapsed = self._state.days_elapsed
        timeframe = config.timeframe_days

        if timeframe <= 0 or days_elapsed <= 0:
            return False

        # Expected progress at this point (linear pace)
        expected_pct = config.target_return_pct * (days_elapsed / timeframe)
        actual_pct = self._state.cumulative_pnl_pct

        # Trigger 1: >30% deviation from expected pace
        if expected_pct > 0:
            deviation = abs(actual_pct - expected_pct) / expected_pct
            if deviation > DEVIATION_TRIGGER_PCT:
                return True

        # Trigger 3: >50% time elapsed, <30% target achieved
        time_progress = days_elapsed / timeframe
        if config.target_return_pct > 0:
            target_progress = self._state.cumulative_pnl_pct / config.target_return_pct
        else:
            target_progress = 1.0

        if time_progress > TIME_PROGRESS_TRIGGER and target_progress < TARGET_PROGRESS_TRIGGER:
            return True

        return False

    def get_remaining_target(self) -> dict:
        """Calculate what's left to achieve."""
        config = self._state.config
        if config is None:
            return {
                "remaining_pct": 0.0,
                "remaining_dollar": 0.0,
                "remaining_days": 0,
                "daily_target_pct": 0.0,
                "on_track": False,
                "pace": "unknown",
            }

        remaining_pct = max(0.0, config.target_return_pct - self._state.cumulative_pnl_pct)
        remaining_dollar = remaining_pct * config.capital
        remaining_days = max(0, config.timeframe_days - self._state.days_elapsed)

        daily_target_pct = remaining_pct / remaining_days if remaining_days > 0 else remaining_pct

        # Determine pace
        if self._state.cumulative_pnl_pct >= config.target_return_pct:
            pace = "achieved"
            on_track = True
        elif config.timeframe_days > 0 and self._state.days_elapsed > 0:
            expected = config.target_return_pct * (self._state.days_elapsed / config.timeframe_days)
            if expected > 0:
                ratio = self._state.cumulative_pnl_pct / expected
                if ratio >= (1 + PACE_TOLERANCE):
                    pace = "ahead"
                    on_track = True
                elif ratio >= (1 - PACE_TOLERANCE):
                    pace = "on_track"
                    on_track = True
                else:
                    pace = "behind"
                    on_track = False
            else:
                pace = "on_track"
                on_track = True
        else:
            pace = "on_track"
            on_track = True

        return {
            "remaining_pct": round(remaining_pct, 6),
            "remaining_dollar": round(remaining_dollar, 2),
            "remaining_days": remaining_days,
            "daily_target_pct": round(daily_target_pct, 6),
            "on_track": on_track,
            "pace": pace,
        }

    def check_loss_limit(self) -> bool:
        """Return True if cumulative loss has hit max_loss_pct."""
        config = self._state.config
        if config is None:
            return False

        # Loss is negative P&L
        if self._state.cumulative_pnl_pct < 0:
            return abs(self._state.cumulative_pnl_pct) >= config.max_loss_pct

        return False
