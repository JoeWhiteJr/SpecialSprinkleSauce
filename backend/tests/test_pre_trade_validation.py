"""Unit tests for pre-trade validation — 4 checks, SEPARATE from risk engine.

All tests use mock data. No database, no API calls.
"""

import inspect
import os
from datetime import datetime, timedelta

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

from app.services.risk.pre_trade_validation import (  # noqa: E402
    PreTradeContext,
    run_pre_trade_validation,
    MAX_ORDER_SHARES,
    DUPLICATE_WINDOW_SECONDS,
    PRE_TRADE_CHECKS,
)


# ---------------------------------------------------------------------------
# Helper: build a clean PreTradeContext that passes all 4 checks
# ---------------------------------------------------------------------------

def _clean_order(**overrides) -> PreTradeContext:
    """Return a PreTradeContext that passes all 4 validation checks."""
    defaults = dict(
        ticker="NVDA",
        side="buy",
        quantity=50,
        price=190.0,
        portfolio_value=100_000.0,
        recent_orders=[],
    )
    defaults.update(overrides)
    return PreTradeContext(**defaults)


# ---------------------------------------------------------------------------
# Test: quantity sanity check
# ---------------------------------------------------------------------------

def test_quantity_sanity_check_zero():
    """Zero quantity fails."""
    ctx = _clean_order(quantity=0)
    result = run_pre_trade_validation(ctx)
    assert "quantity_sanity" in result["checks_failed"]


def test_quantity_sanity_check_negative():
    """Negative quantity fails."""
    ctx = _clean_order(quantity=-10)
    result = run_pre_trade_validation(ctx)
    assert "quantity_sanity" in result["checks_failed"]


def test_quantity_sanity_check_over_max():
    """Quantity exceeding MAX_ORDER_SHARES fails."""
    ctx = _clean_order(quantity=MAX_ORDER_SHARES + 1)
    result = run_pre_trade_validation(ctx)
    assert "quantity_sanity" in result["checks_failed"]


def test_quantity_sanity_check_passes():
    """Valid quantity passes."""
    ctx = _clean_order(quantity=100)
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "quantity_sanity")
    assert detail["passed"] is True


# ---------------------------------------------------------------------------
# Test: duplicate detection
# ---------------------------------------------------------------------------

def test_duplicate_detection():
    """Same ticker + side within the duplicate window fails."""
    recent_ts = (datetime.utcnow() - timedelta(seconds=10)).isoformat() + "Z"
    ctx = _clean_order(
        ticker="NVDA",
        side="buy",
        recent_orders=[
            {"ticker": "NVDA", "side": "buy", "timestamp": recent_ts},
        ],
    )
    result = run_pre_trade_validation(ctx)
    assert "duplicate_detection" in result["checks_failed"]


def test_duplicate_detection_different_ticker():
    """Different ticker within window passes."""
    recent_ts = (datetime.utcnow() - timedelta(seconds=10)).isoformat() + "Z"
    ctx = _clean_order(
        ticker="NVDA",
        side="buy",
        recent_orders=[
            {"ticker": "AAPL", "side": "buy", "timestamp": recent_ts},
        ],
    )
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "duplicate_detection")
    assert detail["passed"] is True


def test_duplicate_detection_outside_window():
    """Same ticker but outside the window passes."""
    old_ts = (datetime.utcnow() - timedelta(seconds=DUPLICATE_WINDOW_SECONDS + 30)).isoformat() + "Z"
    ctx = _clean_order(
        recent_orders=[
            {"ticker": "NVDA", "side": "buy", "timestamp": old_ts},
        ],
    )
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "duplicate_detection")
    assert detail["passed"] is True


# ---------------------------------------------------------------------------
# Test: portfolio impact check
# ---------------------------------------------------------------------------

def test_portfolio_impact_check():
    """Trade value exceeding PORTFOLIO_IMPACT_WARN_PCT of portfolio fails."""
    # 200 shares @ $600 = $120k > 10% of $100k
    ctx = _clean_order(quantity=200, price=600.0, portfolio_value=100_000.0)
    result = run_pre_trade_validation(ctx)
    assert "portfolio_impact" in result["checks_failed"]


def test_portfolio_impact_check_passes():
    """Trade value within impact threshold passes."""
    # 10 shares @ $190 = $1,900 = 1.9% of $100k
    ctx = _clean_order(quantity=10, price=190.0, portfolio_value=100_000.0)
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "portfolio_impact")
    assert detail["passed"] is True


# ---------------------------------------------------------------------------
# Test: dollar sanity check
# ---------------------------------------------------------------------------

def test_dollar_sanity_check():
    """Order value exceeding MAX_POSITION_PCT x portfolio_value fails."""
    # MAX_POSITION_PCT = 0.12 => max = $12,000 on $100k
    # 100 shares @ $150 = $15,000 > $12,000
    ctx = _clean_order(quantity=100, price=150.0, portfolio_value=100_000.0)
    result = run_pre_trade_validation(ctx)
    assert "dollar_sanity" in result["checks_failed"]


def test_dollar_sanity_check_passes():
    """Order value within max position size passes."""
    # 50 shares @ $190 = $9,500 < $12,000
    ctx = _clean_order(quantity=50, price=190.0, portfolio_value=100_000.0)
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "dollar_sanity")
    assert detail["passed"] is True


# ---------------------------------------------------------------------------
# Test: all validations pass
# ---------------------------------------------------------------------------

def test_all_validations_pass():
    """Clean order passes all 4 validation checks."""
    ctx = _clean_order()
    result = run_pre_trade_validation(ctx)
    assert result["passed"] is True
    assert result["checks_failed"] == []
    assert len(result["details"]) == 4
    for detail in result["details"]:
        assert detail["passed"] is True, f"{detail['check_name']} unexpectedly failed"


def test_four_checks_executed():
    """Exactly 4 checks are registered."""
    assert len(PRE_TRADE_CHECKS) == 4


# ---------------------------------------------------------------------------
# Test: separation enforcement
# ---------------------------------------------------------------------------

def test_zero_imports_from_risk_engine():
    """pre_trade_validation.py has zero imports from risk_engine."""
    from app.services.risk import pre_trade_validation
    source = inspect.getsource(pre_trade_validation)

    # Check only import lines (not comments or docstrings mentioning risk_engine)
    import_lines = [
        line.strip() for line in source.split("\n")
        if line.strip().startswith(("import ", "from "))
    ]
    import_text = "\n".join(import_lines)
    assert "risk_engine" not in import_text, (
        "pre_trade_validation must not import from risk_engine"
    )


def test_pre_trade_is_separate_module():
    """pre_trade_validation.py is a different file from risk_engine.py."""
    from app.services.risk import pre_trade_validation
    from app.services.risk import risk_engine

    ptv_file = inspect.getfile(pre_trade_validation)
    re_file = inspect.getfile(risk_engine)
    assert ptv_file != re_file, (
        "pre_trade_validation and risk_engine must be separate modules"
    )
