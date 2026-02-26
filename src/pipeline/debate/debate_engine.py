"""Debate engine — orchestrates bull/bear rounds and agreement detection."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from backend.app.models.schemas import (
    DebateOutcome,
    DebateRound,
    DebateTranscript,
    JuryResult,
    TradeAction,
)
from src.intelligence.wasden_watch.config import WasdenWatchSettings

from .agreement_detector import AgreementDetector
from .bear_researcher import BearResearcher
from .bull_researcher import BullResearcher
from .debate_llm_client import DebateLLMClient

logger = logging.getLogger("debate_engine")

MAX_REBUTTAL_ROUNDS = 2


@dataclass
class DebateContext:
    """All data needed to run a bull/bear debate on a ticker."""

    ticker: str
    price: float
    quant_scores: dict
    wasden_verdict: str
    wasden_confidence: float
    wasden_reasoning: str
    fundamentals: dict | None = field(default=None)


class DebateEngine:
    """Orchestrates bull/bear debate rounds and agreement check.

    Flow:
        1. Round 1: initial bull (Claude) and bear (Gemini) arguments
        2. Rounds 2-N: rebuttals (configurable, default 2 rebuttal rounds)
        3. Agreement detection via LLM judge
        4. Returns DebateTranscript (caller handles jury if disagreement)
    """

    def __init__(
        self,
        settings: WasdenWatchSettings | None = None,
        max_rebuttal_rounds: int = MAX_REBUTTAL_ROUNDS,
    ):
        self._settings = settings or WasdenWatchSettings()
        self._client = DebateLLMClient(self._settings)
        self._bull = BullResearcher(self._client)
        self._bear = BearResearcher(self._client)
        self._agreement = AgreementDetector(self._client)
        self._max_rebuttal_rounds = max_rebuttal_rounds

    @property
    def client(self) -> DebateLLMClient:
        """Expose the LLM client for jury system to reuse."""
        return self._client

    def run_debate(self, context: DebateContext, pipeline_run_id: str) -> DebateTranscript:
        """Run a full bull/bear debate for a ticker.

        Args:
            context: Ticker data and scores for the debate.
            pipeline_run_id: UUID of the current pipeline run.

        Returns:
            DebateTranscript with all rounds and outcome.
        """
        logger.info(f"[{context.ticker}] Starting debate — max {1 + self._max_rebuttal_rounds} rounds")
        rounds: list[DebateRound] = []

        # Round 1: initial arguments
        bull_arg = self._bull.generate_initial(context)
        bear_arg = self._bear.generate_initial(context)
        round_1 = DebateRound(
            round_number=1,
            bull_argument=bull_arg,
            bear_argument=bear_arg,
        )
        rounds.append(round_1)
        logger.info(f"[{context.ticker}] Round 1 complete")

        # Rebuttal rounds
        for i in range(self._max_rebuttal_rounds):
            round_num = i + 2
            prev_round = rounds[-1]

            bull_rebuttal = self._bull.generate_rebuttal(context, prev_round)
            bear_rebuttal = self._bear.generate_rebuttal(context, prev_round)

            rebuttal_round = DebateRound(
                round_number=round_num,
                bull_argument=bull_rebuttal,
                bear_argument=bear_rebuttal,
            )
            rounds.append(rebuttal_round)
            logger.info(f"[{context.ticker}] Round {round_num} complete")

        # Agreement detection
        outcome, agreed_action = self._agreement.evaluate(context.ticker, rounds)
        jury_triggered = outcome == DebateOutcome.DISAGREEMENT

        transcript = DebateTranscript(
            pipeline_run_id=pipeline_run_id,
            ticker=context.ticker,
            timestamp=datetime.now(timezone.utc).isoformat(),
            rounds=rounds,
            outcome=outcome,
            bull_model=self._settings.claude_model,
            bear_model=self._settings.gemini_model,
            jury_triggered=jury_triggered,
        )

        logger.info(
            f"[{context.ticker}] Debate complete — outcome={outcome.value}, "
            f"jury_triggered={jury_triggered}"
        )
        return transcript

    @staticmethod
    def make_no_jury_result(agreed_action: str | None) -> JuryResult:
        """Create a JuryResult for when the debate reached agreement (no jury needed)."""
        action = TradeAction(agreed_action) if agreed_action else TradeAction.HOLD
        return JuryResult(
            spawned=False,
            reason="Debate reached agreement — jury not required",
            votes=[],
            final_count=None,
            decision=action,
            escalated_to_human=False,
        )
