"""Performance tracker for paper trading — records trades, calculates returns and risk metrics.

Stores trades in memory (list of dicts). Persistence to Supabase deferred to DB migration phase.
Metric formulas follow PROJECT_STANDARDS_v2.md Sections 7-8 and ensemble_method_adr.md.
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger("wasden_watch.monitoring.performance")


@dataclass
class TradeRecord:
    """A single completed trade."""

    ticker: str
    action: str  # BUY or SELL
    entry_price: float
    exit_price: float
    position_size: float  # fraction of portfolio
    timestamp: str  # ISO-8601
    pnl: float = 0.0
    pnl_pct: float = 0.0

    def __post_init__(self) -> None:
        if self.entry_price > 0:
            if self.action == "BUY":
                self.pnl_pct = (self.exit_price - self.entry_price) / self.entry_price
            else:  # SELL (short)
                self.pnl_pct = (self.entry_price - self.exit_price) / self.entry_price
            self.pnl = self.pnl_pct * self.position_size


@dataclass
class DecisionRecord:
    """A pipeline decision (any action, not just completed trades)."""

    ticker: str
    action: str  # BUY, SELL, HOLD, BLOCKED, ESCALATED
    timestamp: str
    pipeline_run_id: str = ""
    quant_composite: float = 0.0
    quant_std_dev: float = 0.0
    wasden_verdict: str = ""
    wasden_confidence: float = 0.0
    recommended_position_size: float = 0.0
    sector: str = ""
    jury_spawned: bool = False
    jury_escalated: bool = False
    debate_outcome: str = ""


class PerformanceTracker:
    """Tracks paper-trading performance: trades, returns, and risk-adjusted metrics.

    All trades stored in memory. Will be persisted to Supabase after DB migration.
    """

    def __init__(self, risk_free_rate: float = 0.05, initial_capital: float = 100_000.0):
        """Initialize the performance tracker.

        Args:
            risk_free_rate: Annualized risk-free rate for Sharpe/Sortino (default 5%).
            initial_capital: Starting portfolio value in USD.
        """
        self._trades: list[TradeRecord] = []
        self._decisions: list[DecisionRecord] = []
        self._risk_free_rate = risk_free_rate
        self._initial_capital = initial_capital
        logger.info(
            "PerformanceTracker initialized: initial_capital=%.2f, risk_free_rate=%.4f",
            initial_capital,
            risk_free_rate,
        )

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_trade(
        self,
        ticker: str,
        action: str,
        entry_price: float,
        exit_price: float,
        position_size: float,
        timestamp: Optional[str] = None,
    ) -> TradeRecord:
        """Log a completed trade (entry filled and exited).

        Args:
            ticker: Stock ticker (e.g. "AAPL US Equity").
            action: "BUY" or "SELL".
            entry_price: Fill price at entry.
            exit_price: Fill price at exit.
            position_size: Fraction of portfolio allocated (0.0-1.0).
            timestamp: ISO-8601 string; defaults to now.

        Returns:
            The created TradeRecord.
        """
        ts = timestamp or (datetime.utcnow().isoformat() + "Z")
        trade = TradeRecord(
            ticker=ticker,
            action=action,
            entry_price=entry_price,
            exit_price=exit_price,
            position_size=position_size,
            timestamp=ts,
        )
        self._trades.append(trade)
        logger.info(
            "Trade recorded: %s %s entry=%.2f exit=%.2f pnl_pct=%.4f",
            action,
            ticker,
            entry_price,
            exit_price,
            trade.pnl_pct,
        )
        return trade

    def record_decision(self, journal_entry: dict) -> DecisionRecord:
        """Log a pipeline decision from a decision journal dict.

        Args:
            journal_entry: Dict matching the DecisionJournalEntry schema
                           from PROJECT_STANDARDS_v2.md Section 4.

        Returns:
            The created DecisionRecord.
        """
        final = journal_entry.get("final_decision", {})
        quant = journal_entry.get("quant_scores", {})
        wasden = journal_entry.get("wasden_verdict", {})
        jury = journal_entry.get("jury", {})
        debate = journal_entry.get("debate_result", {})

        record = DecisionRecord(
            ticker=journal_entry.get("ticker", ""),
            action=final.get("action", "HOLD"),
            timestamp=journal_entry.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            pipeline_run_id=journal_entry.get("pipeline_run_id", ""),
            quant_composite=quant.get("composite", 0.0),
            quant_std_dev=quant.get("std_dev", 0.0),
            wasden_verdict=wasden.get("verdict", ""),
            wasden_confidence=wasden.get("confidence", 0.0),
            recommended_position_size=final.get("recommended_position_size", 0.0),
            jury_spawned=jury.get("spawned", False),
            jury_escalated=jury.get("escalated_to_human", False),
            debate_outcome=debate.get("outcome", ""),
        )
        self._decisions.append(record)
        logger.info(
            "Decision recorded: %s %s (pipeline_run_id=%s)",
            record.action,
            record.ticker,
            record.pipeline_run_id,
        )
        return record

    # ------------------------------------------------------------------
    # Return calculations
    # ------------------------------------------------------------------

    def calculate_returns(self) -> dict:
        """Calculate comprehensive return and risk metrics.

        Returns:
            Dict with total_return, annualized_return, sharpe_ratio, sortino_ratio,
            max_drawdown, max_drawdown_duration, win_rate, loss_rate, profit_factor,
            average_win, average_loss, best_trade, worst_trade, trade_count.
        """
        if not self._trades:
            return self._empty_returns()

        pnls = [t.pnl_pct for t in self._trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        # Cumulative return (compounded)
        cumulative = 1.0
        for p in pnls:
            cumulative *= (1.0 + p)
        total_return = cumulative - 1.0

        # Annualized return
        annualized_return = self._annualize_return(total_return, len(pnls))

        # Sharpe ratio (annualized)
        sharpe = self._sharpe_ratio(pnls)

        # Sortino ratio (annualized, downside deviation only)
        sortino = self._sortino_ratio(pnls)

        # Drawdown
        max_dd, max_dd_duration = self._max_drawdown(pnls)

        # Win/loss rates
        win_rate = len(wins) / len(pnls) if pnls else 0.0
        loss_rate = len(losses) / len(pnls) if pnls else 0.0

        # Profit factor
        gross_profit = sum(wins) if wins else 0.0
        gross_loss = abs(sum(losses)) if losses else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0

        # Averages
        average_win = (sum(wins) / len(wins)) if wins else 0.0
        average_loss = (sum(losses) / len(losses)) if losses else 0.0

        # Best and worst
        best_trade = max(pnls)
        worst_trade = min(pnls)

        return {
            "total_return": round(total_return, 6),
            "annualized_return": round(annualized_return, 6),
            "sharpe_ratio": round(sharpe, 4),
            "sortino_ratio": round(sortino, 4),
            "max_drawdown": round(max_dd, 6),
            "max_drawdown_duration": max_dd_duration,
            "win_rate": round(win_rate, 4),
            "loss_rate": round(loss_rate, 4),
            "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else "inf",
            "average_win": round(average_win, 6),
            "average_loss": round(average_loss, 6),
            "best_trade": round(best_trade, 6),
            "worst_trade": round(worst_trade, 6),
            "trade_count": len(pnls),
        }

    def vs_benchmark(self, benchmark_returns: list[float]) -> dict:
        """Compare portfolio returns against a benchmark (e.g. SPY).

        Args:
            benchmark_returns: List of benchmark period returns aligned with trade returns.

        Returns:
            Dict with alpha, beta, tracking_error, information_ratio.
        """
        portfolio_returns = [t.pnl_pct for t in self._trades]

        if not portfolio_returns or not benchmark_returns:
            return {"alpha": 0.0, "beta": 0.0, "tracking_error": 0.0, "information_ratio": 0.0}

        # Align lengths (use shorter of the two)
        n = min(len(portfolio_returns), len(benchmark_returns))
        port = portfolio_returns[:n]
        bench = benchmark_returns[:n]

        # Beta = Cov(port, bench) / Var(bench)
        port_mean = sum(port) / n
        bench_mean = sum(bench) / n

        cov = sum((p - port_mean) * (b - bench_mean) for p, b in zip(port, bench)) / n
        bench_var = sum((b - bench_mean) ** 2 for b in bench) / n

        beta = (cov / bench_var) if bench_var > 0 else 0.0

        # Alpha = port_mean - beta * bench_mean (single-period)
        alpha = port_mean - beta * bench_mean

        # Tracking error = std(port - bench)
        excess = [p - b for p, b in zip(port, bench)]
        excess_mean = sum(excess) / n
        tracking_error_var = sum((e - excess_mean) ** 2 for e in excess) / n if n > 1 else 0.0
        tracking_error = math.sqrt(tracking_error_var)

        # Information ratio = excess_mean / tracking_error
        information_ratio = (excess_mean / tracking_error) if tracking_error > 0 else 0.0

        return {
            "alpha": round(alpha, 6),
            "beta": round(beta, 4),
            "tracking_error": round(tracking_error, 6),
            "information_ratio": round(information_ratio, 4),
        }

    def rolling_metrics(self, window_days: int = 30) -> dict:
        """Calculate rolling metrics over a trailing window.

        Args:
            window_days: Number of most recent trades to include in the window.

        Returns:
            Dict with rolling_sharpe, rolling_win_rate, rolling_drawdown.
        """
        if not self._trades:
            return {"rolling_sharpe": 0.0, "rolling_win_rate": 0.0, "rolling_drawdown": 0.0}

        # Use last N trades as the window
        window_trades = self._trades[-window_days:]
        pnls = [t.pnl_pct for t in window_trades]

        rolling_sharpe = self._sharpe_ratio(pnls)

        wins = [p for p in pnls if p > 0]
        rolling_win_rate = len(wins) / len(pnls) if pnls else 0.0

        rolling_dd, _ = self._max_drawdown(pnls)

        return {
            "rolling_sharpe": round(rolling_sharpe, 4),
            "rolling_win_rate": round(rolling_win_rate, 4),
            "rolling_drawdown": round(rolling_dd, 6),
            "window_size": len(window_trades),
        }

    def summary_report(self) -> dict:
        """Generate a formatted summary suitable for dashboard display.

        Returns:
            Dict with returns, benchmark (empty until benchmark data provided),
            rolling metrics, trade statistics, and recent trades.
        """
        returns = self.calculate_returns()
        rolling = self.rolling_metrics()

        # Recent trades (last 10)
        recent = []
        for t in self._trades[-10:]:
            recent.append({
                "ticker": t.ticker,
                "action": t.action,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "pnl_pct": round(t.pnl_pct, 6),
                "position_size": t.position_size,
                "timestamp": t.timestamp,
            })

        # Decision distribution
        action_counts: dict[str, int] = {}
        for d in self._decisions:
            action_counts[d.action] = action_counts.get(d.action, 0) + 1

        return {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "initial_capital": self._initial_capital,
            "risk_free_rate": self._risk_free_rate,
            "returns": returns,
            "rolling_30d": rolling,
            "decision_distribution": action_counts,
            "total_decisions": len(self._decisions),
            "recent_trades": recent,
        }

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def trades(self) -> list[TradeRecord]:
        """All recorded trades."""
        return list(self._trades)

    @property
    def decisions(self) -> list[DecisionRecord]:
        """All recorded decisions."""
        return list(self._decisions)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sharpe_ratio(self, returns: list[float]) -> float:
        """Annualized Sharpe ratio.

        Sharpe = (mean_excess_return / std_dev) * sqrt(252)
        """
        if len(returns) < 2:
            return 0.0

        daily_rf = self._risk_free_rate / 252.0
        excess = [r - daily_rf for r in returns]
        mean_excess = sum(excess) / len(excess)
        variance = sum((r - mean_excess) ** 2 for r in excess) / (len(excess) - 1)
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return 0.0

        return (mean_excess / std_dev) * math.sqrt(252)

    def _sortino_ratio(self, returns: list[float]) -> float:
        """Annualized Sortino ratio (uses downside deviation only)."""
        if len(returns) < 2:
            return 0.0

        daily_rf = self._risk_free_rate / 252.0
        excess = [r - daily_rf for r in returns]
        mean_excess = sum(excess) / len(excess)

        # Downside deviation: only negative excess returns
        downside_sq = [e ** 2 for e in excess if e < 0]
        if not downside_sq:
            return float("inf") if mean_excess > 0 else 0.0

        downside_dev = math.sqrt(sum(downside_sq) / len(downside_sq))

        if downside_dev == 0:
            return 0.0

        return (mean_excess / downside_dev) * math.sqrt(252)

    def _max_drawdown(self, returns: list[float]) -> tuple[float, int]:
        """Calculate maximum drawdown and its duration in number of trades.

        Returns:
            Tuple of (max_drawdown_pct, max_drawdown_duration_trades).
        """
        if not returns:
            return 0.0, 0

        # Build equity curve
        equity = [1.0]
        for r in returns:
            equity.append(equity[-1] * (1.0 + r))

        peak = equity[0]
        max_dd = 0.0
        max_dd_duration = 0
        current_dd_start = 0

        for i, value in enumerate(equity):
            if value >= peak:
                peak = value
                current_dd_start = i
            dd = (peak - value) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
                max_dd_duration = i - current_dd_start

        return max_dd, max_dd_duration

    def _annualize_return(self, total_return: float, num_trades: int) -> float:
        """Annualize total return assuming ~252 trading days per year."""
        if num_trades == 0:
            return 0.0
        # Approximate: assume 1 trade per day
        years = num_trades / 252.0
        if years <= 0:
            return 0.0
        if total_return <= -1.0:
            return -1.0
        return (1.0 + total_return) ** (1.0 / years) - 1.0

    @staticmethod
    def _empty_returns() -> dict:
        """Return structure when no trades exist."""
        return {
            "total_return": 0.0,
            "annualized_return": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_duration": 0,
            "win_rate": 0.0,
            "loss_rate": 0.0,
            "profit_factor": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "trade_count": 0,
        }
