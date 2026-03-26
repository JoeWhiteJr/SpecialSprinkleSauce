"""Stage 2 portfolio-level debate — argues over which combination of trades hits the goal."""

from __future__ import annotations

import json
import logging

from .goal_state import GoalConfig
from .portfolio_debate_prompts import (
    PORTFOLIO_AGREEMENT_SYSTEM_PROMPT,
    PORTFOLIO_AGREEMENT_USER_PROMPT,
    PORTFOLIO_BEAR_SYSTEM_PROMPT,
    PORTFOLIO_BULL_SYSTEM_PROMPT,
    PORTFOLIO_INITIAL_PROMPT,
    PORTFOLIO_REBUTTAL_PROMPT,
    PORTFOLIO_REBUTTAL_SYSTEM_PROMPT,
    format_candidates_section,
)

logger = logging.getLogger("wasden_watch.pipeline.goal.portfolio_debate")

MAX_REBUTTAL_ROUNDS = 1  # Shorter than per-ticker debates


class PortfolioDebateResult:
    """Result of the Stage 2 portfolio debate."""

    def __init__(
        self,
        bull_argument: str,
        bear_argument: str,
        outcome: str,
        allocations: list[dict],
        reasoning: str,
    ):
        self.bull_argument = bull_argument
        self.bear_argument = bear_argument
        self.outcome = outcome
        self.allocations = allocations
        self.reasoning = reasoning


class PortfolioDebateEngine:
    """Runs Stage 2 debate over portfolio allocation to hit the goal.

    Bull argues for the most effective allocation.
    Bear argues for the safest allocation.
    Agreement detector picks consensus allocation.
    """

    def __init__(self, llm_client=None, max_rebuttal_rounds: int = MAX_REBUTTAL_ROUNDS):
        self._client = llm_client
        self._max_rebuttal_rounds = max_rebuttal_rounds

    def run_portfolio_debate(
        self,
        goal_config: GoalConfig,
        ticker_results: dict[str, dict],
    ) -> PortfolioDebateResult:
        """Run bull/bear debate on portfolio composition.

        Args:
            goal_config: The financial goal (capital, target, timeframe, loss limit).
            ticker_results: Per-ticker pipeline results (only viable tickers).

        Returns:
            PortfolioDebateResult with consensus allocations.
        """
        candidates_section = format_candidates_section(ticker_results)

        user_prompt = PORTFOLIO_INITIAL_PROMPT.format(
            capital=goal_config.capital,
            target_pct=goal_config.target_return_pct,
            target_dollar=goal_config.target_dollar,
            timeframe_days=goal_config.timeframe_days,
            max_loss_pct=goal_config.max_loss_pct,
            max_loss_dollar=goal_config.max_loss_dollar,
            daily_target_pct=goal_config.daily_target_pct,
            candidates_section=candidates_section,
        )

        # Round 1: initial arguments
        if self._client:
            bull_arg = self._client.call_bull(PORTFOLIO_BULL_SYSTEM_PROMPT, user_prompt)
            bear_arg = self._client.call_bear(PORTFOLIO_BEAR_SYSTEM_PROMPT, user_prompt)
        else:
            bull_arg = "[Mock bull portfolio argument]"
            bear_arg = "[Mock bear portfolio argument]"

        logger.info("Portfolio debate Round 1 complete")

        # Rebuttal round
        for i in range(self._max_rebuttal_rounds):
            rebuttal_prompt = PORTFOLIO_REBUTTAL_PROMPT.format(
                prev_bull_argument=bull_arg,
                prev_bear_argument=bear_arg,
            )
            if self._client:
                bull_arg = self._client.call_bull(PORTFOLIO_REBUTTAL_SYSTEM_PROMPT, rebuttal_prompt)
                bear_arg = self._client.call_bear(PORTFOLIO_REBUTTAL_SYSTEM_PROMPT, rebuttal_prompt)
            logger.info(f"Portfolio debate Round {i + 2} complete")

        # Agreement detection
        allocations, reasoning = self._detect_agreement(goal_config, bull_arg, bear_arg)

        outcome = "agreement" if allocations else "disagreement"

        logger.info(
            f"Portfolio debate complete — outcome={outcome}, "
            f"{len(allocations)} allocations"
        )

        return PortfolioDebateResult(
            bull_argument=bull_arg,
            bear_argument=bear_arg,
            outcome=outcome,
            allocations=allocations,
            reasoning=reasoning,
        )

    def _detect_agreement(
        self,
        goal_config: GoalConfig,
        bull_arg: str,
        bear_arg: str,
    ) -> tuple[list[dict], str]:
        """Evaluate final arguments and extract consensus allocation."""
        if self._client:
            user_prompt = PORTFOLIO_AGREEMENT_USER_PROMPT.format(
                capital=goal_config.capital,
                target_pct=goal_config.target_return_pct,
                timeframe_days=goal_config.timeframe_days,
                max_loss_pct=goal_config.max_loss_pct,
                final_bull_argument=bull_arg,
                final_bear_argument=bear_arg,
            )
            raw = self._client.call_judge(PORTFOLIO_AGREEMENT_SYSTEM_PROMPT, user_prompt)
            return _parse_allocations(raw)

        # Mock mode — no LLM client
        return [], "Mock mode — no consensus"


def _parse_allocations(raw_response: str) -> tuple[list[dict], str]:
    """Parse LLM JSON response into allocations list."""
    try:
        data = json.loads(raw_response)
        allocations = data.get("allocations", [])
        reasoning = data.get("reasoning", "")
        return allocations, reasoning
    except (json.JSONDecodeError, AttributeError):
        logger.warning("Failed to parse portfolio debate agreement response")
        return [], "Failed to parse LLM response"
