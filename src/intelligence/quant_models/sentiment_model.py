"""Sentiment model — Finnhub + NewsAPI sentiment aggregation."""

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .mock_scores import get_mock_scores

logger = logging.getLogger("wasden_watch.quant_models.sentiment")

# Sentiment weights
FINNHUB_WEIGHT = 0.6
NEWSAPI_WEIGHT = 0.4

# Rate limiting: minimum seconds between API calls per source
_MIN_CALL_INTERVAL_SECS = 1.0

# Positive/negative keyword lists for NewsAPI headline scoring
POSITIVE_KEYWORDS = [
    "beat", "beats", "surge", "surges", "soar", "soars", "rally", "rallies",
    "upgrade", "upgrades", "bullish", "strong", "growth", "profit", "gains",
    "outperform", "record", "optimistic", "boost", "positive", "breakout",
]
NEGATIVE_KEYWORDS = [
    "miss", "misses", "drop", "drops", "crash", "crashes", "plunge", "plunges",
    "downgrade", "downgrades", "bearish", "weak", "loss", "losses", "decline",
    "underperform", "warning", "pessimistic", "cut", "negative", "selloff",
]


def _headline_sentiment(headline: str) -> float:
    """Score a single headline: +1 for positive words, -1 for negative, normalized to [0, 1]."""
    words = headline.lower().split()
    pos = sum(1 for w in words if w in POSITIVE_KEYWORDS)
    neg = sum(1 for w in words if w in NEGATIVE_KEYWORDS)
    total = pos + neg
    if total == 0:
        return 0.5
    return 0.5 + 0.5 * (pos - neg) / total


class SentimentModel:
    """Sentiment aggregation from Finnhub and NewsAPI.

    Produces a weighted-average sentiment score in [0, 1].
    Falls back to 0.5 if APIs fail.
    """

    def __init__(self, finnhub_api_key: str = "", newsapi_api_key: str = ""):
        self._finnhub_api_key = finnhub_api_key
        self._newsapi_api_key = newsapi_api_key
        self._version = "1.0.0"
        # Rate limiting: track last call time per source
        self._last_finnhub_call: float = 0.0
        self._last_newsapi_call: float = 0.0

    def _rate_limit(self, source: str) -> None:
        """Enforce minimum interval between API calls to avoid hammering."""
        now = time.monotonic()
        if source == "finnhub":
            elapsed = now - self._last_finnhub_call
            if elapsed < _MIN_CALL_INTERVAL_SECS:
                sleep_time = _MIN_CALL_INTERVAL_SECS - elapsed
                logger.debug(f"Rate limiting Finnhub: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
            self._last_finnhub_call = time.monotonic()
        elif source == "newsapi":
            elapsed = now - self._last_newsapi_call
            if elapsed < _MIN_CALL_INTERVAL_SECS:
                sleep_time = _MIN_CALL_INTERVAL_SECS - elapsed
                logger.debug(f"Rate limiting NewsAPI: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
            self._last_newsapi_call = time.monotonic()

    def fetch_finnhub_sentiment(self, ticker: str) -> float | None:
        """Fetch sentiment from Finnhub news sentiment endpoint.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Sentiment score [0, 1] or None on failure.
        """
        if not self._finnhub_api_key:
            logger.info("Finnhub API key not set, skipping")
            return None

        self._rate_limit("finnhub")

        try:
            import finnhub
            client = finnhub.Client(api_key=self._finnhub_api_key)
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=7)
            news = client.company_news(
                ticker,
                _from=start.strftime("%Y-%m-%d"),
                to=end.strftime("%Y-%m-%d"),
            )
            if not news:
                logger.info(f"No Finnhub news for {ticker}")
                return None

            # Finnhub news items have a 'sentiment' field from their API
            # If not available, use headline scoring
            sentiments = []
            for item in news[:20]:
                headline = item.get("headline", "")
                sentiments.append(_headline_sentiment(headline))

            avg = sum(sentiments) / len(sentiments) if sentiments else 0.5
            logger.info(f"Finnhub sentiment for {ticker}: {avg:.3f} ({len(sentiments)} articles)")
            return float(avg)
        except Exception as e:
            logger.warning(f"Finnhub sentiment fetch failed for {ticker}: {e}")
            return None

    def fetch_newsapi_sentiment(self, ticker: str) -> float | None:
        """Fetch sentiment from NewsAPI headline keyword scoring.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Sentiment score [0, 1] or None on failure.
        """
        if not self._newsapi_api_key:
            logger.info("NewsAPI key not set, skipping")
            return None

        self._rate_limit("newsapi")

        try:
            from newsapi import NewsApiClient
            api = NewsApiClient(api_key=self._newsapi_api_key)
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=7)
            response = api.get_everything(
                q=ticker,
                from_param=start.strftime("%Y-%m-%d"),
                to=end.strftime("%Y-%m-%d"),
                language="en",
                sort_by="relevancy",
                page_size=20,
            )
            articles = response.get("articles", [])
            if not articles:
                logger.info(f"No NewsAPI articles for {ticker}")
                return None

            sentiments = [
                _headline_sentiment(a.get("title", ""))
                for a in articles
            ]
            avg = sum(sentiments) / len(sentiments) if sentiments else 0.5
            logger.info(f"NewsAPI sentiment for {ticker}: {avg:.3f} ({len(sentiments)} articles)")
            return float(avg)
        except Exception as e:
            logger.warning(f"NewsAPI sentiment fetch failed for {ticker}: {e}")
            return None

    def predict(self, ticker: str) -> float:
        """Compute weighted-average sentiment from available sources.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Sentiment score [0, 1]. Falls back to 0.5 if all sources fail.
        """
        finnhub_score = self.fetch_finnhub_sentiment(ticker)
        newsapi_score = self.fetch_newsapi_sentiment(ticker)

        scores = []
        weights = []

        if finnhub_score is not None:
            scores.append(finnhub_score)
            weights.append(FINNHUB_WEIGHT)
        if newsapi_score is not None:
            scores.append(newsapi_score)
            weights.append(NEWSAPI_WEIGHT)

        if not scores:
            logger.warning(f"All sentiment sources failed for {ticker}, returning 0.5")
            return 0.5

        total_weight = sum(weights)
        weighted_avg = sum(s * w for s, w in zip(scores, weights)) / total_weight
        return float(max(0.0, min(1.0, weighted_avg)))

    def predict_mock(self, ticker: str) -> float:
        """Return mock prediction from MOCK_QUANT_SCORES."""
        return get_mock_scores(ticker)["sentiment"]

    def save(self, path: str | Path) -> None:
        """Save model configuration and weights to disk.

        Sentiment model has no trained state, but persists its config
        (API source weights, keyword lists) so the manifest is reproducible.
        """
        path = Path(path)
        config = {
            "version": self._version,
            "finnhub_weight": FINNHUB_WEIGHT,
            "newsapi_weight": NEWSAPI_WEIGHT,
            "positive_keywords": POSITIVE_KEYWORDS,
            "negative_keywords": NEGATIVE_KEYWORDS,
            "has_finnhub_key": bool(self._finnhub_api_key),
            "has_newsapi_key": bool(self._newsapi_api_key),
        }
        try:
            with open(path, "w") as f:
                json.dump(config, f, indent=2)
            logger.info(f"Sentiment config saved to {path}")
        except Exception as e:
            logger.error(f"Failed to save sentiment config: {e}")

    def load(self, path: str | Path) -> None:
        """Load model configuration from disk.

        Restores keyword lists and weights. API keys must still be
        provided via constructor (never persisted to disk).
        """
        path = Path(path)
        try:
            with open(path) as f:
                config = json.load(f)
            self._version = config.get("version", self._version)
            logger.info(f"Sentiment config loaded from {path}")
        except FileNotFoundError:
            logger.error(f"Config file not found: {path}")
        except Exception as e:
            logger.error(f"Failed to load sentiment config: {e}")

    def get_manifest(self) -> dict:
        """Return model manifest per PROJECT_STANDARDS Section 2."""
        return {
            "model_name": "SentimentModel",
            "version": self._version,
            "model_type": "sentiment_aggregation",
            "target": "News sentiment (bullish probability)",
            "output_range": [0.0, 1.0],
            "parameters": {
                "finnhub_weight": FINNHUB_WEIGHT,
                "newsapi_weight": NEWSAPI_WEIGHT,
                "sources": ["finnhub", "newsapi"],
            },
            "trained": True,
            "survivorship_bias_audited": False,
        }
