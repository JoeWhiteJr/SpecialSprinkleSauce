"""Elastic Net direction model — regularized regression with sigmoid output."""

import logging
from pathlib import Path

import numpy as np

from .mock_scores import get_mock_scores

logger = logging.getLogger("wasden_watch.quant_models.elastic_net")

DEFAULT_PARAMS = {
    "alpha": 0.1,
    "l1_ratio": 0.5,
    "max_iter": 1000,
    "random_state": 42,
}


def _sigmoid(x: float) -> float:
    """Apply sigmoid function to map value to [0, 1]."""
    return 1.0 / (1.0 + np.exp(-x))


class ElasticNetDirectionModel:
    """Regularized regression model for 5-day forward return prediction.

    Outputs predicted return passed through sigmoid to produce [0, 1] probability.
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
        """Train the Elastic Net model.

        Args:
            X_train: Training features.
            y_train: Training labels (0/1 or continuous returns).
            X_val: Optional validation features.
            y_val: Optional validation labels.

        Returns:
            Dict with training/validation metrics.
        """
        try:
            from sklearn.linear_model import ElasticNet
        except ImportError:
            logger.error("scikit-learn not installed")
            return {"error": "scikit-learn not installed"}

        self._model = ElasticNet(**self._params)
        self._model.fit(X_train, y_train)
        self._trained = True

        metrics = {"train_samples": len(X_train)}
        if X_val is not None and y_val is not None:
            raw_preds = self._model.predict(X_val)
            proba_preds = np.array([_sigmoid(p) for p in raw_preds])
            binary_preds = (proba_preds > 0.5).astype(int)
            accuracy = float(np.mean(binary_preds == y_val))
            metrics["val_samples"] = len(X_val)
            metrics["val_accuracy"] = round(accuracy, 4)
            logger.info(f"ElasticNet trained — val accuracy: {accuracy:.4f}")

        return metrics

    def predict(self, features: dict | np.ndarray) -> float:
        """Predict bullish probability for a single sample.

        Args:
            features: Dict of feature name -> value, or 1D numpy array.

        Returns:
            Bullish probability [0, 1] (sigmoid of raw prediction).
        """
        if self._model is None:
            logger.warning("Model not trained, returning 0.5")
            return 0.5

        if isinstance(features, dict):
            X = np.array([list(features.values())])
        else:
            X = features.reshape(1, -1) if features.ndim == 1 else features

        raw = float(self._model.predict(X)[0])
        return float(_sigmoid(raw))

    def predict_mock(self, ticker: str) -> float:
        """Return mock prediction from MOCK_QUANT_SCORES."""
        return get_mock_scores(ticker)["elastic_net"]

    def save(self, path: str | Path) -> None:
        """Save model to disk via joblib."""
        if self._model is None:
            return
        try:
            import joblib
            joblib.dump(self._model, str(path))
            logger.info(f"ElasticNet model saved to {path}")
        except ImportError:
            logger.error("joblib not installed")

    def load(self, path: str | Path) -> None:
        """Load model from disk via joblib."""
        try:
            import joblib
            self._model = joblib.load(str(path))
            self._trained = True
            logger.info(f"ElasticNet model loaded from {path}")
        except ImportError:
            logger.error("joblib not installed")

    def get_manifest(self) -> dict:
        """Return model manifest per PROJECT_STANDARDS Section 2."""
        return {
            "model_name": "ElasticNetDirectionModel",
            "version": self._version,
            "model_type": "regression_sigmoid",
            "target": "5-day forward return direction",
            "output_range": [0.0, 1.0],
            "parameters": self._params,
            "trained": self._trained,
            "survivorship_bias_audited": False,
        }
