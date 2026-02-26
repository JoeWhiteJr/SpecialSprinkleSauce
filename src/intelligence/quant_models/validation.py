"""Walk-forward validation and time-series cross-validation for quant models.

Implements expanding-window walk-forward validation with configurable step sizes
and retrain intervals, plus a gap-aware time-series cross-validator to prevent
look-ahead bias.

All metrics align with PROJECT_STANDARDS_v2.md Section 2 model manifest schema:
accuracy, sharpe_on_holdout, max_drawdown_on_holdout, win_rate.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd

logger = logging.getLogger("wasden_watch.quant_models.validation")


# ---------------------------------------------------------------------------
# Data classes for structured results
# ---------------------------------------------------------------------------


@dataclass
class StepResult:
    """Result of a single walk-forward step."""

    step: int
    train_size: int
    test_start_idx: int
    test_end_idx: int
    predictions: list[float] = field(default_factory=list)
    actuals: list[float] = field(default_factory=list)
    retrained: bool = False


@dataclass
class ValidationResult:
    """Aggregated result from a full walk-forward run."""

    model_name: str
    total_steps: int
    total_predictions: int
    metrics: dict = field(default_factory=dict)
    step_results: list[StepResult] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""


# ---------------------------------------------------------------------------
# Metrics calculation
# ---------------------------------------------------------------------------


def calculate_metrics(predictions: np.ndarray, actuals: np.ndarray) -> dict:
    """Calculate comprehensive validation metrics from predictions vs actuals.

    Both inputs are expected as arrays of bullish probabilities [0, 1] for
    classification models (XGBoost, Elastic Net) or directional confidence
    for ARIMA/Sentiment. Actuals are binary labels (1=up, 0=down).

    Args:
        predictions: Array of predicted bullish probabilities [0, 1].
        actuals: Array of actual binary labels (0 or 1).

    Returns:
        Dict with directional accuracy, precision, recall, F1, Sharpe ratio,
        max drawdown, win rate, profit factor, and information coefficient.
    """
    predictions = np.asarray(predictions, dtype=float)
    actuals = np.asarray(actuals, dtype=float)

    if len(predictions) == 0 or len(actuals) == 0:
        logger.warning("Empty predictions or actuals — returning zeroed metrics")
        return _zeroed_metrics()

    if len(predictions) != len(actuals):
        raise ValueError(
            f"Predictions length ({len(predictions)}) != actuals length ({len(actuals)})"
        )

    # Directional predictions: > 0.5 = bullish (1), <= 0.5 = bearish (0)
    pred_direction = (predictions > 0.5).astype(int)
    actual_direction = actuals.astype(int)

    # --- Classification metrics ---
    correct = pred_direction == actual_direction
    accuracy = float(np.mean(correct))

    # Precision: TP / (TP + FP)
    true_positives = int(np.sum((pred_direction == 1) & (actual_direction == 1)))
    false_positives = int(np.sum((pred_direction == 1) & (actual_direction == 0)))
    false_negatives = int(np.sum((pred_direction == 0) & (actual_direction == 1)))

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # --- Trading metrics ---
    # Win rate: percentage of trades that were correct directional calls
    win_rate = accuracy  # for directional models, accuracy IS win rate

    # Simulated P&L: +1 unit on correct prediction, -1 on incorrect
    # This is a simplified stand-in until real return data is available
    pnl_per_step = np.where(correct, 1.0, -1.0)

    # Sharpe ratio (annualized, assuming daily trading)
    # 252 trading days per year
    if len(pnl_per_step) > 1 and np.std(pnl_per_step) > 0:
        daily_sharpe = float(np.mean(pnl_per_step) / np.std(pnl_per_step))
        sharpe = daily_sharpe * np.sqrt(252)
    else:
        sharpe = 0.0

    # Max drawdown
    cumulative_pnl = np.cumsum(pnl_per_step)
    running_max = np.maximum.accumulate(cumulative_pnl)
    drawdowns = cumulative_pnl - running_max
    max_drawdown = float(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0

    # Profit factor: gross profit / gross loss
    gross_profit = float(np.sum(pnl_per_step[pnl_per_step > 0]))
    gross_loss = float(np.abs(np.sum(pnl_per_step[pnl_per_step < 0])))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0

    # Information coefficient: correlation between predictions and actuals
    if np.std(predictions) > 0 and np.std(actuals) > 0:
        ic = float(np.corrcoef(predictions, actuals)[0, 1])
    else:
        ic = 0.0

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "sharpe_ratio": round(sharpe, 4),
        "max_drawdown": round(max_drawdown, 4),
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 4),
        "information_coefficient": round(ic, 4),
        "total_predictions": len(predictions),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def _zeroed_metrics() -> dict:
    """Return a metrics dict with all values at zero/neutral."""
    return {
        "accuracy": 0.0,
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "sharpe_ratio": 0.0,
        "max_drawdown": 0.0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "information_coefficient": 0.0,
        "total_predictions": 0,
        "true_positives": 0,
        "false_positives": 0,
        "false_negatives": 0,
    }


# ---------------------------------------------------------------------------
# Walk-forward validator
# ---------------------------------------------------------------------------


class WalkForwardValidator:
    """Expanding-window walk-forward validation for quant models.

    Starts with an initial training set (default 60% of data), then steps
    forward `step_size` trading days at a time, retraining every
    `retrain_every` days. Predictions are collected at each step and
    compared against actuals.

    This approach respects temporal ordering and prevents look-ahead bias,
    unlike random train/test splits (which are a known limitation of the
    Miller NN models — see miller_nn.py docstring).
    """

    def __init__(
        self,
        initial_train_pct: float = 0.60,
        step_size: int = 20,
        retrain_every: int = 60,
    ):
        """Initialize walk-forward validator.

        Args:
            initial_train_pct: Fraction of data used for initial training window.
            step_size: Number of trading days to step forward each iteration.
            retrain_every: Retrain the model every N days of forward steps.
        """
        if not 0.1 <= initial_train_pct <= 0.9:
            raise ValueError(f"initial_train_pct must be in [0.1, 0.9], got {initial_train_pct}")
        if step_size < 1:
            raise ValueError(f"step_size must be >= 1, got {step_size}")
        if retrain_every < 1:
            raise ValueError(f"retrain_every must be >= 1, got {retrain_every}")

        self.initial_train_pct = initial_train_pct
        self.step_size = step_size
        self.retrain_every = retrain_every

    def run_walk_forward(
        self,
        model,
        features: np.ndarray,
        labels: np.ndarray,
        model_name: str = "unknown",
    ) -> ValidationResult:
        """Run expanding-window walk-forward validation.

        The model must implement:
            - train(X_train, y_train) or train(X_train, y_train, X_val, y_val)
            - predict(features) -> float  (single-sample prediction)

        For ARIMA, the caller should wrap it in an adapter that conforms
        to this interface (see TrainingPipeline for examples).

        Args:
            model: Model instance with train() and predict() methods.
            features: 2D feature array (n_samples, n_features).
            labels: 1D label array (n_samples,).
            model_name: Name for logging and result identification.

        Returns:
            ValidationResult with per-step results and aggregated metrics.
        """
        started_at = datetime.now(timezone.utc).isoformat()
        n_samples = len(features)
        initial_train_size = int(n_samples * self.initial_train_pct)

        if initial_train_size < 30:
            logger.warning(
                f"Initial training set too small ({initial_train_size} samples). "
                f"Need at least 30 for meaningful training."
            )
            return ValidationResult(
                model_name=model_name,
                total_steps=0,
                total_predictions=0,
                metrics=_zeroed_metrics(),
                started_at=started_at,
                finished_at=datetime.now(timezone.utc).isoformat(),
            )

        all_predictions = []
        all_actuals = []
        step_results = []
        step_count = 0
        days_since_retrain = 0

        current_train_end = initial_train_size
        current_test_start = initial_train_size

        # Initial training
        logger.info(
            f"[{model_name}] Walk-forward: {n_samples} samples, "
            f"initial train={initial_train_size}, step={self.step_size}, "
            f"retrain_every={self.retrain_every}"
        )

        X_train = features[:current_train_end]
        y_train = labels[:current_train_end]
        _safe_train(model, X_train, y_train)
        needs_retrain = False

        while current_test_start < n_samples:
            current_test_end = min(current_test_start + self.step_size, n_samples)

            # Retrain if needed (expanding window)
            retrained = False
            if needs_retrain:
                X_train = features[:current_test_start]
                y_train = labels[:current_test_start]
                _safe_train(model, X_train, y_train)
                retrained = True
                days_since_retrain = 0
                needs_retrain = False
                logger.info(
                    f"[{model_name}] Retrained at step {step_count} "
                    f"with {len(X_train)} training samples"
                )

            # Generate predictions for test window
            step_preds = []
            step_actuals = []
            for i in range(current_test_start, current_test_end):
                pred = _safe_predict(model, features[i])
                step_preds.append(pred)
                step_actuals.append(float(labels[i]))

            all_predictions.extend(step_preds)
            all_actuals.extend(step_actuals)

            step_results.append(StepResult(
                step=step_count,
                train_size=current_test_start,
                test_start_idx=current_test_start,
                test_end_idx=current_test_end,
                predictions=step_preds,
                actuals=step_actuals,
                retrained=retrained,
            ))

            # Advance
            step_count += 1
            days_since_retrain += (current_test_end - current_test_start)
            current_test_start = current_test_end

            if days_since_retrain >= self.retrain_every:
                needs_retrain = True

        # Calculate aggregate metrics
        metrics = calculate_metrics(
            np.array(all_predictions),
            np.array(all_actuals),
        )

        finished_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"[{model_name}] Walk-forward complete: {step_count} steps, "
            f"{len(all_predictions)} predictions, accuracy={metrics['accuracy']:.4f}, "
            f"sharpe={metrics['sharpe_ratio']:.4f}"
        )

        return ValidationResult(
            model_name=model_name,
            total_steps=step_count,
            total_predictions=len(all_predictions),
            metrics=metrics,
            step_results=step_results,
            started_at=started_at,
            finished_at=finished_at,
        )


# ---------------------------------------------------------------------------
# Time-series cross-validator
# ---------------------------------------------------------------------------


class TimeSeriesCrossValidator:
    """Time-series cross-validation with gap between train and test.

    Unlike sklearn's TimeSeriesSplit, this implementation enforces a
    configurable gap between training and test sets to prevent information
    leakage from sequential data points. This is critical for financial
    time-series where autocorrelation is significant.

    Per PROJECT_STANDARDS_v2.md Section 2, all model validation must avoid
    look-ahead bias.
    """

    def __init__(self, n_splits: int = 5, gap_days: int = 5):
        """Initialize time-series cross-validator.

        Args:
            n_splits: Number of train/test folds.
            gap_days: Number of days to skip between train and test sets
                to prevent leakage from autocorrelation.
        """
        if n_splits < 2:
            raise ValueError(f"n_splits must be >= 2, got {n_splits}")
        if gap_days < 0:
            raise ValueError(f"gap_days must be >= 0, got {gap_days}")

        self.n_splits = n_splits
        self.gap_days = gap_days

    def split(self, data: np.ndarray | pd.DataFrame) -> list[tuple[np.ndarray, np.ndarray]]:
        """Generate train/test index pairs for time-series cross-validation.

        Produces `n_splits` folds with expanding training windows. Each fold
        has a gap of `gap_days` between the end of training and the start
        of testing to prevent leakage.

        Fold structure example (n_splits=3, gap=5, 100 samples):
            Fold 0: train=[0..29], gap=[30..34], test=[35..54]
            Fold 1: train=[0..49], gap=[50..54], test=[55..74]
            Fold 2: train=[0..69], gap=[70..74], test=[75..99]

        Args:
            data: Array or DataFrame whose length determines split indices.

        Returns:
            List of (train_indices, test_indices) tuples as numpy arrays.
        """
        n_samples = len(data)
        splits = []

        # Calculate test size: evenly divide the non-initial portion
        # Reserve space for initial training set and gaps
        min_train_size = max(30, n_samples // (self.n_splits + 1))
        remaining = n_samples - min_train_size
        fold_size = remaining // self.n_splits

        if fold_size <= self.gap_days:
            logger.warning(
                f"Dataset too small ({n_samples} samples) for {self.n_splits} splits "
                f"with {self.gap_days}-day gap. Reducing gap to 0."
            )
            effective_gap = 0
        else:
            effective_gap = self.gap_days

        for fold in range(self.n_splits):
            train_end = min_train_size + fold * fold_size
            test_start = train_end + effective_gap
            test_end = train_end + fold_size

            if test_start >= n_samples:
                logger.warning(f"Fold {fold}: test_start ({test_start}) >= n_samples ({n_samples}), skipping")
                continue
            if test_end > n_samples:
                test_end = n_samples
            if test_start >= test_end:
                logger.warning(f"Fold {fold}: empty test set after gap, skipping")
                continue

            train_indices = np.arange(0, train_end)
            test_indices = np.arange(test_start, test_end)

            splits.append((train_indices, test_indices))
            logger.debug(
                f"Fold {fold}: train=[0..{train_end - 1}] ({len(train_indices)} samples), "
                f"gap={effective_gap}, test=[{test_start}..{test_end - 1}] ({len(test_indices)} samples)"
            )

        if not splits:
            logger.error(
                f"No valid splits generated for {n_samples} samples with "
                f"{self.n_splits} splits and {self.gap_days}-day gap"
            )

        return splits

    def cross_validate(
        self,
        model_class,
        model_params: dict,
        features: np.ndarray,
        labels: np.ndarray,
        model_name: str = "unknown",
    ) -> dict:
        """Run full cross-validation across all folds.

        Creates a fresh model instance for each fold to prevent information
        leakage from model state.

        Args:
            model_class: Model class to instantiate (e.g., XGBoostDirectionModel).
            model_params: Kwargs dict passed to model_class constructor.
            features: 2D feature array.
            labels: 1D label array.
            model_name: Name for logging.

        Returns:
            Dict with per-fold metrics and aggregated summary.
        """
        splits = self.split(features)
        fold_metrics = []

        for fold_idx, (train_idx, test_idx) in enumerate(splits):
            model = model_class(**model_params) if model_params else model_class()

            X_train = features[train_idx]
            y_train = labels[train_idx]
            X_test = features[test_idx]
            y_test = labels[test_idx]

            _safe_train(model, X_train, y_train, X_test, y_test)

            predictions = []
            for i in range(len(X_test)):
                pred = _safe_predict(model, X_test[i])
                predictions.append(pred)

            metrics = calculate_metrics(np.array(predictions), y_test)
            metrics["fold"] = fold_idx
            metrics["train_size"] = len(train_idx)
            metrics["test_size"] = len(test_idx)
            fold_metrics.append(metrics)

            logger.info(
                f"[{model_name}] Fold {fold_idx}: accuracy={metrics['accuracy']:.4f}, "
                f"sharpe={metrics['sharpe_ratio']:.4f}, train={len(train_idx)}, test={len(test_idx)}"
            )

        # Aggregate across folds
        if fold_metrics:
            avg_metrics = {}
            numeric_keys = [
                "accuracy", "precision", "recall", "f1",
                "sharpe_ratio", "max_drawdown", "win_rate",
                "profit_factor", "information_coefficient",
            ]
            for key in numeric_keys:
                values = [m[key] for m in fold_metrics]
                avg_metrics[f"mean_{key}"] = round(float(np.mean(values)), 4)
                avg_metrics[f"std_{key}"] = round(float(np.std(values)), 4)
        else:
            avg_metrics = {}

        return {
            "model_name": model_name,
            "n_splits": len(splits),
            "gap_days": self.gap_days,
            "fold_metrics": fold_metrics,
            "aggregate": avg_metrics,
        }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_validation_report(results: ValidationResult | dict) -> dict:
    """Generate a summary report suitable for model manifests.

    Translates validation results into the format expected by
    PROJECT_STANDARDS_v2.md Section 2 model manifest schema.

    Args:
        results: Either a ValidationResult or a dict from cross_validate().

    Returns:
        Dict with manifest-compatible validation_results and metadata.
    """
    if isinstance(results, ValidationResult):
        metrics = results.metrics
        return {
            "validation_method": "walk_forward",
            "model_name": results.model_name,
            "total_steps": results.total_steps,
            "total_predictions": results.total_predictions,
            "started_at": results.started_at,
            "finished_at": results.finished_at,
            "validation_results": {
                "accuracy": metrics.get("accuracy", 0.0),
                "sharpe_on_holdout": metrics.get("sharpe_ratio", 0.0),
                "max_drawdown_on_holdout": metrics.get("max_drawdown", 0.0),
                "win_rate": metrics.get("win_rate", 0.0),
            },
            "extended_metrics": {
                "precision": metrics.get("precision", 0.0),
                "recall": metrics.get("recall", 0.0),
                "f1": metrics.get("f1", 0.0),
                "profit_factor": metrics.get("profit_factor", 0.0),
                "information_coefficient": metrics.get("information_coefficient", 0.0),
            },
        }

    # Cross-validation result (dict)
    aggregate = results.get("aggregate", {})
    return {
        "validation_method": "time_series_cross_validation",
        "model_name": results.get("model_name", "unknown"),
        "n_splits": results.get("n_splits", 0),
        "gap_days": results.get("gap_days", 0),
        "validation_results": {
            "accuracy": aggregate.get("mean_accuracy", 0.0),
            "sharpe_on_holdout": aggregate.get("mean_sharpe_ratio", 0.0),
            "max_drawdown_on_holdout": aggregate.get("mean_max_drawdown", 0.0),
            "win_rate": aggregate.get("mean_win_rate", 0.0),
        },
        "extended_metrics": {
            "precision": aggregate.get("mean_precision", 0.0),
            "recall": aggregate.get("mean_recall", 0.0),
            "f1": aggregate.get("mean_f1", 0.0),
            "profit_factor": aggregate.get("mean_profit_factor", 0.0),
            "information_coefficient": aggregate.get("mean_information_coefficient", 0.0),
        },
        "stability": {
            "accuracy_std": aggregate.get("std_accuracy", 0.0),
            "sharpe_std": aggregate.get("std_sharpe_ratio", 0.0),
            "win_rate_std": aggregate.get("std_win_rate", 0.0),
        },
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _safe_train(model, X_train, y_train, X_val=None, y_val=None) -> dict:
    """Train a model with flexible signature handling.

    Handles differences between model train() signatures:
    - XGBoost/ElasticNet: train(X_train, y_train, X_val, y_val)
    - ARIMA: train(series)
    - Sentiment: no train() needed

    Args:
        model: Model instance.
        X_train: Training features.
        y_train: Training labels.
        X_val: Optional validation features.
        y_val: Optional validation labels.

    Returns:
        Training result dict, or empty dict on failure.
    """
    try:
        if X_val is not None and y_val is not None:
            return model.train(X_train, y_train, X_val, y_val)
        return model.train(X_train, y_train)
    except TypeError:
        # Model might have a different signature (e.g., ARIMA takes a series)
        try:
            return model.train(X_train)
        except Exception as e:
            logger.warning(f"Training failed: {e}")
            return {}
    except Exception as e:
        logger.warning(f"Training failed: {e}")
        return {}


def _safe_predict(model, features) -> float:
    """Predict with error handling, returning 0.5 on failure.

    Args:
        model: Model instance.
        features: Single sample features.

    Returns:
        Predicted value [0, 1]. Returns 0.5 on any failure.
    """
    try:
        return float(model.predict(features))
    except Exception as e:
        logger.warning(f"Prediction failed: {e}")
        return 0.5
