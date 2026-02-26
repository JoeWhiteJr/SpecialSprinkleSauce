"""Model comparison utility for quant ensemble analysis.

Accumulates validation results from multiple models, generates formatted
comparison tables, identifies the best performer by configurable metric,
and analyzes ensemble vs individual model performance and inter-model
disagreement patterns.

Per PROJECT_STANDARDS_v2.md Section 2:
- Ensemble uses equal-weighted arithmetic mean of 4 Tier 1 model scores
- std_dev > 0.50 = high disagreement flag
- Disagreement reduces position sizing automatically
"""

import logging
import statistics
from collections import OrderedDict

import numpy as np

logger = logging.getLogger("wasden_watch.quant_models.model_comparison")

# Metrics displayed in comparison tables
DISPLAY_METRICS = [
    "accuracy",
    "precision",
    "recall",
    "f1",
    "sharpe_ratio",
    "max_drawdown",
    "win_rate",
    "profit_factor",
    "information_coefficient",
]


class ModelComparison:
    """Accumulates and compares validation results across multiple models.

    Usage:
        comparison = ModelComparison()
        comparison.add_result("xgboost", xgb_metrics)
        comparison.add_result("elastic_net", enet_metrics)
        comparison.add_result("arima", arima_metrics)
        comparison.add_result("sentiment", sentiment_metrics)
        print(comparison.summary_table())
        print(comparison.best_model("sharpe_ratio"))
    """

    def __init__(self):
        """Initialize with empty results store."""
        self._results: OrderedDict[str, dict] = OrderedDict()
        self._raw_predictions: dict[str, np.ndarray] = {}

    def add_result(self, model_name: str, metrics: dict) -> None:
        """Accumulate a model's validation metrics.

        Args:
            model_name: Identifier for the model (e.g., "xgboost").
            metrics: Dict from calculate_metrics() with accuracy, sharpe, etc.
        """
        self._results[model_name] = metrics.copy()
        logger.info(
            f"Added result for {model_name}: "
            f"accuracy={metrics.get('accuracy', 0):.4f}, "
            f"sharpe={metrics.get('sharpe_ratio', 0):.4f}"
        )

    def add_predictions(self, model_name: str, predictions: np.ndarray) -> None:
        """Store raw predictions for disagreement analysis.

        Args:
            model_name: Model identifier.
            predictions: Array of predicted probabilities [0, 1].
        """
        self._raw_predictions[model_name] = np.asarray(predictions, dtype=float)

    def summary_table(self) -> list[dict]:
        """Generate a formatted comparison of all models.

        Returns a list of dicts, one per model, containing all display
        metrics. Suitable for rendering as a table or serializing to JSON.

        Returns:
            List of dicts with 'model' key plus all metric keys.
        """
        if not self._results:
            logger.warning("No results to compare")
            return []

        rows = []
        for model_name, metrics in self._results.items():
            row = {"model": model_name}
            for metric in DISPLAY_METRICS:
                row[metric] = metrics.get(metric, 0.0)
            rows.append(row)

        return rows

    def summary_text(self) -> str:
        """Generate a human-readable comparison table string.

        Returns:
            Formatted text table comparing all models.
        """
        rows = self.summary_table()
        if not rows:
            return "No model results available."

        # Header
        header = f"{'Model':<15}"
        for metric in DISPLAY_METRICS:
            header += f" {metric:>12}"
        lines = [header, "-" * len(header)]

        # Data rows
        for row in rows:
            line = f"{row['model']:<15}"
            for metric in DISPLAY_METRICS:
                val = row.get(metric, 0.0)
                line += f" {val:>12.4f}"
            lines.append(line)

        return "\n".join(lines)

    def best_model(self, metric: str = "sharpe_ratio") -> str | None:
        """Identify the best-performing model by a given metric.

        For max_drawdown (which is negative), "best" means the value
        closest to zero (least drawdown).

        Args:
            metric: Metric name to rank by. Default is sharpe_ratio per
                PROJECT_STANDARDS_v2.md emphasis on risk-adjusted returns.

        Returns:
            Name of the best model, or None if no results.
        """
        if not self._results:
            return None

        if metric == "max_drawdown":
            # Best = closest to 0 (least negative)
            best_name = max(
                self._results.keys(),
                key=lambda m: self._results[m].get(metric, float("-inf")),
            )
        else:
            # Best = highest value
            best_name = max(
                self._results.keys(),
                key=lambda m: self._results[m].get(metric, 0.0),
            )

        best_val = self._results[best_name].get(metric, 0.0)
        logger.info(f"Best model by {metric}: {best_name} ({best_val:.4f})")
        return best_name

    def ensemble_vs_individual(self) -> dict:
        """Compare the equal-weighted ensemble composite against each individual model.

        The ensemble score at each prediction step is the arithmetic mean
        of all models' predictions, consistent with the orchestrator's
        scoring logic (QuantModelOrchestrator.score_ticker).

        Requires raw predictions to be stored via add_predictions().
        If no raw predictions are available, falls back to comparing
        aggregated metrics.

        Returns:
            Dict with ensemble metrics and per-model comparison.
        """
        if self._raw_predictions:
            return self._ensemble_from_predictions()
        return self._ensemble_from_metrics()

    def _ensemble_from_predictions(self) -> dict:
        """Compute ensemble metrics from raw prediction arrays."""

        models = list(self._raw_predictions.keys())
        if len(models) < 2:
            return {"error": "Need at least 2 models with predictions for ensemble comparison"}

        # Verify all prediction arrays have the same length
        lengths = {m: len(self._raw_predictions[m]) for m in models}
        if len(set(lengths.values())) > 1:
            return {"error": f"Prediction arrays have different lengths: {lengths}"}

        # Compute ensemble as arithmetic mean (equal weights per PROJECT_STANDARDS)
        all_preds = np.array([self._raw_predictions[m] for m in models])

        # Compute standard deviation across models at each step
        std_devs = np.std(all_preds, axis=0)
        high_disagreement_pct = float(np.mean(std_devs > 0.50)) * 100

        result = {
            "ensemble_stats": {
                "mean_std_dev": round(float(np.mean(std_devs)), 4),
                "max_std_dev": round(float(np.max(std_devs)), 4),
                "high_disagreement_pct": round(high_disagreement_pct, 2),
            },
            "models": models,
        }

        # Compare each model against ensemble
        comparisons = {}
        for model_name in models:
            model_metrics = self._results.get(model_name, {})
            comparisons[model_name] = {
                "accuracy": model_metrics.get("accuracy", 0.0),
                "sharpe_ratio": model_metrics.get("sharpe_ratio", 0.0),
                "win_rate": model_metrics.get("win_rate", 0.0),
            }

        result["individual_models"] = comparisons

        # Note: ensemble accuracy requires actuals, which are not stored here.
        # The comparison is based on individual model metrics only.
        result["note"] = (
            "Ensemble composite is the arithmetic mean of all model predictions. "
            "Full ensemble metrics require actuals array — use WalkForwardValidator "
            "for complete ensemble validation."
        )

        return result

    def _ensemble_from_metrics(self) -> dict:
        """Compare models using aggregated metrics (no raw predictions)."""
        if not self._results:
            return {"error": "No model results available"}

        models = list(self._results.keys())
        comparison = {}

        for metric in ["accuracy", "sharpe_ratio", "win_rate", "max_drawdown", "f1"]:
            values = [self._results[m].get(metric, 0.0) for m in models]
            comparison[metric] = {
                "mean": round(statistics.mean(values), 4) if values else 0.0,
                "std": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
                "min": round(min(values), 4) if values else 0.0,
                "max": round(max(values), 4) if values else 0.0,
                "per_model": {m: v for m, v in zip(models, values)},
            }

        return {
            "models": models,
            "metric_comparison": comparison,
            "note": (
                "Aggregated metric comparison — add raw predictions via "
                "add_predictions() for full ensemble analysis."
            ),
        }

    def disagreement_analysis(self) -> dict:
        """Analyze how often models disagree and compute correlation matrix.

        Disagreement is measured as:
        1. Directional disagreement: how often models disagree on up/down
        2. Correlation matrix: pairwise correlations between model predictions
        3. Per-pair agreement rates

        Requires raw predictions via add_predictions().
        Falls back to metric-based analysis if predictions unavailable.

        Returns:
            Dict with disagreement statistics and correlation matrix.
        """
        if len(self._raw_predictions) < 2:
            return self._disagreement_from_metrics()

        models = list(self._raw_predictions.keys())
        n_models = len(models)

        # Directional predictions: > 0.5 = bullish
        directions = {
            m: (self._raw_predictions[m] > 0.5).astype(int)
            for m in models
        }

        # Pairwise agreement rates
        pair_agreement = {}
        for i in range(n_models):
            for j in range(i + 1, n_models):
                m1, m2 = models[i], models[j]
                agree_pct = float(np.mean(directions[m1] == directions[m2])) * 100
                pair_agreement[f"{m1}_vs_{m2}"] = round(agree_pct, 2)

        # Correlation matrix of raw predictions
        pred_matrix = np.array([self._raw_predictions[m] for m in models])
        corr_matrix = np.corrcoef(pred_matrix)

        corr_dict = {}
        for i in range(n_models):
            for j in range(n_models):
                corr_dict[f"{models[i]}_vs_{models[j]}"] = round(float(corr_matrix[i, j]), 4)

        # Unanimous agreement rate (all models agree on direction)
        all_directions = np.array([directions[m] for m in models])
        unanimous = float(np.mean(np.all(all_directions == all_directions[0], axis=0))) * 100

        # Per-step standard deviation
        all_preds = np.array([self._raw_predictions[m] for m in models])
        step_std = np.std(all_preds, axis=0)

        return {
            "models": models,
            "n_predictions": len(self._raw_predictions[models[0]]),
            "pairwise_directional_agreement": pair_agreement,
            "unanimous_agreement_pct": round(unanimous, 2),
            "correlation_matrix": corr_dict,
            "std_dev_stats": {
                "mean": round(float(np.mean(step_std)), 4),
                "median": round(float(np.median(step_std)), 4),
                "max": round(float(np.max(step_std)), 4),
                "min": round(float(np.min(step_std)), 4),
                "high_disagreement_pct": round(float(np.mean(step_std > 0.50)) * 100, 2),
            },
        }

    def _disagreement_from_metrics(self) -> dict:
        """Estimate disagreement from aggregated metrics only."""
        if len(self._results) < 2:
            return {"error": "Need at least 2 models for disagreement analysis"}

        models = list(self._results.keys())

        # Compare accuracy spread as a proxy for disagreement
        accuracies = [self._results[m].get("accuracy", 0.5) for m in models]
        sharpes = [self._results[m].get("sharpe_ratio", 0.0) for m in models]

        return {
            "models": models,
            "accuracy_spread": {
                "min": round(min(accuracies), 4),
                "max": round(max(accuracies), 4),
                "range": round(max(accuracies) - min(accuracies), 4),
                "std": round(statistics.stdev(accuracies), 4) if len(accuracies) > 1 else 0.0,
            },
            "sharpe_spread": {
                "min": round(min(sharpes), 4),
                "max": round(max(sharpes), 4),
                "range": round(max(sharpes) - min(sharpes), 4),
                "std": round(statistics.stdev(sharpes), 4) if len(sharpes) > 1 else 0.0,
            },
            "note": (
                "Metric-based disagreement estimate only. Add raw predictions "
                "via add_predictions() for full pairwise and correlation analysis."
            ),
        }

    def rank_models(self, metric: str = "sharpe_ratio") -> list[tuple[str, float]]:
        """Rank all models by a given metric, descending.

        Args:
            metric: Metric to rank by.

        Returns:
            List of (model_name, metric_value) tuples sorted best-first.
        """
        items = [
            (name, metrics.get(metric, 0.0))
            for name, metrics in self._results.items()
        ]

        if metric == "max_drawdown":
            # Best = closest to 0
            items.sort(key=lambda x: x[1], reverse=True)
        else:
            items.sort(key=lambda x: x[1], reverse=True)

        return items

    def to_dict(self) -> dict:
        """Serialize all comparison data to a dict.

        Returns:
            Dict with all results, comparison table, rankings, and analysis.
        """
        return {
            "results": dict(self._results),
            "summary": self.summary_table(),
            "rankings": {
                "by_sharpe": self.rank_models("sharpe_ratio"),
                "by_accuracy": self.rank_models("accuracy"),
                "by_win_rate": self.rank_models("win_rate"),
            },
            "best": {
                "sharpe": self.best_model("sharpe_ratio"),
                "accuracy": self.best_model("accuracy"),
                "win_rate": self.best_model("win_rate"),
            },
            "ensemble_comparison": self.ensemble_vs_individual(),
            "disagreement": self.disagreement_analysis(),
        }
