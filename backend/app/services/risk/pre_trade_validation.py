"""
Pre-Trade Validation — SEPARATE from risk engine. Never merge.

4 validation checks:
1. Order quantity sanity (> 0, < max shares)
2. Duplicate detection (same ticker within 60 seconds)
3. Portfolio impact
4. Dollar sanity (< MAX_POSITION_PCT × portfolio_value)

ZERO imports from risk_engine.py — enforced separation.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.services.risk.constants import MAX_POSITION_PCT

logger = logging.getLogger("wasden_watch.pre_trade_validation")

# Maximum single order shares (sanity cap)
MAX_ORDER_SHARES = 100_000

# Duplicate detection window
DUPLICATE_WINDOW_SECONDS = 60

# Portfolio impact threshold (warn if single trade > this % of portfolio)
PORTFOLIO_IMPACT_WARN_PCT = 0.10


@dataclass
class PreTradeContext:
    """All inputs needed for pre-trade validation. SEPARATE from RiskContext."""
    ticker: str
    side: str  # "buy" or "sell"
    quantity: int
    price: float
    portfolio_value: float
    # Recent orders for duplicate detection: list of {ticker, side, timestamp}
    recent_orders: list[dict] = field(default_factory=list)


@dataclass
class PreTradeCheckDetail:
    """Result of a single pre-trade validation check."""
    check_name: str
    passed: bool
    detail: str


def _check_quantity_sanity(ctx: PreTradeContext) -> PreTradeCheckDetail:
    """Check 1: Order quantity > 0 and < MAX_ORDER_SHARES."""
    if ctx.quantity <= 0:
        return PreTradeCheckDetail(
            check_name="quantity_sanity",
            passed=False,
            detail=f"Quantity {ctx.quantity} must be > 0",
        )
    if ctx.quantity > MAX_ORDER_SHARES:
        return PreTradeCheckDetail(
            check_name="quantity_sanity",
            passed=False,
            detail=f"Quantity {ctx.quantity} exceeds max {MAX_ORDER_SHARES}",
        )
    return PreTradeCheckDetail(
        check_name="quantity_sanity",
        passed=True,
        detail=f"Quantity {ctx.quantity} within bounds",
    )


def _check_duplicate_order(ctx: PreTradeContext) -> PreTradeCheckDetail:
    """Check 2: No duplicate order for same ticker within 60 seconds."""
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=DUPLICATE_WINDOW_SECONDS)

    for order in ctx.recent_orders:
        if order.get("ticker") != ctx.ticker:
            continue
        if order.get("side") != ctx.side:
            continue

        order_ts = order.get("timestamp")
        if isinstance(order_ts, str):
            try:
                order_ts = datetime.fromisoformat(order_ts.rstrip("Z"))
            except ValueError:
                continue

        if isinstance(order_ts, datetime) and order_ts >= cutoff:
            return PreTradeCheckDetail(
                check_name="duplicate_detection",
                passed=False,
                detail=(
                    f"Duplicate {ctx.side} order for {ctx.ticker} "
                    f"within {DUPLICATE_WINDOW_SECONDS}s window"
                ),
            )

    return PreTradeCheckDetail(
        check_name="duplicate_detection",
        passed=True,
        detail="No duplicate orders detected",
    )


def _check_portfolio_impact(ctx: PreTradeContext) -> PreTradeCheckDetail:
    """Check 3: Single trade portfolio impact."""
    trade_value = ctx.quantity * ctx.price
    impact_pct = trade_value / ctx.portfolio_value if ctx.portfolio_value > 0 else 1.0

    if impact_pct > PORTFOLIO_IMPACT_WARN_PCT:
        return PreTradeCheckDetail(
            check_name="portfolio_impact",
            passed=False,
            detail=(
                f"Trade value ${trade_value:,.2f} is {impact_pct:.1%} "
                f"of portfolio (threshold {PORTFOLIO_IMPACT_WARN_PCT:.1%})"
            ),
        )
    return PreTradeCheckDetail(
        check_name="portfolio_impact",
        passed=True,
        detail=f"Trade value ${trade_value:,.2f} ({impact_pct:.1%} of portfolio)",
    )


def _check_dollar_sanity(ctx: PreTradeContext) -> PreTradeCheckDetail:
    """Check 4: Order dollar value < MAX_POSITION_PCT × portfolio_value."""
    trade_value = ctx.quantity * ctx.price
    max_value = MAX_POSITION_PCT * ctx.portfolio_value

    if trade_value > max_value:
        return PreTradeCheckDetail(
            check_name="dollar_sanity",
            passed=False,
            detail=(
                f"Trade ${trade_value:,.2f} exceeds max position "
                f"${max_value:,.2f} ({MAX_POSITION_PCT:.1%} of portfolio)"
            ),
        )
    return PreTradeCheckDetail(
        check_name="dollar_sanity",
        passed=True,
        detail=f"Trade ${trade_value:,.2f} within max ${max_value:,.2f}",
    )


PRE_TRADE_CHECKS = [
    _check_quantity_sanity,
    _check_duplicate_order,
    _check_portfolio_impact,
    _check_dollar_sanity,
]


def run_pre_trade_validation(ctx: PreTradeContext) -> dict:
    """Run all 4 pre-trade validation checks.

    Returns dict compatible with PreTradeValidation schema:
        - passed: bool
        - checks_failed: list[str]
        - details: list[dict]
    """
    details = []
    checks_failed = []

    for check_fn in PRE_TRADE_CHECKS:
        result = check_fn(ctx)
        details.append({
            "check_name": result.check_name,
            "passed": result.passed,
            "detail": result.detail,
        })
        if not result.passed:
            checks_failed.append(result.check_name)
            logger.warning(
                f"Pre-trade validation FAILED for {ctx.ticker}: "
                f"{result.check_name} — {result.detail}"
            )

    all_passed = len(checks_failed) == 0

    if all_passed:
        logger.info(f"Pre-trade validation PASSED for {ctx.ticker}")

    return {
        "passed": all_passed,
        "checks_failed": checks_failed,
        "details": details,
    }
