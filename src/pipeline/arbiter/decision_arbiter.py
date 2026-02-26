"""Decision Arbiter — combines all pipeline signals into a final trading decision.

CRITICAL: This module reads pre-computed results from TradingState.
It does NOT import risk_engine.py or pre_trade_validation.py directly.
Separation is enforced by test.
"""

import logging

from app.services.risk.constants import MAX_POSITION_PCT

from src.pipeline.state import TradingState

logger = logging.getLogger("wasden_watch.pipeline.arbiter")


class DecisionArbiter:
    """Combines all pipeline signals into a final trading decision.

    Rules (in priority order):
        1. wasden_vetoed → BLOCKED, position_size=0
        2. jury_escalated → ESCALATED, human_approval_required=True
        3. risk_passed == False → BLOCKED
        4. pre_trade_passed == False → BLOCKED
        5. high_disagreement_flag → reduce position by 50%
        6. Otherwise: map jury/debate decision to BUY/SELL/HOLD

    Position sizing:
        base_size * wasden_confidence * (1 - quant_std_dev)
        Capped at MAX_POSITION_PCT (0.12)
    """

    @staticmethod
    def decide(state: TradingState) -> TradingState:
        """Apply decision rules to the pipeline state.

        Args:
            state: TradingState with all prior node results populated.

        Returns:
            Updated TradingState with final_action, final_reason,
            recommended_position_size, and human_approval_required set.
        """
        # Rule 1: Wasden veto → BLOCKED
        if state.wasden_vetoed:
            state.final_action = "BLOCKED"
            state.final_reason = (
                f"Wasden Watch VETO — {state.wasden_reasoning[:200]}"
            )
            state.recommended_position_size = 0.0
            state.human_approval_required = False
            logger.info(f"[{state.ticker}] BLOCKED by Wasden VETO")
            return state

        # Rule 2: Jury escalation (5-5 tie) → ESCALATED
        if state.jury_escalated:
            state.final_action = "ESCALATED"
            state.final_reason = "5-5 jury tie — escalated to human decision"
            state.recommended_position_size = 0.0
            state.human_approval_required = True
            logger.info(f"[{state.ticker}] ESCALATED — 5-5 jury tie")
            return state

        # Rule 3: Risk check failed → BLOCKED
        if not state.risk_passed:
            failed = state.risk_check.get("checks_failed", [])
            state.final_action = "BLOCKED"
            state.final_reason = f"Risk check failed: {', '.join(failed)}"
            state.recommended_position_size = 0.0
            state.human_approval_required = False
            logger.info(f"[{state.ticker}] BLOCKED by risk check: {failed}")
            return state

        # Rule 4: Pre-trade validation failed → BLOCKED
        if not state.pre_trade_passed:
            failed = state.pre_trade_validation.get("checks_failed", [])
            state.final_action = "BLOCKED"
            state.final_reason = f"Pre-trade validation failed: {', '.join(failed)}"
            state.recommended_position_size = 0.0
            state.human_approval_required = False
            logger.info(f"[{state.ticker}] BLOCKED by pre-trade validation: {failed}")
            return state

        # Determine action from jury/debate result
        action = _resolve_action(state)
        state.final_action = action

        # Calculate position size
        base_size = MAX_POSITION_PCT
        confidence_adj = max(0.0, min(1.0, state.wasden_confidence))
        disagreement_adj = max(0.0, 1.0 - state.quant_std_dev)
        position_size = base_size * confidence_adj * disagreement_adj

        # Rule 5: High disagreement → reduce by 50%
        if state.high_disagreement_flag:
            position_size *= 0.5
            logger.info(
                f"[{state.ticker}] High model disagreement — position reduced 50%"
            )

        # Cap at MAX_POSITION_PCT
        position_size = min(position_size, MAX_POSITION_PCT)
        state.recommended_position_size = round(position_size, 4)

        # Build reason
        state.final_reason = _build_reason(state)
        state.human_approval_required = False

        logger.info(
            f"[{state.ticker}] Decision: {action}, "
            f"position_size={state.recommended_position_size:.4f}"
        )
        return state


def _resolve_action(state: TradingState) -> str:
    """Resolve the final trading action from jury/debate signals."""
    # If jury was spawned, use jury decision
    if state.jury_spawned and state.jury_result:
        jury_decision = state.jury_result.get("decision", "HOLD")
        return jury_decision

    # If debate reached agreement, use debate outcome
    if state.debate_agreed:
        # Map agreement to BUY (if composite > 0.6), SELL (< 0.4), else HOLD
        if state.quant_composite > 0.6:
            return "BUY"
        elif state.quant_composite < 0.4:
            return "SELL"
        else:
            return "HOLD"

    return "HOLD"


def _build_reason(state: TradingState) -> str:
    """Build a human-readable reason string for the decision."""
    parts = []
    parts.append(f"Quant composite: {state.quant_composite:.3f}")
    parts.append(f"Wasden: {state.wasden_verdict} ({state.wasden_confidence:.2f})")

    if state.jury_spawned:
        jury_decision = state.jury_result.get("decision", "N/A") if state.jury_result else "N/A"
        parts.append(f"Jury: {jury_decision}")
    elif state.debate_agreed:
        parts.append("Debate: agreement (no jury)")

    if state.high_disagreement_flag:
        parts.append(f"Model disagreement: {state.quant_std_dev:.3f} (position halved)")

    return " | ".join(parts)
