from fastapi import APIRouter

from app.config import settings
from app.mock.generators import (
    generate_risk_check_mock,
    generate_circuit_breaker_mock,
    generate_stress_tests_mock,
    generate_consecutive_loss_mock,
)
from app.services.risk import constants

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get("/check")
async def run_risk_check(
    ticker: str = "NVDA",
    position_pct: float = 0.05,
):
    """Run risk checks for a proposed trade."""
    if settings.use_mock_data:
        return generate_risk_check_mock(ticker, position_pct)

    from app.services.risk.risk_engine import RiskContext, run_risk_checks
    ctx = RiskContext(
        ticker=ticker,
        proposed_position_pct=position_pct,
        portfolio_value=100_000,
        cash_balance=35_000,
    )
    return run_risk_checks(ctx)


@router.get("/circuit-breaker")
async def get_circuit_breaker():
    """Get circuit breaker status."""
    if settings.use_mock_data:
        return generate_circuit_breaker_mock()

    from app.services.risk.circuit_breaker import (
        get_circuit_breaker_state,
        circuit_breaker_to_dict,
    )
    return circuit_breaker_to_dict(get_circuit_breaker_state())


@router.get("/stress-test")
async def run_stress_tests():
    """Run all 5 crash scenario stress tests."""
    if settings.use_mock_data:
        return generate_stress_tests_mock()

    from app.services.risk.stress_test import run_all_stress_tests
    from app.mock.generators import generate_positions

    positions = [
        {
            "ticker": p["ticker"].replace(" US Equity", ""),
            "sector": "Technology",
            "current_value": p["current_price"] * p["quantity"],
        }
        for p in generate_positions()
        if p["status"] == "open"
    ]
    return run_all_stress_tests(positions, 100_000)


@router.get("/constants")
async def get_risk_constants():
    """Return all risk constants (read-only)."""
    return {
        "MAX_POSITION_PCT": constants.MAX_POSITION_PCT,
        "RISK_PER_TRADE_PCT": constants.RISK_PER_TRADE_PCT,
        "MIN_CASH_RESERVE_PCT": constants.MIN_CASH_RESERVE_PCT,
        "MAX_CORRELATED_POSITIONS": constants.MAX_CORRELATED_POSITIONS,
        "CORRELATION_THRESHOLD": constants.CORRELATION_THRESHOLD,
        "STRESS_CORRELATION_THRESHOLD": constants.STRESS_CORRELATION_THRESHOLD,
        "REGIME_CIRCUIT_BREAKER_SPY_DROP": constants.REGIME_CIRCUIT_BREAKER_SPY_DROP,
        "DEFENSIVE_POSITION_REDUCTION": constants.DEFENSIVE_POSITION_REDUCTION,
        "DEFENSIVE_CASH_TARGET": constants.DEFENSIVE_CASH_TARGET,
        "HIGH_MODEL_DISAGREEMENT_THRESHOLD": constants.HIGH_MODEL_DISAGREEMENT_THRESHOLD,
        "SLIPPAGE_ADV_THRESHOLD": constants.SLIPPAGE_ADV_THRESHOLD,
        "SLIPPAGE_PER_ADV_PCT": constants.SLIPPAGE_PER_ADV_PCT,
        "CONSECUTIVE_LOSS_WARNING": constants.CONSECUTIVE_LOSS_WARNING,
    }


@router.get("/consecutive-loss")
async def get_consecutive_loss():
    """Get consecutive loss counter state."""
    if settings.use_mock_data:
        return generate_consecutive_loss_mock()

    from app.services.risk.consecutive_loss import (
        get_current_streak,
        consecutive_loss_to_dict,
    )
    return consecutive_loss_to_dict(get_current_streak())
