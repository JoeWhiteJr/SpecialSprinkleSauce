"""Bear case researcher — generates initial arguments and rebuttals via Gemini."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .prompts import (
    BEAR_INITIAL_PROMPT,
    BEAR_REBUTTAL_SYSTEM_PROMPT,
    BEAR_SYSTEM_PROMPT,
    REBUTTAL_PROMPT,
)

if TYPE_CHECKING:
    from backend.app.models.schemas import DebateRound
    from .debate_engine import DebateContext
    from .debate_llm_client import DebateLLMClient

logger = logging.getLogger("debate_engine")


class BearResearcher:
    """Generates bear-case arguments using Gemini (no Claude fallback)."""

    def __init__(self, client: DebateLLMClient):
        self._client = client

    def generate_initial(self, context: DebateContext) -> str:
        """Generate the opening bear argument for a ticker."""
        user_prompt = BEAR_INITIAL_PROMPT.format(
            ticker=context.ticker,
            price=context.price,
            quant_composite=context.quant_scores.get("composite", 0.0),
            wasden_verdict=context.wasden_verdict,
            wasden_confidence=context.wasden_confidence,
            wasden_reasoning=context.wasden_reasoning,
            quant_scores_section=_format_quant_scores(context.quant_scores),
            fundamentals_section=_format_fundamentals(context.fundamentals),
        )
        return self._client.call_bear(BEAR_SYSTEM_PROMPT, user_prompt)

    def generate_rebuttal(self, context: DebateContext, prev_round: DebateRound) -> str:
        """Generate a rebuttal to the bull's previous argument."""
        user_prompt = REBUTTAL_PROMPT.format(
            current_round=prev_round.round_number + 1,
            prev_bull_argument=prev_round.bull_argument,
            prev_bear_argument=prev_round.bear_argument,
        )
        return self._client.call_bear(BEAR_REBUTTAL_SYSTEM_PROMPT, user_prompt)


def _format_quant_scores(scores: dict) -> str:
    """Format quant scores dict into readable bullet points."""
    if not scores:
        return "- No quant scores available"
    lines = []
    for key, value in scores.items():
        if key == "composite":
            continue
        if isinstance(value, bool):
            lines.append(f"- {key}: {'Yes' if value else 'No'}")
        elif isinstance(value, float):
            lines.append(f"- {key}: {value:.3f}")
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) if lines else "- No additional scores"


def _format_fundamentals(fundamentals: dict | None) -> str:
    """Format optional fundamentals dict into a section."""
    if not fundamentals:
        return ""
    lines = ["## Fundamentals"]
    for key, value in fundamentals.items():
        if isinstance(value, float):
            lines.append(f"- {key}: {value:.2f}")
        else:
            lines.append(f"- {key}: {value}")
    lines.append("")
    return "\n".join(lines)
