"""
Slippage model — per PROJECT_STANDARDS_v2.md Section 7.

Orders > 1% ADV: model 0.1% slippage per 1% of ADV.
Paper results without slippage are misleadingly optimistic.
"""

import logging

from app.services.risk.constants import (
    SLIPPAGE_ADV_THRESHOLD,
    SLIPPAGE_PER_ADV_PCT,
)

logger = logging.getLogger("wasden_watch.slippage")


def calculate_slippage(
    order_quantity: int,
    price: float,
    avg_daily_volume: int,
) -> float:
    """Calculate estimated slippage for an order.

    Args:
        order_quantity: Number of shares in the order.
        price: Current share price.
        avg_daily_volume: Average daily volume (shares).

    Returns:
        Estimated slippage as a dollar amount.
        Returns 0.0 if order is below ADV threshold.
    """
    if avg_daily_volume <= 0:
        logger.warning("ADV is zero or negative, cannot compute slippage")
        return 0.0

    adv_fraction = order_quantity / avg_daily_volume

    if adv_fraction <= SLIPPAGE_ADV_THRESHOLD:
        return 0.0

    # Slippage: 0.1% per 1% of ADV
    # adv_fraction is in decimal (0.02 = 2% of ADV)
    # SLIPPAGE_PER_ADV_PCT = 0.001 (0.1% per 1%)
    slippage_pct = adv_fraction * (SLIPPAGE_PER_ADV_PCT / 0.01)
    order_value = order_quantity * price
    slippage_dollars = order_value * slippage_pct

    logger.info(
        f"Slippage estimate: {order_quantity} shares @ ${price:.2f}, "
        f"ADV={avg_daily_volume:,}, fraction={adv_fraction:.4f}, "
        f"slippage={slippage_pct:.4%} = ${slippage_dollars:.2f}"
    )

    return round(slippage_dollars, 2)
