"""XGBoost direction classifier — 5-day forward return direction."""

import logging
from pathlib import Path

import numpy as np

from .mock_scores import get_mock_scores

logger = logging.getLogger("wasden_watch.quant_models.xgboost")

# Default hyperparameters
DEFAULT_PARAMS = {
    "n_estimators": 200,
    "max_depth": 6,
    "learning_rate": 0.1,
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "use_label_encoder": False,
    "random_state": 42,
}


class XGBoostDirectionModel:
    """5-day forward return direction classifier using XGBoost.

    Predicts bullish probability [0, 1] for a given set of features.
    """

    def __init__(self, params: dict | None = None):
        self._params = params or DEFAULT_PARAMS.copy()
        self._model = None
        self._version = "1.0.0"
        self._trained = False

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
    ) -> dict:
        """Train the XGBoost model.

        Args:
            X_train: Training features array.
            y_train: Training labels (0/1).
            X_val: Optional validation features.
            y_val: Optional validation labels.

        Returns:
            Dict with validation metrics.
        """
        try:
            from xgboost import XGBClassifier
        except ImportError:
            logger.error("xgboost not installed. Install with: pip install xgboost")
            return {"error": "xgboost not installed"}

        self._model = XGBClassifier(**self._params)

        eval_set = []
        if X_val is not None and y_val is not None:
            eval_set = [(X_val, y_val)]

        self._model.fit(
            X_train, y_train,
            eval_set=eval_set if eval_set else None,
            verbose=False,
        )
        self._trained = True

        metrics = {"train_samples": len(X_train)}
        if X_val is not None and y_val is not None:
            val_preds = self._model.predict(X_val)
            accuracy = float(np.mean(val_preds == y_val))
            metrics["val_samples"] = len(X_val)
            metrics["val_accuracy"] = round(accuracy, 4)
            logger.info(f"XGBoost trained — val accuracy: {accuracy:.4f}")

        return metrics

    def predict(self, features: dict | np.ndarray) -> float:
        """Predict bullish probability for a single sample.

        Args:
            features: Dict of feature name -> value, or 1D numpy array.

        Returns:
            Bullish probability [0, 1].
        """
        if self._model is None:
            logger.warning("Model not trained, returning 0.5")
            return 0.5

        if isinstance(features, dict):
            X = np.array([list(features.values())])
        else:
            X = features.reshape(1, -1) if features.ndim == 1 else features

        proba = self._model.predict_proba(X)
        return float(proba[0][1])

    def predict_mock(self, ticker: str) -> float:
        """Return mock prediction from MOCK_QUANT_SCORES.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Mock bullish probability [0, 1].
        """
        return get_mock_scores(ticker)["xgboost"]

    def save(self, path: str | Path) -> None:
        """Save model to disk via joblib."""
        if self._model is None:
            logger.warning("No model to save")
            return
        try:
            import joblib
            joblib.dump(self._model, str(path))
            logger.info(f"XGBoost model saved to {path}")
        except ImportError:
            logger.error("joblib not installed")

    def load(self, path: str | Path) -> None:
        """Load model from disk via joblib."""
        try:
            import joblib
            self._model = joblib.load(str(path))
            self._trained = True
            logger.info(f"XGBoost model loaded from {path}")
        except ImportError:
            logger.error("joblib not installed")

    def get_manifest(self) -> dict:
        """Return model manifest per PROJECT_STANDARDS Section 2.

        Returns:
            Dict with model metadata.
        """
        return {
            "model_name": "XGBoostDirectionModel",
            "version": self._version,
            "model_type": "classification",
            "target": "5-day forward return direction",
            "output_range": [0.0, 1.0],
            "parameters": self._params,
            "trained": self._trained,
            "survivorship_bias_audited": False,
        }
