"""Miller Neural Networks — DowSmall1a and DowLarger1a ports from R to Python (PyTorch).

Ported from DowSmall1a.Rmd architecture specification (models/miller_nn/DowSmall1a_Architecture.txt).
The original R source file (DowSmall1a.Rmd) was not found in the repository; this implementation
was built from the architecture documentation and PROJECT_STANDARDS_v2.md Section 2.

Architecture (from Dr. Miller):
    Input:  5 neurons (Open_Lag0, Open_Lag1, Open_Lag2, Open_Lag3, Open_Lag4)
    Hidden: Layer 1 = 5 neurons (sigmoid), Layer 2 = 3 neurons (sigmoid)
    Output: 1 neuron (linear) — predicted closing price (scaled [0, 1])

The R version uses the neuralnet package with:
    - Activation: logistic (sigmoid) on hidden layers, linear on output
    - Training: resilient backpropagation (rprop+)
    - Convergence threshold: 0.01
    - Normalization: global min-max across Open and Close columns
    - Train/test split: 80/20 random (known limitation — see LIMITATIONS below)

This Python port uses PyTorch to replicate the same architecture. Key adaptations for
Wasden Watch integration (per PROJECT_STANDARDS_v2.md Section 2):
    - Output is converted from raw price prediction to directional confidence [0, 1]
      via: predicted_close > current_open => bullish (>0.5)
    - Model manifest includes survivorship_bias_audited flag
    - Tier 2 model — NOT included in Phase 1 ensemble

LIMITATIONS (inherited from R source, documented in Architecture.txt):
    1. Random train/test split introduces lookahead bias for time-series data
    2. Only opening prices as features — ignores volume, volatility, fundamentals
    3. Single-index scope (DJIA), not individual equities
    4. No cross-validation
    5. Static model — no automatic retraining
    6. Global min/max normalization may degrade on out-of-range inputs
"""

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from .mock_scores import get_mock_scores

logger = logging.getLogger("wasden_watch.quant_models.miller_nn")

# --- Architecture constants matching DowSmall1a.Rmd ---
INPUT_SIZE = 5           # Open_Lag0 through Open_Lag4
HIDDEN_LAYERS = [5, 3]   # Two hidden layers
OUTPUT_SIZE = 1           # Predicted close price (normalized)

# --- Training defaults matching R neuralnet() behavior ---
DEFAULT_PARAMS = {
    "hidden_layers": HIDDEN_LAYERS,
    "learning_rate": 0.01,
    "convergence_threshold": 0.01,   # R: threshold = 0.01
    "max_epochs": 10000,
    "train_split": 0.80,             # R: 80/20 random split
    "random_seed": 123,              # R: set.seed(123)
    "activation": "sigmoid",         # R: neuralnet default (logistic)
}

# Feature names matching the R lag engineering
FEATURE_NAMES = ["Open_Lag0", "Open_Lag1", "Open_Lag2", "Open_Lag3", "Open_Lag4"]

# --- DowLarger1a constants ---
LARGER_INPUT_SIZE = 6
LARGER_HIDDEN_LAYERS = [10, 8, 6]
LARGER_FEATURE_NAMES = [
    "Open_Lag0", "Open_Lag1", "Open_Lag2", "Open_Lag3", "Open_Lag4", "Close_Lag1",
]
LARGER_DEFAULT_PARAMS = {
    "hidden_layers": LARGER_HIDDEN_LAYERS,
    "threshold": 0.001,
    "stepmax": 10_000_000,
    "train_split": 0.80,
    "seed": 123,
    "optimizer": "Rprop",
}


def _build_lag_features(open_prices: np.ndarray, close_prices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Build lag features from raw Open/Close series, matching R's data preparation.

    Steps (per DowSmall1a_Architecture.txt Section 2):
        1. Create Open_Lag0 (current) through Open_Lag4 (4 days back)
        2. Target = current day's Close
        3. Drop first 4 rows (insufficient lag history)

    Args:
        open_prices: Array of daily opening prices, chronologically sorted.
        close_prices: Array of daily closing prices, chronologically sorted.

    Returns:
        (X, y) where X is (n_samples, 5) lag features, y is (n_samples,) close prices.
    """
    n = len(open_prices)
    if n < 5:
        raise ValueError(f"Need at least 5 data points for lag features, got {n}")

    X_rows = []
    y_rows = []
    for i in range(4, n):
        row = [
            open_prices[i],       # Open_Lag0 (today)
            open_prices[i - 1],   # Open_Lag1 (1 day ago)
            open_prices[i - 2],   # Open_Lag2 (2 days ago)
            open_prices[i - 3],   # Open_Lag3 (3 days ago)
            open_prices[i - 4],   # Open_Lag4 (4 days ago)
        ]
        X_rows.append(row)
        y_rows.append(close_prices[i])

    return np.array(X_rows, dtype=np.float64), np.array(y_rows, dtype=np.float64)


def _minmax_normalize(data: np.ndarray, min_val: float, max_val: float) -> np.ndarray:
    """Min-max normalize to [0, 1], matching R's normalization.

    Formula: x_scaled = (x - min) / (max - min)
    """
    denom = max_val - min_val
    if denom == 0:
        return np.zeros_like(data)
    return (data - min_val) / denom


def _minmax_denormalize(data: np.ndarray, min_val: float, max_val: float) -> np.ndarray:
    """Inverse min-max normalization back to original scale.

    Formula: x_original = x_scaled * (max - min) + min
    """
    return data * (max_val - min_val) + min_val


def _directional_confidence(current_open: float, predicted_close: float) -> float:
    """Convert predicted close price to directional confidence [0, 1].

    Per PROJECT_STANDARDS_v2.md Section 2 integration plan:
        predicted_close > current_price = bullish (> 0.5)
        predicted_close < current_price = bearish (< 0.5)

    Uses sigmoid scaling so +-2% price change maps to roughly [0.25, 0.75].

    Args:
        current_open: Today's opening price (un-normalized).
        predicted_close: Model's predicted closing price (un-normalized).

    Returns:
        Directional confidence in [0.0, 1.0]. 0.5 = neutral.
    """
    if current_open <= 0:
        return 0.5
    pct_change = (predicted_close - current_open) / current_open
    confidence = 1.0 / (1.0 + np.exp(-pct_change * 50))
    return float(np.clip(confidence, 0.0, 1.0))


class MillerNNSmall:
    """DowSmall1a neural network — 5-input MLP for DJIA close price prediction.

    This is a Tier 2 model (per PROJECT_STANDARDS_v2.md Section 2) and is NOT
    included in the Phase 1 ensemble. It is provided for validation, backtesting,
    and future integration once retrained on modern data.

    Architecture: 5 -> [5, 3] -> 1 (sigmoid hidden, linear output)
    Input: 5-day window of opening prices (Open_Lag0 through Open_Lag4)
    Output: Directional confidence [0, 1] (converted from raw close prediction)

    The model stores normalization parameters (min_val, max_val) from training
    and applies them consistently at inference time, matching the R implementation.
    """

    def __init__(self, params: dict | None = None):
        self._params = params or DEFAULT_PARAMS.copy()
        self._model = None
        self._version = "1.0.0"
        self._trained = False
        self._min_val: float | None = None
        self._max_val: float | None = None
        self._training_metrics: dict = {}

    def _build_network(self):
        """Construct the PyTorch network matching DowSmall1a topology.

        Architecture:
            Input(5) -> Linear(5,5) -> Sigmoid -> Linear(5,3) -> Sigmoid -> Linear(3,1)

        The R neuralnet package uses logistic (sigmoid) activation on hidden layers
        and linear output (linear.output=TRUE). This is replicated exactly.
        """
        try:
            import torch.nn as nn
        except ImportError:
            logger.error("PyTorch not installed. Install with: pip install torch")
            return None

        hidden = self._params.get("hidden_layers", HIDDEN_LAYERS)

        layers = []
        prev_size = INPUT_SIZE
        for h_size in hidden:
            layers.append(nn.Linear(prev_size, h_size))
            layers.append(nn.Sigmoid())
            prev_size = h_size
        layers.append(nn.Linear(prev_size, OUTPUT_SIZE))

        return nn.Sequential(*layers)

    def train(
        self,
        open_prices: np.ndarray,
        close_prices: np.ndarray,
    ) -> dict:
        """Train the neural network on OHLCV data, replicating DowSmall1a.Rmd pipeline.

        Full pipeline (matching R sections 2-5):
            1. Build lag features from open/close arrays
            2. Compute global min/max for normalization (across Open_Lag0 and Close)
            3. Min-max normalize all features and targets to [0, 1]
            4. Random 80/20 train/test split (seed=123)
            5. Train MLP with sigmoid hidden layers and linear output

        Args:
            open_prices: Array of daily opening prices, chronologically sorted.
            close_prices: Array of daily closing prices, chronologically sorted.

        Returns:
            Dict with training metrics (RMSE, MAPE, accuracy proxy, sample counts).
        """
        try:
            import torch
            import torch.nn as nn
            import torch.optim as optim
        except ImportError:
            logger.error("PyTorch not installed. Install with: pip install torch")
            return {"error": "torch not installed"}

        # Step 1: Build lag features
        X, y = _build_lag_features(open_prices, close_prices)
        logger.info(f"Built {len(X)} samples from {len(open_prices)} data points")

        # Step 2: Compute global min/max (R: across Open_Lag0 and Close)
        self._min_val = float(min(np.min(X[:, 0]), np.min(y)))
        self._max_val = float(max(np.max(X[:, 0]), np.max(y)))
        logger.info(f"Normalization range: [{self._min_val:.2f}, {self._max_val:.2f}]")

        # Step 3: Normalize
        X_norm = _minmax_normalize(X, self._min_val, self._max_val)
        y_norm = _minmax_normalize(y, self._min_val, self._max_val)

        # Step 4: Random 80/20 split (matching R: set.seed(123))
        rng = np.random.default_rng(self._params.get("random_seed", 123))
        n_samples = len(X_norm)
        split_ratio = self._params.get("train_split", 0.80)
        n_train = int(n_samples * split_ratio)
        indices = rng.permutation(n_samples)
        train_idx = indices[:n_train]
        test_idx = indices[n_train:]

        X_train = torch.tensor(X_norm[train_idx], dtype=torch.float32)
        y_train = torch.tensor(y_norm[train_idx].reshape(-1, 1), dtype=torch.float32)
        X_test = torch.tensor(X_norm[test_idx], dtype=torch.float32)
        y_test = torch.tensor(y_norm[test_idx].reshape(-1, 1), dtype=torch.float32)

        # Step 5: Build and train
        self._model = self._build_network()
        if self._model is None:
            return {"error": "Failed to build network"}

        criterion = nn.MSELoss()
        lr = self._params.get("learning_rate", 0.01)
        optimizer = optim.Adam(self._model.parameters(), lr=lr)

        threshold = self._params.get("convergence_threshold", 0.01)
        max_epochs = self._params.get("max_epochs", 10000)

        self._model.train()
        prev_loss = float("inf")
        for epoch in range(max_epochs):
            optimizer.zero_grad()
            output = self._model(X_train)
            loss = criterion(output, y_train)
            loss.backward()
            optimizer.step()

            current_loss = loss.item()
            if abs(prev_loss - current_loss) < threshold and epoch > 100:
                logger.info(f"Converged at epoch {epoch}, loss={current_loss:.6f}")
                break
            prev_loss = current_loss

            if epoch % 1000 == 0:
                logger.debug(f"Epoch {epoch}: loss={current_loss:.6f}")
        else:
            logger.info(f"Reached max epochs ({max_epochs}), final loss={current_loss:.6f}")

        self._trained = True

        # Step 6: Evaluate on test set (matching R Section 6)
        self._model.eval()
        with torch.no_grad():
            test_preds_norm = self._model(X_test).numpy().flatten()

        # Un-normalize for metrics
        test_preds = _minmax_denormalize(test_preds_norm, self._min_val, self._max_val)
        test_actual = _minmax_denormalize(y_test.numpy().flatten(), self._min_val, self._max_val)

        mse = float(np.mean((test_actual - test_preds) ** 2))
        rmse = float(np.sqrt(mse))
        mape = float(np.mean(np.abs((test_actual - test_preds) / np.where(test_actual == 0, 1, test_actual))) * 100)
        accuracy_proxy = 100.0 - mape

        self._training_metrics = {
            "train_samples": n_train,
            "test_samples": len(test_idx),
            "total_samples": n_samples,
            "rmse_dollars": round(rmse, 2),
            "mape_pct": round(mape, 4),
            "accuracy_proxy_pct": round(accuracy_proxy, 4),
            "epochs_trained": epoch + 1,
            "final_loss": round(current_loss, 6),
            "converged": epoch + 1 < max_epochs,
            "normalization_min": self._min_val,
            "normalization_max": self._max_val,
        }

        logger.info(
            f"DowSmall1a trained: RMSE=${rmse:.2f}, MAPE={mape:.2f}%, "
            f"Accuracy~{accuracy_proxy:.2f}%, {epoch + 1} epochs"
        )

        return self._training_metrics

    def predict(self, open_lags: np.ndarray | list[float]) -> float:
        """Predict directional confidence from a 5-value opening price window.

        Replicates R's predict_new_close() function (Section 7 of Architecture.txt)
        but converts the raw close prediction to directional confidence [0, 1].

        Args:
            open_lags: Exactly 5 values: [Open_Lag0, Open_Lag1, Open_Lag2,
                       Open_Lag3, Open_Lag4] (today's open first, oldest last).

        Returns:
            Directional confidence [0, 1]. >0.5 = bullish, <0.5 = bearish.
            Returns 0.5 if model not trained or input validation fails.
        """
        if self._model is None or not self._trained:
            logger.warning("Model not trained, returning 0.5")
            return 0.5

        try:
            import torch
        except ImportError:
            logger.error("PyTorch not installed")
            return 0.5

        open_lags = np.array(open_lags, dtype=np.float64).flatten()
        if len(open_lags) != INPUT_SIZE:
            logger.error(f"Expected {INPUT_SIZE} inputs, got {len(open_lags)}")
            return 0.5

        if self._min_val is None or self._max_val is None:
            logger.error("Normalization parameters not set")
            return 0.5

        # Normalize using training min/max (critical for consistency)
        normalized = _minmax_normalize(open_lags, self._min_val, self._max_val)

        # Forward pass
        self._model.eval()
        with torch.no_grad():
            x = torch.tensor(normalized.reshape(1, -1), dtype=torch.float32)
            pred_norm = self._model(x).item()

        # Un-normalize predicted close
        predicted_close = _minmax_denormalize(np.array([pred_norm]), self._min_val, self._max_val)[0]

        # Convert to directional confidence: predicted_close vs current open
        current_open = open_lags[0]
        confidence = _directional_confidence(current_open, predicted_close)

        logger.info(
            f"DowSmall1a predict: open={current_open:.2f}, "
            f"pred_close={predicted_close:.2f}, confidence={confidence:.3f}"
        )

        return confidence

    def predict_raw(self, open_lags: np.ndarray | list[float]) -> float:
        """Predict raw closing price (un-normalized), matching R's predict_new_close().

        This method returns the actual predicted close in dollars, before
        directional conversion. Useful for debugging and validation against R output.

        Args:
            open_lags: Exactly 5 values: [Open_Lag0..Open_Lag4].

        Returns:
            Predicted closing price in USD. Returns 0.0 if model not trained.
        """
        if self._model is None or not self._trained:
            logger.warning("Model not trained, returning 0.0")
            return 0.0

        try:
            import torch
        except ImportError:
            logger.error("PyTorch not installed")
            return 0.0

        open_lags = np.array(open_lags, dtype=np.float64).flatten()
        if len(open_lags) != INPUT_SIZE:
            logger.error(f"Expected {INPUT_SIZE} inputs, got {len(open_lags)}")
            return 0.0

        if self._min_val is None or self._max_val is None:
            logger.error("Normalization parameters not set")
            return 0.0

        normalized = _minmax_normalize(open_lags, self._min_val, self._max_val)

        self._model.eval()
        with torch.no_grad():
            x = torch.tensor(normalized.reshape(1, -1), dtype=torch.float32)
            pred_norm = self._model(x).item()

        return float(_minmax_denormalize(np.array([pred_norm]), self._min_val, self._max_val)[0])

    def predict_mock(self, ticker: str) -> float:
        """Return mock prediction from MOCK_QUANT_SCORES.

        Uses the 'miller_nn' key from mock scores. Falls back to 0.5 for
        unknown tickers (matching the pattern of other quant models).

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Mock directional confidence [0, 1].
        """
        scores = get_mock_scores(ticker)
        return scores.get("miller_nn", 0.5)

    def save(self, path: str | Path) -> None:
        """Save model state to disk (PyTorch state dict + normalization params).

        Saves a dict containing:
            - model_state_dict: PyTorch model weights
            - min_val / max_val: normalization parameters
            - params: training hyperparameters
            - version: model version string
            - training_metrics: last training evaluation metrics

        Args:
            path: File path for the saved model (.pt or .pth).
        """
        if self._model is None:
            logger.warning("No model to save")
            return

        try:
            import torch
            save_dict = {
                "model_state_dict": self._model.state_dict(),
                "min_val": self._min_val,
                "max_val": self._max_val,
                "params": self._params,
                "version": self._version,
                "training_metrics": self._training_metrics,
            }
            torch.save(save_dict, str(path))
            logger.info(f"MillerNNSmall model saved to {path}")
        except ImportError:
            logger.error("PyTorch not installed")

    def load(self, path: str | Path) -> None:
        """Load model state from disk.

        Reconstructs the network architecture from saved params, then loads
        the state dict and normalization parameters.

        Args:
            path: File path to the saved model (.pt or .pth).
        """
        try:
            import torch
            save_dict = torch.load(str(path), weights_only=False)
            self._params = save_dict.get("params", self._params)
            self._min_val = save_dict.get("min_val")
            self._max_val = save_dict.get("max_val")
            self._version = save_dict.get("version", self._version)
            self._training_metrics = save_dict.get("training_metrics", {})

            self._model = self._build_network()
            if self._model is not None:
                self._model.load_state_dict(save_dict["model_state_dict"])
                self._model.eval()
                self._trained = True
                logger.info(f"MillerNNSmall model loaded from {path}")
        except ImportError:
            logger.error("PyTorch not installed")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")

    def get_manifest(self) -> dict:
        """Return model manifest per PROJECT_STANDARDS_v2.md Section 2.

        The manifest includes all required fields:
            - model_name, version, trained_date, training_data_range
            - survivorship_bias_audited (always False until Week 3 audit)
            - holdout_period, validation_results, parameters, notes

        Returns:
            Dict with model metadata conforming to the manifest schema.
        """
        return {
            "model_name": "MillerNNSmall_DowSmall1a",
            "version": self._version,
            "model_type": "regression_directional",
            "tier": 2,
            "tier_note": "Tier 2 — not included in Phase 1 ensemble per PROJECT_STANDARDS_v2.md",
            "origin": "Dr. Miller DowSmall1a.Rmd (R neuralnet package)",
            "ported_from": "Architecture spec (models/miller_nn/DowSmall1a_Architecture.txt)",
            "r_source_available": False,
            "architecture": {
                "input_size": INPUT_SIZE,
                "hidden_layers": HIDDEN_LAYERS,
                "output_size": OUTPUT_SIZE,
                "activation_hidden": "sigmoid",
                "activation_output": "linear",
                "framework": "PyTorch",
            },
            "features": FEATURE_NAMES,
            "target": "DJIA close price (converted to directional confidence [0, 1])",
            "output_range": [0.0, 1.0],
            "parameters": self._params,
            "trained": self._trained,
            "training_metrics": self._training_metrics,
            "survivorship_bias_audited": False,
            "known_limitations": [
                "Random train/test split — lookahead bias for time-series data",
                "Only opening prices as inputs — no volume, volatility, or fundamentals",
                "Single-index scope (DJIA) — not individual equities",
                "No cross-validation or walk-forward validation",
                "Static model — no automatic retraining mechanism",
                "Global min/max normalization may degrade on out-of-range inputs",
            ],
            "integration_notes": (
                "Convert to chronological walk-forward validation before production use. "
                "Directional signal: predicted_close > current_open = bullish. "
                "Consider extending inputs to include volume, RSI, MACD, or Bloomberg fundamentals."
            ),
        }


# ---------------------------------------------------------------------------
# DowLarger1a — 6 inputs, hidden [10, 8, 6]
# ---------------------------------------------------------------------------


def _prepare_dow_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare Dow Jones OHLCV data for DowLarger1a.

    Replicates the R data preparation pipeline:
    1. Select Date, Open, Close
    2. Sort by Date ascending
    3. Engineer lag features: Open_Lag0..Open_Lag4, Close_Lag1
    4. Drop rows with NaN (first 4 rows)
    """
    data = df.copy()
    col_map = {}
    for col in data.columns:
        if col.lower() == "date":
            col_map[col] = "Date"
        elif col.lower() == "open":
            col_map[col] = "Open"
        elif col.lower() == "close":
            col_map[col] = "Close"
    data = data.rename(columns=col_map)
    data = data[["Date", "Open", "Close"]].copy()
    data = data.sort_values("Date").reset_index(drop=True)
    data["Open_Lag0"] = data["Open"]
    data["Open_Lag1"] = data["Open"].shift(1)
    data["Open_Lag2"] = data["Open"].shift(2)
    data["Open_Lag3"] = data["Open"].shift(3)
    data["Open_Lag4"] = data["Open"].shift(4)
    data["Close_Lag1"] = data["Close"].shift(1)
    data = data[["Date"] + LARGER_FEATURE_NAMES + ["Close"]].copy()
    data = data.dropna().reset_index(drop=True)
    return data


class DowLarger1aModel:
    """Dr. Miller's DowLarger1a neural network — ported from R to PyTorch.

    6 inputs: Open_Lag0..Open_Lag4 + Close_Lag1
    Hidden: [10, 8, 6] with sigmoid activation
    Output: linear (close price regression)

    Key differences from DowSmall1a:
        - 6 inputs (adds Close_Lag1) vs 5
        - Hidden [10, 8, 6] vs [5, 3]
        - Threshold 0.001 vs 0.01
        - Global min/max across ALL numeric columns

    Tier 2 model — not included in Phase 1 ensemble.
    """

    def __init__(
        self,
        hidden_layers: list[int] | None = None,
        threshold: float = 0.001,
        stepmax: int = 10_000_000,
        seed: int = 123,
    ):
        self._hidden_layers = hidden_layers or LARGER_HIDDEN_LAYERS.copy()
        self._threshold = threshold
        self._stepmax = stepmax
        self._seed = seed
        self._version = "1.0.0"
        self._trained = False
        self._min_val: float | None = None
        self._max_val: float | None = None
        self._model = None
        self._training_metrics: dict = {}
        self._converged: bool = False

    def _build_network(self):
        """Construct the PyTorch network matching DowLarger1a topology.

        Architecture: 6 -> [10] -> [8] -> [6] -> 1
        """
        try:
            import torch.nn as nn
        except ImportError:
            logger.error("PyTorch not installed")
            return None

        layers = []
        prev_size = LARGER_INPUT_SIZE
        for h_size in self._hidden_layers:
            layers.append(nn.Linear(prev_size, h_size))
            layers.append(nn.Sigmoid())
            prev_size = h_size
        layers.append(nn.Linear(prev_size, OUTPUT_SIZE))
        return nn.Sequential(*layers)

    def train(
        self,
        df: pd.DataFrame,
        learning_rate: float = 0.01,
        train_split: float = 0.80,
    ) -> dict:
        """Train the DowLarger1a model on Dow Jones OHLCV data.

        Args:
            df: DataFrame with Date, Open, Close columns.
            learning_rate: Optimizer learning rate.
            train_split: Fraction of data for training.

        Returns:
            Dict with training metrics.
        """
        try:
            import torch
            import torch.nn as nn
            import torch.optim as optim
        except ImportError:
            logger.error("PyTorch not installed")
            return {"error": "torch not installed"}

        data = _prepare_dow_data(df)
        if len(data) < 20:
            return {"error": f"Insufficient data: {len(data)} rows"}

        # Global min/max across ALL numeric columns (key difference from DowSmall1a)
        numeric_cols = LARGER_FEATURE_NAMES + ["Close"]
        all_numeric = data[numeric_cols].values
        self._min_val = float(np.min(all_numeric))
        self._max_val = float(np.max(all_numeric))

        X_all = data[LARGER_FEATURE_NAMES].values.astype(np.float32)
        y_all = data[["Close"]].values.astype(np.float32)
        X_norm = _minmax_normalize(X_all, self._min_val, self._max_val).astype(np.float32)
        y_norm = _minmax_normalize(y_all, self._min_val, self._max_val).astype(np.float32)

        rng = np.random.default_rng(self._seed)
        n_samples = len(X_norm)
        indices = rng.permutation(n_samples)
        n_train = int(n_samples * train_split)
        train_idx, test_idx = indices[:n_train], indices[n_train:]

        X_train = torch.tensor(X_norm[train_idx], dtype=torch.float32)
        y_train = torch.tensor(y_norm[train_idx], dtype=torch.float32)
        X_test = torch.tensor(X_norm[test_idx], dtype=torch.float32)
        y_test = torch.tensor(y_norm[test_idx], dtype=torch.float32)

        self._model = self._build_network()
        if self._model is None:
            return {"error": "Failed to build network"}

        # Rprop matches R neuralnet default optimizer
        optimizer = optim.Rprop(self._model.parameters(), lr=learning_rate)
        criterion = nn.MSELoss()

        self._model.train()
        best_loss = float("inf")
        patience_counter = 0
        epoch = 0
        self._converged = False
        current_loss = float("inf")

        while epoch < self._stepmax:
            optimizer.zero_grad()
            output = self._model(X_train)
            loss = criterion(output, y_train)
            loss.backward()
            optimizer.step()
            current_loss = loss.item()

            if current_loss < self._threshold:
                self._converged = True
                logger.info(f"Converged at epoch {epoch + 1}, loss={current_loss:.6f}")
                break

            if current_loss < best_loss:
                best_loss = current_loss
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= 1000:
                logger.warning(f"Early stop at epoch {epoch + 1}, loss={current_loss:.6f}")
                break

            if (epoch + 1) % 5000 == 0:
                logger.info(f"Epoch {epoch + 1}: loss={current_loss:.6f}")
            epoch += 1

        self._trained = True
        self._model.eval()
        with torch.no_grad():
            test_preds_norm = self._model(X_test).numpy()

        test_preds = _minmax_denormalize(test_preds_norm, self._min_val, self._max_val)
        test_actual = _minmax_denormalize(y_test.numpy(), self._min_val, self._max_val)

        mse = float(np.mean((test_actual - test_preds) ** 2))
        rmse = float(np.sqrt(mse))
        nonzero = test_actual.flatten() != 0
        mape = float(np.mean(np.abs(
            (test_actual.flatten()[nonzero] - test_preds.flatten()[nonzero])
            / test_actual.flatten()[nonzero]
        )) * 100) if nonzero.any() else 0.0

        self._training_metrics = {
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "total_samples": n_samples,
            "epochs": epoch + 1,
            "converged": self._converged,
            "final_loss": round(current_loss, 6),
            "rmse_dollars": round(rmse, 2),
            "mape_pct": round(mape, 4),
            "accuracy_pct": round(100.0 - mape, 4),
        }

        logger.info(
            f"DowLarger1a trained: RMSE=${rmse:.2f}, MAPE={mape:.2f}%, "
            f"Converged={self._converged}"
        )
        return self._training_metrics

    def predict(self, features: dict | np.ndarray | list) -> float:
        """Predict directional confidence from 6 lagged price features.

        Args:
            features: 6 values: [Open_Lag0..Open_Lag4, Close_Lag1].

        Returns:
            Directional confidence [0, 1]. 0.5 if untrained.
        """
        if not self._trained or self._model is None:
            return 0.5

        try:
            import torch
        except ImportError:
            return 0.5

        if isinstance(features, dict):
            values = np.array([features[k] for k in LARGER_FEATURE_NAMES], dtype=np.float32)
        elif isinstance(features, list):
            if len(features) != LARGER_INPUT_SIZE:
                logger.error(f"Expected {LARGER_INPUT_SIZE} inputs, got {len(features)}")
                return 0.5
            values = np.array(features, dtype=np.float32)
        else:
            values = np.asarray(features, dtype=np.float32).flatten()
            if len(values) != LARGER_INPUT_SIZE:
                return 0.5

        current_price = float(values[0])
        values_norm = _minmax_normalize(values, self._min_val, self._max_val)
        x_tensor = torch.tensor(values_norm.reshape(1, -1), dtype=torch.float32)

        self._model.eval()
        with torch.no_grad():
            pred_norm = self._model(x_tensor).item()

        predicted_close = _minmax_denormalize(
            np.array([pred_norm]), self._min_val, self._max_val
        )[0]
        return _directional_confidence(current_price, float(predicted_close))

    def predict_raw_price(self, features: dict | np.ndarray | list) -> float | None:
        """Predict raw close price in dollars (for R validation)."""
        if not self._trained or self._model is None:
            return None

        try:
            import torch
        except ImportError:
            return None

        if isinstance(features, dict):
            values = np.array([features[k] for k in LARGER_FEATURE_NAMES], dtype=np.float32)
        elif isinstance(features, list):
            values = np.array(features, dtype=np.float32)
        else:
            values = np.asarray(features, dtype=np.float32).flatten()

        if len(values) != LARGER_INPUT_SIZE:
            return None

        values_norm = _minmax_normalize(values, self._min_val, self._max_val)
        x_tensor = torch.tensor(values_norm.reshape(1, -1), dtype=torch.float32)

        self._model.eval()
        with torch.no_grad():
            pred_norm = self._model(x_tensor).item()

        return float(_minmax_denormalize(
            np.array([pred_norm]), self._min_val, self._max_val
        )[0])

    def predict_mock(self, ticker: str) -> float:
        """Return 0.5 (neutral) — Tier 2 model, not in Phase 1 ensemble."""
        return 0.5

    def save(self, path: str | Path) -> None:
        """Save model weights (.pt) and metadata (.json)."""
        if not self._trained or self._model is None:
            return

        try:
            import torch
        except ImportError:
            return

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self._model.state_dict(), str(path.with_suffix(".pt")))
        meta = {
            "model_name": "DowLarger1a",
            "version": self._version,
            "hidden_layers": self._hidden_layers,
            "threshold": self._threshold,
            "min_val": self._min_val,
            "max_val": self._max_val,
            "converged": self._converged,
            "training_metrics": self._training_metrics,
        }
        path.with_suffix(".json").write_text(json.dumps(meta, indent=2))
        logger.info(f"DowLarger1a saved to {path}")

    def load(self, path: str | Path) -> None:
        """Load model weights and metadata."""
        try:
            import torch
        except ImportError:
            return

        path = Path(path)
        meta_path = path.with_suffix(".json")
        if not meta_path.exists():
            logger.error(f"Metadata not found: {meta_path}")
            return
        meta = json.loads(meta_path.read_text())
        self._min_val = meta["min_val"]
        self._max_val = meta["max_val"]
        self._hidden_layers = meta.get("hidden_layers", LARGER_HIDDEN_LAYERS)
        self._converged = meta.get("converged", False)
        self._training_metrics = meta.get("training_metrics", {})

        self._model = self._build_network()
        weights_path = path.with_suffix(".pt")
        if self._model and weights_path.exists():
            self._model.load_state_dict(torch.load(str(weights_path), weights_only=True))
            self._trained = True
            logger.info(f"DowLarger1a loaded from {path}")

    def get_manifest(self) -> dict:
        """Return model manifest per PROJECT_STANDARDS_v2.md Section 2."""
        return {
            "model_name": "DowLarger1a",
            "version": self._version,
            "model_type": "regression_directional",
            "tier": 2,
            "phase_1_ensemble": False,
            "origin": "Dr. Miller neural network (ported from R neuralnet)",
            "r_source": "DowLarger1a.Rmd (architecture doc in models/miller_nn/)",
            "target": "DJIA close price -> directional confidence [0, 1]",
            "output_range": [0.0, 1.0],
            "input_features": LARGER_FEATURE_NAMES,
            "architecture": {
                "input_dim": LARGER_INPUT_SIZE,
                "hidden_layers": self._hidden_layers,
                "output_dim": 1,
                "hidden_activation": "sigmoid",
                "output_activation": "linear",
            },
            "parameters": LARGER_DEFAULT_PARAMS,
            "trained": self._trained,
            "converged": self._converged,
            "training_metrics": self._training_metrics,
            "survivorship_bias_audited": False,
            "known_limitations": [
                "Random train/test split (should be chronological for time-series)",
                "Trained on DJIA 1928-2009 data — significant regime gap",
                "Deeper architecture [10,8,6] increases overfitting risk",
                "No volume, volatility, or fundamental features",
                "Static model — no online learning or retraining",
            ],
        }
