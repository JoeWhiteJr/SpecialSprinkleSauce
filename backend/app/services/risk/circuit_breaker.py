"""
Regime Circuit Breaker — per PROJECT_STANDARDS_v2.md Section 8.

SPY drops > 5% in rolling 5-day window:
  - Cut all positions by 50%
  - Increase cash to 40%
  - Halt new entries
  - Log regime_circuit_breaker_active: true
  - Alert both partners
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.services.risk.constants import (
    REGIME_CIRCUIT_BREAKER_SPY_DROP,
    DEFENSIVE_POSITION_REDUCTION,
    DEFENSIVE_CASH_TARGET,
)

logger = logging.getLogger("wasden_watch.circuit_breaker")


@dataclass
class CircuitBreakerState:
    """Current circuit breaker state."""
    active: bool = False
    triggered_at: Optional[str] = None
    spy_5day_return: Optional[float] = None
    actions_taken: list[str] = field(default_factory=list)
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None


# In-memory state (will be backed by DB in production via migration 017)
_state = CircuitBreakerState()


def check_circuit_breaker(spy_5day_return: float) -> CircuitBreakerState:
    """Check if circuit breaker should trigger based on SPY 5-day return.

    Args:
        spy_5day_return: SPY rolling 5-day return as a decimal (e.g., -0.06 = -6%)

    Returns:
        Updated CircuitBreakerState.
    """
    global _state

    # Already active — don't re-trigger
    if _state.active:
        logger.info(
            f"Circuit breaker already active (triggered {_state.triggered_at}). "
            f"SPY 5-day: {spy_5day_return:.2%}"
        )
        return _state

    # Check trigger condition: SPY drop > threshold (both are negative)
    if spy_5day_return <= -REGIME_CIRCUIT_BREAKER_SPY_DROP:
        logger.critical(
            f"CIRCUIT BREAKER TRIGGERED: SPY 5-day return {spy_5day_return:.2%} "
            f"<= -{REGIME_CIRCUIT_BREAKER_SPY_DROP:.1%} threshold"
        )
        _state = CircuitBreakerState(
            active=True,
            triggered_at=datetime.utcnow().isoformat() + "Z",
            spy_5day_return=spy_5day_return,
            actions_taken=[
                f"Cut all positions by {DEFENSIVE_POSITION_REDUCTION:.0%}",
                f"Increase cash target to {DEFENSIVE_CASH_TARGET:.0%}",
                "Halt new entries",
                "Alert both partners",
            ],
        )
    else:
        logger.debug(
            f"Circuit breaker NOT triggered: SPY 5-day {spy_5day_return:.2%} "
            f"> -{REGIME_CIRCUIT_BREAKER_SPY_DROP:.1%}"
        )

    return _state


def get_circuit_breaker_state() -> CircuitBreakerState:
    """Return current circuit breaker state."""
    return _state


def reset_circuit_breaker(approved_by: str) -> CircuitBreakerState:
    """Reset circuit breaker after human approval.

    Args:
        approved_by: Name of person approving the reset (Joe or Jared).

    Returns:
        Updated (inactive) CircuitBreakerState.
    """
    global _state

    if not _state.active:
        logger.info("Circuit breaker already inactive, nothing to reset")
        return _state

    logger.info(f"Circuit breaker RESET approved by {approved_by}")
    _state = CircuitBreakerState(
        active=False,
        resolved_at=datetime.utcnow().isoformat() + "Z",
        resolved_by=approved_by,
    )
    return _state


def circuit_breaker_to_dict(state: CircuitBreakerState) -> dict:
    """Convert CircuitBreakerState to API-friendly dict."""
    return {
        "active": state.active,
        "triggered_at": state.triggered_at,
        "spy_5day_return": state.spy_5day_return,
        "actions_taken": state.actions_taken,
        "resolved_at": state.resolved_at,
        "resolved_by": state.resolved_by,
    }
