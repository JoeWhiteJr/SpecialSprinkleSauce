"""Tests for GoalConfig, GoalState, and GoalArbiter."""

import os

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

from src.pipeline.goal.goal_state import (  # noqa: E402
    GOAL_STATUS_PLANNING,
    GoalConfig,
    GoalState,
)
from src.pipeline.goal.goal_arbiter import GoalArbiter  # noqa: E402
from app.services.risk.constants import MAX_POSITION_PCT, RISK_PER_TRADE_PCT  # noqa: E402

import pytest  # noqa: E402


# ---------------------------------------------------------------------------
# GoalConfig validation
# ---------------------------------------------------------------------------


class TestGoalConfig:

    def test_create_valid(self):
        """GoalConfig.create with valid params produces correct computed fields."""
        config = GoalConfig.create(
            capital=1000.0,
            target_return_pct=0.02,
            timeframe_days=5,
            max_loss_pct=0.01,
        )
        assert config.capital == 1000.0
        assert config.target_return_pct == 0.02
        assert config.timeframe_days == 5
        assert config.max_loss_pct == 0.01
        assert config.target_dollar == 20.0  # 1000 * 0.02
        assert config.max_loss_dollar == 10.0  # 1000 * 0.01
        assert config.goal_id  # non-empty UUID
        assert config.created_at  # non-empty timestamp

    def test_daily_target_pct(self):
        """daily_target_pct divides evenly across timeframe."""
        config = GoalConfig.create(capital=1000, target_return_pct=0.10, timeframe_days=10, max_loss_pct=0.05)
        assert abs(config.daily_target_pct - 0.01) < 1e-9

    def test_create_zero_capital_raises(self):
        with pytest.raises(ValueError, match="capital must be positive"):
            GoalConfig.create(capital=0, target_return_pct=0.02, timeframe_days=5, max_loss_pct=0.01)

    def test_create_negative_target_raises(self):
        with pytest.raises(ValueError, match="target_return_pct must be positive"):
            GoalConfig.create(capital=1000, target_return_pct=-0.01, timeframe_days=5, max_loss_pct=0.01)

    def test_create_timeframe_out_of_range_raises(self):
        with pytest.raises(ValueError, match="timeframe_days must be 1-90"):
            GoalConfig.create(capital=1000, target_return_pct=0.02, timeframe_days=0, max_loss_pct=0.01)
        with pytest.raises(ValueError, match="timeframe_days must be 1-90"):
            GoalConfig.create(capital=1000, target_return_pct=0.02, timeframe_days=91, max_loss_pct=0.01)

    def test_create_zero_max_loss_raises(self):
        with pytest.raises(ValueError, match="max_loss_pct must be positive"):
            GoalConfig.create(capital=1000, target_return_pct=0.02, timeframe_days=5, max_loss_pct=0)

    def test_frozen_after_creation(self):
        """GoalConfig is immutable."""
        config = GoalConfig.create(capital=1000, target_return_pct=0.02, timeframe_days=5, max_loss_pct=0.01)
        with pytest.raises(AttributeError):
            config.capital = 2000  # type: ignore[misc]


# ---------------------------------------------------------------------------
# GoalState
# ---------------------------------------------------------------------------


class TestGoalState:

    def test_viable_tickers_excludes_blocked_and_escalated(self):
        state = GoalState(
            ticker_results={
                "NVDA": {"final_action": "BUY", "recommended_position_size": 0.08},
                "XOM": {"final_action": "BLOCKED", "recommended_position_size": 0.0},
                "TSM": {"final_action": "ESCALATED", "recommended_position_size": 0.0},
                "AAPL": {"final_action": "HOLD", "recommended_position_size": 0.05},
            }
        )
        viable = state.viable_tickers()
        assert "NVDA" in viable
        assert "AAPL" in viable
        assert "XOM" not in viable
        assert "TSM" not in viable

    def test_viable_tickers_empty_when_all_blocked(self):
        state = GoalState(
            ticker_results={
                "XOM": {"final_action": "BLOCKED"},
                "TSM": {"final_action": "ESCALATED"},
            }
        )
        assert state.viable_tickers() == []

    def test_default_status_is_planning(self):
        state = GoalState()
        assert state.status == GOAL_STATUS_PLANNING


# ---------------------------------------------------------------------------
# GoalArbiter — position sizing
# ---------------------------------------------------------------------------


def _make_config(**overrides) -> GoalConfig:
    """Helper to create a GoalConfig with sensible defaults."""
    defaults = dict(capital=10000.0, target_return_pct=0.02, timeframe_days=5, max_loss_pct=0.01)
    defaults.update(overrides)
    return GoalConfig.create(**defaults)


def _make_state(
    config: GoalConfig,
    allocations: list[dict],
    ticker_results: dict[str, dict],
) -> GoalState:
    """Helper to create a GoalState ready for the arbiter."""
    return GoalState(
        goal_id=config.goal_id,
        config=config,
        portfolio_allocations=allocations,
        ticker_results=ticker_results,
    )


class TestGoalArbiter:

    def test_basic_trade_plan(self):
        """Two-ticker allocation produces two trades with correct sizing."""
        config = _make_config(capital=10000.0)
        state = _make_state(
            config=config,
            allocations=[
                {"ticker": "NVDA", "allocation_pct": 40},
                {"ticker": "AAPL", "allocation_pct": 30},
            ],
            ticker_results={
                "NVDA": {"final_action": "BUY", "recommended_position_size": 0.10, "price": 200.0},
                "AAPL": {"final_action": "BUY", "recommended_position_size": 0.08, "price": 180.0},
            },
        )

        trades = GoalArbiter.build_trade_plan(state)
        assert len(trades) == 2
        assert trades[0].ticker == "NVDA"
        assert trades[1].ticker == "AAPL"
        assert all(t.shares > 0 for t in trades)
        assert all(t.stop_loss_price < t.entry_price_est for t in trades)

    def test_allocation_never_exceeds_capital(self):
        """Total allocated dollars never exceed available capital."""
        config = _make_config(capital=1000.0)
        state = _make_state(
            config=config,
            allocations=[
                {"ticker": "NVDA", "allocation_pct": 60},
                {"ticker": "AAPL", "allocation_pct": 60},  # Total 120% — should be capped
            ],
            ticker_results={
                "NVDA": {"final_action": "BUY", "recommended_position_size": 0.12, "price": 200.0},
                "AAPL": {"final_action": "BUY", "recommended_position_size": 0.12, "price": 180.0},
            },
        )

        trades = GoalArbiter.build_trade_plan(state)
        total_allocated = sum(t.position_dollar for t in trades)
        assert total_allocated <= config.capital

    def test_position_respects_max_position_pct(self):
        """No single trade exceeds MAX_POSITION_PCT of capital."""
        config = _make_config(capital=10000.0)
        state = _make_state(
            config=config,
            allocations=[{"ticker": "NVDA", "allocation_pct": 90}],  # 90% allocation
            ticker_results={
                "NVDA": {"final_action": "BUY", "recommended_position_size": 0.50, "price": 200.0},
            },
        )

        trades = GoalArbiter.build_trade_plan(state)
        assert len(trades) == 1
        max_allowed = MAX_POSITION_PCT * config.capital
        assert trades[0].position_dollar <= max_allowed + 0.01  # float tolerance

    def test_loss_limit_user_stricter_than_system(self):
        """When user max_loss is stricter, it wins."""
        # User: 0.5% loss limit, System: 1.5% (RISK_PER_TRADE_PCT)
        config = _make_config(capital=10000.0, max_loss_pct=0.005)
        position_dollar = 1000.0

        effective = GoalArbiter.effective_max_loss_per_trade(config, position_dollar)
        expected_user_loss = 0.005 * position_dollar  # $5

        assert effective == expected_user_loss  # User is stricter

    def test_loss_limit_system_stricter_than_user(self):
        """When system RISK_PER_TRADE_PCT is stricter, it wins."""
        # User: 50% loss limit (very loose), System: 1.5%
        config = _make_config(capital=10000.0, max_loss_pct=0.50)
        position_dollar = 5000.0

        effective = GoalArbiter.effective_max_loss_per_trade(config, position_dollar)
        expected_system_loss = RISK_PER_TRADE_PCT * config.capital  # $150

        assert effective == expected_system_loss  # System is stricter

    def test_skip_blocked_tickers(self):
        """Blocked tickers in allocations are skipped."""
        config = _make_config()
        state = _make_state(
            config=config,
            allocations=[
                {"ticker": "XOM", "allocation_pct": 50},
                {"ticker": "NVDA", "allocation_pct": 50},
            ],
            ticker_results={
                "XOM": {"final_action": "BLOCKED", "recommended_position_size": 0.0, "price": 100.0},
                "NVDA": {"final_action": "BUY", "recommended_position_size": 0.10, "price": 200.0},
            },
        )

        trades = GoalArbiter.build_trade_plan(state)
        tickers_in_plan = [t.ticker for t in trades]
        assert "XOM" not in tickers_in_plan
        assert "NVDA" in tickers_in_plan

    def test_empty_allocations_returns_empty(self):
        """No allocations → empty trade plan."""
        config = _make_config()
        state = _make_state(config=config, allocations=[], ticker_results={})

        trades = GoalArbiter.build_trade_plan(state)
        assert trades == []

    def test_stop_loss_below_entry(self):
        """Stop-loss price is always below entry price for BUY trades."""
        config = _make_config(capital=10000.0, max_loss_pct=0.02)
        state = _make_state(
            config=config,
            allocations=[{"ticker": "NVDA", "allocation_pct": 50}],
            ticker_results={
                "NVDA": {"final_action": "BUY", "recommended_position_size": 0.10, "price": 200.0},
            },
        )

        trades = GoalArbiter.build_trade_plan(state)
        assert len(trades) == 1
        assert trades[0].stop_loss_price < trades[0].entry_price_est

    def test_target_exit_above_entry(self):
        """Target exit price is above entry for BUY trades."""
        config = _make_config(capital=10000.0)
        state = _make_state(
            config=config,
            allocations=[{"ticker": "NVDA", "allocation_pct": 50}],
            ticker_results={
                "NVDA": {"final_action": "BUY", "recommended_position_size": 0.10, "price": 200.0},
            },
        )

        trades = GoalArbiter.build_trade_plan(state)
        assert len(trades) == 1
        assert trades[0].target_exit_price > trades[0].entry_price_est

    def test_hold_action_skipped(self):
        """HOLD actions are skipped — no trade is created."""
        config = _make_config(capital=10000.0)
        state = _make_state(
            config=config,
            allocations=[{"ticker": "PYPL", "allocation_pct": 50}],
            ticker_results={
                "PYPL": {"final_action": "HOLD", "recommended_position_size": 0.05, "price": 68.90},
            },
        )

        trades = GoalArbiter.build_trade_plan(state)
        assert trades == [], "HOLD should not produce a trade"

    def test_unexpected_action_skipped(self):
        """Unknown/unexpected actions are skipped with a warning."""
        config = _make_config(capital=10000.0)
        state = _make_state(
            config=config,
            allocations=[{"ticker": "NVDA", "allocation_pct": 50}],
            ticker_results={
                "NVDA": {"final_action": "BANANA", "recommended_position_size": 0.10, "price": 200.0},
            },
        )

        trades = GoalArbiter.build_trade_plan(state)
        assert trades == [], "Unknown action should not produce a trade"

    def test_sell_action_preserved(self):
        """SELL actions produce a trade with action='SELL'."""
        config = _make_config(capital=10000.0)
        state = _make_state(
            config=config,
            allocations=[{"ticker": "NVDA", "allocation_pct": 50}],
            ticker_results={
                "NVDA": {"final_action": "SELL", "recommended_position_size": 0.10, "price": 200.0},
            },
        )

        trades = GoalArbiter.build_trade_plan(state)
        assert len(trades) == 1
        assert trades[0].action == "SELL"

    def test_config_required(self):
        """build_trade_plan raises if config is None."""
        state = GoalState()
        with pytest.raises(ValueError, match="config must be set"):
            GoalArbiter.build_trade_plan(state)


# ---------------------------------------------------------------------------
# Separation enforcement — same pattern as DecisionArbiter test
# ---------------------------------------------------------------------------


def test_goal_arbiter_does_not_import_risk_engine():
    """GoalArbiter must not import risk_engine or pre_trade_validation."""
    import importlib
    import src.pipeline.goal.goal_arbiter as module

    source = importlib.util.find_spec(module.__name__)
    assert source is not None and source.origin is not None

    with open(source.origin) as f:
        code = f.read()

    assert "from app.services.risk.risk_engine" not in code, "GoalArbiter must not import risk_engine"
    assert "from app.services.risk.pre_trade_validation" not in code, "GoalArbiter must not import pre_trade_validation"
    assert "import risk_engine" not in code
    assert "import pre_trade_validation" not in code
