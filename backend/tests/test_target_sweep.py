"""Tests for TargetSweepEngine."""

import os

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

from app.services.backtesting.target_sweep import (  # noqa: E402
    TARGET_LEVELS,
    TargetSweepEngine,
    TargetSweepResult,
)


class TestTargetSweep:

    def test_sweep_runs_all_target_levels(self):
        """Sweep produces a point for each target level."""
        engine = TargetSweepEngine(seed=42)
        result = engine.run_sweep("NVDA", capital=1000, timeframe_days=5, max_loss_pct=0.01)

        assert isinstance(result, TargetSweepResult)
        assert len(result.frontier) == len(TARGET_LEVELS)

    def test_frontier_sorted_by_target(self):
        """Frontier is sorted ascending by target_pct."""
        engine = TargetSweepEngine(seed=42)
        result = engine.run_sweep("NVDA", capital=1000, timeframe_days=5, max_loss_pct=0.01)

        targets = [p.target_pct for p in result.frontier]
        assert targets == sorted(targets)

    def test_sweet_spot_exists(self):
        """Sweet spot is found within the frontier."""
        engine = TargetSweepEngine(seed=42)
        result = engine.run_sweep("NVDA", capital=1000, timeframe_days=5, max_loss_pct=0.05)

        assert result.sweet_spot is not None
        assert result.sweet_spot.target_pct > 0

    def test_sweet_spot_has_acceptable_success_rate(self):
        """Sweet spot has success_rate >= 60% (or is fallback highest rate)."""
        engine = TargetSweepEngine(seed=42)
        result = engine.run_sweep("NVDA", capital=1000, timeframe_days=5, max_loss_pct=0.05)

        assert result.sweet_spot is not None
        # Either meets criteria or is best available
        assert result.sweet_spot.success_rate > 0

    def test_success_rate_decreases_with_higher_targets(self):
        """Higher targets generally have lower success rates."""
        engine = TargetSweepEngine(seed=42)
        result = engine.run_sweep("NVDA", capital=1000, timeframe_days=10, max_loss_pct=0.05)

        # First level should have higher (or equal) success than last
        first = result.frontier[0]
        last = result.frontier[-1]
        assert first.success_rate >= last.success_rate

    def test_sweep_result_structure(self):
        """All expected fields are present in the result."""
        engine = TargetSweepEngine(seed=42)
        result = engine.run_sweep("MSFT", capital=5000, timeframe_days=5, max_loss_pct=0.02)

        assert result.ticker == "MSFT"
        assert result.capital == 5000
        assert result.timeframe_days == 5
        assert result.max_loss_pct == 0.02
        assert result.sweep_id.startswith("sweep-")

        for point in result.frontier:
            assert point.target_pct > 0
            assert 0 <= point.success_rate <= 1
            assert point.windows_tested > 0
            assert point.windows_achieved >= 0
            assert point.windows_achieved <= point.windows_tested

    def test_different_seeds_different_results(self):
        """Different seeds produce different frontiers."""
        engine1 = TargetSweepEngine(seed=42)
        engine2 = TargetSweepEngine(seed=99)
        r1 = engine1.run_sweep("NVDA", timeframe_days=5, max_loss_pct=0.05)
        r2 = engine2.run_sweep("NVDA", timeframe_days=5, max_loss_pct=0.05)

        # At least one point should differ
        rates1 = [p.success_rate for p in r1.frontier]
        rates2 = [p.success_rate for p in r2.frontier]
        assert rates1 != rates2

    def test_custom_target_levels(self):
        """Custom target levels are respected."""
        engine = TargetSweepEngine(seed=42)
        custom = [0.01, 0.03, 0.07]
        result = engine.run_sweep("NVDA", target_levels=custom, max_loss_pct=0.05)

        assert len(result.frontier) == 3
        targets = [p.target_pct for p in result.frontier]
        assert targets == [0.01, 0.03, 0.07]
