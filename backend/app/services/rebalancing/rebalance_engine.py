"""
Portfolio Rebalancing Engine for Wasden Watch.

Calculates portfolio drift from target weights and generates rebalance trades.
Respects PROTECTED risk constants (MAX_POSITION_PCT, MIN_CASH_RESERVE_PCT)
imported from the risk engine — never hardcoded.
"""

import logging
import math

from app.services.risk.constants import MAX_POSITION_PCT, MIN_CASH_RESERVE_PCT
from app.mock.generators import PILOT_TICKERS, BLOOMBERG_PRICES

logger = logging.getLogger("wasden_watch.rebalancing")

DRIFT_THRESHOLD = 0.02  # 2% drift before rebalancing


class RebalanceEngine:
    """Calculates portfolio drift and generates rebalance trades.

    Enforces:
    - No single position exceeds MAX_POSITION_PCT (12%)
    - Cash reserve stays above MIN_CASH_RESERVE_PCT (10%)
    - Only generates trades when drift exceeds DRIFT_THRESHOLD (2%)
    """

    def __init__(
        self,
        max_position_pct: float = MAX_POSITION_PCT,
        min_cash_reserve_pct: float = MIN_CASH_RESERVE_PCT,
        drift_threshold: float = DRIFT_THRESHOLD,
    ):
        self.max_position_pct = max_position_pct
        self.min_cash_reserve_pct = min_cash_reserve_pct
        self.drift_threshold = drift_threshold
        self._target_weights: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Target weights management
    # ------------------------------------------------------------------

    def set_target_weights(self, weights: dict[str, float]) -> None:
        """Set target allocation weights for the portfolio.

        Validates:
        - All values >= 0
        - Sum of all weights <= 1.0 (remainder is implicit cash)
        - No single weight exceeds max_position_pct

        Raises:
            ValueError: If any validation rule is violated.
        """
        if not weights:
            raise ValueError("Weights dict must not be empty")

        # Reject negative weights
        for ticker, weight in weights.items():
            if weight < 0:
                raise ValueError(
                    f"Weight for {ticker} is negative ({weight}). "
                    "All weights must be >= 0."
                )

        # Reject sum > 1.0
        total = sum(weights.values())
        if total > 1.0:
            raise ValueError(
                f"Total weight sum ({total:.4f}) exceeds 1.0. "
                "Remainder after weights is allocated to cash."
            )

        # Reject any single weight exceeding max_position_pct
        for ticker, weight in weights.items():
            if weight > self.max_position_pct:
                raise ValueError(
                    f"Weight for {ticker} ({weight:.4f}) exceeds "
                    f"MAX_POSITION_PCT ({self.max_position_pct:.4f}). "
                    "Risk constants are PROTECTED."
                )

        self._target_weights = dict(weights)
        logger.info(
            "Target weights set for %d tickers, total=%.4f, cash=%.4f",
            len(weights),
            total,
            1.0 - total,
        )

    def get_target_weights(self) -> dict[str, float]:
        """Return a copy of the current target weights."""
        return dict(self._target_weights)

    # ------------------------------------------------------------------
    # Drift calculation
    # ------------------------------------------------------------------

    def calculate_drift(
        self,
        current_positions: list[dict],
        portfolio_value: float,
    ) -> dict:
        """Calculate drift between current portfolio and target weights.

        Args:
            current_positions: List of position dicts, each with keys:
                {ticker, quantity, current_price, market_value}
            portfolio_value: Total portfolio value (positions + cash).

        Returns:
            Dict with portfolio_value, total_drift, and per-position drift details.
        """
        if portfolio_value <= 0:
            return {
                "portfolio_value": 0.0,
                "total_drift": 0.0,
                "positions": {},
            }

        # Build current weights from positions
        current_weights: dict[str, float] = {}
        for pos in current_positions:
            ticker = pos["ticker"]
            market_value = pos["market_value"]
            current_weights[ticker] = market_value / portfolio_value

        # Gather all tickers (from targets + current positions)
        all_tickers = set(self._target_weights.keys()) | set(current_weights.keys())

        positions_drift: dict[str, dict] = {}
        total_drift = 0.0

        for ticker in sorted(all_tickers):
            current_weight = current_weights.get(ticker, 0.0)
            target_weight = self._target_weights.get(ticker, 0.0)
            drift = current_weight - target_weight
            drift_pct = abs(drift)

            # Determine status
            if drift_pct < 0.001:  # <0.1% considered on-target
                status = "on_target"
            elif drift > 0:
                status = "over"
            else:
                status = "under"

            # Flag positions exceeding MAX_POSITION_PCT
            exceeds_max = current_weight > self.max_position_pct

            positions_drift[ticker] = {
                "current_weight": round(current_weight, 6),
                "target_weight": round(target_weight, 6),
                "drift": round(drift, 6),
                "drift_pct": round(drift_pct, 6),
                "status": status,
                "exceeds_max_position": exceeds_max,
            }

            total_drift += drift_pct

        return {
            "portfolio_value": portfolio_value,
            "total_drift": round(total_drift, 6),
            "positions": positions_drift,
        }

    # ------------------------------------------------------------------
    # Rebalance check
    # ------------------------------------------------------------------

    def check_rebalance_needed(
        self,
        current_positions: list[dict],
        portfolio_value: float,
    ) -> bool:
        """Check if any position has drifted beyond the threshold.

        Returns True if any single position's drift exceeds drift_threshold.
        """
        drift_result = self.calculate_drift(current_positions, portfolio_value)
        for _ticker, details in drift_result["positions"].items():
            if details["drift_pct"] > self.drift_threshold:
                return True
        return False

    # ------------------------------------------------------------------
    # Trade generation
    # ------------------------------------------------------------------

    def generate_rebalance_trades(
        self,
        current_positions: list[dict],
        portfolio_value: float,
    ) -> list[dict]:
        """Generate trades to rebalance portfolio to target weights.

        Only generates trades for positions with drift > drift_threshold.
        Respects MAX_POSITION_PCT cap and MIN_CASH_RESERVE_PCT reserve.

        Returns:
            List of trade dicts, each with:
                {ticker, side, quantity, estimated_value, current_weight,
                 target_weight, reason}
            Empty list if no rebalancing is needed.
        """
        if not self._target_weights:
            logger.warning("No target weights set — cannot generate trades")
            return []

        drift_result = self.calculate_drift(current_positions, portfolio_value)
        positions_drift = drift_result["positions"]

        # Build a price lookup from current positions
        price_lookup: dict[str, float] = {}
        for pos in current_positions:
            price_lookup[pos["ticker"]] = pos["current_price"]

        # For tickers in targets but not in positions, use BLOOMBERG_PRICES as fallback
        for ticker in self._target_weights:
            if ticker not in price_lookup and ticker in BLOOMBERG_PRICES:
                price_lookup[ticker] = BLOOMBERG_PRICES[ticker]

        # Calculate cash currently available
        total_position_value = sum(pos["market_value"] for pos in current_positions)
        available_cash = portfolio_value - total_position_value

        # Reserve minimum cash
        min_cash = portfolio_value * self.min_cash_reserve_pct
        deployable_cash = max(0.0, available_cash - min_cash)

        trades: list[dict] = []

        # First pass: generate sells (frees up cash)
        for ticker, details in positions_drift.items():
            if details["drift_pct"] <= self.drift_threshold:
                continue
            if details["status"] != "over":
                continue

            price = price_lookup.get(ticker)
            if not price or price <= 0:
                logger.warning("No price for %s — skipping sell trade", ticker)
                continue

            # Calculate value to sell
            sell_value = details["drift"] * portfolio_value
            sell_quantity = math.floor(sell_value / price)

            if sell_quantity <= 0:
                continue

            estimated_value = sell_quantity * price
            deployable_cash += estimated_value

            trades.append({
                "ticker": ticker,
                "side": "sell",
                "quantity": sell_quantity,
                "estimated_value": round(estimated_value, 2),
                "current_weight": details["current_weight"],
                "target_weight": details["target_weight"],
                "reason": f"Over-allocated by {details['drift_pct']:.2%}",
            })

        # Second pass: generate buys (limited by deployable cash)
        for ticker, details in positions_drift.items():
            if details["drift_pct"] <= self.drift_threshold:
                continue
            if details["status"] != "under":
                continue

            price = price_lookup.get(ticker)
            if not price or price <= 0:
                logger.warning("No price for %s — skipping buy trade", ticker)
                continue

            # Target buy value (negative drift means under-weight)
            target_buy_value = abs(details["drift"]) * portfolio_value

            # Cap buy to deployable cash
            buy_value = min(target_buy_value, deployable_cash)
            buy_quantity = math.floor(buy_value / price)

            if buy_quantity <= 0:
                continue

            estimated_value = buy_quantity * price
            deployable_cash -= estimated_value

            trades.append({
                "ticker": ticker,
                "side": "buy",
                "quantity": buy_quantity,
                "estimated_value": round(estimated_value, 2),
                "current_weight": details["current_weight"],
                "target_weight": details["target_weight"],
                "reason": f"Under-allocated by {details['drift_pct']:.2%}",
            })

        if trades:
            logger.info(
                "Generated %d rebalance trades (sells=%d, buys=%d)",
                len(trades),
                sum(1 for t in trades if t["side"] == "sell"),
                sum(1 for t in trades if t["side"] == "buy"),
            )
        else:
            logger.info("No rebalance trades needed — portfolio within drift threshold")

        return trades

    # ------------------------------------------------------------------
    # Mock data generation
    # ------------------------------------------------------------------

    def generate_mock_positions(
        self,
        portfolio_value: float = 100_000.0,
    ) -> list[dict]:
        """Generate mock positions with intentional drift from targets.

        Uses PILOT_TICKERS and BLOOMBERG_PRICES. Creates positions with
        weights that deliberately differ from target weights to simulate
        drift scenarios.

        Args:
            portfolio_value: Total portfolio value to size positions against.

        Returns:
            List of position dicts with {ticker, quantity, current_price, market_value}.
        """
        # If no target weights set, use equal-weight defaults for pilot tickers
        if not self._target_weights:
            equal_weight = min(
                1.0 / len(PILOT_TICKERS),
                self.max_position_pct,
            )
            targets = {t: equal_weight for t in PILOT_TICKERS}
        else:
            targets = self._target_weights

        # Drift multipliers to create intentional drift from targets
        # Some over-weighted, some under-weighted
        drift_multipliers = [1.25, 0.70, 1.15, 0.85, 1.30, 0.60]

        positions: list[dict] = []
        for i, ticker in enumerate(targets):
            if ticker not in BLOOMBERG_PRICES:
                continue

            price = BLOOMBERG_PRICES[ticker]
            target_weight = targets[ticker]

            # Apply drift multiplier (cycle through if more tickers than multipliers)
            multiplier = drift_multipliers[i % len(drift_multipliers)]
            drifted_weight = target_weight * multiplier

            # Calculate quantity from drifted weight
            target_value = portfolio_value * drifted_weight
            quantity = math.floor(target_value / price)

            if quantity <= 0:
                quantity = 1

            market_value = round(quantity * price, 2)

            positions.append({
                "ticker": ticker,
                "quantity": quantity,
                "current_price": price,
                "market_value": market_value,
            })

        return positions
