"""Training pipeline CLI for all quant models.

Loads OHLCV data from CSV (Emery, Dow Jones, or custom path), runs feature
engineering, trains all 4 Tier 1 models, performs walk-forward validation,
saves trained models, and generates comparison reports.

Designed to work immediately when real data (Emery 10-year OHLCV, Dow Jones
1928-2009) arrives in data/raw/. Until then, mock mode exercises the full
pipeline with synthetic data.

Usage:
    python -m src.intelligence.quant_models.train_pipeline --data emery --output models/trained/
    python -m src.intelligence.quant_models.train_pipeline --data dow_jones --output models/trained/
    python -m src.intelligence.quant_models.train_pipeline --data mock --output models/trained/
    python -m src.intelligence.quant_models.train_pipeline --data /path/to/custom.csv --output models/trained/
    python -m src.intelligence.quant_models.train_pipeline --data mock --model xgboost --output models/trained/
"""

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .arima_model import ARIMAModel
from .elastic_net_model import ElasticNetDirectionModel
from .feature_engineer import FeatureEngineer
from .model_comparison import ModelComparison
from .sentiment_model import SentimentModel
from .validation import (
    TimeSeriesCrossValidator,
    WalkForwardValidator,
    generate_validation_report,
)
from .xgboost_model import XGBoostDirectionModel

logger = logging.getLogger("wasden_watch.quant_models.train_pipeline")

# Default data directories per PROJECT_STANDARDS_v2.md Section 1
DATA_RAW_DIR = Path("data/raw")
DEFAULT_OUTPUT_DIR = Path("models/trained")

# Model registry: name -> (class, type)
MODEL_REGISTRY = {
    "xgboost": (XGBoostDirectionModel, "feature_based"),
    "elastic_net": (ElasticNetDirectionModel, "feature_based"),
    "arima": (ARIMAModel, "time_series"),
    "sentiment": (SentimentModel, "sentiment"),
}

TIER_1_MODELS = ["xgboost", "elastic_net", "arima", "sentiment"]


class TrainingPipeline:
    """End-to-end training pipeline for Wasden Watch quant models.

    Orchestrates data loading, feature engineering, model training,
    walk-forward validation, model serialization, and manifest generation.

    In mock mode, generates synthetic OHLCV data to exercise the full
    pipeline without real market data.
    """

    def __init__(
        self,
        data_dir: str | Path = DATA_RAW_DIR,
        output_dir: str | Path = DEFAULT_OUTPUT_DIR,
        use_mock: bool = False,
    ):
        """Initialize training pipeline.

        Args:
            data_dir: Directory containing raw CSV data files.
            output_dir: Directory for trained model artifacts.
            use_mock: If True, generate synthetic data instead of loading files.
        """
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.use_mock = use_mock
        self.feature_engineer = FeatureEngineer()
        self._ohlcv_df: pd.DataFrame | None = None
        self._features: pd.DataFrame | None = None
        self._labels: pd.Series | None = None
        self._results: dict[str, dict] = {}

    def load_data(self, source: str = "emery") -> pd.DataFrame:
        """Load OHLCV data from the specified source.

        Supports:
            - "emery": Emery S&P 500 10-year OHLCV (data/raw/)
            - "dow_jones": Dow Jones 1928-2009 OHLCV (data/raw/)
            - "mock": Synthetic OHLCV data for pipeline testing
            - Any file path: Custom CSV with OHLCV columns

        All data is tagged survivorship_bias_unaudited per
        PROJECT_STANDARDS_v2.md Section 1.

        Args:
            source: Data source identifier or path to CSV.

        Returns:
            DataFrame with columns: date, open, high, low, close, volume.

        Raises:
            FileNotFoundError: If the specified data file does not exist.
            ValueError: If the CSV does not contain required OHLCV columns.
        """
        if source == "mock" or self.use_mock:
            logger.info("Generating mock OHLCV data for pipeline testing")
            return self._generate_mock_ohlcv()

        if source == "emery":
            return self._load_emery()
        elif source == "dow_jones":
            return self._load_dow_jones()
        else:
            # Treat as file path
            return self._load_csv(Path(source))

    def _generate_mock_ohlcv(self, n_days: int = 500, seed: int = 42) -> pd.DataFrame:
        """Generate synthetic OHLCV data mimicking realistic market behavior.

        Creates a random walk with drift, volume patterns, and
        realistic open/high/low/close relationships.

        Args:
            n_days: Number of trading days to generate.
            seed: Random seed for reproducibility.

        Returns:
            DataFrame with columns: date, open, high, low, close, volume.
        """
        rng = np.random.default_rng(seed)
        dates = pd.bdate_range(end="2026-02-20", periods=n_days, freq="B")

        # Random walk for close prices (starting at $100)
        daily_returns = rng.normal(0.0004, 0.015, n_days)
        close_prices = 100.0 * np.cumprod(1 + daily_returns)

        # Derive OHLC from close
        open_prices = close_prices * (1 + rng.normal(0, 0.005, n_days))
        high_prices = np.maximum(open_prices, close_prices) * (1 + np.abs(rng.normal(0, 0.008, n_days)))
        low_prices = np.minimum(open_prices, close_prices) * (1 - np.abs(rng.normal(0, 0.008, n_days)))
        volumes = rng.lognormal(17, 0.5, n_days).astype(int)  # ~24M avg volume

        df = pd.DataFrame({
            "date": dates,
            "open": np.round(open_prices, 2),
            "high": np.round(high_prices, 2),
            "low": np.round(low_prices, 2),
            "close": np.round(close_prices, 2),
            "volume": volumes,
        })

        logger.info(f"Generated mock OHLCV: {len(df)} days, price range ${df['close'].min():.2f}-${df['close'].max():.2f}")
        self._ohlcv_df = df
        return df

    def _load_emery(self) -> pd.DataFrame:
        """Load Emery S&P 500 10-year OHLCV data.

        Looks for CSV files in data/raw/ matching Emery naming conventions.
        Per SCHEMA.md, the raw data is 1-minute bars which will need
        daily aggregation.

        Returns:
            DataFrame with daily OHLCV data.
        """
        emery_files = sorted(self.data_dir.glob("*emery*")) + sorted(self.data_dir.glob("*sp500*"))
        if not emery_files:
            raise FileNotFoundError(
                f"No Emery data files found in {self.data_dir}. "
                f"Expected CSV files with 'emery' or 'sp500' in the filename. "
                f"Place Emery OHLCV data in {self.data_dir}/ to proceed."
            )

        logger.info(f"Loading Emery data from {emery_files[0]}")
        df = self._load_csv(emery_files[0])

        # If minute-bar data, aggregate to daily
        if "window_start" in df.columns or "ticker" in df.columns:
            logger.info("Detected minute-bar format, aggregating to daily OHLCV")
            df = self._aggregate_to_daily(df)

        self._ohlcv_df = df
        return df

    def _load_dow_jones(self) -> pd.DataFrame:
        """Load Dow Jones 1928-2009 historical data.

        Per data/raw/SCHEMA.md: CSV with Date, Open, High, Low, Close,
        Volume, Adj Close columns. 20,204 trading days.

        Returns:
            DataFrame with daily OHLCV data.
        """
        dow_files = sorted(self.data_dir.glob("*dow*")) + sorted(self.data_dir.glob("*djia*"))
        if not dow_files:
            raise FileNotFoundError(
                f"No Dow Jones data files found in {self.data_dir}. "
                f"Expected CSV files with 'dow' or 'djia' in the filename. "
                f"Place Dow Jones CSV in {self.data_dir}/ to proceed."
            )

        logger.info(f"Loading Dow Jones data from {dow_files[0]}")
        df = self._load_csv(dow_files[0])
        self._ohlcv_df = df
        return df

    def _load_csv(self, path: Path) -> pd.DataFrame:
        """Load a CSV file and normalize column names to lowercase OHLCV format.

        Args:
            path: Path to the CSV file.

        Returns:
            DataFrame with columns: date, open, high, low, close, volume.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If required columns are missing.
        """
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")

        df = pd.read_csv(path)
        # Normalize column names
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        # Map common aliases
        col_map = {
            "adj_close": "adj_close",
            "adj close": "adj_close",
            "adjclose": "adj_close",
        }
        df = df.rename(columns=col_map)

        # Ensure required columns exist
        required = {"date", "open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                f"CSV missing required columns: {missing}. "
                f"Found columns: {list(df.columns)}"
            )

        # Parse dates
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        logger.info(
            f"Loaded {len(df)} rows from {path.name}, "
            f"date range: {df['date'].iloc[0].date()} to {df['date'].iloc[-1].date()}"
        )
        return df

    def _aggregate_to_daily(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate minute-bar data to daily OHLCV.

        Per Emery data schema: columns include ticker, volume, open, close,
        high, low, window_start (nanosecond epoch), transactions.

        Args:
            df: Minute-bar DataFrame.

        Returns:
            Daily OHLCV DataFrame.
        """
        if "window_start" in df.columns:
            df["date"] = pd.to_datetime(df["window_start"], unit="ns")
        df["date"] = df["date"].dt.date
        df["date"] = pd.to_datetime(df["date"])

        daily = df.groupby("date").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }).reset_index()

        return daily.sort_values("date").reset_index(drop=True)

    def _prepare_features_and_labels(self, ohlcv_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        """Build features and labels from OHLCV data.

        Uses FeatureEngineer.build_features() for the 12 technical indicators
        and FeatureEngineer.build_labels() for 5-day forward return direction.

        Aligns features and labels by index after dropping NaN rows.

        Args:
            ohlcv_df: OHLCV DataFrame.

        Returns:
            (features_df, labels_series) with aligned indices.
        """
        features = self.feature_engineer.build_features(ohlcv_df)
        labels = self.feature_engineer.build_labels(ohlcv_df)

        # Align: features has fewer rows due to rolling window warm-up
        # Labels also has NaN for last 5 rows (forward return)
        # Align on the original DataFrame index
        feature_start_idx = len(ohlcv_df) - len(features)
        aligned_labels = labels.iloc[feature_start_idx:feature_start_idx + len(features)].reset_index(drop=True)

        # Drop any remaining NaN labels (last 5 rows)
        valid_mask = ~aligned_labels.isna()
        features_clean = features[valid_mask].reset_index(drop=True)
        labels_clean = aligned_labels[valid_mask].reset_index(drop=True)

        logger.info(
            f"Features: {features_clean.shape}, Labels: {len(labels_clean)}, "
            f"label distribution: up={int(labels_clean.sum())}, "
            f"down={int(len(labels_clean) - labels_clean.sum())}"
        )

        self._features = features_clean
        self._labels = labels_clean
        return features_clean, labels_clean

    def run_full_pipeline(
        self,
        source: str = "emery",
        walk_forward_kwargs: dict | None = None,
        cross_val_kwargs: dict | None = None,
    ) -> dict:
        """Execute the complete training pipeline for all Tier 1 models.

        Steps:
            1. Load OHLCV data from source
            2. Feature engineering (12 technical indicators)
            3. Train all 4 Tier 1 models
            4. Run walk-forward validation on each
            5. Save trained models to output_dir
            6. Update manifests with real training metadata
            7. Generate comparison report

        Args:
            source: Data source identifier ("emery", "dow_jones", "mock", or path).
            walk_forward_kwargs: Override defaults for WalkForwardValidator.
            cross_val_kwargs: Override defaults for TimeSeriesCrossValidator.

        Returns:
            Dict with training results, validation metrics, and comparison.
        """
        started_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"=== Training Pipeline Started ({source}) ===")

        # Step 1: Load data
        ohlcv_df = self.load_data(source)
        data_range = f"{ohlcv_df['date'].iloc[0].date()} to {ohlcv_df['date'].iloc[-1].date()}"

        # Step 2: Feature engineering
        features_df, labels = self._prepare_features_and_labels(ohlcv_df)

        # Extract numpy arrays for training (exclude date column)
        feature_cols = [c for c in features_df.columns if c != "date"]
        X = features_df[feature_cols].values
        y = labels.values

        # Step 3-4: Train each model and validate
        wf_kwargs = walk_forward_kwargs or {}
        validator = WalkForwardValidator(**wf_kwargs)
        comparison = ModelComparison()

        for model_name in TIER_1_MODELS:
            logger.info(f"--- Training {model_name} ---")
            result = self.run_single_model(
                model_name=model_name,
                features=X,
                labels=y,
                ohlcv_df=ohlcv_df,
                validator=validator,
                data_range=data_range,
            )
            self._results[model_name] = result
            if "validation" in result and "metrics" in result["validation"]:
                comparison.add_result(model_name, result["validation"]["metrics"])

        # Step 5: Save models
        self._save_all_models()

        # Step 6: Generate manifests
        manifests = self._generate_manifests(data_range)

        # Step 7: Comparison report
        comparison_report = comparison.summary_table()
        best = comparison.best_model(metric="sharpe_ratio")

        # Optional cross-validation
        cv_results = {}
        if cross_val_kwargs is not None:
            cv = TimeSeriesCrossValidator(**cross_val_kwargs)
            for model_name in ["xgboost", "elastic_net"]:
                model_class, _ = MODEL_REGISTRY[model_name]
                cv_result = cv.cross_validate(
                    model_class=model_class,
                    model_params={},
                    features=X,
                    labels=y,
                    model_name=model_name,
                )
                cv_results[model_name] = cv_result

        finished_at = datetime.now(timezone.utc).isoformat()
        logger.info("=== Training Pipeline Complete ===")
        logger.info(f"Best model by Sharpe: {best}")

        return {
            "pipeline_run": {
                "started_at": started_at,
                "finished_at": finished_at,
                "source": source,
                "data_range": data_range,
                "total_samples": len(ohlcv_df),
                "feature_samples": len(X),
                "use_mock": self.use_mock or source == "mock",
            },
            "model_results": self._results,
            "manifests": manifests,
            "comparison": comparison_report,
            "best_model": best,
            "cross_validation": cv_results if cv_results else None,
        }

    def run_single_model(
        self,
        model_name: str,
        features: np.ndarray | None = None,
        labels: np.ndarray | None = None,
        ohlcv_df: pd.DataFrame | None = None,
        validator: WalkForwardValidator | None = None,
        data_range: str = "",
    ) -> dict:
        """Train and validate a single model.

        Handles the different input requirements per model type:
        - XGBoost/Elastic Net: features + labels
        - ARIMA: close price series
        - Sentiment: no training data needed (API-based)

        Args:
            model_name: One of "xgboost", "elastic_net", "arima", "sentiment".
            features: Feature array for feature-based models.
            labels: Label array for feature-based models.
            ohlcv_df: OHLCV DataFrame for ARIMA.
            validator: WalkForwardValidator instance.
            data_range: Data range string for manifest.

        Returns:
            Dict with training metrics, validation results, and model reference.
        """
        if model_name not in MODEL_REGISTRY:
            raise ValueError(f"Unknown model: {model_name}. Valid: {list(MODEL_REGISTRY.keys())}")

        model_class, model_type = MODEL_REGISTRY[model_name]
        result = {"model_name": model_name, "model_type": model_type}

        if model_type == "feature_based":
            if features is None or labels is None:
                raise ValueError(f"Features and labels required for {model_name}")

            model = model_class()

            # Train with 60/40 split for initial metrics
            split_idx = int(len(features) * 0.6)
            X_train, y_train = features[:split_idx], labels[:split_idx]
            X_val, y_val = features[split_idx:], labels[split_idx:]

            train_metrics = model.train(X_train, y_train, X_val, y_val)
            result["training_metrics"] = train_metrics

            # Walk-forward validation
            if validator is not None:
                wf_result = validator.run_walk_forward(
                    model=model_class(),  # fresh instance for clean validation
                    features=features,
                    labels=labels,
                    model_name=model_name,
                )
                result["validation"] = {
                    "method": "walk_forward",
                    "metrics": wf_result.metrics,
                    "total_steps": wf_result.total_steps,
                    "total_predictions": wf_result.total_predictions,
                }
                result["manifest_report"] = generate_validation_report(wf_result)

            result["model_instance"] = model

        elif model_type == "time_series":
            model = model_class()

            if ohlcv_df is not None:
                close_series = ohlcv_df["close"].values

                # Train on first 60%
                split_idx = int(len(close_series) * 0.6)
                train_series = close_series[:split_idx]
                train_metrics = model.train(train_series)
                result["training_metrics"] = train_metrics

                # Walk-forward validation for ARIMA
                # Use an adapter wrapper that matches the expected interface
                if validator is not None and labels is not None and features is not None:
                    arima_adapter = _ARIMAWalkForwardAdapter(close_series)
                    wf_result = validator.run_walk_forward(
                        model=arima_adapter,
                        features=features,
                        labels=labels,
                        model_name=model_name,
                    )
                    result["validation"] = {
                        "method": "walk_forward",
                        "metrics": wf_result.metrics,
                        "total_steps": wf_result.total_steps,
                        "total_predictions": wf_result.total_predictions,
                    }
                    result["manifest_report"] = generate_validation_report(wf_result)
            else:
                result["training_metrics"] = {"note": "No OHLCV data provided for ARIMA training"}

            result["model_instance"] = model

        elif model_type == "sentiment":
            model = model_class()
            result["training_metrics"] = {
                "note": "Sentiment model is API-based, no training data required",
                "sources": ["finnhub", "newsapi"],
            }

            # For walk-forward, sentiment returns 0.5 (no API keys in training)
            if validator is not None and features is not None and labels is not None:
                sentiment_adapter = _SentimentWalkForwardAdapter()
                wf_result = validator.run_walk_forward(
                    model=sentiment_adapter,
                    features=features,
                    labels=labels,
                    model_name=model_name,
                )
                result["validation"] = {
                    "method": "walk_forward",
                    "metrics": wf_result.metrics,
                    "total_steps": wf_result.total_steps,
                    "total_predictions": wf_result.total_predictions,
                    "note": "Sentiment validated with neutral predictions (no API keys during training)",
                }
                result["manifest_report"] = generate_validation_report(wf_result)

            result["model_instance"] = model

        return result

    def _save_all_models(self) -> None:
        """Save all trained model artifacts to output_dir.

        Creates output_dir if it doesn't exist. Each model is saved
        using its native serialization (joblib for sklearn, pickle for
        statsmodels, JSON for sentiment config).
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        for model_name, result in self._results.items():
            model = result.get("model_instance")
            if model is None:
                continue

            model_path = self.output_dir / f"{model_name}_model"
            try:
                if model_name == "xgboost":
                    model.save(model_path.with_suffix(".joblib"))
                elif model_name == "elastic_net":
                    model.save(model_path.with_suffix(".joblib"))
                elif model_name == "arima":
                    model.save(model_path.with_suffix(".pkl"))
                elif model_name == "sentiment":
                    model.save(model_path.with_suffix(".json"))
                logger.info(f"Saved {model_name} to {model_path}")
            except Exception as e:
                logger.warning(f"Failed to save {model_name}: {e}")

    def _generate_manifests(self, data_range: str) -> dict:
        """Generate model manifests per PROJECT_STANDARDS_v2.md Section 2.

        Updates the pre-training manifests with real training metadata,
        validation results, and holdout period. Saves each manifest as
        a JSON file alongside the model artifact.

        Args:
            data_range: Training data date range string.

        Returns:
            Dict of model_name -> manifest.
        """
        manifests = {}
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        for model_name, result in self._results.items():
            model = result.get("model_instance")
            if model is None:
                continue

            manifest = model.get_manifest()

            # Update with training metadata
            manifest["trained_date"] = today
            manifest["training_data_range"] = data_range
            manifest["survivorship_bias_audited"] = False

            # Add validation results if available
            if "manifest_report" in result:
                report = result["manifest_report"]
                manifest["validation_results"] = report.get("validation_results", {})
                manifest["extended_validation"] = report.get("extended_metrics", {})

            # Set holdout period from data range
            if data_range:
                manifest["holdout_period"] = "walk_forward_expanding_from_60pct"

            manifests[model_name] = manifest

            # Save manifest JSON
            manifest_path = self.output_dir / f"{model_name}_manifest.json"
            try:
                self.output_dir.mkdir(parents=True, exist_ok=True)
                # Remove non-serializable model_instance before saving
                save_manifest = {k: v for k, v in manifest.items() if k != "model_instance"}
                with open(manifest_path, "w") as f:
                    json.dump(save_manifest, f, indent=2, default=str)
                logger.info(f"Manifest saved: {manifest_path}")
            except Exception as e:
                logger.warning(f"Failed to save manifest for {model_name}: {e}")

        return manifests

    def compare_models(self) -> dict:
        """Generate a comparison table of all trained models.

        Returns:
            ModelComparison summary dict.
        """
        comparison = ModelComparison()
        for model_name, result in self._results.items():
            if "validation" in result and "metrics" in result["validation"]:
                comparison.add_result(model_name, result["validation"]["metrics"])

        return {
            "summary": comparison.summary_table(),
            "best_by_sharpe": comparison.best_model("sharpe_ratio"),
            "best_by_accuracy": comparison.best_model("accuracy"),
            "best_by_win_rate": comparison.best_model("win_rate"),
        }


# ---------------------------------------------------------------------------
# Walk-forward adapters for non-standard model interfaces
# ---------------------------------------------------------------------------


class _ARIMAWalkForwardAdapter:
    """Adapter to make ARIMA compatible with WalkForwardValidator interface.

    ARIMA operates on raw close prices, not feature arrays. This adapter
    maps from the feature-based walk-forward interface to ARIMA's series-based
    interface by maintaining the original close price series.
    """

    def __init__(self, close_series: np.ndarray):
        self._close_series = close_series
        self._arima = ARIMAModel()
        self._current_train_end = 0

    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> dict:
        """Train ARIMA on the close price series up to the current train window."""
        self._current_train_end = len(X_train)
        # Use the close series up to the training window boundary
        # The feature array length is shorter than OHLCV due to rolling windows,
        # but we approximate by training on the first N close prices
        train_end = min(self._current_train_end + 50, len(self._close_series))
        train_series = self._close_series[:train_end]
        return self._arima.train(train_series)

    def predict(self, features: np.ndarray) -> float:
        """Predict using the current ARIMA model."""
        # Use the close series up to the approximate current point
        train_end = min(self._current_train_end + 50, len(self._close_series))
        series = self._close_series[:train_end]
        return self._arima.predict(series)


class _SentimentWalkForwardAdapter:
    """Adapter for SentimentModel in walk-forward validation.

    Sentiment is API-based and cannot be meaningfully backtested on
    historical OHLCV data alone. This adapter returns neutral (0.5)
    predictions as a baseline. Real sentiment validation requires
    historical news data.
    """

    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> dict:
        """No-op training for sentiment."""
        return {"note": "Sentiment model does not train on OHLCV features"}

    def predict(self, features: np.ndarray) -> float:
        """Return neutral prediction (no API keys during training)."""
        return 0.5


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Wasden Watch quant model training pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.intelligence.quant_models.train_pipeline --data mock --output models/trained/
  python -m src.intelligence.quant_models.train_pipeline --data emery --output models/trained/
  python -m src.intelligence.quant_models.train_pipeline --data dow_jones --output models/trained/
  python -m src.intelligence.quant_models.train_pipeline --data /path/to/data.csv --model xgboost
        """,
    )
    parser.add_argument(
        "--data", "-d",
        required=True,
        help="Data source: 'emery', 'dow_jones', 'mock', or path to CSV",
    )
    parser.add_argument(
        "--output", "-o",
        default="models/trained/",
        help="Output directory for trained models (default: models/trained/)",
    )
    parser.add_argument(
        "--model", "-m",
        choices=list(MODEL_REGISTRY.keys()),
        default=None,
        help="Train a single model instead of all Tier 1 models",
    )
    parser.add_argument(
        "--step-size",
        type=int,
        default=20,
        help="Walk-forward step size in trading days (default: 20)",
    )
    parser.add_argument(
        "--retrain-every",
        type=int,
        default=60,
        help="Retrain interval in trading days (default: 60)",
    )
    parser.add_argument(
        "--initial-train-pct",
        type=float,
        default=0.60,
        help="Initial training set percentage (default: 0.60)",
    )
    parser.add_argument(
        "--cross-validate",
        action="store_true",
        help="Also run time-series cross-validation (slower)",
    )
    parser.add_argument(
        "--cv-splits",
        type=int,
        default=5,
        help="Number of cross-validation splits (default: 5)",
    )
    parser.add_argument(
        "--cv-gap",
        type=int,
        default=5,
        help="Gap days between CV train/test sets (default: 5)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict:
    """Main entry point for the training pipeline CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv).

    Returns:
        Pipeline results dict.
    """
    args = _parse_args(argv)

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    use_mock = args.data == "mock"
    pipeline = TrainingPipeline(
        output_dir=args.output,
        use_mock=use_mock,
    )

    walk_forward_kwargs = {
        "initial_train_pct": args.initial_train_pct,
        "step_size": args.step_size,
        "retrain_every": args.retrain_every,
    }

    cross_val_kwargs = None
    if args.cross_validate:
        cross_val_kwargs = {
            "n_splits": args.cv_splits,
            "gap_days": args.cv_gap,
        }

    if args.model:
        # Single model mode
        ohlcv_df = pipeline.load_data(args.data)
        features_df, labels = pipeline._prepare_features_and_labels(ohlcv_df)
        feature_cols = [c for c in features_df.columns if c != "date"]
        X = features_df[feature_cols].values
        y = labels.values

        validator = WalkForwardValidator(**walk_forward_kwargs)
        result = pipeline.run_single_model(
            model_name=args.model,
            features=X,
            labels=y,
            ohlcv_df=ohlcv_df,
            validator=validator,
        )

        # Print summary
        print(f"\n{'=' * 60}")
        print(f"Model: {args.model}")
        print(f"{'=' * 60}")
        if "validation" in result and "metrics" in result["validation"]:
            metrics = result["validation"]["metrics"]
            print(f"  Accuracy:     {metrics.get('accuracy', 0):.4f}")
            print(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.4f}")
            print(f"  Win Rate:     {metrics.get('win_rate', 0):.4f}")
            print(f"  Max Drawdown: {metrics.get('max_drawdown', 0):.4f}")
            print(f"  F1 Score:     {metrics.get('f1', 0):.4f}")
            print(f"  IC:           {metrics.get('information_coefficient', 0):.4f}")
        return {"single_model": result}

    else:
        # Full pipeline mode
        results = pipeline.run_full_pipeline(
            source=args.data,
            walk_forward_kwargs=walk_forward_kwargs,
            cross_val_kwargs=cross_val_kwargs,
        )

        # Print comparison table
        print(f"\n{'=' * 80}")
        print("WASDEN WATCH QUANT MODEL TRAINING RESULTS")
        print(f"{'=' * 80}")
        print(f"Data source: {args.data}")
        print(f"Data range:  {results['pipeline_run']['data_range']}")
        print(f"Samples:     {results['pipeline_run']['feature_samples']}")
        print(f"Best model:  {results['best_model']}")
        print()

        comparison = results.get("comparison", {})
        if isinstance(comparison, list):
            # Print formatted table
            header = f"{'Model':<15} {'Accuracy':>10} {'Sharpe':>10} {'Win Rate':>10} {'Max DD':>10} {'F1':>10} {'IC':>10}"
            print(header)
            print("-" * len(header))
            for row in comparison:
                print(
                    f"{row['model']:<15} "
                    f"{row.get('accuracy', 0):>10.4f} "
                    f"{row.get('sharpe_ratio', 0):>10.4f} "
                    f"{row.get('win_rate', 0):>10.4f} "
                    f"{row.get('max_drawdown', 0):>10.4f} "
                    f"{row.get('f1', 0):>10.4f} "
                    f"{row.get('information_coefficient', 0):>10.4f}"
                )

        return results


if __name__ == "__main__":
    main()
