"""ARIMA model — time-series forecasting for 5-day close prediction."""

import logging

import numpy as np

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

    def train(self, close_series: np.ndarray) -> dict:
        """Fit ARIMA model to close price series.

        Args:
            close_series: Array of closing prices (time-ordered).

        Returns:
            Dict with training metrics.
        """
        self._close_series = close_series
        self._trained = True
        self._last_training_samples = len(close_series)
        return {
            "train_samples": len(close_series),
            "order": self._order,
        }

    def predict(self, close_series: np.ndarray, forward_days: int = 5) -> float:
        """Predict directional confidence using ARIMA forecast.

        Args:
            close_series: Array of closing prices (time-ordered).
            forward_days: Number of days to forecast.

        Returns:
            Directional confidence [0, 1]. Returns 0.5 on convergence failure.
        """
        try:
            from statsmodels.tsa.arima.model import ARIMA
        except ImportError:
            logger.error("statsmodels not installed")
            return 0.5

        if len(close_series) < 30:
            logger.warning(f"Insufficient data ({len(close_series)} points), returning 0.5")
            return 0.5

        try:
            model = ARIMA(close_series, order=self._order)
            fitted = model.fit()
            forecast = fitted.forecast(steps=forward_days)
            predicted_price = float(forecast[-1])
            current_price = float(close_series[-1])

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

    def get_manifest(self) -> dict:
        """Return model manifest per PROJECT_STANDARDS Section 2."""
        return {
            "model_name": "ARIMAModel",
            "version": self._version,
            "model_type": "time_series",
            "target": "5-day forward close price (directional confidence)",
            "output_range": [0.0, 1.0],
            "parameters": {"order": self._order},
            "trained": self._trained,
            "survivorship_bias_audited": False,
        }
