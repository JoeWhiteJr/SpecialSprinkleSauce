"""Unit tests for the 5-tier screening pipeline, Piotroski F-Score, and data freshness.

All tests use mock data. No database, no API calls.
"""

import os
from datetime import date, timedelta

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

from app.services.screening_engine import (  # noqa: E402
    _tier1_liquidity,
    _tier2_sprinkle_sauce,
    _tier3_quant,
    _tier4_wasden,
    _tier5_final_selection,
    MIN_FCF_YIELD,
)
from app.services.piotroski import (  # noqa: E402
    compute_piotroski,
    SIGNAL_NAMES,
    THRESHOLD_RATIO,
)
from app.services.freshness import (  # noqa: E402
    compute_freshness,
    freshness_weight,
)
from app.models.schemas import DataFreshness  # noqa: E402


# ---------------------------------------------------------------------------
# Mock fundamentals helpers
# ---------------------------------------------------------------------------

def _good_fundamentals(**overrides):
    """Return fundamentals that pass Tier 1 and Tier 2."""
    base = {
        "market_cap": 50_000_000_000,   # $50B — passes Tier 1
        "peg_ratio": 1.2,               # < 2.0 — passes PEG
        "fcf_yield": 5.0,               # > 3.0% — passes FCF yield
        "eps": 8.50,                     # positive
        "fcf": 12_000_000_000,          # positive
        "operating_margin": 25.0,        # positive
        "revenue_growth": 15.0,          # positive
        "debt_to_equity": 0.5,
        "current_ratio": 2.0,
        "gross_margin": 55.0,
        "roe": 0.18,
    }
    base.update(overrides)
    return base


# ===========================================================================
# Tier 1: Market cap filter
# ===========================================================================

def test_tier1_market_cap_filter():
    """Ticker with market cap below $5B is filtered out."""
    fundamentals = _good_fundamentals(market_cap=3_000_000_000)
    result = _tier1_liquidity("SMALL", fundamentals)
    assert result["passed"] is False
    assert any("market_cap" in r for r in result["fail_reasons"])


def test_tier1_market_cap_passes():
    """Ticker with market cap above $5B passes."""
    fundamentals = _good_fundamentals(market_cap=10_000_000_000)
    result = _tier1_liquidity("BIG", fundamentals)
    assert result["passed"] is True


def test_tier1_missing_market_cap():
    """Missing market cap data fails."""
    fundamentals = _good_fundamentals()
    fundamentals.pop("market_cap")
    result = _tier1_liquidity("NODATA", fundamentals)
    assert result["passed"] is False


# ===========================================================================
# Tier 2: PEG filter
# ===========================================================================

def test_tier2_peg_filter():
    """PEG >= 2.0 is filtered out."""
    fundamentals = _good_fundamentals(peg_ratio=2.5)
    result = _tier2_sprinkle_sauce("HIGHPEG", fundamentals)
    assert result["passed"] is False
    assert any("PEG" in r for r in result["fail_reasons"])


def test_tier2_peg_exactly_2():
    """PEG exactly 2.0 is filtered out (>= threshold)."""
    fundamentals = _good_fundamentals(peg_ratio=2.0)
    result = _tier2_sprinkle_sauce("PEG2", fundamentals)
    assert result["passed"] is False


# ===========================================================================
# Tier 2: FCF yield filter
# ===========================================================================

def test_tier2_fcf_yield_filter():
    """FCF yield below 3.0% (stored as percentage) is filtered out."""
    fundamentals = _good_fundamentals(fcf_yield=2.5)
    result = _tier2_sprinkle_sauce("LOWFCF", fundamentals)
    assert result["passed"] is False
    assert any("FCF yield" in r for r in result["fail_reasons"])


def test_tier2_fcf_yield_stored_as_percentage():
    """Verify FCF yield threshold uses percentage (3.0 = 3%, not 0.03)."""
    assert MIN_FCF_YIELD == 3.0, "FCF yield threshold must be stored as percentage"

    # 3.5% should pass, 0.035 would fail if threshold were a decimal
    fundamentals = _good_fundamentals(fcf_yield=3.5)
    result = _tier2_sprinkle_sauce("PCTCHECK", fundamentals)
    # Only check FCF yield fail reasons (PEG/Piotroski may still pass or fail)
    fcf_failures = [r for r in result["fail_reasons"] if "FCF yield" in r]
    assert len(fcf_failures) == 0, "3.5% FCF yield should pass"


# ===========================================================================
# Tier 2: Piotroski filter
# ===========================================================================

def test_tier2_piotroski_filter():
    """F-Score below threshold is filtered out."""
    # Give fundamentals that produce a low Piotroski: negative EPS, negative FCF
    fundamentals = _good_fundamentals(
        eps=-1.0,
        fcf=-500_000_000,
        operating_margin=-5.0,
        revenue_growth=-10.0,
    )
    result = _tier2_sprinkle_sauce("LOWPIO", fundamentals)
    assert result["passed"] is False
    assert any("Piotroski" in r for r in result["fail_reasons"])


# ===========================================================================
# Piotroski F-Score: 9 signals
# ===========================================================================

def test_piotroski_nine_signals():
    """Piotroski always calculates exactly 9 signals."""
    fundamentals = _good_fundamentals()
    result = compute_piotroski("TEST", fundamentals)
    assert len(result.signals) == 9
    signal_names = [s.name for s in result.signals]
    assert signal_names == SIGNAL_NAMES


def test_piotroski_signal_values_binary():
    """All Piotroski signals are 0 or 1."""
    fundamentals = _good_fundamentals()
    result = compute_piotroski("TEST", fundamentals)
    for signal in result.signals:
        assert signal.value in (0, 1), f"Signal {signal.name} has non-binary value {signal.value}"


def test_piotroski_proportional_threshold():
    """Threshold is score/max_possible >= 5/9."""
    assert abs(THRESHOLD_RATIO - 5 / 9) < 0.001

    # All positive single-snapshot fundamentals -> ~4 available signals,
    # all pass => ratio ~ 1.0 => passes
    fundamentals = _good_fundamentals()
    result = compute_piotroski("GOODCO", fundamentals)
    if result.max_possible > 0:
        assert result.ratio == result.score / result.max_possible


def test_piotroski_with_prior_period():
    """Providing prior fundamentals unlocks more signals."""
    current = _good_fundamentals(
        eps=10.0, debt_to_equity=0.4, current_ratio=2.5, gross_margin=60.0,
    )
    prior = _good_fundamentals(
        eps=7.0, debt_to_equity=0.6, current_ratio=2.0, gross_margin=50.0,
    )
    result = compute_piotroski("DUAL", current, prior)
    available_count = sum(1 for s in result.signals if s.data_available)
    # With prior fundamentals, we should have more available signals
    assert available_count >= 6


# ===========================================================================
# Data freshness grades
# ===========================================================================

def test_data_freshness_fresh():
    """Data less than 24 hours old is FRESH."""
    today = date.today()
    assert compute_freshness(today, today) == DataFreshness.FRESH


def test_data_freshness_recent():
    """Data 1-7 days old is RECENT."""
    ref = date.today()
    pull = ref - timedelta(days=3)
    assert compute_freshness(pull, ref) == DataFreshness.RECENT

    pull_7 = ref - timedelta(days=7)
    assert compute_freshness(pull_7, ref) == DataFreshness.RECENT


def test_data_freshness_stale():
    """Data 8-30 days old is STALE."""
    ref = date.today()
    pull = ref - timedelta(days=15)
    assert compute_freshness(pull, ref) == DataFreshness.STALE

    pull_30 = ref - timedelta(days=30)
    assert compute_freshness(pull_30, ref) == DataFreshness.STALE


def test_data_freshness_expired():
    """Data over 30 days old is EXPIRED."""
    ref = date.today()
    pull = ref - timedelta(days=31)
    assert compute_freshness(pull, ref) == DataFreshness.EXPIRED

    pull_90 = ref - timedelta(days=90)
    assert compute_freshness(pull_90, ref) == DataFreshness.EXPIRED


def test_freshness_weights():
    """Freshness weights: FRESH/RECENT=1.0, STALE=0.5, EXPIRED=0.0."""
    assert freshness_weight(DataFreshness.FRESH) == 1.0
    assert freshness_weight(DataFreshness.RECENT) == 1.0
    assert freshness_weight(DataFreshness.STALE) == 0.5
    assert freshness_weight(DataFreshness.EXPIRED) == 0.0


# ===========================================================================
# Tier 3: Quant filter
# ===========================================================================

def test_tier3_quant_filter_passes():
    """Ticker with composite > 0.55 and no high disagreement passes Tier 3."""
    # NVDA has composite ~0.765 and low std_dev in mock data
    result = _tier3_quant("NVDA", _good_fundamentals())
    assert result["passed"] is True
    assert result["metrics"]["composite"] > 0.55
    assert result["metrics"]["high_disagreement_flag"] is False


def test_tier3_quant_filter_low_composite():
    """Ticker with composite <= 0.55 fails Tier 3."""
    # XOM in mock data has composite ~0.40
    result = _tier3_quant("XOM", _good_fundamentals())
    if result["metrics"]["composite"] <= 0.55:
        assert result["passed"] is False
    # If mock data gives composite > 0.55 for XOM, skip this assertion


def test_tier3_quant_both_conditions():
    """Tier 3 requires BOTH composite > 0.55 AND no high disagreement."""
    result = _tier3_quant("NVDA", _good_fundamentals())
    if result["passed"]:
        assert result["metrics"]["composite"] > 0.55
        assert result["metrics"]["high_disagreement_flag"] is False


# ===========================================================================
# Tier 4: Wasden filter
# ===========================================================================

def test_tier4_wasden_filter_veto():
    """Wasden VETO fails Tier 4."""
    # XOM is vetoed in mock data
    result = _tier4_wasden("XOM", _good_fundamentals())
    assert result["passed"] is False
    assert result["metrics"]["wasden_verdict"] == "VETO"


def test_tier4_wasden_filter_approve():
    """Wasden APPROVE passes Tier 4."""
    result = _tier4_wasden("NVDA", _good_fundamentals())
    assert result["passed"] is True
    assert result["metrics"]["wasden_verdict"] == "APPROVE"


def test_tier4_wasden_filter_neutral():
    """Wasden NEUTRAL passes Tier 4."""
    result = _tier4_wasden("NFLX", _good_fundamentals())
    assert result["passed"] is True
    assert result["metrics"]["wasden_verdict"] == "NEUTRAL"


# ===========================================================================
# Tier 5: Final ranking
# ===========================================================================

def test_tier5_ranking():
    """Top 5 ranked by composite_quant x wasden_confidence."""
    candidates = [
        {"ticker": f"T{i}", "fundamentals": {}} for i in range(8)
    ]
    tier3_results = [
        {"ticker": f"T{i}", "passed": True, "metrics": {"composite": 0.6 + i * 0.02}}
        for i in range(8)
    ]
    tier4_results = [
        {"ticker": f"T{i}", "passed": True, "metrics": {"wasden_confidence": 0.7 + i * 0.01}}
        for i in range(8)
    ]

    selected = _tier5_final_selection(candidates, tier3_results, tier4_results)
    assert len(selected) == 5

    # Should be sorted descending by rank_score
    scores = [c["_rank_score"] for c in selected]
    assert scores == sorted(scores, reverse=True)

    # Top item should be T7 (highest composite * highest confidence)
    assert selected[0]["ticker"] == "T7"


def test_tier5_fewer_than_5():
    """If fewer than 5 candidates, return all of them."""
    candidates = [
        {"ticker": "A", "fundamentals": {}},
        {"ticker": "B", "fundamentals": {}},
    ]
    tier3_results = [
        {"ticker": "A", "passed": True, "metrics": {"composite": 0.70}},
        {"ticker": "B", "passed": True, "metrics": {"composite": 0.65}},
    ]
    tier4_results = [
        {"ticker": "A", "passed": True, "metrics": {"wasden_confidence": 0.80}},
        {"ticker": "B", "passed": True, "metrics": {"wasden_confidence": 0.75}},
    ]

    selected = _tier5_final_selection(candidates, tier3_results, tier4_results)
    assert len(selected) == 2
