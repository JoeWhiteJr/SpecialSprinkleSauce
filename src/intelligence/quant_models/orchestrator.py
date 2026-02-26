"""Quant model orchestrator — coordinates all 4 models and produces composite scores."""

import logging
import statistics

from app.services.risk.constants import HIGH_MODEL_DISAGREEMENT_THRESHOLD

from .arima_model import ARIMAModel
from .elastic_net_model import ElasticNetDirectionModel
from .mock_scores import PILOT_TICKERS, get_mock_scores
from .sentiment_model import SentimentModel
from .xgboost_model import XGBoostDirectionModel

logger = logging.getLogger("wasden_watch.quant_models.orchestrator")


class QuantModelOrchestrator:
    """Coordinates all 4 quant models and produces composite scores.

    In mock mode, uses MOCK_QUANT_SCORES.
    In live mode, calls each model's predict() method.
    """

    def __init__(
        self,
        use_mock: bool = True,
        finnhub_api_key: str = "",
        newsapi_api_key: str = "",
    ):
        self._use_mock = use_mock
        self._xgboost = XGBoostDirectionModel()
        self._elastic_net = ElasticNetDirectionModel()
        self._arima = ARIMAModel()
        self._sentiment = SentimentModel(
            finnhub_api_key=finnhub_api_key,
            newsapi_api_key=newsapi_api_key,
        )

    def score_ticker(
        self,
        ticker: str,
        ohlcv_df=None,
        fundamentals: dict | None = None,
    ) -> dict:
        """Score a single ticker across all 4 models.

        Args:
            ticker: Stock ticker symbol.
            ohlcv_df: Optional OHLCV DataFrame for live mode.
            fundamentals: Optional fundamentals dict.

        Returns:
            Dict with individual scores, composite, std_dev, and disagreement flag.
        """
        ticker = ticker.upper()

        if self._use_mock:
            scores = get_mock_scores(ticker)
            xgb = scores["xgboost"]
            enet = scores["elastic_net"]
            arima = scores["arima"]
            sent = scores["sentiment"]
        else:
            xgb = self._xgboost.predict(fundamentals) if fundamentals else 0.5
            enet = self._elastic_net.predict(fundamentals) if fundamentals else 0.5
            if ohlcv_df is not None and len(ohlcv_df) >= 30:
                close_series = ohlcv_df["close"].values
                arima = self._arima.predict(close_series)
            else:
                arima = 0.5
            sent = self._sentiment.predict(ticker)

        all_scores = [xgb, enet, arima, sent]
        composite = statistics.mean(all_scores)
        std_dev = statistics.stdev(all_scores) if len(all_scores) > 1 else 0.0

        return {
            "xgboost": round(xgb, 4),
            "elastic_net": round(enet, 4),
            "arima": round(arima, 4),
            "sentiment": round(sent, 4),
            "composite": round(composite, 4),
            "std_dev": round(std_dev, 4),
            "high_disagreement_flag": std_dev > HIGH_MODEL_DISAGREEMENT_THRESHOLD,
        }

    def score_multiple(
        self,
        tickers: list[str],
        ohlcv_data: dict | None = None,
        fundamentals_data: dict | None = None,
    ) -> dict[str, dict]:
        """Score multiple tickers.

        Args:
            tickers: List of ticker symbols.
            ohlcv_data: Optional dict of ticker -> OHLCV DataFrame.
            fundamentals_data: Optional dict of ticker -> fundamentals dict.

        Returns:
            Dict of ticker -> score dict.
        """
        ohlcv_data = ohlcv_data or {}
        fundamentals_data = fundamentals_data or {}
        results = {}

        for ticker in tickers:
            results[ticker] = self.score_ticker(
                ticker,
                ohlcv_df=ohlcv_data.get(ticker),
                fundamentals=fundamentals_data.get(ticker),
            )

        return results

    def get_all_manifests(self) -> dict:
        """Return manifests for all 4 models.

        Returns:
            Dict of model_name -> manifest.
        """
        return {
            "xgboost": self._xgboost.get_manifest(),
            "elastic_net": self._elastic_net.get_manifest(),
            "arima": self._arima.get_manifest(),
            "sentiment": self._sentiment.get_manifest(),
        }

    def get_agreement_metrics(self, tickers: list[str] | None = None) -> dict:
        """Calculate agreement metrics across tickers.

        Args:
            tickers: List of tickers to analyze. Defaults to PILOT_TICKERS.

        Returns:
            Dict with agreement statistics.
        """
        tickers = tickers or PILOT_TICKERS
        all_scores = self.score_multiple(tickers)

        std_devs = [s["std_dev"] for s in all_scores.values()]
        disagreements = [s for s in all_scores.values() if s["high_disagreement_flag"]]

        return {
            "tickers_analyzed": len(tickers),
            "avg_std_dev": round(statistics.mean(std_devs), 4) if std_devs else 0.0,
            "max_std_dev": round(max(std_devs), 4) if std_devs else 0.0,
            "min_std_dev": round(min(std_devs), 4) if std_devs else 0.0,
            "high_disagreement_count": len(disagreements),
            "high_disagreement_tickers": [
                ticker for ticker, s in all_scores.items()
                if s["high_disagreement_flag"]
            ],
            "threshold": HIGH_MODEL_DISAGREEMENT_THRESHOLD,
        }
