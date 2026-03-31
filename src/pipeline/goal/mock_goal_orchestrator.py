"""Mock Goal Orchestrator — deterministic results without LLM calls."""

from __future__ import annotations

import logging

from .goal_arbiter import GoalArbiter
from .goal_state import (
    GOAL_STATUS_ACTIVE,
    GOAL_STATUS_PLANNING,
    GoalConfig,
    GoalState,
)

logger = logging.getLogger("wasden_watch.pipeline.goal.mock")

# Deterministic mock screening output (subset of pilot tickers)
MOCK_SCREENING_CANDIDATES = ["NVDA", "MSFT", "AMZN", "AMD", "PYPL"]

# Deterministic mock pipeline results (per-ticker)
MOCK_TICKER_RESULTS: dict[str, dict] = {
    "NVDA": {
        "final_action": "BUY",
        "recommended_position_size": 0.10,
        "price": 189.82,
        "quant_scores": {"composite": 0.72, "std_dev": 0.15, "high_disagreement_flag": False},
        "wasden_verdict": {"verdict": "APPROVE", "confidence": 0.85},
    },
    "MSFT": {
        "final_action": "BUY",
        "recommended_position_size": 0.09,
        "price": 420.50,
        "quant_scores": {"composite": 0.68, "std_dev": 0.12, "high_disagreement_flag": False},
        "wasden_verdict": {"verdict": "APPROVE", "confidence": 0.82},
    },
    "AMZN": {
        "final_action": "BUY",
        "recommended_position_size": 0.08,
        "price": 185.30,
        "quant_scores": {"composite": 0.65, "std_dev": 0.18, "high_disagreement_flag": False},
        "wasden_verdict": {"verdict": "APPROVE", "confidence": 0.75},
    },
    "AMD": {
        "final_action": "BUY",
        "recommended_position_size": 0.07,
        "price": 162.40,
        "quant_scores": {"composite": 0.70, "std_dev": 0.22, "high_disagreement_flag": False},
        "wasden_verdict": {"verdict": "APPROVE", "confidence": 0.77},
    },
    "PYPL": {
        "final_action": "HOLD",
        "recommended_position_size": 0.05,
        "price": 68.90,
        "quant_scores": {"composite": 0.58, "std_dev": 0.25, "high_disagreement_flag": False},
        "wasden_verdict": {"verdict": "APPROVE", "confidence": 0.72},
    },
}

# Deterministic mock portfolio debate allocations
MOCK_PORTFOLIO_ALLOCATIONS = [
    {"ticker": "NVDA", "allocation_pct": 35, "rationale": "Strongest quant composite + Wasden confidence"},
    {"ticker": "MSFT", "allocation_pct": 30, "rationale": "Solid fundamentals, low model disagreement"},
    {"ticker": "AMZN", "allocation_pct": 20, "rationale": "Diversified tech exposure, strong AWS growth"},
    {"ticker": "AMD", "allocation_pct": 15, "rationale": "AI chip demand, moderate position to manage volatility"},
]


class MockGoalOrchestrator:
    """Deterministic goal orchestrator for testing — no LLM or screening calls."""

    def run(self, config: GoalConfig) -> GoalState:
        """Run mock goal orchestration.

        Args:
            config: The financial goal configuration.

        Returns:
            GoalState with deterministic results.
        """
        state = GoalState(
            goal_id=config.goal_id,
            config=config,
            status=GOAL_STATUS_PLANNING,
        )

        # Step 1: Mock screening
        state.candidates = list(MOCK_SCREENING_CANDIDATES)
        logger.info(f"[MockGoal] Candidates: {state.candidates}")

        # Step 2: Mock per-ticker pipeline results
        state.ticker_results = {
            ticker: dict(MOCK_TICKER_RESULTS[ticker])
            for ticker in state.candidates
            if ticker in MOCK_TICKER_RESULTS
        }

        # Step 3: Mock portfolio debate
        state.portfolio_bull_case = "[Mock] Aggressive allocation — NVDA 35%, MSFT 30%, AMZN 20%, AMD 15%"
        state.portfolio_bear_case = "[Mock] Conservative allocation — diversified across 4 positions"
        state.portfolio_debate_outcome = "agreement"
        state.portfolio_allocations = list(MOCK_PORTFOLIO_ALLOCATIONS)

        # Step 4: Goal arbiter — real logic, mock data
        state.trade_plan = GoalArbiter.build_trade_plan(state)

        # Step 5: Set remaining state
        state.remaining_capital = config.capital - sum(t.position_dollar for t in state.trade_plan)
        state.remaining_target_pct = config.target_return_pct
        state.status = GOAL_STATUS_ACTIVE

        logger.info(
            f"[MockGoal] Complete — {len(state.trade_plan)} trades planned, "
            f"${state.remaining_capital:.2f} remaining"
        )
        return state
