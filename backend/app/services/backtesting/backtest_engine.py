"""
Backtesting engine — runs historical simulations with slippage and commission modeling.

Uses the existing slippage model from app.services.risk.slippage to ensure
backtested results are consistent with live paper-trading execution costs.
"""

import logging
import math
import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.mock.generators import BLOOMBERG_PRICES
from app.services.risk.slippage import calculate_slippage

logger = logging.getLogger("wasden_watch.backtesting")


@dataclass
class BacktestResult:
    """Complete result of a backtest run."""

    equity_curve: list[dict] = field(default_factory=list)
    # Each entry: {date, equity, cash, invested}

    trades: list[dict] = field(default_factory=list)
    # Each entry: {id, ticker, side, entry_date, entry_price,
    #              exit_date, exit_price, quantity, pnl, pnl_pct}

    metrics: dict = field(default_factory=dict)
    # total_return, sharpe_ratio, sortino_ratio, max_drawdown,
    # win_rate, profit_factor, calmar_ratio, avg_trade_pnl,
    # max_consecutive_wins, max_consecutive_losses

    initial_capital: float = 0.0
    final_equity: float = 0.0
    total_trades: int = 0


class BacktestEngine:
    """Event-driven backtesting engine with slippage and commission support.

    Args:
        initial_capital: Starting portfolio value in dollars.
        slippage_model: Whether to apply the risk slippage model.
        commission_pct: Commission as a fraction of trade value (0.0 = no commission).
    """

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        slippage_model: bool = True,
        commission_pct: float = 0.0,
    ):
        self.initial_capital = initial_capital
        self.slippage_model = slippage_model
        self.commission_pct = commission_pct

    def run(
        self,
        ohlcv_data: list[dict],
        signals: list[dict],
    ) -> BacktestResult:
        """Run a backtest simulation over historical OHLCV data with trade signals.

        Args:
            ohlcv_data: List of {date, open, high, low, close, volume} dicts,
                        sorted by date ascending.
            signals: List of {date, action, ticker, quantity} dicts.
                     action is "buy" or "sell".

        Returns:
            BacktestResult with equity curve, trades, and performance metrics.
        """
        cash = self.initial_capital
        positions: dict[str, dict] = {}  # ticker -> {quantity, avg_price}
        equity_curve: list[dict] = []
        completed_trades: list[dict] = []
        open_trade_entries: dict[str, dict] = {}  # ticker -> {entry_date, entry_price, quantity}
        trade_counter = 0

        # Index signals by date for O(1) lookup
        signal_by_date: dict[str, list[dict]] = {}
        for sig in signals:
            sig_date = sig["date"]
            if sig_date not in signal_by_date:
                signal_by_date[sig_date] = []
            signal_by_date[sig_date].append(sig)

        for bar in ohlcv_data:
            bar_date = bar["date"]
            price = bar["close"]
            volume = bar["volume"]

            # Process any signals for this date
            day_signals = signal_by_date.get(bar_date, [])
            for sig in day_signals:
                action = sig["action"]
                ticker = sig["ticker"]
                quantity = sig["quantity"]

                if action == "buy":
                    # Calculate costs
                    order_value = quantity * price
                    slippage = 0.0
                    if self.slippage_model:
                        slippage = calculate_slippage(quantity, price, volume)
                    commission = order_value * self.commission_pct
                    total_cost = order_value + slippage + commission

                    if total_cost > cash:
                        logger.warning(
                            f"Insufficient cash for BUY {quantity} {ticker} @ ${price:.2f}. "
                            f"Need ${total_cost:.2f}, have ${cash:.2f}. Skipping."
                        )
                        continue

                    cash -= total_cost
                    effective_price = (order_value + slippage) / quantity

                    if ticker in positions:
                        # Average into existing position
                        existing = positions[ticker]
                        total_qty = existing["quantity"] + quantity
                        existing["avg_price"] = (
                            (existing["avg_price"] * existing["quantity"])
                            + (effective_price * quantity)
                        ) / total_qty
                        existing["quantity"] = total_qty
                    else:
                        positions[ticker] = {
                            "quantity": quantity,
                            "avg_price": effective_price,
                        }

                    open_trade_entries[ticker] = {
                        "entry_date": bar_date,
                        "entry_price": effective_price,
                        "quantity": quantity,
                    }

                    logger.info(
                        f"BUY {quantity} {ticker} @ ${price:.2f} "
                        f"(effective ${effective_price:.2f}, slippage ${slippage:.2f})"
                    )

                elif action == "sell":
                    if ticker not in positions or positions[ticker]["quantity"] <= 0:
                        logger.warning(
                            f"No position in {ticker} to sell. Skipping."
                        )
                        continue

                    pos = positions[ticker]
                    sell_qty = min(quantity, pos["quantity"])
                    order_value = sell_qty * price

                    slippage = 0.0
                    if self.slippage_model:
                        slippage = calculate_slippage(sell_qty, price, volume)
                    commission = order_value * self.commission_pct

                    proceeds = order_value - slippage - commission
                    cash += proceeds
                    effective_sell_price = proceeds / sell_qty

                    # Record completed trade
                    entry_info = open_trade_entries.get(ticker, {})
                    entry_price = entry_info.get("entry_price", pos["avg_price"])
                    entry_date = entry_info.get("entry_date", bar_date)

                    pnl = (effective_sell_price - entry_price) * sell_qty
                    pnl_pct = (
                        (effective_sell_price - entry_price) / entry_price
                        if entry_price > 0
                        else 0.0
                    )

                    trade_counter += 1
                    completed_trades.append({
                        "id": trade_counter,
                        "ticker": ticker,
                        "side": "round_trip",
                        "entry_date": entry_date,
                        "entry_price": round(entry_price, 4),
                        "exit_date": bar_date,
                        "exit_price": round(effective_sell_price, 4),
                        "quantity": sell_qty,
                        "pnl": round(pnl, 2),
                        "pnl_pct": round(pnl_pct, 6),
                    })

                    pos["quantity"] -= sell_qty
                    if pos["quantity"] <= 0:
                        del positions[ticker]
                        if ticker in open_trade_entries:
                            del open_trade_entries[ticker]

                    logger.info(
                        f"SELL {sell_qty} {ticker} @ ${price:.2f} "
                        f"(effective ${effective_sell_price:.2f}), PnL=${pnl:.2f}"
                    )

            # Calculate end-of-day equity
            invested = sum(
                pos["quantity"] * price
                for pos in positions.values()
            )
            equity = cash + invested

            equity_curve.append({
                "date": bar_date,
                "equity": round(equity, 2),
                "cash": round(cash, 2),
                "invested": round(invested, 2),
            })

        # Final equity
        final_equity = equity_curve[-1]["equity"] if equity_curve else self.initial_capital

        metrics = self._calculate_metrics(equity_curve, completed_trades)

        return BacktestResult(
            equity_curve=equity_curve,
            trades=completed_trades,
            metrics=metrics,
            initial_capital=self.initial_capital,
            final_equity=final_equity,
            total_trades=len(completed_trades),
        )

    def _calculate_metrics(
        self,
        equity_curve: list[dict],
        trades: list[dict],
    ) -> dict:
        """Calculate performance metrics from equity curve and trade list.

        Returns dict with: total_return, sharpe_ratio, sortino_ratio,
        max_drawdown, win_rate, profit_factor, calmar_ratio,
        avg_trade_pnl, max_consecutive_wins, max_consecutive_losses.
        """
        # --- Total return ---
        if not equity_curve:
            return self._empty_metrics()

        initial = equity_curve[0]["equity"]
        final = equity_curve[-1]["equity"]
        total_return = (final - initial) / initial if initial > 0 else 0.0

        # --- Daily returns ---
        daily_returns: list[float] = []
        for i in range(1, len(equity_curve)):
            prev_eq = equity_curve[i - 1]["equity"]
            curr_eq = equity_curve[i]["equity"]
            if prev_eq > 0:
                daily_returns.append((curr_eq - prev_eq) / prev_eq)
            else:
                daily_returns.append(0.0)

        # --- Sharpe ratio (annualized) ---
        sharpe_ratio = 0.0
        if daily_returns:
            mean_ret = sum(daily_returns) / len(daily_returns)
            std_ret = _std(daily_returns)
            if std_ret > 0:
                sharpe_ratio = (mean_ret / std_ret) * math.sqrt(252)

        # --- Sortino ratio (annualized) ---
        sortino_ratio = 0.0
        if daily_returns:
            mean_ret = sum(daily_returns) / len(daily_returns)
            downside = [r for r in daily_returns if r < 0]
            downside_std = _std(downside) if downside else 0.0
            if downside_std > 0:
                sortino_ratio = (mean_ret / downside_std) * math.sqrt(252)

        # --- Max drawdown ---
        max_drawdown = 0.0
        peak = equity_curve[0]["equity"]
        for point in equity_curve:
            eq = point["equity"]
            if eq > peak:
                peak = eq
            drawdown = (peak - eq) / peak if peak > 0 else 0.0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # --- Trade-based metrics ---
        total_trades = len(trades)
        winning_trades = [t for t in trades if t["pnl"] > 0]
        losing_trades = [t for t in trades if t["pnl"] <= 0]

        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0

        winning_pnl = sum(t["pnl"] for t in winning_trades)
        losing_pnl = sum(t["pnl"] for t in losing_trades)
        profit_factor = (
            winning_pnl / abs(losing_pnl)
            if losing_pnl != 0
            else (float("inf") if winning_pnl > 0 else 0.0)
        )

        avg_trade_pnl = (
            sum(t["pnl"] for t in trades) / total_trades
            if total_trades > 0
            else 0.0
        )

        # --- Calmar ratio ---
        # Annualized return / |max drawdown|
        num_days = len(equity_curve)
        annualized_return = (
            ((1 + total_return) ** (252 / num_days) - 1)
            if num_days > 0 and total_return > -1
            else 0.0
        )
        calmar_ratio = (
            annualized_return / abs(max_drawdown)
            if max_drawdown > 0
            else 0.0
        )

        # --- Consecutive wins / losses ---
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_wins = 0
        current_losses = 0
        for t in trades:
            if t["pnl"] > 0:
                current_wins += 1
                current_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_losses)

        return {
            "total_return": round(total_return, 6),
            "sharpe_ratio": round(sharpe_ratio, 4),
            "sortino_ratio": round(sortino_ratio, 4),
            "max_drawdown": round(max_drawdown, 6),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else None,
            "calmar_ratio": round(calmar_ratio, 4),
            "avg_trade_pnl": round(avg_trade_pnl, 2),
            "max_consecutive_wins": max_consecutive_wins,
            "max_consecutive_losses": max_consecutive_losses,
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "annualized_return": round(annualized_return, 6),
        }

    def _empty_metrics(self) -> dict:
        """Return zeroed-out metrics when no data is available."""
        return {
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "calmar_ratio": 0.0,
            "avg_trade_pnl": 0.0,
            "max_consecutive_wins": 0,
            "max_consecutive_losses": 0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "annualized_return": 0.0,
        }

    @staticmethod
    def generate_mock_ohlcv(
        ticker: str,
        num_days: int = 252,
        seed: int = 42,
    ) -> list[dict]:
        """Generate synthetic OHLCV data for backtesting.

        Uses a geometric random walk with slight upward drift starting from
        the Bloomberg snapshot price for the given ticker.

        Args:
            ticker: Stock ticker (must be in BLOOMBERG_PRICES).
            num_days: Number of trading days to generate.
            seed: Random seed for deterministic output.

        Returns:
            List of {date, open, high, low, close, volume} dicts sorted by date.
        """
        rng = random.Random(seed)
        base_price = BLOOMBERG_PRICES.get(ticker, 100.0)
        current_date = date(2025, 1, 2)  # First trading day of 2025

        bars: list[dict] = []
        price = base_price

        for _ in range(num_days):
            # Skip weekends
            while current_date.weekday() >= 5:
                current_date = current_date + timedelta(days=1)

            # Random walk with slight upward drift (~8% annualized)
            daily_drift = 0.08 / 252
            daily_vol = 0.02  # ~32% annualized vol
            daily_return = daily_drift + rng.gauss(0, daily_vol)

            open_price = price
            close_price = price * (1 + daily_return)
            close_price = max(close_price, 0.01)  # Floor at 1 cent

            # High/low within the day
            intraday_range = abs(close_price - open_price) + price * rng.uniform(0.002, 0.015)
            high_price = max(open_price, close_price) + intraday_range * rng.uniform(0.1, 0.5)
            low_price = min(open_price, close_price) - intraday_range * rng.uniform(0.1, 0.5)
            low_price = max(low_price, 0.01)

            # Volume: base volume with random variation
            base_volume = int(base_price * 50_000)  # Rough heuristic
            volume = int(base_volume * rng.uniform(0.5, 2.0))

            bars.append({
                "date": current_date.isoformat(),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": volume,
            })

            price = close_price
            current_date = current_date + timedelta(days=1)

        return bars

    @staticmethod
    def generate_mock_signals(
        ticker: str,
        ohlcv_data: list[dict],
        seed: int = 42,
    ) -> list[dict]:
        """Generate buy/sell signals using SMA crossover strategy (20/50).

        Buys when SMA20 crosses above SMA50, sells when it crosses below.
        Uses a fixed quantity of 100 shares per trade.

        Args:
            ticker: Stock ticker for the signals.
            ohlcv_data: OHLCV data (output of generate_mock_ohlcv).
            seed: Random seed (unused, signals are fully deterministic from SMA).

        Returns:
            List of {date, action, ticker, quantity} dicts.
        """
        if len(ohlcv_data) < 50:
            return []

        closes = [bar["close"] for bar in ohlcv_data]
        signals: list[dict] = []
        in_position = False
        quantity = 100

        for i in range(50, len(ohlcv_data)):
            sma20 = sum(closes[i - 20:i]) / 20
            sma50 = sum(closes[i - 50:i]) / 50

            prev_sma20 = sum(closes[i - 21:i - 1]) / 20
            prev_sma50 = sum(closes[i - 51:i - 1]) / 50

            # Buy signal: SMA20 crosses above SMA50
            if not in_position and prev_sma20 <= prev_sma50 and sma20 > sma50:
                signals.append({
                    "date": ohlcv_data[i]["date"],
                    "action": "buy",
                    "ticker": ticker,
                    "quantity": quantity,
                })
                in_position = True

            # Sell signal: SMA20 crosses below SMA50
            elif in_position and prev_sma20 >= prev_sma50 and sma20 < sma50:
                signals.append({
                    "date": ohlcv_data[i]["date"],
                    "action": "sell",
                    "ticker": ticker,
                    "quantity": quantity,
                })
                in_position = False

        return signals


def _std(values: list[float]) -> float:
    """Population standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)
