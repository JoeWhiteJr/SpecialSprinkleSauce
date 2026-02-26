"""Jury spawner — runs 10 agents in parallel via asyncio.gather."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from backend.app.models.schemas import JuryVote, JuryVoteChoice
from .jury_prompts import JURY_AGENTS, JURY_USER_PROMPT, JURY_VOTE_FORMAT

if TYPE_CHECKING:
    from src.pipeline.debate.debate_engine import DebateContext
    from src.pipeline.debate.debate_llm_client import DebateLLMClient
    from backend.app.models.schemas import DebateTranscript

logger = logging.getLogger("debate_engine")


class JurySpawner:
    """Spawns 10 jury agents in parallel to vote on a ticker."""

    def __init__(self, client: DebateLLMClient):
        self._client = client

    async def spawn_jury(
        self,
        ticker: str,
        transcript: DebateTranscript,
        context: DebateContext,
    ) -> list[JuryVote]:
        """Run all 10 jury agents in parallel and collect votes.

        Failed agents get one retry, then cast a HOLD vote with error reasoning.
        """
        transcript_text = _format_transcript(transcript)
        user_prompt = JURY_USER_PROMPT.format(
            ticker=context.ticker,
            price=context.price,
            transcript_text=transcript_text,
            quant_composite=context.quant_scores.get("composite", 0.0),
            quant_scores_section=_format_quant_scores(context.quant_scores),
            wasden_verdict=context.wasden_verdict,
            wasden_confidence=context.wasden_confidence,
            fundamentals_section=_format_fundamentals(context.fundamentals),
            vote_format=JURY_VOTE_FORMAT,
        )

        tasks = [
            self._run_agent(agent, user_prompt)
            for agent in JURY_AGENTS
        ]

        votes = await asyncio.gather(*tasks)
        logger.info(f"[{ticker}] Jury complete — {len(votes)} votes collected")
        return list(votes)

    async def _run_agent(self, agent: dict, user_prompt: str) -> JuryVote:
        """Run a single jury agent with one retry on failure."""
        agent_id = agent["agent_id"]
        system_prompt = agent["system_prompt"]
        focus_area = agent["focus_area"]

        for attempt in range(2):
            try:
                result = await asyncio.to_thread(
                    self._client.call_judge, system_prompt, user_prompt
                )
                vote_str = result.get("vote", "HOLD").upper()
                reasoning = result.get("reasoning", "No reasoning provided")

                # Validate vote choice
                try:
                    vote_choice = JuryVoteChoice(vote_str)
                except ValueError:
                    vote_choice = JuryVoteChoice.HOLD
                    reasoning = f"Invalid vote '{vote_str}' defaulted to HOLD. Original: {reasoning}"

                return JuryVote(
                    agent_id=agent_id,
                    vote=vote_choice,
                    reasoning=reasoning,
                    focus_area=focus_area,
                )
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"Jury agent {agent_id} failed (attempt 1): {e}, retrying")
                    continue
                logger.error(f"Jury agent {agent_id} failed (attempt 2): {e}, defaulting to HOLD")
                return JuryVote(
                    agent_id=agent_id,
                    vote=JuryVoteChoice.HOLD,
                    reasoning=f"Agent failed after 2 attempts: {e}",
                    focus_area=focus_area,
                )

        # Unreachable but satisfies type checker
        return JuryVote(
            agent_id=agent_id,
            vote=JuryVoteChoice.HOLD,
            reasoning="Unexpected fallthrough",
            focus_area=focus_area,
        )


def _format_transcript(transcript: DebateTranscript) -> str:
    """Format debate transcript into readable text for jury agents."""
    lines = []
    for r in transcript.rounds:
        lines.append(f"### Round {r.round_number}")
        lines.append(f"**Bull ({transcript.bull_model}):** {r.bull_argument}")
        lines.append(f"**Bear ({transcript.bear_model}):** {r.bear_argument}")
        lines.append("")
    return "\n".join(lines)


def _format_quant_scores(scores: dict) -> str:
    """Format quant scores dict into bullet points."""
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
    """Format optional fundamentals dict."""
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
