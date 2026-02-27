"""Unit tests for the backtesting engine.

All tests use mock data. No database, no API calls.
Validates engine mechanics, metric calculations, slippage integration,
and deterministic reproducibility.
"""

import os

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

from app.services.backtesting.backtest_engine import (  # noqa: E402
    BacktestEngine,
    BacktestResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _engine(**kwargs) -> BacktestEngine:
    """Create a BacktestEngine with sensible test defaults."""
    defaults = dict(initial_capital=100_000.0, slippage_model=True, commission_pct=0.0)
    defaults.update(kwargs)
    return BacktestEngine(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_backtest_mock_ohlcv():
    """generate_mock_ohlcv returns 252 bars with required keys."""
    ohlcv = BacktestEngine.generate_mock_ohlcv("NVDA", num_days=252, seed=42)
    assert len(ohlcv) == 252
    required_keys = {"date", "open", "high", "low", "close", "volume"}
    for bar in ohlcv:
        assert required_keys.issubset(bar.keys()), f"Missing keys in bar: {bar.keys()}"
        assert bar["high"] >= bar["low"]
        assert bar["volume"] > 0


def test_backtest_metrics_calculation():
    """Metrics are computed and have correct types."""
    engine = _engine()
    ohlcv = engine.generate_mock_ohlcv("AAPL", num_days=252, seed=42)
    signals = engine.generate_mock_signals("AAPL", ohlcv, seed=42)
    result = engine.run(ohlcv, signals)

    assert isinstance(result, BacktestResult)
    m = result.metrics
    assert isinstance(m["sharpe_ratio"], float)
    assert isinstance(m["sortino_ratio"], float)
    assert isinstance(m["max_drawdown"], float)
    assert isinstance(m["total_return"], float)
    assert isinstance(m["win_rate"], float)
    assert isinstance(m["avg_trade_pnl"], float)
    assert isinstance(m["max_consecutive_wins"], int)
    assert isinstance(m["max_consecutive_losses"], int)
    # Drawdown is non-negative
    assert m["max_drawdown"] >= 0.0


def test_backtest_slippage_integration():
    """Slippage model integrates with risk slippage module.

    With high volume and small quantity, slippage should be 0 because
    the order is below the ADV threshold (SLIPPAGE_ADV_THRESHOLD = 0.01).
    """
    engine = _engine(slippage_model=True)
    # Create minimal OHLCV with very high volume so slippage = 0
    ohlcv = [
        {"date": "2025-01-02", "open": 100, "high": 105, "low": 99, "close": 100, "volume": 10_000_000},
        {"date": "2025-01-03", "open": 100, "high": 106, "low": 99, "close": 102, "volume": 10_000_000},
        {"date": "2025-01-06", "open": 102, "high": 107, "low": 101, "close": 105, "volume": 10_000_000},
    ]
    signals = [
        {"date": "2025-01-02", "action": "buy", "ticker": "TEST", "quantity": 10},
        {"date": "2025-01-06", "action": "sell", "ticker": "TEST", "quantity": 10},
    ]
    result = engine.run(ohlcv, signals)

    # With 10 shares out of 10M volume, ADV fraction = 0.000001 < 0.01 threshold
    # So slippage should be 0 and entry price should equal close price exactly
    assert result.total_trades == 1
    trade = result.trades[0]
    # Entry at close of day 1 = 100, exit at close of day 3 = 105
    assert trade["entry_price"] == 100.0
    assert trade["exit_price"] == 105.0
    assert trade["pnl"] == 50.0  # (105 - 100) * 10


def test_equity_curve_monotonic_dates():
    """Dates in the equity curve are strictly increasing."""
    engine = _engine()
    ohlcv = engine.generate_mock_ohlcv("NVDA", num_days=100, seed=42)
    signals = engine.generate_mock_signals("NVDA", ohlcv, seed=42)
    result = engine.run(ohlcv, signals)

    dates = [point["date"] for point in result.equity_curve]
    for i in range(1, len(dates)):
        assert dates[i] > dates[i - 1], (
            f"Dates not strictly increasing at index {i}: {dates[i-1]} >= {dates[i]}"
        )


def test_backtest_no_lookahead_bias():
    """Signals only reference dates that exist in the OHLCV data (no future dates)."""
    engine = _engine()
    ohlcv = engine.generate_mock_ohlcv("PYPL", num_days=252, seed=42)
    signals = engine.generate_mock_signals("PYPL", ohlcv, seed=42)

    ohlcv_dates = set(bar["date"] for bar in ohlcv)
    for sig in signals:
        assert sig["date"] in ohlcv_dates, (
            f"Signal date {sig['date']} not found in OHLCV data — possible lookahead bias"
        )

    # Additionally: signals should only start at index 50+ (need 50 bars for SMA50)
    if signals:
        first_signal_date = signals[0]["date"]
        ohlcv_date_list = [bar["date"] for bar in ohlcv]
        first_signal_idx = ohlcv_date_list.index(first_signal_date)
        assert first_signal_idx >= 50, (
            f"First signal at index {first_signal_idx}, but SMA50 requires 50 bars of history"
        )


def test_zero_trades_handled():
    """Empty signals produce valid result with 0 trades and computed metrics."""
    engine = _engine()
    ohlcv = engine.generate_mock_ohlcv("XOM", num_days=100, seed=42)
    signals = []  # No signals at all
    result = engine.run(ohlcv, signals)

    assert result.total_trades == 0
    assert result.trades == []
    assert result.metrics["total_trades"] == 0
    assert result.metrics["win_rate"] == 0.0
    assert result.metrics["avg_trade_pnl"] == 0.0
    # Equity curve should still exist (one entry per bar)
    assert len(result.equity_curve) == 100
    # With no trades, equity should remain at initial capital
    assert result.equity_curve[0]["equity"] == 100_000.0
    assert result.final_equity == 100_000.0


def test_initial_capital_preserved():
    """First equity curve entry matches initial capital."""
    engine = _engine(initial_capital=50_000.0)
    ohlcv = engine.generate_mock_ohlcv("TSM", num_days=60, seed=42)
    # No signals on first day, so first equity should be initial capital
    result = engine.run(ohlcv, [])

    assert result.equity_curve[0]["equity"] == 50_000.0
    assert result.initial_capital == 50_000.0


def test_backtest_deterministic():
    """Same seed produces identical results across two runs."""
    engine = _engine()

    ohlcv_1 = engine.generate_mock_ohlcv("NFLX", num_days=252, seed=99)
    signals_1 = engine.generate_mock_signals("NFLX", ohlcv_1, seed=99)
    result_1 = engine.run(ohlcv_1, signals_1)

    ohlcv_2 = engine.generate_mock_ohlcv("NFLX", num_days=252, seed=99)
    signals_2 = engine.generate_mock_signals("NFLX", ohlcv_2, seed=99)
    result_2 = engine.run(ohlcv_2, signals_2)

    assert ohlcv_1 == ohlcv_2
    assert signals_1 == signals_2
    assert result_1.equity_curve == result_2.equity_curve
    assert result_1.trades == result_2.trades
    assert result_1.metrics == result_2.metrics
    assert result_1.final_equity == result_2.final_equity


def test_generate_mock_signals():
    """generate_mock_signals returns list of dicts with required keys."""
    ohlcv = BacktestEngine.generate_mock_ohlcv("AAPL", num_days=252, seed=42)
    signals = BacktestEngine.generate_mock_signals("AAPL", ohlcv, seed=42)

    assert isinstance(signals, list)
    required_keys = {"date", "action", "ticker", "quantity"}
    for sig in signals:
        assert required_keys.issubset(sig.keys()), f"Missing keys in signal: {sig.keys()}"
        assert sig["action"] in ("buy", "sell"), f"Invalid action: {sig['action']}"
        assert sig["ticker"] == "AAPL"
        assert isinstance(sig["quantity"], int)
        assert sig["quantity"] > 0

    # Signals should alternate: first buy, then sell, then buy, etc.
    if signals:
        assert signals[0]["action"] == "buy", "First signal should be a buy"
        for i in range(1, len(signals)):
            if signals[i - 1]["action"] == "buy":
                assert signals[i]["action"] == "sell", (
                    f"Expected sell after buy at index {i}"
                )
            else:
                assert signals[i]["action"] == "buy", (
                    f"Expected buy after sell at index {i}"
                )
