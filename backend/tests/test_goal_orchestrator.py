"""Tests for GoalOrchestrator, MockGoalOrchestrator, and PortfolioDebate."""

import os

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

from src.pipeline.goal.goal_state import GoalConfig, GoalState  # noqa: E402
from src.pipeline.goal.goal_orchestrator import (  # noqa: E402
    GoalOrchestrator,
    build_goal_context_string,
)
from src.pipeline.goal.mock_goal_orchestrator import (  # noqa: E402
    MOCK_SCREENING_CANDIDATES,
    MOCK_TICKER_RESULTS,
    MockGoalOrchestrator,
)
from src.pipeline.goal.portfolio_debate import (  # noqa: E402
    PortfolioDebateEngine,
    PortfolioDebateResult,
)
from src.pipeline.goal.portfolio_debate_prompts import format_candidates_section  # noqa: E402


def _default_config(**overrides) -> GoalConfig:
    defaults = dict(capital=10000.0, target_return_pct=0.02, timeframe_days=5, max_loss_pct=0.01)
    defaults.update(overrides)
    return GoalConfig.create(**defaults)


# ---------------------------------------------------------------------------
# MockGoalOrchestrator
# ---------------------------------------------------------------------------


class TestMockGoalOrchestrator:

    def test_returns_active_state(self):
        """Mock orchestrator returns a GoalState with status=active."""
        config = _default_config()
        state = MockGoalOrchestrator().run(config)

        assert state.status == "active"
        assert state.goal_id == config.goal_id
        assert state.config == config

    def test_has_candidates(self):
        """Mock produces screening candidates."""
        config = _default_config()
        state = MockGoalOrchestrator().run(config)

        assert len(state.candidates) == len(MOCK_SCREENING_CANDIDATES)
        assert "NVDA" in state.candidates

    def test_has_ticker_results(self):
        """Mock produces per-ticker pipeline results."""
        config = _default_config()
        state = MockGoalOrchestrator().run(config)

        assert len(state.ticker_results) > 0
        for ticker in state.candidates:
            if ticker in MOCK_TICKER_RESULTS:
                assert ticker in state.ticker_results

    def test_has_portfolio_debate(self):
        """Mock produces portfolio debate output."""
        config = _default_config()
        state = MockGoalOrchestrator().run(config)

        assert state.portfolio_debate_outcome == "agreement"
        assert len(state.portfolio_allocations) > 0

    def test_has_trade_plan(self):
        """Mock produces a non-empty trade plan."""
        config = _default_config()
        state = MockGoalOrchestrator().run(config)

        assert len(state.trade_plan) > 0
        for trade in state.trade_plan:
            assert trade.shares > 0
            assert trade.entry_price_est > 0
            assert trade.stop_loss_price < trade.entry_price_est

    def test_remaining_capital_tracked(self):
        """Remaining capital = initial - sum of trade allocations."""
        config = _default_config()
        state = MockGoalOrchestrator().run(config)

        allocated = sum(t.position_dollar for t in state.trade_plan)
        expected_remaining = config.capital - allocated
        assert abs(state.remaining_capital - expected_remaining) < 0.01

    def test_deterministic(self):
        """Same config produces identical results."""
        config = _default_config()
        state1 = MockGoalOrchestrator().run(config)
        state2 = MockGoalOrchestrator().run(config)

        assert len(state1.trade_plan) == len(state2.trade_plan)
        for t1, t2 in zip(state1.trade_plan, state2.trade_plan):
            assert t1.ticker == t2.ticker
            assert t1.shares == t2.shares
            assert t1.position_dollar == t2.position_dollar

    def test_trade_plan_respects_capital(self):
        """Total allocated never exceeds capital."""
        config = _default_config(capital=500.0)
        state = MockGoalOrchestrator().run(config)

        total = sum(t.position_dollar for t in state.trade_plan)
        assert total <= config.capital + 0.01


# ---------------------------------------------------------------------------
# GoalOrchestrator (mock mode via use_mock=True)
# ---------------------------------------------------------------------------


class TestGoalOrchestrator:

    def test_mock_mode_delegates_to_mock(self):
        """GoalOrchestrator(use_mock=True) uses MockGoalOrchestrator."""
        config = _default_config()
        state = GoalOrchestrator(use_mock=True).run(config)

        assert state.status == "active"
        assert len(state.trade_plan) > 0

    def test_goal_context_string_format(self):
        """build_goal_context_string produces readable context."""
        config = _default_config(capital=1000, target_return_pct=0.02, timeframe_days=5, max_loss_pct=0.01)
        ctx = build_goal_context_string(config, ["NVDA", "MSFT", "AMD"])

        assert "$1,000.00" in ctx
        assert "2.0%" in ctx
        assert "5 trading days" in ctx
        assert "1.0%" in ctx
        assert "NVDA" in ctx
        assert "MSFT" in ctx

    def test_goal_context_string_with_empty_candidates(self):
        config = _default_config()
        ctx = build_goal_context_string(config, [])
        assert "Available capital" in ctx


# ---------------------------------------------------------------------------
# PortfolioDebateEngine (no LLM client = mock mode)
# ---------------------------------------------------------------------------


class TestPortfolioDebate:

    def test_no_client_returns_empty_allocations(self):
        """Without LLM client, debate returns empty allocations."""
        config = _default_config()
        engine = PortfolioDebateEngine(llm_client=None)
        result = engine.run_portfolio_debate(config, MOCK_TICKER_RESULTS)

        assert isinstance(result, PortfolioDebateResult)
        assert result.outcome == "disagreement"  # No LLM → can't agree
        assert result.allocations == []

    def test_format_candidates_section(self):
        """format_candidates_section produces readable output."""
        section = format_candidates_section(MOCK_TICKER_RESULTS)
        assert "NVDA" in section
        assert "BUY" in section
        assert "189.82" in section

    def test_format_candidates_section_empty(self):
        assert "No candidates" in format_candidates_section({})


# ---------------------------------------------------------------------------
# GoalState.viable_tickers integration
# ---------------------------------------------------------------------------


class TestViableTickersIntegration:

    def test_mock_results_all_viable(self):
        """All mock ticker results (except PYPL=HOLD) should be viable."""
        state = GoalState(ticker_results=dict(MOCK_TICKER_RESULTS))
        viable = state.viable_tickers()
        # All should be viable since none are BLOCKED or ESCALATED
        assert len(viable) == len(MOCK_TICKER_RESULTS)

    def test_veto_excluded(self):
        """Tickers with BLOCKED action are excluded."""
        results = dict(MOCK_TICKER_RESULTS)
        results["XOM"] = {"final_action": "BLOCKED", "recommended_position_size": 0.0}
        state = GoalState(ticker_results=results)
        viable = state.viable_tickers()
        assert "XOM" not in viable


# ---------------------------------------------------------------------------
# Standalone pipeline regression
# ---------------------------------------------------------------------------


def test_standalone_pipeline_still_works():
    """Existing per-ticker pipeline works without goal context (regression)."""
    from src.pipeline.decision_pipeline import DecisionPipeline

    pipeline = DecisionPipeline(use_mock=True)
    result = pipeline.run("NVDA", price=189.82)

    assert result["final_decision"]["action"] in ("BUY", "HOLD", "SELL")
    assert "pipeline_run_id" in result
