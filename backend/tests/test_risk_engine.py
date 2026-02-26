"""Unit tests for the risk engine — 7 sequential risk checks.

All tests use mock portfolio data. No database, no API calls.
Verifies risk constants match PROJECT_STANDARDS_v2.md Section 8 exactly.
"""

import os

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

from app.services.risk.risk_engine import (  # noqa: E402
    RiskContext,
    run_risk_checks,
    RISK_CHECKS,
)
from app.services.risk.constants import (  # noqa: E402
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


# ---------------------------------------------------------------------------
# Helper: build a clean RiskContext that passes all 7 checks
# ---------------------------------------------------------------------------

def _clean_context(**overrides) -> RiskContext:
    """Return a RiskContext that passes all 7 checks by default."""
    defaults = dict(
        ticker="NVDA",
        proposed_position_pct=0.05,       # well within 12%
        portfolio_value=100_000.0,
        cash_balance=30_000.0,            # 30% cash (after 5% trade = 25%)
        existing_positions=[
            {"ticker": "MSFT", "sector": "Technology", "position_pct": 0.08},
            {"ticker": "AMZN", "sector": "Consumer Discretionary", "position_pct": 0.06},
        ],
        correlations={"MSFT": 0.55, "AMZN": 0.40},
        stress_correlations={"MSFT": 0.65, "AMZN": 0.50},
        sector="Semiconductors",
        sector_limits={},
        default_sector_limit=0.40,
        gap_risk_score=0.30,
        gap_risk_threshold=0.70,
        model_std_dev=0.15,
    )
    defaults.update(overrides)
    return RiskContext(**defaults)


# ---------------------------------------------------------------------------
# Test: position size check
# ---------------------------------------------------------------------------

def test_position_size_check_passes():
    """Proposed position within MAX_POSITION_PCT passes."""
    ctx = _clean_context(proposed_position_pct=0.10)
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "position_size")
    assert detail["passed"] is True


def test_position_size_check_fails():
    """Proposed position exceeding MAX_POSITION_PCT fails."""
    ctx = _clean_context(proposed_position_pct=0.15)
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "position_size")
    assert detail["passed"] is False
    assert "position_size" in result["checks_failed"]


# ---------------------------------------------------------------------------
# Test: cash reserve check
# ---------------------------------------------------------------------------

def test_cash_reserve_check():
    """Post-trade cash below MIN_CASH_RESERVE_PCT fails."""
    # 5% position on $100k = $5k trade; starting cash $12k -> remaining $7k = 7% < 10%
    ctx = _clean_context(
        proposed_position_pct=0.05,
        portfolio_value=100_000.0,
        cash_balance=12_000.0,
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "cash_reserve")
    assert detail["passed"] is False
    assert "cash_reserve" in result["checks_failed"]


def test_cash_reserve_check_passes():
    """Post-trade cash above MIN_CASH_RESERVE_PCT passes."""
    ctx = _clean_context(
        proposed_position_pct=0.05,
        portfolio_value=100_000.0,
        cash_balance=50_000.0,
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "cash_reserve")
    assert detail["passed"] is True


# ---------------------------------------------------------------------------
# Test: correlation check
# ---------------------------------------------------------------------------

def test_correlation_check():
    """Having >= MAX_CORRELATED_POSITIONS correlated positions fails."""
    # 3 existing positions all above 0.70 threshold => 3 >= 3 => fail
    ctx = _clean_context(
        existing_positions=[
            {"ticker": "MSFT", "sector": "Technology", "position_pct": 0.08},
            {"ticker": "AMD", "sector": "Semiconductors", "position_pct": 0.06},
            {"ticker": "INTC", "sector": "Semiconductors", "position_pct": 0.04},
        ],
        correlations={"MSFT": 0.75, "AMD": 0.80, "INTC": 0.72},
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "correlation")
    assert detail["passed"] is False
    assert "correlation" in result["checks_failed"]


def test_correlation_check_passes():
    """Fewer than MAX_CORRELATED_POSITIONS correlated positions passes."""
    ctx = _clean_context(
        correlations={"MSFT": 0.40, "AMZN": 0.30},
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "correlation")
    assert detail["passed"] is True


# ---------------------------------------------------------------------------
# Test: sector concentration check
# ---------------------------------------------------------------------------

def test_sector_concentration_check():
    """Sector concentration above default limit fails."""
    # Two existing Technology at 20% each + proposed 5% in Technology = 45% > 40%
    ctx = _clean_context(
        sector="Technology",
        existing_positions=[
            {"ticker": "MSFT", "sector": "Technology", "position_pct": 0.20},
            {"ticker": "AAPL", "sector": "Technology", "position_pct": 0.20},
        ],
        proposed_position_pct=0.05,
        default_sector_limit=0.40,
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "sector_concentration")
    assert detail["passed"] is False
    assert "sector_concentration" in result["checks_failed"]


def test_sector_concentration_check_passes():
    """Sector concentration within limit passes."""
    ctx = _clean_context(
        sector="Technology",
        existing_positions=[
            {"ticker": "MSFT", "sector": "Technology", "position_pct": 0.10},
        ],
        proposed_position_pct=0.05,
        default_sector_limit=0.40,
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "sector_concentration")
    assert detail["passed"] is True


# ---------------------------------------------------------------------------
# Test: model disagreement check
# ---------------------------------------------------------------------------

def test_model_disagreement_check():
    """Model std_dev above HIGH_MODEL_DISAGREEMENT_THRESHOLD fails."""
    ctx = _clean_context(model_std_dev=0.60)
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "model_disagreement")
    assert detail["passed"] is False
    assert "model_disagreement" in result["checks_failed"]


def test_model_disagreement_check_passes():
    """Model std_dev within threshold passes."""
    ctx = _clean_context(model_std_dev=0.25)
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "model_disagreement")
    assert detail["passed"] is True


# ---------------------------------------------------------------------------
# Test: all 7 checks pass
# ---------------------------------------------------------------------------

def test_all_checks_pass():
    """Clean portfolio passes all 7 risk checks."""
    ctx = _clean_context()
    result = run_risk_checks(ctx)
    assert result["passed"] is True
    assert result["checks_failed"] == []
    assert len(result["details"]) == 7
    for detail in result["details"]:
        assert detail["passed"] is True, f"{detail['check_name']} unexpectedly failed"


def test_seven_checks_executed_in_order():
    """All 7 checks run in the order specified by PROJECT_STANDARDS Section 8."""
    assert len(RISK_CHECKS) == 7
    ctx = _clean_context()
    result = run_risk_checks(ctx)
    expected_order = [
        "position_size", "cash_reserve", "correlation",
        "stress_correlation", "sector_concentration", "gap_risk",
        "model_disagreement",
    ]
    actual_order = [d["check_name"] for d in result["details"]]
    assert actual_order == expected_order


# ---------------------------------------------------------------------------
# Test: risk constants match PROJECT_STANDARDS_v2.md Section 8 exactly
# ---------------------------------------------------------------------------

def test_risk_constants_are_protected():
    """Verify all 13 constants match PROJECT_STANDARDS_v2.md Section 8 values exactly."""
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


def test_constants_are_numeric():
    """All risk constants are numeric types (int or float)."""
    all_constants = [
        MAX_POSITION_PCT, RISK_PER_TRADE_PCT, MIN_CASH_RESERVE_PCT,
        MAX_CORRELATED_POSITIONS, CORRELATION_THRESHOLD,
        STRESS_CORRELATION_THRESHOLD, REGIME_CIRCUIT_BREAKER_SPY_DROP,
        DEFENSIVE_POSITION_REDUCTION, DEFENSIVE_CASH_TARGET,
        HIGH_MODEL_DISAGREEMENT_THRESHOLD, SLIPPAGE_ADV_THRESHOLD,
        SLIPPAGE_PER_ADV_PCT, CONSECUTIVE_LOSS_WARNING,
    ]
    for c in all_constants:
        assert isinstance(c, (int, float)), f"Constant {c} is not numeric"
