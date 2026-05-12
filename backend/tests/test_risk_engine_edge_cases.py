"""Edge case tests for the risk engine — 7 sequential risk checks.

Covers exact boundary values, zero/negative inputs, empty collections,
floating-point rounding, and maximum-scale portfolios.
All tests use mock portfolio data. No database, no API calls.
"""

import os

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

from app.services.risk.risk_engine import (  # noqa: E402
    RiskContext,
    run_risk_checks,
)
from app.services.risk.constants import (  # noqa: E402
    MAX_POSITION_PCT,
    CORRELATION_THRESHOLD,
    STRESS_CORRELATION_THRESHOLD,
    HIGH_MODEL_DISAGREEMENT_THRESHOLD,
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
# Check 1: Position size — exact boundary
# ---------------------------------------------------------------------------

def test_position_size_exactly_at_max_passes():
    """proposed_position_pct == MAX_POSITION_PCT (0.12) should pass (<=)."""
    ctx = _clean_context(
        proposed_position_pct=MAX_POSITION_PCT,  # 0.12
        cash_balance=50_000.0,                   # enough cash headroom
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "position_size")
    assert detail["passed"] is True, (
        f"position_pct == MAX_POSITION_PCT should pass; got detail={detail['detail']}"
    )


def test_position_size_one_epsilon_over_max_fails():
    """proposed_position_pct = 0.120001 (just above MAX_POSITION_PCT) must fail."""
    ctx = _clean_context(
        proposed_position_pct=0.120001,
        cash_balance=50_000.0,
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "position_size")
    assert detail["passed"] is False
    assert "position_size" in result["checks_failed"]


def test_position_size_zero_passes():
    """Proposed position of 0.0 is technically <= MAX_POSITION_PCT and should pass."""
    ctx = _clean_context(
        proposed_position_pct=0.0,
        cash_balance=50_000.0,
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "position_size")
    assert detail["passed"] is True


def test_position_size_negative_passes_size_check():
    """Negative position_pct (<= MAX_POSITION_PCT) passes the position_size check itself."""
    # The check is only `<= MAX_POSITION_PCT`; negative values satisfy that.
    ctx = _clean_context(
        proposed_position_pct=-0.05,
        cash_balance=50_000.0,
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "position_size")
    assert detail["passed"] is True


# ---------------------------------------------------------------------------
# Check 2: Cash reserve — zero and exact boundaries
# ---------------------------------------------------------------------------

def test_cash_reserve_zero_portfolio_value_does_not_raise():
    """portfolio_value = 0 must not raise ZeroDivisionError (guarded by engine)."""
    ctx = _clean_context(
        portfolio_value=0.0,
        cash_balance=0.0,
        proposed_position_pct=0.05,
    )
    # Should return a result dict, not blow up
    result = run_risk_checks(ctx)
    assert isinstance(result, dict)
    assert "details" in result


def test_cash_reserve_zero_portfolio_fails_cash_check():
    """With portfolio_value = 0 the remaining_pct guard defaults to 0, failing the check."""
    ctx = _clean_context(
        portfolio_value=0.0,
        cash_balance=0.0,
        proposed_position_pct=0.05,
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "cash_reserve")
    # remaining_pct = 0 < MIN_CASH_RESERVE_PCT (0.10) => should fail
    assert detail["passed"] is False


def test_cash_reserve_exactly_at_minimum_passes():
    """Post-trade cash exactly equal to MIN_CASH_RESERVE_PCT should pass (>=)."""
    # We want: (cash_balance - trade_cost) / portfolio_value == MIN_CASH_RESERVE_PCT
    # trade_cost = proposed_position_pct * portfolio_value = 0.05 * 100_000 = 5_000
    # remaining = cash_balance - 5_000 must equal 0.10 * 100_000 = 10_000
    # => cash_balance = 15_000
    ctx = _clean_context(
        proposed_position_pct=0.05,
        portfolio_value=100_000.0,
        cash_balance=15_000.0,
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "cash_reserve")
    assert detail["passed"] is True


def test_cash_reserve_one_cent_under_minimum_fails():
    """Post-trade cash one cent short of MIN_CASH_RESERVE_PCT must fail."""
    # remaining needed = 10_000.00; set cash so remaining = 9_999.99
    # cash_balance = 9_999.99 + 5_000 = 14_999.99
    ctx = _clean_context(
        proposed_position_pct=0.05,
        portfolio_value=100_000.0,
        cash_balance=14_999.99,
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "cash_reserve")
    assert detail["passed"] is False
    assert "cash_reserve" in result["checks_failed"]


def test_cash_reserve_very_large_portfolio():
    """Very large portfolio value ($1 billion) does not overflow or miscompute."""
    ctx = _clean_context(
        portfolio_value=1_000_000_000.0,
        cash_balance=500_000_000.0,   # 50% cash — easily passes
        proposed_position_pct=0.05,
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "cash_reserve")
    assert detail["passed"] is True


# ---------------------------------------------------------------------------
# Check 3: Correlation — exact count boundaries
# ---------------------------------------------------------------------------

def test_correlation_exactly_two_correlated_passes():
    """Exactly 2 correlated positions (< MAX_CORRELATED_POSITIONS=3) should pass."""
    ctx = _clean_context(
        existing_positions=[
            {"ticker": "MSFT", "sector": "Technology", "position_pct": 0.08},
            {"ticker": "AMD", "sector": "Semiconductors", "position_pct": 0.06},
            {"ticker": "INTC", "sector": "Semiconductors", "position_pct": 0.04},
        ],
        correlations={"MSFT": 0.75, "AMD": 0.80, "INTC": 0.50},  # only 2 above threshold
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "correlation")
    assert detail["passed"] is True


def test_correlation_exactly_three_correlated_fails():
    """Exactly MAX_CORRELATED_POSITIONS (3) correlated positions fails (>= 3 fails)."""
    ctx = _clean_context(
        existing_positions=[
            {"ticker": "MSFT", "sector": "Technology", "position_pct": 0.08},
            {"ticker": "AMD", "sector": "Semiconductors", "position_pct": 0.06},
            {"ticker": "INTC", "sector": "Semiconductors", "position_pct": 0.04},
        ],
        correlations={"MSFT": 0.75, "AMD": 0.80, "INTC": 0.72},  # all 3 above threshold
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "correlation")
    assert detail["passed"] is False
    assert "correlation" in result["checks_failed"]


def test_correlation_at_exact_threshold_triggers():
    """Correlation exactly equal to CORRELATION_THRESHOLD (0.70) counts as correlated."""
    # The check is `c >= CORRELATION_THRESHOLD` so 0.70 is included.
    ctx = _clean_context(
        existing_positions=[
            {"ticker": "MSFT", "sector": "Technology", "position_pct": 0.08},
            {"ticker": "AMD", "sector": "Semiconductors", "position_pct": 0.06},
            {"ticker": "INTC", "sector": "Semiconductors", "position_pct": 0.04},
        ],
        correlations={"MSFT": CORRELATION_THRESHOLD, "AMD": CORRELATION_THRESHOLD, "INTC": CORRELATION_THRESHOLD},
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "correlation")
    assert detail["passed"] is False


def test_correlation_just_below_threshold_does_not_trigger():
    """Correlation of 0.6999 (just below threshold) must not count as correlated."""
    ctx = _clean_context(
        existing_positions=[
            {"ticker": "MSFT", "sector": "Technology", "position_pct": 0.08},
            {"ticker": "AMD", "sector": "Semiconductors", "position_pct": 0.06},
            {"ticker": "INTC", "sector": "Semiconductors", "position_pct": 0.04},
        ],
        correlations={"MSFT": 0.6999, "AMD": 0.6999, "INTC": 0.6999},
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "correlation")
    assert detail["passed"] is True


def test_correlation_empty_dict_passes():
    """Empty correlations dict means zero correlated positions — must pass."""
    ctx = _clean_context(correlations={})
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "correlation")
    assert detail["passed"] is True


def test_correlation_ticker_not_in_existing_positions():
    """High correlation for a ticker not in existing_positions does not count."""
    ctx = _clean_context(
        existing_positions=[
            {"ticker": "MSFT", "sector": "Technology", "position_pct": 0.08},
        ],
        # TSLA, AMD, INTC correlated but none are in existing_positions
        correlations={"TSLA": 0.90, "AMD": 0.85, "INTC": 0.80},
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "correlation")
    assert detail["passed"] is True


# ---------------------------------------------------------------------------
# Check 4: Stress correlation — boundaries and empty dict
# ---------------------------------------------------------------------------

def test_stress_correlation_empty_dict_passes():
    """Empty stress_correlations dict means no high-stress tickers — must pass."""
    ctx = _clean_context(stress_correlations={})
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "stress_correlation")
    assert detail["passed"] is True


def test_stress_correlation_exactly_at_threshold_fails():
    """Stress correlation exactly equal to STRESS_CORRELATION_THRESHOLD (0.80) triggers failure."""
    ctx = _clean_context(
        stress_correlations={"MSFT": STRESS_CORRELATION_THRESHOLD},
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "stress_correlation")
    assert detail["passed"] is False
    assert "stress_correlation" in result["checks_failed"]


def test_stress_correlation_just_below_threshold_passes():
    """Stress correlation of 0.7999 (just below threshold) must pass."""
    ctx = _clean_context(
        stress_correlations={"MSFT": 0.7999},
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "stress_correlation")
    assert detail["passed"] is True


def test_stress_correlation_negative_value_passes():
    """Negative stress correlation (inverse) is far below threshold — must pass."""
    ctx = _clean_context(
        stress_correlations={"MSFT": -0.90},
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "stress_correlation")
    assert detail["passed"] is True


# ---------------------------------------------------------------------------
# Check 5: Sector concentration — sector_limits fallback
# ---------------------------------------------------------------------------

def test_sector_concentration_uses_sector_specific_limit():
    """When sector_limits has an entry for the sector, that limit is used."""
    # Custom limit of 0.25 for Technology; total = 0.10 + 0.05 = 0.15 => passes
    ctx = _clean_context(
        sector="Technology",
        existing_positions=[
            {"ticker": "MSFT", "sector": "Technology", "position_pct": 0.10},
        ],
        proposed_position_pct=0.05,
        sector_limits={"Technology": 0.25},
        default_sector_limit=0.40,
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "sector_concentration")
    assert detail["passed"] is True
    assert detail["threshold"] == 0.25


def test_sector_concentration_sector_not_in_sector_limits_uses_default():
    """Sector missing from sector_limits falls back to default_sector_limit."""
    ctx = _clean_context(
        sector="Biotechnology",
        existing_positions=[
            {"ticker": "BIOA", "sector": "Biotechnology", "position_pct": 0.30},
        ],
        proposed_position_pct=0.05,
        sector_limits={"Technology": 0.30},  # Biotechnology NOT here
        default_sector_limit=0.40,
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "sector_concentration")
    # 0.30 + 0.05 = 0.35 <= 0.40 (default) => passes
    assert detail["passed"] is True
    assert detail["threshold"] == 0.40


def test_sector_concentration_tight_custom_limit_fails():
    """Custom tight sector limit causes check to fail when threshold is breached."""
    ctx = _clean_context(
        sector="Energy",
        existing_positions=[
            {"ticker": "XOM", "sector": "Energy", "position_pct": 0.10},
        ],
        proposed_position_pct=0.05,
        sector_limits={"Energy": 0.12},  # total = 0.15 > 0.12
        default_sector_limit=0.40,
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "sector_concentration")
    assert detail["passed"] is False
    assert "sector_concentration" in result["checks_failed"]


def test_sector_concentration_empty_sector_string_skips_check():
    """Empty sector string causes the check to be skipped (returns passed=True)."""
    ctx = _clean_context(
        sector="",
        existing_positions=[
            {"ticker": "MSFT", "sector": "Technology", "position_pct": 0.35},
        ],
        proposed_position_pct=0.10,
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "sector_concentration")
    assert detail["passed"] is True


def test_sector_concentration_no_existing_positions_in_sector_passes():
    """If no existing positions share the proposed sector, only proposed_pct counts."""
    ctx = _clean_context(
        sector="Healthcare",
        existing_positions=[
            {"ticker": "MSFT", "sector": "Technology", "position_pct": 0.30},
        ],
        proposed_position_pct=0.05,
        default_sector_limit=0.40,
    )
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "sector_concentration")
    assert detail["passed"] is True


# ---------------------------------------------------------------------------
# Check 6: Gap risk — boundary values and negative scores
# ---------------------------------------------------------------------------

def test_gap_risk_negative_score_passes():
    """Negative gap_risk_score is below any threshold — must pass."""
    ctx = _clean_context(gap_risk_score=-0.50)
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "gap_risk")
    assert detail["passed"] is True


def test_gap_risk_exactly_at_threshold_fails():
    """gap_risk_score == gap_risk_threshold (0.70) fails (check is strict <)."""
    ctx = _clean_context(gap_risk_score=0.70, gap_risk_threshold=0.70)
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "gap_risk")
    assert detail["passed"] is False
    assert "gap_risk" in result["checks_failed"]


def test_gap_risk_just_below_threshold_passes():
    """gap_risk_score = 0.6999 (just below threshold=0.70) must pass."""
    ctx = _clean_context(gap_risk_score=0.6999, gap_risk_threshold=0.70)
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "gap_risk")
    assert detail["passed"] is True


# ---------------------------------------------------------------------------
# Check 7: Model disagreement — exact boundary and negative std_dev
# ---------------------------------------------------------------------------

def test_model_disagreement_exactly_at_threshold_passes():
    """model_std_dev == HIGH_MODEL_DISAGREEMENT_THRESHOLD (0.50) passes (check is <=)."""
    ctx = _clean_context(model_std_dev=HIGH_MODEL_DISAGREEMENT_THRESHOLD)
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "model_disagreement")
    assert detail["passed"] is True


def test_model_disagreement_one_epsilon_over_threshold_fails():
    """model_std_dev = 0.500001 (just above threshold) must fail."""
    ctx = _clean_context(model_std_dev=0.500001)
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "model_disagreement")
    assert detail["passed"] is False
    assert "model_disagreement" in result["checks_failed"]


def test_model_disagreement_negative_std_dev_passes():
    """Negative model_std_dev is below threshold — must pass (no sign validation here)."""
    ctx = _clean_context(model_std_dev=-0.30)
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "model_disagreement")
    assert detail["passed"] is True


def test_model_disagreement_zero_std_dev_passes():
    """model_std_dev = 0.0 (perfect model agreement) must pass."""
    ctx = _clean_context(model_std_dev=0.0)
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "model_disagreement")
    assert detail["passed"] is True


# ---------------------------------------------------------------------------
# Multi-check / result structure edge cases
# ---------------------------------------------------------------------------

def test_multiple_checks_fail_simultaneously():
    """Context that violates position_size AND model_disagreement reports both failures."""
    ctx = _clean_context(
        proposed_position_pct=0.20,   # exceeds MAX_POSITION_PCT
        model_std_dev=0.99,           # exceeds HIGH_MODEL_DISAGREEMENT_THRESHOLD
        cash_balance=50_000.0,
    )
    result = run_risk_checks(ctx)
    assert result["passed"] is False
    assert "position_size" in result["checks_failed"]
    assert "model_disagreement" in result["checks_failed"]


def test_result_always_has_seven_detail_entries():
    """run_risk_checks always returns exactly 7 detail entries regardless of failures."""
    ctx = _clean_context(
        proposed_position_pct=0.99,  # forces many failures
        cash_balance=1.0,
        model_std_dev=0.99,
        gap_risk_score=0.99,
        stress_correlations={"MSFT": 0.99},
    )
    result = run_risk_checks(ctx)
    assert len(result["details"]) == 7


def test_detail_value_and_threshold_populated_for_position_size():
    """position_size detail contains numeric value and threshold fields."""
    ctx = _clean_context(proposed_position_pct=0.08, cash_balance=50_000.0)
    result = run_risk_checks(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "position_size")
    assert detail["value"] == 0.08
    assert detail["threshold"] == MAX_POSITION_PCT


def test_large_number_of_existing_positions_no_crash():
    """100 existing positions in correlations dict does not crash the engine."""
    tickers = [f"TICK{i:03d}" for i in range(100)]
    existing = [{"ticker": t, "sector": "Technology", "position_pct": 0.001} for t in tickers]
    # Only 2 above correlation threshold — should pass
    correlations = {t: 0.30 for t in tickers}
    correlations["TICK000"] = 0.80
    correlations["TICK001"] = 0.75
    ctx = _clean_context(
        existing_positions=existing,
        correlations=correlations,
        stress_correlations={},
        cash_balance=80_000.0,
    )
    result = run_risk_checks(ctx)
    assert isinstance(result, dict)
    assert len(result["details"]) == 7
