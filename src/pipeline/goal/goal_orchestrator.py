"""Goal Orchestrator — task-based trading with a defined financial target.

Sits ON TOP of the existing per-ticker pipeline. Does not replace it.

Flow:
    1. Source candidates from 5-tier screening funnel
    2. Run existing 10-node pipeline per candidate (with goal context)
    3. Stage 2 portfolio debate (which combination of trades hits the goal?)
    4. GoalArbiter sizes positions across trades
    5. Returns GoalState with trade plan
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.pipeline.decision_pipeline import DecisionPipeline

from .goal_arbiter import GoalArbiter
from .goal_state import GOAL_STATUS_ACTIVE, GOAL_STATUS_PLANNING, GoalConfig, GoalState
from .mock_goal_orchestrator import MockGoalOrchestrator
from .portfolio_debate import PortfolioDebateEngine

logger = logging.getLogger("wasden_watch.pipeline.goal")


def build_goal_context_string(config: GoalConfig, candidates: list[str]) -> str:
    """Build the goal context string injected into per-ticker debate prompts."""
    other_tickers = ", ".join(candidates)
    return (
        f"- Available capital: ${config.capital:,.2f}\n"
        f"- Target: +{config.target_return_pct:.1%} "
        f"(${config.target_dollar:,.2f}) over {config.timeframe_days} trading days\n"
        f"- Max acceptable loss: -{config.max_loss_pct:.1%} "
        f"(${config.max_loss_dollar:,.2f})\n"
        f"- Other candidates under review: {other_tickers}\n"
        f"- Evaluate whether this ticker merits allocation toward this goal."
    )


class GoalOrchestrator:
    """Orchestrates goal-based trading across multiple tickers.

    Args:
        use_mock: If True, uses MockGoalOrchestrator (deterministic, no LLMs).
    """

    def __init__(self, use_mock: bool = True):
        self._use_mock = use_mock

    def run(self, config: GoalConfig) -> GoalState:
        """Run the full goal orchestration pipeline.

        Args:
            config: The financial goal (capital, target, timeframe, max loss).

        Returns:
            GoalState with candidates, pipeline results, debate, and trade plan.
        """
        if self._use_mock:
            return MockGoalOrchestrator().run(config)

        state = GoalState(
            goal_id=config.goal_id,
            config=config,
            status=GOAL_STATUS_PLANNING,
        )

        # Step 1: Source candidates from screening
        state.candidates = self._source_candidates()
        if not state.candidates:
            state.status = "failed"
            state.errors.append({
                "stage": "screening",
                "error": "No candidates from screening funnel",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            logger.warning("[GoalOrchestrator] No candidates — aborting")
            return state

        logger.info(f"[GoalOrchestrator] {len(state.candidates)} candidates from screening")

        # Step 2: Run per-ticker pipeline with goal context
        goal_context = build_goal_context_string(config, state.candidates)
        pipeline = DecisionPipeline(use_mock=False)

        for ticker in state.candidates:
            try:
                result = pipeline.run(ticker, price=0.0, fundamentals={"goal_context": goal_context})
                state.ticker_results[ticker] = result
                logger.info(f"[GoalOrchestrator] {ticker} → {result.get('final_decision', {}).get('action', 'N/A')}")
            except Exception as exc:
                logger.error(f"[GoalOrchestrator] {ticker} pipeline failed: {exc}")
                state.errors.append({
                    "stage": "per_ticker_pipeline",
                    "ticker": ticker,
                    "error": str(exc),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        # Check for viable tickers
        viable = state.viable_tickers()
        if not viable:
            state.status = "failed"
            state.errors.append({
                "stage": "viable_check",
                "error": "All candidates were BLOCKED or ESCALATED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            logger.warning("[GoalOrchestrator] No viable tickers — aborting")
            return state

        # Step 3: Stage 2 portfolio debate (viable tickers only)
        viable_results = {t: state.ticker_results[t] for t in viable if t in state.ticker_results}
        debate_engine = PortfolioDebateEngine()
        debate_result = debate_engine.run_portfolio_debate(config, viable_results)

        state.portfolio_bull_case = debate_result.bull_argument
        state.portfolio_bear_case = debate_result.bear_argument
        state.portfolio_debate_outcome = debate_result.outcome
        state.portfolio_allocations = debate_result.allocations

        # Step 4: Goal arbiter — build trade plan
        state.trade_plan = GoalArbiter.build_trade_plan(state)

        # Step 5: Finalize state
        state.remaining_capital = config.capital - sum(t.position_dollar for t in state.trade_plan)
        state.remaining_target_pct = config.target_return_pct
        state.status = GOAL_STATUS_ACTIVE if state.trade_plan else "failed"

        logger.info(
            f"[GoalOrchestrator] Complete — {len(state.trade_plan)} trades, "
            f"status={state.status}"
        )
        return state

    @staticmethod
    def _source_candidates() -> list[str]:
        """Pull candidates from the screening funnel.

        Returns:
            List of ticker symbols (without ' US Equity' suffix).
        """
        try:
            from app.mock.generators import generate_screening_runs

            runs = generate_screening_runs()
            if runs:
                raw = runs[0].get("final_candidates", [])
                # Strip " US Equity" suffix
                return [t.replace(" US Equity", "") for t in raw]
        except ImportError:
            logger.warning("[GoalOrchestrator] Could not import screening — using empty list")

        return []
