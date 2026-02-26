"""Agreement detector — evaluates whether bull/bear debate has converged."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend.app.models.schemas import DebateOutcome
from .prompts import AGREEMENT_SYSTEM_PROMPT, AGREEMENT_USER_PROMPT

if TYPE_CHECKING:
    from backend.app.models.schemas import DebateRound
    from .debate_llm_client import DebateLLMClient

logger = logging.getLogger("debate_engine")


class AgreementDetector:
    """Uses an LLM judge to determine if bull and bear sides agree."""

    def __init__(self, client: DebateLLMClient):
        self._client = client

    def evaluate(
        self, ticker: str, rounds: list[DebateRound]
    ) -> tuple[DebateOutcome, str | None]:
        """Evaluate whether the debate has reached agreement.

        Returns:
            (DebateOutcome.AGREEMENT, "BUY"/"SELL"/"HOLD") if agreed,
            (DebateOutcome.DISAGREEMENT, None) if they disagree.
        """
        final_round = rounds[-1]

        user_prompt = AGREEMENT_USER_PROMPT.format(
            ticker=ticker,
            final_bull_argument=final_round.bull_argument,
            final_bear_argument=final_round.bear_argument,
        )

        result = self._client.call_judge(AGREEMENT_SYSTEM_PROMPT, user_prompt)

        outcome_str = result.get("outcome", "disagreement").lower()
        agreed_action = result.get("agreed_action")

        if outcome_str == "agreement" and agreed_action:
            logger.info(f"[{ticker}] Debate reached agreement: {agreed_action}")
            return DebateOutcome.AGREEMENT, agreed_action.upper()

        logger.info(f"[{ticker}] Debate ended in disagreement — jury required")
        return DebateOutcome.DISAGREEMENT, None
