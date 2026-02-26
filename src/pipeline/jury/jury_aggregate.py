"""Jury aggregator — counts votes and determines final decision."""

import logging
from collections import Counter

from backend.app.models.schemas import (
    JuryResult,
    JuryVote,
    JuryVoteChoice,
    TradeAction,
)

logger = logging.getLogger("debate_engine")

DECISIVE_THRESHOLD = 6


class JuryAggregator:
    """Aggregates 10 jury votes into a final trading decision.

    Rules:
        - 6+ votes for one action → decisive BUY/SELL/HOLD
        - 5-5 tie (any two-way split) → ESCALATED to human
        - Other split (no 6+ majority) → HOLD (no conviction)
    """

    @staticmethod
    def aggregate(votes: list[JuryVote]) -> JuryResult:
        """Aggregate jury votes into a final decision.

        Args:
            votes: Exactly 10 JuryVote objects.

        Returns:
            JuryResult with vote counts and decision.
        """
        if len(votes) != 10:
            logger.warning(f"Expected 10 jury votes, got {len(votes)}")

        # Count votes
        counts = Counter(v.vote for v in votes)
        buy_count = counts.get(JuryVoteChoice.BUY, 0)
        sell_count = counts.get(JuryVoteChoice.SELL, 0)
        hold_count = counts.get(JuryVoteChoice.HOLD, 0)

        final_count = {
            "buy": buy_count,
            "sell": sell_count,
            "hold": hold_count,
        }

        # Determine decision
        sorted_counts = counts.most_common()

        # Check for 5-5 tie (any two-way exact split)
        if (
            len(sorted_counts) >= 2
            and sorted_counts[0][1] == 5
            and sorted_counts[1][1] == 5
        ):
            logger.info(
                f"Jury 5-5 tie: {sorted_counts[0][0].value} vs {sorted_counts[1][0].value} — escalating"
            )
            return JuryResult(
                spawned=True,
                reason="5-5 jury tie — escalated to human decision",
                votes=votes,
                final_count=final_count,
                decision=TradeAction.ESCALATED,
                escalated_to_human=True,
            )

        # Check for decisive majority (6+)
        if sorted_counts and sorted_counts[0][1] >= DECISIVE_THRESHOLD:
            winning_vote = sorted_counts[0][0]
            action = TradeAction(winning_vote.value)
            logger.info(
                f"Jury decisive: {action.value} with {sorted_counts[0][1]}/10 votes"
            )
            return JuryResult(
                spawned=True,
                reason=f"Decisive {sorted_counts[0][1]}-vote majority for {action.value}",
                votes=votes,
                final_count=final_count,
                decision=action,
                escalated_to_human=False,
            )

        # No clear majority — default to HOLD
        logger.info(f"Jury split with no majority: {dict(counts)} — defaulting to HOLD")
        return JuryResult(
            spawned=True,
            reason=f"No decisive majority (buy={buy_count}, sell={sell_count}, hold={hold_count}) — defaulting to HOLD",
            votes=votes,
            final_count=final_count,
            decision=TradeAction.HOLD,
            escalated_to_human=False,
        )
