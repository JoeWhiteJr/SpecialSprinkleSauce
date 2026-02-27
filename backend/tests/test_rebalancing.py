"""Unit tests for the portfolio rebalancing engine.

All tests use mock portfolio data. No database, no API calls.
Verifies drift calculation, trade generation, and risk constraint enforcement.
"""

import os

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

import math  # noqa: E402

from app.services.rebalancing.rebalance_engine import (  # noqa: E402
    RebalanceEngine,
)
from app.services.risk.constants import (  # noqa: E402
    MAX_POSITION_PCT,
    MIN_CASH_RESERVE_PCT,
)
from app.mock.generators import PILOT_TICKERS, BLOOMBERG_PRICES  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine_with_targets(weights: dict[str, float] | None = None) -> RebalanceEngine:
    """Create engine with target weights pre-configured."""
    engine = RebalanceEngine()
    if weights is None:
        # Default equal-weight for pilot tickers
        equal_weight = min(1.0 / len(PILOT_TICKERS), MAX_POSITION_PCT)
        weights = {t: equal_weight for t in PILOT_TICKERS}
    engine.set_target_weights(weights)
    return engine


def _make_positions_at_targets(
    engine: RebalanceEngine,
    portfolio_value: float = 100_000.0,
) -> list[dict]:
    """Create positions that exactly match target weights (no drift)."""
    targets = engine.get_target_weights()
    positions = []
    for ticker, weight in targets.items():
        price = BLOOMBERG_PRICES.get(ticker, 100.0)
        target_value = portfolio_value * weight
        quantity = math.floor(target_value / price)
        market_value = round(quantity * price, 2)
        positions.append({
            "ticker": ticker,
            "quantity": quantity,
            "current_price": price,
            "market_value": market_value,
        })
    return positions


def _make_drifted_positions(
    engine: RebalanceEngine,
    portfolio_value: float = 100_000.0,
) -> list[dict]:
    """Create positions with significant drift from targets."""
    targets = engine.get_target_weights()
    tickers = list(targets.keys())
    multipliers = [1.40, 0.50, 1.35, 0.55, 1.45, 0.45]
    positions = []
    for i, ticker in enumerate(tickers):
        price = BLOOMBERG_PRICES.get(ticker, 100.0)
        weight = targets[ticker]
        drifted_weight = weight * multipliers[i % len(multipliers)]
        target_value = portfolio_value * drifted_weight
        quantity = max(1, math.floor(target_value / price))
        market_value = round(quantity * price, 2)
        positions.append({
            "ticker": ticker,
            "quantity": quantity,
            "current_price": price,
            "market_value": market_value,
        })
    return positions


# ---------------------------------------------------------------------------
# Test: drift calculation
# ---------------------------------------------------------------------------

def test_drift_calculation():
    """Drift percentages are correctly computed for each position."""
    engine = _make_engine_with_targets({"NVDA": 0.10, "AAPL": 0.10})
    positions = [
        {"ticker": "NVDA", "quantity": 63, "current_price": 189.82, "market_value": 63 * 189.82},
        {"ticker": "AAPL", "quantity": 42, "current_price": 264.58, "market_value": 42 * 264.58},
    ]
    portfolio_value = 100_000.0
    result = engine.calculate_drift(positions, portfolio_value)

    assert "positions" in result
    assert "NVDA" in result["positions"]
    assert "AAPL" in result["positions"]

    # NVDA: market_value = 63 * 189.82 = 11958.66 => weight ~0.1196
    nvda = result["positions"]["NVDA"]
    assert nvda["target_weight"] == 0.10
    assert nvda["current_weight"] > 0.10  # over-allocated
    assert nvda["status"] == "over"

    # AAPL: market_value = 42 * 264.58 = 11112.36 => weight ~0.1111
    aapl = result["positions"]["AAPL"]
    assert aapl["target_weight"] == 0.10
    assert aapl["current_weight"] > 0.10
    assert aapl["drift_pct"] >= 0


# ---------------------------------------------------------------------------
# Test: drift threshold — no trades when drift < 2%
# ---------------------------------------------------------------------------

def test_drift_threshold():
    """No trades generated when all positions drift less than 2%."""
    engine = _make_engine_with_targets({"NVDA": 0.10, "AAPL": 0.10})

    # Create positions very close to targets (drift < 2%)
    # NVDA target: 10% of 100k = $10,000, at $189.82/share = 52.68 shares
    # Use 53 shares => 53 * 189.82 = $10,060.46 => weight = 10.06% => drift = 0.06%
    positions = [
        {"ticker": "NVDA", "quantity": 53, "current_price": 189.82, "market_value": 53 * 189.82},
        {"ticker": "AAPL", "quantity": 38, "current_price": 264.58, "market_value": 38 * 264.58},
    ]
    portfolio_value = 100_000.0

    trades = engine.generate_rebalance_trades(positions, portfolio_value)
    assert trades == [], f"Expected no trades for <2% drift, got {len(trades)}"


# ---------------------------------------------------------------------------
# Test: rebalance trades generated with correct sides
# ---------------------------------------------------------------------------

def test_rebalance_trades_generated():
    """Buy/sell sides are correct: over-weight -> sell, under-weight -> buy."""
    engine = _make_engine_with_targets({"NVDA": 0.10, "AAPL": 0.10})

    # NVDA heavily over-allocated, AAPL heavily under-allocated
    positions = [
        {"ticker": "NVDA", "quantity": 80, "current_price": 189.82, "market_value": 80 * 189.82},
        {"ticker": "AAPL", "quantity": 10, "current_price": 264.58, "market_value": 10 * 264.58},
    ]
    portfolio_value = 100_000.0

    trades = engine.generate_rebalance_trades(positions, portfolio_value)
    assert len(trades) > 0

    nvda_trades = [t for t in trades if t["ticker"] == "NVDA"]
    aapl_trades = [t for t in trades if t["ticker"] == "AAPL"]

    # NVDA is over-weight => should have sell
    assert len(nvda_trades) == 1
    assert nvda_trades[0]["side"] == "sell"

    # AAPL is under-weight => should have buy
    assert len(aapl_trades) == 1
    assert aapl_trades[0]["side"] == "buy"


# ---------------------------------------------------------------------------
# Test: MAX_POSITION_PCT cap
# ---------------------------------------------------------------------------

def test_max_position_cap():
    """Rejects target weights exceeding MAX_POSITION_PCT (0.12)."""
    engine = RebalanceEngine()

    try:
        engine.set_target_weights({"NVDA": 0.15})
        assert False, "Should have raised ValueError for weight > MAX_POSITION_PCT"
    except ValueError as exc:
        assert "MAX_POSITION_PCT" in str(exc)
        assert "NVDA" in str(exc)

    # Verify weight at exactly MAX_POSITION_PCT is accepted
    engine.set_target_weights({"NVDA": MAX_POSITION_PCT})
    assert engine.get_target_weights()["NVDA"] == MAX_POSITION_PCT


# ---------------------------------------------------------------------------
# Test: rebalance with empty portfolio (all buys)
# ---------------------------------------------------------------------------

def test_rebalance_with_empty_portfolio():
    """Empty portfolio generates only buy trades."""
    engine = _make_engine_with_targets({"NVDA": 0.10, "AAPL": 0.10})
    positions: list[dict] = []
    portfolio_value = 100_000.0

    trades = engine.generate_rebalance_trades(positions, portfolio_value)

    # All trades should be buys
    assert len(trades) > 0
    for trade in trades:
        assert trade["side"] == "buy", f"Expected buy, got {trade['side']} for {trade['ticker']}"


# ---------------------------------------------------------------------------
# Test: cash reserve preservation
# ---------------------------------------------------------------------------

def test_rebalance_preserves_cash_reserve():
    """Total buy value does not exceed deployable cash (respects MIN_CASH_RESERVE_PCT)."""
    engine = _make_engine_with_targets({"NVDA": 0.10, "AAPL": 0.10})
    positions: list[dict] = []
    portfolio_value = 100_000.0

    trades = engine.generate_rebalance_trades(positions, portfolio_value)

    total_buy_value = sum(t["estimated_value"] for t in trades if t["side"] == "buy")
    min_cash = portfolio_value * MIN_CASH_RESERVE_PCT
    max_deployable = portfolio_value - min_cash

    assert total_buy_value <= max_deployable + 0.01, (
        f"Buy total (${total_buy_value:.2f}) exceeds max deployable "
        f"(${max_deployable:.2f}) — cash reserve violated"
    )


# ---------------------------------------------------------------------------
# Test: target weights sum validation
# ---------------------------------------------------------------------------

def test_target_weights_sum():
    """Rejects weights that sum to more than 1.0."""
    engine = RebalanceEngine()

    try:
        engine.set_target_weights({
            "NVDA": 0.10,
            "AAPL": 0.10,
            "MSFT": 0.10,
            "AMZN": 0.10,
            "TSLA": 0.10,
            "AMD": 0.10,
            "TSM": 0.10,
            "XOM": 0.10,
            "PYPL": 0.10,
            "NFLX": 0.11,  # Total = 1.01
        })
        assert False, "Should have raised ValueError for sum > 1.0"
    except ValueError as exc:
        assert "1.0" in str(exc)


# ---------------------------------------------------------------------------
# Test: negative weight validation
# ---------------------------------------------------------------------------

def test_target_weights_validation():
    """Rejects negative weights."""
    engine = RebalanceEngine()

    try:
        engine.set_target_weights({"NVDA": -0.05})
        assert False, "Should have raised ValueError for negative weight"
    except ValueError as exc:
        assert "negative" in str(exc).lower()


# ---------------------------------------------------------------------------
# Test: generate_mock_positions returns valid dicts
# ---------------------------------------------------------------------------

def test_generate_mock_positions():
    """Mock positions contain required keys with valid values."""
    engine = _make_engine_with_targets()
    positions = engine.generate_mock_positions(portfolio_value=100_000.0)

    assert len(positions) > 0
    required_keys = {"ticker", "quantity", "current_price", "market_value"}
    for pos in positions:
        assert required_keys.issubset(pos.keys()), f"Missing keys in position: {pos}"
        assert pos["quantity"] > 0
        assert pos["current_price"] > 0
        assert pos["market_value"] > 0
        assert pos["ticker"] in BLOOMBERG_PRICES


# ---------------------------------------------------------------------------
# Test: on-target positions produce no trades
# ---------------------------------------------------------------------------

def test_on_target_no_trades():
    """Positions matching targets (within threshold) produce no trades."""
    engine = _make_engine_with_targets({"NVDA": 0.10, "AAPL": 0.10})
    positions = _make_positions_at_targets(engine, portfolio_value=100_000.0)
    portfolio_value = 100_000.0

    trades = engine.generate_rebalance_trades(positions, portfolio_value)

    # Positions built at target weights should have minimal drift => no trades
    assert trades == [], (
        f"Expected no trades for on-target positions, got {len(trades)}: "
        f"{[t['ticker'] + '/' + t['side'] for t in trades]}"
    )
