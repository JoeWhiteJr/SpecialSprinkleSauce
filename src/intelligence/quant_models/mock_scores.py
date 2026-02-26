"""Mock quant scores for 10 pilot tickers — single source of truth for all mock quant data."""

MOCK_QUANT_SCORES: dict[str, dict[str, float]] = {
    "NVDA": {"xgboost": 0.82, "elastic_net": 0.75, "arima": 0.68, "sentiment": 0.88},
    "PYPL": {"xgboost": 0.61, "elastic_net": 0.58, "arima": 0.55, "sentiment": 0.64},
    "NFLX": {"xgboost": 0.54, "elastic_net": 0.49, "arima": 0.52, "sentiment": 0.51},
    "TSM": {"xgboost": 0.71, "elastic_net": 0.69, "arima": 0.63, "sentiment": 0.74},
    "XOM": {"xgboost": 0.45, "elastic_net": 0.42, "arima": 0.48, "sentiment": 0.38},
    "AAPL": {"xgboost": 0.73, "elastic_net": 0.70, "arima": 0.66, "sentiment": 0.78},
    "MSFT": {"xgboost": 0.77, "elastic_net": 0.74, "arima": 0.71, "sentiment": 0.80},
    "AMZN": {"xgboost": 0.69, "elastic_net": 0.65, "arima": 0.62, "sentiment": 0.72},
    "TSLA": {"xgboost": 0.85, "elastic_net": 0.35, "arima": 0.42, "sentiment": 0.91},
    "AMD": {"xgboost": 0.76, "elastic_net": 0.72, "arima": 0.65, "sentiment": 0.79},
}

PILOT_TICKERS = list(MOCK_QUANT_SCORES.keys())


def get_mock_scores(ticker: str) -> dict[str, float]:
    """Return mock scores for a ticker, defaulting to neutral 0.5 for unknown tickers."""
    return MOCK_QUANT_SCORES.get(
        ticker.upper(),
        {"xgboost": 0.50, "elastic_net": 0.50, "arima": 0.50, "sentiment": 0.50},
    )
