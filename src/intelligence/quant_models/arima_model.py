"""ARIMA model — time-series forecasting for 5-day close prediction."""

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from .mock_scores import get_mock_scores

logger = logging.getLogger("wasden_watch.quant_models.arima")

DEFAULT_ORDER = (5, 1, 0)


def _directional_confidence(current_price: float, predicted_price: float) -> float:
    """Convert predicted price to directional confidence [0, 1].

    0.5 = no direction, >0.5 = bullish, <0.5 = bearish.
    """
    if current_price <= 0:
        return 0.5
    pct_change = (predicted_price - current_price) / current_price
    # Map pct_change to [0, 1] using sigmoid-like scaling
    # +-5% maps to roughly [0.25, 0.75]
    confidence = 1.0 / (1.0 + np.exp(-pct_change * 20))
    return float(np.clip(confidence, 0.0, 1.0))


class ARIMAModel:
    """Time-series forecasting model using ARIMA(5,1,0).

    Predicts 5-day forward close price, then converts to directional confidence [0, 1].
    """

    def __init__(self, order: tuple[int, int, int] = DEFAULT_ORDER):
        self._order = order
        self._version = "1.0.0"
        self._trained = False
        self._last_training_samples = 0
        self._last_aic = None
        self._last_bic = None
        self._fitted_model = None

    def train(self, series: pd.Series | np.ndarray) -> dict:
        """Fit ARIMA model to close price series and return diagnostics.

        Args:
            series: Closing prices (time-ordered). Accepts pd.Series or np.ndarray.

        Returns:
            Dict with training diagnostics including AIC and BIC.
        """
        try:
            from statsmodels.tsa.arima.model import ARIMA
        except ImportError:
            logger.error("statsmodels not installed — cannot train ARIMA")
            return {"error": "statsmodels not installed"}

        close_array = np.asarray(series, dtype=float)

        if len(close_array) < 30:
            logger.warning(f"Insufficient data for training ({len(close_array)} points, need 30+)")
            return {"error": "insufficient_data", "samples": len(close_array)}

        try:
            model = ARIMA(close_array, order=self._order)
            fitted = model.fit()
            self._fitted_model = fitted
            self._trained = True
            self._last_training_samples = len(close_array)
            self._last_aic = float(fitted.aic)
            self._last_bic = float(fitted.bic)

            logger.info(
                f"ARIMA({self._order}) trained on {len(close_array)} samples — "
                f"AIC={self._last_aic:.2f}, BIC={self._last_bic:.2f}"
            )
            return {
                "train_samples": len(close_array),
                "order": self._order,
                "aic": self._last_aic,
                "bic": self._last_bic,
            }
        except Exception as e:
            logger.warning(f"ARIMA training convergence failure: {e}")
            self._trained = False
            return {"error": "convergence_failure", "detail": str(e)}

    def predict(self, series: pd.Series | np.ndarray, steps: int = 5) -> float:
        """Predict directional confidence using ARIMA forecast.

        If `train()` was previously called on compatible data, uses the fitted model.
        Otherwise, fits a fresh model on the provided series (stateless mode).

        Args:
            series: Closing prices (time-ordered). Accepts pd.Series or np.ndarray.
            steps: Number of days to forecast forward.

        Returns:
            Directional confidence [0, 1]. Returns 0.5 on convergence failure.
        """
        try:
            from statsmodels.tsa.arima.model import ARIMA
        except ImportError:
            logger.error("statsmodels not installed")
            return 0.5

        close_array = np.asarray(series, dtype=float)

        if len(close_array) < 30:
            logger.warning(f"Insufficient data ({len(close_array)} points), returning 0.5")
            return 0.5

        try:
            # Use pre-fitted model if available and trained on same-length series,
            # otherwise fit fresh on the provided data (stateless prediction).
            if self._fitted_model is not None and self._last_training_samples == len(close_array):
                fitted = self._fitted_model
            else:
                model = ARIMA(close_array, order=self._order)
                fitted = model.fit()

            forecast = fitted.forecast(steps=steps)
            predicted_price = float(forecast[-1])
            current_price = float(close_array[-1])

            confidence = _directional_confidence(current_price, predicted_price)
            logger.info(
                f"ARIMA forecast: current={current_price:.2f}, "
                f"predicted={predicted_price:.2f}, confidence={confidence:.3f}"
            )
            return confidence
        except Exception as e:
            logger.warning(f"ARIMA convergence failure: {e}, returning 0.5")
            return 0.5

    def predict_mock(self, ticker: str) -> float:
        """Return mock prediction from MOCK_QUANT_SCORES."""
        return get_mock_scores(ticker)["arima"]

    def save(self, path: str | Path) -> None:
        """Save fitted ARIMA model to disk.

        Saves the fitted model via pickle and metadata as JSON sidecar.
        """
        path = Path(path)
        if self._fitted_model is None:
            logger.warning("No fitted model to save")
            return

        try:
            import pickle
            with open(path, "wb") as f:
                pickle.dump(self._fitted_model, f)

            # Save metadata sidecar
            meta_path = path.with_suffix(".json")
            meta = {
                "order": list(self._order),
                "version": self._version,
                "training_samples": self._last_training_samples,
                "aic": self._last_aic,
                "bic": self._last_bic,
            }
            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=2)

            logger.info(f"ARIMA model saved to {path}")
        except Exception as e:
            logger.error(f"Failed to save ARIMA model: {e}")

    def load(self, path: str | Path) -> None:
        """Load fitted ARIMA model from disk."""
        path = Path(path)
        try:
            import pickle
            with open(path, "rb") as f:
                self._fitted_model = pickle.load(f)  # noqa: S301
            self._trained = True

            # Load metadata sidecar if available
            meta_path = path.with_suffix(".json")
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)
                self._order = tuple(meta.get("order", list(DEFAULT_ORDER)))
                self._last_training_samples = meta.get("training_samples", 0)
                self._last_aic = meta.get("aic")
                self._last_bic = meta.get("bic")

            logger.info(f"ARIMA model loaded from {path}")
        except FileNotFoundError:
            logger.error(f"Model file not found: {path}")
        except Exception as e:
            logger.error(f"Failed to load ARIMA model: {e}")

    def get_manifest(self) -> dict:
        """Return model manifest per PROJECT_STANDARDS Section 2."""
        manifest = {
            "model_name": "ARIMAModel",
            "version": self._version,
            "model_type": "time_series",
            "target": "5-day forward close price (directional confidence)",
            "output_range": [0.0, 1.0],
            "parameters": {"order": self._order},
            "trained": self._trained,
            "survivorship_bias_audited": False,
        }
        if self._last_aic is not None:
            manifest["validation_results"] = {
                "aic": self._last_aic,
                "bic": self._last_bic,
            }
        return manifest
