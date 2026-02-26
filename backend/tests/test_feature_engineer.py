"""Unit tests for feature engineering — technical indicators from OHLCV data.

All tests use mock/synthetic data. No database, no API calls.
"""

import os

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.intelligence.quant_models.feature_engineer import FeatureEngineer  # noqa: E402


# ---------------------------------------------------------------------------
# Helper: build synthetic OHLCV data
# ---------------------------------------------------------------------------

def _make_ohlcv(n_rows: int = 200, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV data for testing."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end="2026-02-21", periods=n_rows, freq="B")

    # Random-walk close prices
    close = 100 + np.cumsum(rng.normal(0.1, 2.0, n_rows))
    close = np.maximum(close, 10.0)  # floor at $10

    return pd.DataFrame({
        "date": dates,
        "open": close + rng.normal(0, 0.5, n_rows),
        "high": close + abs(rng.normal(1, 0.5, n_rows)),
        "low": close - abs(rng.normal(1, 0.5, n_rows)),
        "close": close,
        "volume": rng.integers(500_000, 10_000_000, n_rows),
    })


# ===========================================================================
# Feature building tests
# ===========================================================================

def test_build_features_output_shape():
    """build_features produces correct number of columns."""
    ohlcv = _make_ohlcv()
    features = FeatureEngineer.build_features(ohlcv)

    expected_columns = [
        "date", "sma_5_20_cross", "sma_20_50_cross", "rsi_14",
        "macd", "macd_signal", "macd_histogram",
        "bb_position", "return_1d", "return_5d", "return_20d",
        "volatility_20d", "volume_ratio",
    ]
    assert list(features.columns) == expected_columns
    # After dropping NaN rows from rolling windows (max window=50),
    # should have n_rows - 50 or so rows remaining
    assert len(features) > 0
    assert len(features) < len(ohlcv)


def test_build_features_no_nans():
    """No NaN values in feature output (after dropping insufficient rows)."""
    ohlcv = _make_ohlcv(n_rows=300)
    features = FeatureEngineer.build_features(ohlcv)
    # Exclude the date column for NaN check
    numeric_cols = [c for c in features.columns if c != "date"]
    nan_count = features[numeric_cols].isna().sum().sum()
    assert nan_count == 0, f"Found {nan_count} NaN values in features"


def test_build_labels_binary():
    """Labels are 0 or 1 only."""
    ohlcv = _make_ohlcv()
    labels = FeatureEngineer.build_labels(ohlcv)
    # Drop NaN from forward-looking shift
    labels_clean = labels.dropna()
    unique_vals = set(labels_clean.unique())
    assert unique_vals.issubset({0, 1}), f"Labels contain non-binary values: {unique_vals}"


def test_build_labels_forward_days():
    """Labels use forward_days parameter correctly."""
    ohlcv = _make_ohlcv()
    labels_5 = FeatureEngineer.build_labels(ohlcv, forward_days=5)
    labels_10 = FeatureEngineer.build_labels(ohlcv, forward_days=10)
    # Different forward_days should produce different label distributions
    assert len(labels_5) == len(labels_10) == len(ohlcv)
    # Labels should differ for at least some rows
    assert not labels_5.equals(labels_10)


def test_train_test_split_no_overlap():
    """No index overlap between train and test sets."""
    # Use mock features which have aligned dates and no NaN issues
    features = FeatureEngineer.generate_mock_features(n_rows=300, seed=42)
    # Generate labels as a simple binary series aligned with features
    rng = np.random.default_rng(42)
    labels = pd.Series(rng.integers(0, 2, len(features)), index=features.index)

    X_train, y_train, X_val, y_val = FeatureEngineer.train_test_split(
        features, labels, holdout_start="2025-10-01",
    )

    # No overlapping indices
    train_idx = set(X_train.index)
    val_idx = set(X_val.index)
    assert train_idx.isdisjoint(val_idx), "Train and val sets have overlapping indices"

    # Both sets are non-empty
    assert len(X_train) > 0, "Train set is empty"
    assert len(X_val) > 0, "Validation set is empty"

    # Train labels and val labels align
    assert len(X_train) == len(y_train)
    assert len(X_val) == len(y_val)

    # Total rows add up
    assert len(X_train) + len(X_val) == len(features)


def test_mock_features_deterministic():
    """generate_mock_features with seed=42 produces same output every time."""
    df1 = FeatureEngineer.generate_mock_features(n_rows=100, seed=42)
    df2 = FeatureEngineer.generate_mock_features(n_rows=100, seed=42)

    pd.testing.assert_frame_equal(df1, df2)


def test_mock_features_different_seeds():
    """Different seeds produce different output."""
    df1 = FeatureEngineer.generate_mock_features(n_rows=50, seed=42)
    df2 = FeatureEngineer.generate_mock_features(n_rows=50, seed=99)

    # At least one column should differ
    assert not df1.drop(columns=["date"]).equals(df2.drop(columns=["date"]))


# ===========================================================================
# Specific indicator range tests
# ===========================================================================

def test_rsi_range():
    """RSI values are between 0 and 100."""
    ohlcv = _make_ohlcv(n_rows=300)
    features = FeatureEngineer.build_features(ohlcv)
    rsi_values = features["rsi_14"].dropna()
    assert rsi_values.min() >= 0, f"RSI below 0: {rsi_values.min()}"
    assert rsi_values.max() <= 100, f"RSI above 100: {rsi_values.max()}"


def test_sma_crossover_numeric():
    """SMA crossover values are numeric (float) ratios."""
    ohlcv = _make_ohlcv()
    features = FeatureEngineer.build_features(ohlcv)
    # SMA crossover is a ratio ((sma5 - sma20) / sma20), not binary
    # It should be a float value, typically small
    sma_cross = features["sma_5_20_cross"]
    assert sma_cross.dtype in [np.float64, np.float32, float]
    # Values should generally be in a reasonable range
    assert sma_cross.abs().max() < 1.0, "SMA crossover ratio seems too large"


def test_volume_ratio_positive():
    """Volume ratio is always positive."""
    ohlcv = _make_ohlcv()
    features = FeatureEngineer.build_features(ohlcv)
    vr = features["volume_ratio"]
    assert (vr > 0).all(), "Volume ratio has non-positive values"
