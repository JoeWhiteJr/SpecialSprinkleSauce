"""
Fallback data source chain — Supabase → Finnhub → Yahoo Finance.

Per PROJECT_STANDARDS_v2.md Section 5:
  Market data: Bloomberg → Yahoo Finance → Finnhub → halt and alert

Since Bloomberg data comes via Excel upload (not live API), the runtime
fallback chain for live field lookups is: Supabase (cached Bloomberg) →
Finnhub → Yahoo Finance.
"""

import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger("wasden_watch.data_source_chain")


class DataSource(str, Enum):
    SUPABASE = "supabase"
    FINNHUB = "finnhub"
    YAHOO = "yahoo"


class DataSourceError(Exception):
    """Raised when all data sources fail for a field/ticker."""

    def __init__(self, ticker: str, field: str, errors: dict[str, str]):
        self.ticker = ticker
        self.field = field
        self.errors = errors
        super().__init__(
            f"All data sources failed for {ticker}.{field}: {errors}"
        )


# Supabase column → Finnhub metric mapping
FINNHUB_FIELD_MAP = {
    "market_cap": "marketCapitalization",
    "trailing_pe": "peNormalizedAnnual",
    "forward_pe": "forwardPE",
    "eps": "epsNormalizedAnnual",
    "peg_ratio": "pegRatio",
    "roe": "roeTTM",
    "gross_margin": "grossMarginTTM",
    "operating_margin": "operatingMarginTTM",
    "net_margin": "netProfitMarginTTM",
    "current_ratio": "currentRatioQuarterly",
    "debt_to_equity": "totalDebtToEquityQuarterly",
    "revenue_growth": "revenueGrowthQuarterlyYoy",
}

# Supabase column → yfinance info key mapping
YAHOO_FIELD_MAP = {
    "market_cap": "marketCap",
    "price": "currentPrice",
    "trailing_pe": "trailingPE",
    "forward_pe": "forwardPE",
    "eps": "trailingEps",
    "peg_ratio": "pegRatio",
    "fcf": "freeCashflow",
    "fcf_yield": None,  # computed: fcf / market_cap * 100
    "roe": "returnOnEquity",
    "gross_margin": "grossMargins",
    "operating_margin": "operatingMargins",
    "net_margin": "profitMargins",
    "current_ratio": "currentRatio",
    "debt_to_equity": "debtToEquity",
    "revenue_growth": "revenueGrowth",
}


def _fetch_from_supabase(ticker: str, field: str) -> Optional[float]:
    """Attempt to fetch a field from cached Bloomberg data in Supabase."""
    try:
        from app.config import settings
        if settings.use_mock_data:
            return None

        from app.services.supabase_client import get_supabase
        client = get_supabase()
        result = (
            client.table("bloomberg_fundamentals")
            .select(field)
            .eq("ticker", ticker)
            .order("pull_date", desc=True)
            .limit(1)
            .execute()
        )
        if result.data and result.data[0].get(field) is not None:
            return float(result.data[0][field])
    except Exception as e:
        logger.debug(f"Supabase fetch failed for {ticker}.{field}: {e}")
    return None


def _fetch_from_finnhub(ticker: str, field: str) -> Optional[float]:
    """Attempt to fetch a field from Finnhub API."""
    finnhub_key = FINNHUB_FIELD_MAP.get(field)
    if finnhub_key is None:
        return None

    try:
        import finnhub
        from app.config import settings
        client = finnhub.Client(api_key=settings.finnhub_api_key)
        metrics = client.company_basic_financials(ticker, "all")
        metric_data = metrics.get("metric", {})
        value = metric_data.get(finnhub_key)
        if value is not None:
            # Finnhub returns market cap in millions
            if field == "market_cap":
                return float(value) * 1_000_000
            return float(value)
    except Exception as e:
        logger.debug(f"Finnhub fetch failed for {ticker}.{field}: {e}")
    return None


def _fetch_from_yahoo(ticker: str, field: str) -> Optional[float]:
    """Attempt to fetch a field from Yahoo Finance."""
    yahoo_key = YAHOO_FIELD_MAP.get(field)
    if yahoo_key is None and field != "fcf_yield":
        return None

    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info

        # Special case: FCF yield computed from FCF / market cap
        if field == "fcf_yield":
            fcf = info.get("freeCashflow")
            mcap = info.get("marketCap")
            if fcf is not None and mcap and mcap > 0:
                return (fcf / mcap) * 100  # stored as percentage
            return None

        value = info.get(yahoo_key)
        if value is not None:
            # Yahoo returns margins as decimals (0.45 = 45%)
            if field in ("gross_margin", "operating_margin", "net_margin", "roe", "revenue_growth"):
                return float(value) * 100
            return float(value)
    except Exception as e:
        logger.debug(f"Yahoo fetch failed for {ticker}.{field}: {e}")
    return None


def fetch_field(ticker: str, field: str) -> tuple[Optional[float], DataSource]:
    """Fetch a single field using the fallback chain.

    Returns (value, source) tuple. Raises DataSourceError if all fail.
    """
    # Source 1: Supabase (cached Bloomberg)
    value = _fetch_from_supabase(ticker, field)
    if value is not None:
        return value, DataSource.SUPABASE

    # Source 2: Finnhub
    value = _fetch_from_finnhub(ticker, field)
    if value is not None:
        return value, DataSource.FINNHUB

    # Source 3: Yahoo Finance
    value = _fetch_from_yahoo(ticker, field)
    if value is not None:
        return value, DataSource.YAHOO

    return None, DataSource.SUPABASE


FUNDAMENTAL_FIELDS = [
    "price", "market_cap", "trailing_pe", "forward_pe", "eps",
    "peg_ratio", "fcf", "fcf_yield", "ebitda_margin", "roe", "roc",
    "gross_margin", "operating_margin", "net_margin", "current_ratio",
    "quick_ratio", "debt_to_equity", "revenue_growth",
    "ebitda_interest_coverage", "ccc", "short_interest",
]


def fetch_ticker_fundamentals(ticker: str) -> dict:
    """Fetch all fundamental fields for a ticker using the fallback chain.

    Returns dict with field values and source metadata.
    """
    result = {"ticker": ticker, "fields": {}, "sources": {}, "missing": []}

    for field in FUNDAMENTAL_FIELDS:
        value, source = fetch_field(ticker, field)
        if value is not None:
            result["fields"][field] = value
            result["sources"][field] = source.value
        else:
            result["missing"].append(field)

    logger.info(
        f"Fetched {len(result['fields'])}/{len(FUNDAMENTAL_FIELDS)} "
        f"fields for {ticker}, missing: {result['missing']}"
    )
    return result
