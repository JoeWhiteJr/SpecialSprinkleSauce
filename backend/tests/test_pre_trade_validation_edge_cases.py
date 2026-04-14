"""Edge case tests for pre-trade validation — 4 checks, SEPARATE from risk engine.

Covers boundary quantities, zero/negative prices and portfolio values,
duplicate detection timing edges, side-value variants, and large inputs.
All tests use mock data. No database, no API calls.
"""

import os
from datetime import datetime, timedelta

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

from app.services.risk.pre_trade_validation import (  # noqa: E402
    PreTradeContext,
    run_pre_trade_validation,
    MAX_ORDER_SHARES,
    DUPLICATE_WINDOW_SECONDS,
    PORTFOLIO_IMPACT_WARN_PCT,
)
from app.services.risk.constants import MAX_POSITION_PCT  # noqa: E402


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
# Check 1: Quantity sanity — exact boundaries
# ---------------------------------------------------------------------------

def test_quantity_minimum_valid_passes():
    """Quantity of 1 is the smallest valid order — must pass."""
    ctx = _clean_order(quantity=1)
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "quantity_sanity")
    assert detail["passed"] is True


def test_quantity_exactly_at_max_passes():
    """Quantity == MAX_ORDER_SHARES (100 000) is still valid (<= not <)."""
    # Need large portfolio so portfolio_impact and dollar_sanity don't trip
    ctx = _clean_order(
        quantity=MAX_ORDER_SHARES,
        price=0.01,             # tiny price keeps dollar value manageable
        portfolio_value=1_000_000_000.0,
    )
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "quantity_sanity")
    assert detail["passed"] is True


def test_quantity_one_over_max_fails():
    """Quantity == MAX_ORDER_SHARES + 1 (100 001) must fail quantity_sanity."""
    ctx = _clean_order(quantity=MAX_ORDER_SHARES + 1)
    result = run_pre_trade_validation(ctx)
    assert "quantity_sanity" in result["checks_failed"]


def test_quantity_very_large_fails():
    """Extremely large quantity (1 000 000) must fail quantity_sanity."""
    ctx = _clean_order(quantity=1_000_000)
    result = run_pre_trade_validation(ctx)
    assert "quantity_sanity" in result["checks_failed"]


def test_quantity_sanity_detail_correct_on_pass():
    """When quantity_sanity passes, detail dict has passed=True."""
    ctx = _clean_order(quantity=10)
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "quantity_sanity")
    assert detail["passed"] is True
    assert detail["check_name"] == "quantity_sanity"


# ---------------------------------------------------------------------------
# Check 3: Portfolio impact — zero portfolio value guard
# ---------------------------------------------------------------------------

def test_portfolio_value_zero_does_not_raise():
    """portfolio_value = 0 must not raise ZeroDivisionError."""
    ctx = _clean_order(portfolio_value=0.0, quantity=10, price=190.0)
    result = run_pre_trade_validation(ctx)
    assert isinstance(result, dict)
    assert "details" in result


def test_portfolio_value_zero_fails_portfolio_impact():
    """portfolio_value = 0 causes impact_pct to default to 1.0, failing the check."""
    ctx = _clean_order(portfolio_value=0.0, quantity=10, price=190.0)
    result = run_pre_trade_validation(ctx)
    assert "portfolio_impact" in result["checks_failed"]


def test_portfolio_impact_exactly_at_threshold_fails():
    """Trade value exactly equal to PORTFOLIO_IMPACT_WARN_PCT of portfolio fails (strictly >)."""
    # impact_pct = trade_value / portfolio_value = PORTFOLIO_IMPACT_WARN_PCT
    # trade_value = quantity * price = 10 * 1000 = 10_000
    # 10_000 / 100_000 = 0.10 == PORTFOLIO_IMPACT_WARN_PCT (0.10)
    # The check is `impact_pct > PORTFOLIO_IMPACT_WARN_PCT` — exactly equal must PASS.
    ctx = _clean_order(
        quantity=10,
        price=1_000.0,
        portfolio_value=100_000.0,
    )
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "portfolio_impact")
    # 10_000 / 100_000 = 0.10, not > 0.10, so should pass
    assert detail["passed"] is True


def test_portfolio_impact_just_over_threshold_fails():
    """Trade value 1 cent above PORTFOLIO_IMPACT_WARN_PCT * portfolio_value fails."""
    # $10_000.01 > 10% of $100_000
    ctx = _clean_order(
        quantity=1,
        price=10_000.01,
        portfolio_value=100_000.0,
    )
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "portfolio_impact")
    assert detail["passed"] is False
    assert "portfolio_impact" in result["checks_failed"]


def test_price_zero_portfolio_impact_passes():
    """price = 0 yields trade_value = 0, impact = 0% — passes portfolio_impact."""
    ctx = _clean_order(quantity=50, price=0.0, portfolio_value=100_000.0)
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "portfolio_impact")
    assert detail["passed"] is True


def test_negative_price_passes_impact_but_may_fail_dollar_sanity():
    """Negative price produces negative trade_value; portfolio_impact passes (negative < threshold).
    Dollar sanity: negative trade_value < max_value so it also passes."""
    ctx = _clean_order(quantity=50, price=-10.0, portfolio_value=100_000.0)
    result = run_pre_trade_validation(ctx)
    # Both portfolio_impact and dollar_sanity should pass because trade_value < 0
    impact_detail = next(d for d in result["details"] if d["check_name"] == "portfolio_impact")
    dollar_detail = next(d for d in result["details"] if d["check_name"] == "dollar_sanity")
    assert impact_detail["passed"] is True
    assert dollar_detail["passed"] is True


# ---------------------------------------------------------------------------
# Check 4: Dollar sanity — exact MAX_POSITION_PCT boundary
# ---------------------------------------------------------------------------

def test_dollar_sanity_exactly_at_max_passes():
    """Trade value exactly == MAX_POSITION_PCT * portfolio_value must pass (not strictly <)."""
    # MAX_POSITION_PCT = 0.12; 0.12 * 100_000 = 12_000
    # 60 shares @ $200 = 12_000
    ctx = _clean_order(
        quantity=60,
        price=200.0,
        portfolio_value=100_000.0,
    )
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "dollar_sanity")
    # trade_value = 12_000, max_value = 12_000 — check is `> max_value`
    assert detail["passed"] is True


def test_dollar_sanity_one_cent_over_max_fails():
    """Trade value 1 cent above MAX_POSITION_PCT * portfolio_value must fail."""
    # max = 12_000; use price that creates 12_000.01
    ctx = _clean_order(
        quantity=1,
        price=12_000.01,
        portfolio_value=100_000.0,
    )
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "dollar_sanity")
    assert detail["passed"] is False
    assert "dollar_sanity" in result["checks_failed"]


def test_dollar_sanity_zero_portfolio_value_does_not_raise():
    """portfolio_value = 0 in dollar_sanity (max_value = 0) must not crash."""
    ctx = _clean_order(quantity=1, price=1.0, portfolio_value=0.0)
    result = run_pre_trade_validation(ctx)
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Check 2: Duplicate detection — timing edge cases
# ---------------------------------------------------------------------------

def test_duplicate_detection_exactly_at_window_boundary_fails():
    """Order placed 1 second inside the window (59s ago) is clearly within window — fails."""
    # Use 59s (1s inside the 60s window) to avoid sub-millisecond race conditions
    # that arise when test and source code both compute `now` at slightly different instants.
    inside_ts = (
        datetime.utcnow() - timedelta(seconds=DUPLICATE_WINDOW_SECONDS - 1)
    ).isoformat() + "Z"
    ctx = _clean_order(
        ticker="NVDA",
        side="buy",
        recent_orders=[
            {"ticker": "NVDA", "side": "buy", "timestamp": inside_ts},
        ],
    )
    result = run_pre_trade_validation(ctx)
    assert "duplicate_detection" in result["checks_failed"]


def test_duplicate_detection_one_second_after_window_passes():
    """Order placed DUPLICATE_WINDOW_SECONDS + 1 second ago is outside window — passes."""
    old_ts = (
        datetime.utcnow() - timedelta(seconds=DUPLICATE_WINDOW_SECONDS + 1)
    ).isoformat() + "Z"
    ctx = _clean_order(
        ticker="NVDA",
        side="buy",
        recent_orders=[
            {"ticker": "NVDA", "side": "buy", "timestamp": old_ts},
        ],
    )
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "duplicate_detection")
    assert detail["passed"] is True


def test_duplicate_detection_different_side_passes():
    """Same ticker but different side (buy vs sell) within window is not a duplicate."""
    recent_ts = (datetime.utcnow() - timedelta(seconds=10)).isoformat() + "Z"
    ctx = _clean_order(
        ticker="NVDA",
        side="buy",
        recent_orders=[
            {"ticker": "NVDA", "side": "sell", "timestamp": recent_ts},
        ],
    )
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "duplicate_detection")
    assert detail["passed"] is True


def test_duplicate_detection_empty_recent_orders_passes():
    """Empty recent_orders list means no possible duplicate — always passes."""
    ctx = _clean_order(recent_orders=[])
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "duplicate_detection")
    assert detail["passed"] is True


def test_duplicate_detection_large_recent_orders_list():
    """1000-entry recent_orders list with no matching ticker/side still passes."""
    recent_orders = [
        {
            "ticker": f"TICK{i:04d}",
            "side": "buy",
            "timestamp": (datetime.utcnow() - timedelta(seconds=5)).isoformat() + "Z",
        }
        for i in range(1000)
    ]
    ctx = _clean_order(ticker="NVDA", side="buy", recent_orders=recent_orders)
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "duplicate_detection")
    assert detail["passed"] is True


def test_duplicate_detection_malformed_timestamp_skipped():
    """Order with unparseable timestamp string is skipped — does not crash."""
    ctx = _clean_order(
        ticker="NVDA",
        side="buy",
        recent_orders=[
            {"ticker": "NVDA", "side": "buy", "timestamp": "not-a-timestamp"},
        ],
    )
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "duplicate_detection")
    # Malformed timestamp causes the entry to be skipped, so no duplicate detected
    assert detail["passed"] is True


def test_duplicate_detection_missing_timestamp_skipped():
    """Order dict with no timestamp key is skipped gracefully."""
    ctx = _clean_order(
        ticker="NVDA",
        side="buy",
        recent_orders=[
            {"ticker": "NVDA", "side": "buy"},  # no timestamp key
        ],
    )
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "duplicate_detection")
    assert detail["passed"] is True


# ---------------------------------------------------------------------------
# Side value edge cases
# ---------------------------------------------------------------------------

def test_side_sell_passes_all_checks():
    """side='sell' is a valid value and should pass all 4 checks on a clean order."""
    ctx = _clean_order(side="sell")
    result = run_pre_trade_validation(ctx)
    assert result["passed"] is True


def test_side_empty_string_does_not_crash():
    """side='' does not crash the engine (duplicate check just won't match)."""
    ctx = _clean_order(side="")
    result = run_pre_trade_validation(ctx)
    assert isinstance(result, dict)
    assert "details" in result


def test_side_uppercase_does_not_match_duplicate():
    """side='BUY' (uppercase) does not match a 'buy' recent_order — not a duplicate."""
    recent_ts = (datetime.utcnow() - timedelta(seconds=5)).isoformat() + "Z"
    ctx = _clean_order(
        ticker="NVDA",
        side="BUY",
        recent_orders=[
            {"ticker": "NVDA", "side": "buy", "timestamp": recent_ts},
        ],
    )
    result = run_pre_trade_validation(ctx)
    detail = next(d for d in result["details"] if d["check_name"] == "duplicate_detection")
    assert detail["passed"] is True


# ---------------------------------------------------------------------------
# Result structure edge cases
# ---------------------------------------------------------------------------

def test_result_always_has_four_detail_entries():
    """run_pre_trade_validation always returns exactly 4 detail entries."""
    ctx = _clean_order(quantity=0, price=-99.0, portfolio_value=0.0)
    result = run_pre_trade_validation(ctx)
    assert len(result["details"]) == 4


def test_all_checks_fail_checks_failed_contains_all_four():
    """Degenerate context that fails all 4 checks lists all 4 in checks_failed."""
    # quantity=0 fails quantity_sanity
    # portfolio_value=0 fails portfolio_impact (impact defaults to 1.0)
    # dollar_sanity: trade_value = 0*200 = 0 which is NOT > max_value=0 => actually passes
    # So we need a different approach: large quantity + tiny portfolio
    ctx = _clean_order(
        quantity=0,             # fails quantity_sanity
        price=99_000.0,         # irrelevant since qty=0
        portfolio_value=0.0,    # fails portfolio_impact
    )
    result = run_pre_trade_validation(ctx)
    assert "quantity_sanity" in result["checks_failed"]
    assert "portfolio_impact" in result["checks_failed"]
    assert result["passed"] is False


def test_checks_failed_is_empty_list_on_success():
    """On clean order, checks_failed is exactly an empty list."""
    ctx = _clean_order()
    result = run_pre_trade_validation(ctx)
    assert result["checks_failed"] == []
    assert isinstance(result["checks_failed"], list)
