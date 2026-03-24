"""Tests for GoalProgressTracker."""

import os

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

from src.pipeline.goal.goal_state import (  # noqa: E402
    GOAL_STATUS_ACHIEVED,
    GOAL_STATUS_FAILED,
    GoalConfig,
    GoalState,
)
from src.pipeline.goal.progress_tracker import GoalProgressTracker  # noqa: E402


def _make_config(**overrides) -> GoalConfig:
    defaults = dict(capital=10000.0, target_return_pct=0.02, timeframe_days=5, max_loss_pct=0.01)
    defaults.update(overrides)
    return GoalConfig.create(**defaults)


def _make_state(config: GoalConfig, **overrides) -> GoalState:
    state = GoalState(goal_id=config.goal_id, config=config, remaining_capital=config.capital)
    for k, v in overrides.items():
        setattr(state, k, v)
    return state


class TestProgressTracker:

    def test_record_trade_updates_cumulative_pnl(self):
        """Recording a trade updates cumulative P&L."""
        config = _make_config()
        state = _make_state(config)
        tracker = GoalProgressTracker(state)

        update = tracker.record_trade_result("NVDA", pnl=50.0, pnl_pct=0.005)

        assert update.cumulative_pnl == 50.0
        assert update.cumulative_pnl_pct == 0.005

    def test_multiple_trades_accumulate(self):
        """Multiple trades accumulate toward the goal."""
        config = _make_config(target_return_pct=0.02)
        state = _make_state(config)
        tracker = GoalProgressTracker(state)

        tracker.record_trade_result("NVDA", pnl=100.0, pnl_pct=0.01)
        update = tracker.record_trade_result("MSFT", pnl=80.0, pnl_pct=0.008)

        assert update.cumulative_pnl == 180.0
        assert abs(update.cumulative_pnl_pct - 0.018) < 1e-9

    def test_goal_achieved_status(self):
        """Status changes to 'achieved' when target is hit."""
        config = _make_config(target_return_pct=0.01)
        state = _make_state(config)
        tracker = GoalProgressTracker(state)

        tracker.record_trade_result("NVDA", pnl=100.0, pnl_pct=0.01)

        assert state.status == GOAL_STATUS_ACHIEVED

    def test_loss_limit_halts_goal(self):
        """Status changes to 'failed' when cumulative loss hits max_loss_pct."""
        config = _make_config(max_loss_pct=0.01)
        state = _make_state(config)
        tracker = GoalProgressTracker(state)

        update = tracker.record_trade_result("NVDA", pnl=-100.0, pnl_pct=-0.01)

        assert update.loss_limit_hit is True
        assert state.status == GOAL_STATUS_FAILED

    def test_loss_below_limit_does_not_halt(self):
        """Small loss doesn't trigger halt."""
        config = _make_config(max_loss_pct=0.01)
        state = _make_state(config)
        tracker = GoalProgressTracker(state)

        update = tracker.record_trade_result("NVDA", pnl=-50.0, pnl_pct=-0.005)

        assert update.loss_limit_hit is False

    def test_remaining_target_calculation(self):
        """Remaining target = target - cumulative."""
        config = _make_config(target_return_pct=0.02)
        state = _make_state(config)
        tracker = GoalProgressTracker(state)

        update = tracker.record_trade_result("NVDA", pnl=100.0, pnl_pct=0.008)

        assert abs(update.remaining_target_pct - 0.012) < 1e-6


class TestReEvaluation:

    def test_behind_pace_triggers_re_evaluation(self):
        """Re-evaluate when >50% time elapsed with <30% of target achieved."""
        config = _make_config(target_return_pct=0.10, timeframe_days=10)
        state = _make_state(config, days_elapsed=6, cumulative_pnl_pct=0.01)
        tracker = GoalProgressTracker(state)

        assert tracker.should_re_evaluate() is True

    def test_on_pace_does_not_trigger(self):
        """Don't re-evaluate when progress is on track."""
        config = _make_config(target_return_pct=0.10, timeframe_days=10)
        state = _make_state(config, days_elapsed=5, cumulative_pnl_pct=0.05)
        tracker = GoalProgressTracker(state)

        assert tracker.should_re_evaluate() is False

    def test_no_days_elapsed_does_not_trigger(self):
        """No re-evaluation when timeframe hasn't started."""
        config = _make_config()
        state = _make_state(config, days_elapsed=0)
        tracker = GoalProgressTracker(state)

        assert tracker.should_re_evaluate() is False


class TestPaceTracking:

    def test_pace_achieved(self):
        """Pace is 'achieved' when target is met."""
        config = _make_config(target_return_pct=0.02)
        state = _make_state(config, days_elapsed=3, cumulative_pnl_pct=0.025)
        tracker = GoalProgressTracker(state)

        remaining = tracker.get_remaining_target()
        assert remaining["pace"] == "achieved"
        assert remaining["on_track"] is True

    def test_pace_ahead(self):
        """Pace is 'ahead' when >20% above linear."""
        config = _make_config(target_return_pct=0.10, timeframe_days=10)
        state = _make_state(config, days_elapsed=5, cumulative_pnl_pct=0.08)
        tracker = GoalProgressTracker(state)

        remaining = tracker.get_remaining_target()
        assert remaining["pace"] == "ahead"

    def test_pace_behind(self):
        """Pace is 'behind' when <80% of linear."""
        config = _make_config(target_return_pct=0.10, timeframe_days=10)
        state = _make_state(config, days_elapsed=5, cumulative_pnl_pct=0.01)
        tracker = GoalProgressTracker(state)

        remaining = tracker.get_remaining_target()
        assert remaining["pace"] == "behind"
        assert remaining["on_track"] is False
