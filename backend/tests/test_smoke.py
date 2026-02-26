"""Smoke tests — verify app starts and all routers register.

Tests: app startup, 14 routers, risk constants, separation enforcement.
"""

import os

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

from app.main import app  # noqa: E402


def test_app_starts():
    """FastAPI app initializes without error."""
    assert app is not None
    assert app.title == "Wasden Watch Trading Dashboard API"


def test_14_routers_registered():
    """All 14 API routers are registered."""
    prefixes = set()
    for route in app.routes:
        if hasattr(route, "path"):
            parts = route.path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] == "api":
                prefixes.add(parts[1])

    expected = {
        "health", "portfolio", "recommendations", "journal",
        "debates", "jury", "overrides", "alerts", "bias",
        "screening", "settings", "data", "risk", "execution",
    }
    assert prefixes == expected, f"Missing: {expected - prefixes}, Extra: {prefixes - expected}"


def test_risk_constants_match_standards():
    """Risk constants match PROJECT_STANDARDS_v2.md Section 8 exactly."""
    from app.services.risk.constants import (
        MAX_POSITION_PCT,
        RISK_PER_TRADE_PCT,
        MIN_CASH_RESERVE_PCT,
        MAX_CORRELATED_POSITIONS,
        CORRELATION_THRESHOLD,
        STRESS_CORRELATION_THRESHOLD,
        REGIME_CIRCUIT_BREAKER_SPY_DROP,
        DEFENSIVE_POSITION_REDUCTION,
        DEFENSIVE_CASH_TARGET,
        HIGH_MODEL_DISAGREEMENT_THRESHOLD,
        SLIPPAGE_ADV_THRESHOLD,
        SLIPPAGE_PER_ADV_PCT,
        CONSECUTIVE_LOSS_WARNING,
    )

    assert MAX_POSITION_PCT == 0.12
    assert RISK_PER_TRADE_PCT == 0.015
    assert MIN_CASH_RESERVE_PCT == 0.10
    assert MAX_CORRELATED_POSITIONS == 3
    assert CORRELATION_THRESHOLD == 0.70
    assert STRESS_CORRELATION_THRESHOLD == 0.80
    assert REGIME_CIRCUIT_BREAKER_SPY_DROP == 0.05
    assert DEFENSIVE_POSITION_REDUCTION == 0.50
    assert DEFENSIVE_CASH_TARGET == 0.40
    assert HIGH_MODEL_DISAGREEMENT_THRESHOLD == 0.50
    assert SLIPPAGE_ADV_THRESHOLD == 0.01
    assert SLIPPAGE_PER_ADV_PCT == 0.001
    assert CONSECUTIVE_LOSS_WARNING == 7


def test_pre_trade_validation_separation():
    """pre_trade_validation.py has zero imports from risk_engine.py."""
    import inspect
    from app.services.risk import pre_trade_validation

    source = inspect.getsource(pre_trade_validation)
    assert "risk_engine" not in source.split("# ")[0].replace("risk_engine.py", ""), \
        "pre_trade_validation must not import from risk_engine"

