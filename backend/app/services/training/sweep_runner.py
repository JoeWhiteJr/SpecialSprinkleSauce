"""Parameter Sweep Runner — orchestrates sweeps using the training pipeline.

Wraps the existing TrainingPipeline and BacktestEngine to evaluate model
performance at different parameter values.
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .auto_tuner import PARAMETER_BOUNDS, get_sweep_values, validate_bound

logger = logging.getLogger("wasden_watch.training.sweep_runner")


@dataclass
class SweepDataPoint:
    """Result for a single parameter value in a sweep."""

    value: float
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    accuracy: float
    profit_factor: float = 0.0
    sortino_ratio: float = 0.0
    total_trades: int = 0


@dataclass
class SweepResult:
    """Complete result of a parameter sweep."""

    parameter_name: str
    parameter_category: str
    data_points: list[SweepDataPoint] = field(default_factory=list)
    best_value: float | None = None
    best_metric_name: str = "win_rate"
    best_metric_value: float | None = None
    started_at: str = ""
    completed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameter_name": self.parameter_name,
            "parameter_category": self.parameter_category,
            "values_tested": [dp.value for dp in self.data_points],
            "results_per_value": [
                {
                    "value": dp.value,
                    "win_rate": dp.win_rate,
                    "sharpe_ratio": dp.sharpe_ratio,
                    "max_drawdown": dp.max_drawdown,
                    "accuracy": dp.accuracy,
                    "profit_factor": dp.profit_factor,
                    "sortino_ratio": dp.sortino_ratio,
                    "total_trades": dp.total_trades,
                }
                for dp in self.data_points
            ],
            "best_value": self.best_value,
            "best_metric_name": self.best_metric_name,
            "best_metric_value": self.best_metric_value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# Stress test regime date ranges
STRESS_REGIMES: dict[str, dict[str, str]] = {
    "covid_2020": {"start": "2020-02-19", "end": "2020-04-30", "label": "COVID Crash"},
    "bear_2022": {"start": "2022-01-03", "end": "2022-10-14", "label": "2022 Bear Market"},
    "banking_2023": {"start": "2023-03-01", "end": "2023-05-31", "label": "Regional Banking Crisis"},
    "crash_1929": {"start": "1929-09-01", "end": "1929-12-31", "label": "1929 Crash"},
    "crash_1987": {"start": "1987-09-01", "end": "1987-12-31", "label": "Black Monday"},
    "crash_2008": {"start": "2008-09-01", "end": "2009-03-31", "label": "2008 Financial Crisis"},
}


class SweepRunner:
    """Runs parameter sweeps and evaluates model performance.

    In mock mode, generates synthetic results for UI development.
    When real data arrives, connects to TrainingPipeline + BacktestEngine.
    """

    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock

    def run_parameter_sweep(
        self,
        parameter_name: str,
        data_source: str = "mock",
        optimize_metric: str = "win_rate",
        custom_values: list[float] | None = None,
    ) -> SweepResult:
        """Run a parameter sweep across the bounded range.

        Args:
            parameter_name: Dotted parameter name (e.g. "xgboost.n_estimators")
            data_source: Data to train/validate on ("mock", "emery", "dow_jones")
            optimize_metric: Metric to optimize for ("win_rate", "sharpe_ratio", etc.)
            custom_values: Override the default sweep values
        """
        bound = PARAMETER_BOUNDS.get(parameter_name)
        if not bound:
            raise ValueError(f"Unknown parameter: {parameter_name}")

        values = custom_values or get_sweep_values(parameter_name)
        for v in values:
            validate_bound(parameter_name, v)

        result = SweepResult(
            parameter_name=parameter_name,
            parameter_category=bound.category,
            best_metric_name=optimize_metric,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        if self.use_mock:
            result.data_points = self._generate_mock_sweep(parameter_name, values)
        else:
            result.data_points = self._run_real_sweep(parameter_name, values, data_source)

        # Find best value
        if result.data_points:
            best_dp = max(
                result.data_points,
                key=lambda dp: getattr(dp, optimize_metric, 0),
            )
            result.best_value = best_dp.value
            result.best_metric_value = getattr(best_dp, optimize_metric, 0)

        result.completed_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            "Sweep complete: %s best=%s (%s=%.4f)",
            parameter_name,
            result.best_value,
            optimize_metric,
            result.best_metric_value or 0,
        )
        return result

    def run_ensemble_weight_sweep(
        self,
        data_source: str = "mock",
        grid_step: float = 0.1,
    ) -> list[dict[str, Any]]:
        """Grid search over ensemble weights constrained to sum=1.0.

        Returns list of {weights: {xgb, enet, arima, sent}, win_rate, sharpe, ...}
        """
        import itertools

        steps = [round(i * grid_step, 2) for i in range(int(1 / grid_step) + 1)]
        results: list[dict[str, Any]] = []

        for combo in itertools.product(steps, repeat=4):
            if abs(sum(combo) - 1.0) > 0.001:
                continue

            weights = {
                "xgboost": combo[0],
                "elastic_net": combo[1],
                "arima": combo[2],
                "sentiment": combo[3],
            }

            if self.use_mock:
                metrics = self._mock_ensemble_eval(weights)
            else:
                metrics = self._real_ensemble_eval(weights, data_source)

            results.append({"weights": weights, **metrics})

        results.sort(key=lambda r: r.get("win_rate", 0), reverse=True)
        return results

    def get_stress_regimes(self) -> dict[str, dict[str, str]]:
        """Return available stress test regime definitions."""
        return STRESS_REGIMES

    def run_stress_test(
        self,
        regime: str,
        data_source: str = "mock",
    ) -> dict[str, Any]:
        """Run models against a specific market regime."""
        if regime not in STRESS_REGIMES:
            raise ValueError(f"Unknown regime: {regime}. Available: {list(STRESS_REGIMES.keys())}")

        regime_info = STRESS_REGIMES[regime]

        if self.use_mock:
            return self._mock_stress_test(regime, regime_info)

        return self._real_stress_test(regime, regime_info, data_source)

    # ---- Mock implementations for Phase 1 ----

    def _generate_mock_sweep(
        self, parameter_name: str, values: list[float]
    ) -> list[SweepDataPoint]:
        """Generate realistic-looking mock sweep data.

        Creates an inverted-U curve where performance peaks at an optimal value.
        """
        import random

        random.seed(hash(parameter_name) % 2**32)
        n = len(values)
        peak_idx = n // 2 + random.randint(-n // 6, n // 6)
        peak_idx = max(1, min(n - 2, peak_idx))

        points: list[SweepDataPoint] = []
        for i, value in enumerate(values):
            distance = abs(i - peak_idx) / max(n, 1)
            base_win = 0.65 - 0.15 * distance + random.uniform(-0.02, 0.02)
            base_win = max(0.40, min(0.80, base_win))

            points.append(SweepDataPoint(
                value=value,
                win_rate=round(base_win, 4),
                sharpe_ratio=round(base_win * 1.8 + random.uniform(-0.2, 0.2), 4),
                max_drawdown=round(0.15 + 0.10 * distance + random.uniform(-0.02, 0.02), 4),
                accuracy=round(base_win + random.uniform(-0.03, 0.03), 4),
                profit_factor=round(1.0 + base_win + random.uniform(-0.1, 0.1), 4),
                sortino_ratio=round(base_win * 2.2 + random.uniform(-0.3, 0.3), 4),
                total_trades=random.randint(80, 200),
            ))
        return points

    def _run_real_sweep(
        self, parameter_name: str, values: list[float], data_source: str
    ) -> list[SweepDataPoint]:
        """Run real training + validation for each value. Placeholder for server phase."""
        logger.warning("Real sweep not yet implemented — use mock mode")
        return self._generate_mock_sweep(parameter_name, values)

    def _mock_ensemble_eval(self, weights: dict[str, float]) -> dict[str, Any]:
        """Mock evaluation of an ensemble weight combination."""
        import random

        random.seed(int(sum(weights.values()) * 10000))
        balance = 1 - statistics.stdev(weights.values())
        base = 0.55 + 0.10 * balance

        return {
            "win_rate": round(base + random.uniform(-0.03, 0.03), 4),
            "sharpe_ratio": round(base * 1.6 + random.uniform(-0.2, 0.2), 4),
            "max_drawdown": round(0.12 + random.uniform(-0.03, 0.03), 4),
        }

    def _real_ensemble_eval(
        self, weights: dict[str, float], data_source: str
    ) -> dict[str, Any]:
        """Real ensemble evaluation. Placeholder for server phase."""
        return self._mock_ensemble_eval(weights)

    def _mock_stress_test(
        self, regime: str, regime_info: dict[str, str]
    ) -> dict[str, Any]:
        """Generate mock stress test results."""
        import random

        random.seed(hash(regime))
        severity = {"covid_2020": 0.7, "bear_2022": 0.5, "banking_2023": 0.4,
                     "crash_1929": 0.9, "crash_1987": 0.8, "crash_2008": 0.85}
        sev = severity.get(regime, 0.5)

        models = ["xgboost", "elastic_net", "arima", "sentiment"]
        model_results = {}
        for model in models:
            model_results[model] = {
                "win_rate": round(0.55 - 0.20 * sev + random.uniform(-0.05, 0.05), 4),
                "max_drawdown": round(0.10 + 0.25 * sev + random.uniform(-0.03, 0.03), 4),
                "sharpe_ratio": round(0.50 - 0.80 * sev + random.uniform(-0.15, 0.15), 4),
            }

        return {
            "regime": regime,
            "label": regime_info["label"],
            "date_range": f"{regime_info['start']} to {regime_info['end']}",
            "model_results": model_results,
            "circuit_breaker_triggered": sev > 0.6,
            "data_source": "mock",
        }

    def _real_stress_test(
        self, regime: str, regime_info: dict[str, str], data_source: str
    ) -> dict[str, Any]:
        """Real stress test. Placeholder for server phase."""
        return self._mock_stress_test(regime, regime_info)
