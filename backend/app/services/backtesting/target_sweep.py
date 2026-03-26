"""Target Sweep Engine — runs backtests across multiple target return levels.

Answers: "What's the sweet spot between risk and accuracy at different
target levels?" by sliding windows across historical data and checking
whether each target would be achievable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .backtest_engine import BacktestEngine

logger = logging.getLogger("wasden_watch.backtesting.target_sweep")

# Default target levels to sweep
TARGET_LEVELS = [0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.40]

# Sweet spot criteria
MIN_SUCCESS_RATE = 0.60  # At least 60% success rate
MAX_DRAWDOWN_MULTIPLIER = 2.0  # avg_drawdown < 2x max_loss_pct


@dataclass
class TargetSweepPoint:
    """Result for a single target level."""

    target_pct: float
    success_rate: float
    avg_return: float
    avg_drawdown: float
    trades_taken: int
    windows_tested: int
    windows_achieved: int


@dataclass
class TargetSweepResult:
    """Complete sweep result across all target levels."""

    sweep_id: str
    ticker: str
    capital: float
    timeframe_days: int
    max_loss_pct: float
    frontier: list[TargetSweepPoint] = field(default_factory=list)
    sweet_spot: TargetSweepPoint | None = None


class TargetSweepEngine:
    """Runs the same historical data across multiple target levels.

    For each target level, slides a window of timeframe_days across the
    OHLCV data and checks whether the target return would be achievable
    based on the maximum close-to-close return within each window.
    """

    def __init__(self, seed: int = 42):
        self._seed = seed

    def run_sweep(
        self,
        ticker: str,
        capital: float = 1000.0,
        timeframe_days: int = 5,
        max_loss_pct: float = 0.01,
        target_levels: list[float] | None = None,
        num_days: int = 252,
    ) -> TargetSweepResult:
        """Run target sweep across all target levels.

        Args:
            ticker: Stock ticker for OHLCV data.
            capital: Starting capital.
            timeframe_days: Window size in trading days.
            max_loss_pct: Maximum acceptable loss per window.
            target_levels: List of target return percentages to test.
            num_days: Days of historical OHLCV data to generate.

        Returns:
            TargetSweepResult with frontier and sweet spot.
        """
        levels = target_levels or list(TARGET_LEVELS)

        # Generate OHLCV data
        ohlcv = BacktestEngine.generate_mock_ohlcv(ticker, num_days=num_days, seed=self._seed)

        if len(ohlcv) < timeframe_days + 1:
            logger.warning(f"[TargetSweep] Not enough data for {ticker} — need {timeframe_days + 1}, got {len(ohlcv)}")
            return TargetSweepResult(
                sweep_id=f"sweep-{ticker}-empty",
                ticker=ticker,
                capital=capital,
                timeframe_days=timeframe_days,
                max_loss_pct=max_loss_pct,
            )

        # Extract close prices
        closes = [bar["close"] for bar in ohlcv]

        # Run sweep
        frontier: list[TargetSweepPoint] = []
        for target in sorted(levels):
            point = self._evaluate_target(
                ticker=ticker,
                closes=closes,
                target_pct=target,
                timeframe_days=timeframe_days,
                max_loss_pct=max_loss_pct,
            )
            frontier.append(point)

        # Find sweet spot
        sweet_spot = self._find_sweet_spot(frontier, max_loss_pct)

        import uuid
        sweep_id = f"sweep-{uuid.uuid4().hex[:8]}"

        result = TargetSweepResult(
            sweep_id=sweep_id,
            ticker=ticker,
            capital=capital,
            timeframe_days=timeframe_days,
            max_loss_pct=max_loss_pct,
            frontier=frontier,
            sweet_spot=sweet_spot,
        )

        logger.info(
            f"[TargetSweep] {ticker}: {len(frontier)} levels, "
            f"sweet_spot={sweet_spot.target_pct:.1%} @ {sweet_spot.success_rate:.0%}"
            if sweet_spot else f"[TargetSweep] {ticker}: no sweet spot found"
        )
        return result

    def _evaluate_target(
        self,
        ticker: str,
        closes: list[float],
        target_pct: float,
        timeframe_days: int,
        max_loss_pct: float,
    ) -> TargetSweepPoint:
        """Evaluate a single target level across all windows."""
        num_windows = len(closes) - timeframe_days
        achieved = 0
        total_return = 0.0
        total_drawdown = 0.0
        total_trades = 0

        for i in range(num_windows):
            window = closes[i: i + timeframe_days + 1]
            entry_price = window[0]

            if entry_price <= 0:
                continue

            # Best return within the window (buy at start, sell at best close)
            best_close = max(window[1:]) if len(window) > 1 else entry_price
            best_return = (best_close - entry_price) / entry_price

            # Worst drawdown within the window
            worst_close = min(window[1:]) if len(window) > 1 else entry_price
            worst_drawdown = (entry_price - worst_close) / entry_price

            # Did this window achieve the target without hitting loss limit?
            if best_return >= target_pct and worst_drawdown < max_loss_pct:
                achieved += 1

            total_return += best_return
            total_drawdown += worst_drawdown
            total_trades += 1

        success_rate = achieved / num_windows if num_windows > 0 else 0.0
        avg_return = total_return / num_windows if num_windows > 0 else 0.0
        avg_drawdown = total_drawdown / num_windows if num_windows > 0 else 0.0

        return TargetSweepPoint(
            target_pct=target_pct,
            success_rate=round(success_rate, 4),
            avg_return=round(avg_return, 6),
            avg_drawdown=round(avg_drawdown, 6),
            trades_taken=total_trades,
            windows_tested=num_windows,
            windows_achieved=achieved,
        )

    @staticmethod
    def _find_sweet_spot(
        frontier: list[TargetSweepPoint],
        max_loss_pct: float,
    ) -> TargetSweepPoint | None:
        """Find the highest target with acceptable success rate and drawdown.

        Sweet spot = highest target where:
            success_rate >= 60% AND avg_drawdown < 2x max_loss_pct
        """
        max_drawdown = max_loss_pct * MAX_DRAWDOWN_MULTIPLIER
        candidates = [
            p for p in frontier
            if p.success_rate >= MIN_SUCCESS_RATE and p.avg_drawdown < max_drawdown
        ]

        if not candidates:
            # Fallback: return the one with highest success rate
            if frontier:
                return max(frontier, key=lambda p: p.success_rate)
            return None

        # Highest target among candidates
        return max(candidates, key=lambda p: p.target_pct)
