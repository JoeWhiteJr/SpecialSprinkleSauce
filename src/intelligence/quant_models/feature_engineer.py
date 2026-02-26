"""Feature engineering for quant models — technical indicators from OHLCV data."""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger("wasden_watch.quant_models.feature_engineer")


class FeatureEngineer:
    """Builds ML features from OHLCV and fundamentals data."""

    @staticmethod
    def build_features(ohlcv_df: pd.DataFrame, fundamentals_dict: dict | None = None) -> pd.DataFrame:
        """Build technical indicator features from OHLCV data.

        Args:
            ohlcv_df: DataFrame with columns: date, open, high, low, close, volume.
            fundamentals_dict: Optional dict of fundamental metrics.

        Returns:
            DataFrame with feature columns, indexed by date.
        """
        df = ohlcv_df.copy().sort_values("date").reset_index(drop=True)

        # SMA crossovers
        df["sma_5"] = df["close"].rolling(5).mean()
        df["sma_20"] = df["close"].rolling(20).mean()
        df["sma_50"] = df["close"].rolling(50).mean()
        df["sma_5_20_cross"] = (df["sma_5"] - df["sma_20"]) / df["sma_20"]
        df["sma_20_50_cross"] = (df["sma_20"] - df["sma_50"]) / df["sma_50"]

        # RSI-14
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        df["rsi_14"] = 100 - (100 / (1 + rs))

        # MACD (12, 26, 9)
        ema_12 = df["close"].ewm(span=12, adjust=False).mean()
        ema_26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = ema_12 - ema_26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_histogram"] = df["macd"] - df["macd_signal"]

        # Bollinger Bands (20, 2)
        bb_mid = df["close"].rolling(20).mean()
        bb_std = df["close"].rolling(20).std()
        df["bb_upper"] = bb_mid + 2 * bb_std
        df["bb_lower"] = bb_mid - 2 * bb_std
        df["bb_position"] = (df["close"] - bb_mid) / (2 * bb_std)

        # Returns
        df["return_1d"] = df["close"].pct_change(1)
        df["return_5d"] = df["close"].pct_change(5)
        df["return_20d"] = df["close"].pct_change(20)

        # Volatility (20-day rolling std of daily returns)
        df["volatility_20d"] = df["return_1d"].rolling(20).std()

        # Volume ratio
        df["volume_ratio"] = df["volume"] / df["volume"].rolling(20).mean()

        # Drop rows with NaN from rolling calculations
        feature_cols = [
            "sma_5_20_cross", "sma_20_50_cross", "rsi_14",
            "macd", "macd_signal", "macd_histogram",
            "bb_position", "return_1d", "return_5d", "return_20d",
            "volatility_20d", "volume_ratio",
        ]

        result = df[["date"] + feature_cols].dropna().reset_index(drop=True)
        return result

    @staticmethod
    def build_labels(ohlcv_df: pd.DataFrame, forward_days: int = 5) -> pd.Series:
        """Build binary labels: 1=up, 0=down based on forward return direction.

        Args:
            ohlcv_df: DataFrame with columns: date, close.
            forward_days: Number of days to look ahead.

        Returns:
            Series of 0/1 labels.
        """
        df = ohlcv_df.copy().sort_values("date").reset_index(drop=True)
        forward_return = df["close"].shift(-forward_days) / df["close"] - 1
        labels = (forward_return > 0).astype(int)
        return labels

    @staticmethod
    def train_test_split(
        features: pd.DataFrame,
        labels: pd.Series,
        holdout_start: str = "2025-10-01",
    ) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        """Split features and labels into train/validation sets.

        Args:
            features: Feature DataFrame with a 'date' column.
            labels: Label Series aligned with features.
            holdout_start: Date string for start of holdout period.

        Returns:
            (X_train, y_train, X_val, y_val)
        """
        holdout_date = pd.Timestamp(holdout_start)
        mask_train = features["date"] < holdout_date
        mask_val = features["date"] >= holdout_date

        feature_cols = [c for c in features.columns if c != "date"]
        X_train = features.loc[mask_train, feature_cols]
        y_train = labels.loc[mask_train]
        X_val = features.loc[mask_val, feature_cols]
        y_val = labels.loc[mask_val]

        return X_train, y_train, X_val, y_val

    @staticmethod
    def generate_mock_features(n_rows: int = 200, seed: int = 42) -> pd.DataFrame:
        """Generate synthetic features for mock mode.

        Args:
            n_rows: Number of rows to generate.
            seed: Random seed for reproducibility.

        Returns:
            DataFrame with mock feature values.
        """
        rng = np.random.default_rng(seed)
        dates = pd.date_range(end="2026-02-21", periods=n_rows, freq="B")

        return pd.DataFrame({
            "date": dates,
            "sma_5_20_cross": rng.normal(0.01, 0.03, n_rows),
            "sma_20_50_cross": rng.normal(0.005, 0.02, n_rows),
            "rsi_14": rng.uniform(20, 80, n_rows),
            "macd": rng.normal(0, 2, n_rows),
            "macd_signal": rng.normal(0, 1.5, n_rows),
            "macd_histogram": rng.normal(0, 0.5, n_rows),
            "bb_position": rng.normal(0, 0.5, n_rows),
            "return_1d": rng.normal(0.001, 0.02, n_rows),
            "return_5d": rng.normal(0.005, 0.04, n_rows),
            "return_20d": rng.normal(0.02, 0.08, n_rows),
            "volatility_20d": rng.uniform(0.01, 0.05, n_rows),
            "volume_ratio": rng.lognormal(0, 0.3, n_rows),
        })
