"""
Historical Dataset Loaders — Dow Jones (1928-2009) and Emery S&P 500.

Loads CSV price history into the price_history table via Supabase.
Data files are not on disk yet — loaders are ready-to-run when CSVs arrive.

All data is tagged survivorship_bias_audited=False until Week 3 formal audit.
"""

import csv
import logging
from datetime import date
from pathlib import Path
from typing import Optional

from app.services.supabase_client import get_supabase

logger = logging.getLogger("wasden_watch.data_loader")

# Batch size for upserts
BATCH_SIZE = 500


# ---------------------------------------------------------------------------
# Dow Jones CSV Loader (1928-2009)
# ---------------------------------------------------------------------------

def load_dow_jones_csv(file_path: str | Path) -> dict:
    """Load Dow Jones historical data (1928-2009) from CSV into price_history.

    Expected CSV columns (flexible header matching):
        Date, Open, High, Low, Close, Volume, Adjusted Close (or Adj Close)

    The Dow Jones dataset is a single-ticker index dataset. Ticker is stored
    as 'DJIA' unless a Ticker/Symbol column is present.

    Args:
        file_path: Path to the Dow Jones CSV file.

    Returns:
        DatasetLoadResult-compatible dict with row counts and date range.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    logger.info(f"Loading Dow Jones CSV: {file_path}")

    rows_to_insert = []
    errors = []
    tickers_found = set()
    dates = []

    with open(file_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = {h.strip().lower(): h.strip() for h in (reader.fieldnames or [])}

        # Flexible header mapping
        col_map = _build_column_map(headers)

        for line_num, raw_row in enumerate(reader, start=2):
            try:
                row = {k.strip(): v.strip() if v else "" for k, v in raw_row.items()}
                ticker = _get_field(row, col_map, "ticker") or "DJIA"
                row_date = _parse_date(_get_field(row, col_map, "date"))
                if row_date is None:
                    errors.append(f"Line {line_num}: invalid date")
                    continue

                record = {
                    "ticker": ticker.upper(),
                    "date": str(row_date),
                    "open": _parse_float(_get_field(row, col_map, "open")),
                    "high": _parse_float(_get_field(row, col_map, "high")),
                    "low": _parse_float(_get_field(row, col_map, "low")),
                    "close": _parse_float(_get_field(row, col_map, "close")),
                    "volume": _parse_int(_get_field(row, col_map, "volume")),
                    "adjusted_close": _parse_float(_get_field(row, col_map, "adjusted_close")),
                    "dataset_source": "dow_jones",
                    "survivorship_bias_audited": False,
                }
                rows_to_insert.append(record)
                tickers_found.add(record["ticker"])
                dates.append(row_date)
            except Exception as e:
                errors.append(f"Line {line_num}: {e}")

    # Batch upsert
    rows_loaded = _batch_upsert(rows_to_insert)
    rows_skipped = len(rows_to_insert) - rows_loaded

    result = {
        "dataset_source": "dow_jones",
        "file_path": str(file_path),
        "rows_loaded": rows_loaded,
        "rows_skipped": rows_skipped,
        "date_range_start": str(min(dates)) if dates else None,
        "date_range_end": str(max(dates)) if dates else None,
        "tickers_found": sorted(tickers_found),
        "errors": errors[:50],  # Cap error list
    }

    logger.info(
        f"Dow Jones: loaded {rows_loaded} rows, "
        f"{len(tickers_found)} tickers, "
        f"date range {result['date_range_start']} to {result['date_range_end']}"
    )
    return result


# ---------------------------------------------------------------------------
# Emery S&P 500 CSV Loader (10yr OHLCV)
# ---------------------------------------------------------------------------

def load_emery_dataset(file_path: str | Path) -> dict:
    """Load Emery S&P 500 10-year OHLCV dataset from CSV into price_history.

    Expected CSV columns (flexible header matching):
        Date, Ticker/Symbol, Open, High, Low, Close, Volume

    Multi-ticker dataset covering all US stocks in the S&P 500.

    Args:
        file_path: Path to the Emery CSV file.

    Returns:
        DatasetLoadResult-compatible dict with row counts and date range.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    logger.info(f"Loading Emery S&P 500 dataset: {file_path}")

    rows_to_insert = []
    errors = []
    tickers_found = set()
    dates = []

    with open(file_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = {h.strip().lower(): h.strip() for h in (reader.fieldnames or [])}
        col_map = _build_column_map(headers)

        for line_num, raw_row in enumerate(reader, start=2):
            try:
                row = {k.strip(): v.strip() if v else "" for k, v in raw_row.items()}
                ticker = _get_field(row, col_map, "ticker")
                if not ticker:
                    errors.append(f"Line {line_num}: missing ticker")
                    continue

                row_date = _parse_date(_get_field(row, col_map, "date"))
                if row_date is None:
                    errors.append(f"Line {line_num}: invalid date")
                    continue

                record = {
                    "ticker": ticker.upper(),
                    "date": str(row_date),
                    "open": _parse_float(_get_field(row, col_map, "open")),
                    "high": _parse_float(_get_field(row, col_map, "high")),
                    "low": _parse_float(_get_field(row, col_map, "low")),
                    "close": _parse_float(_get_field(row, col_map, "close")),
                    "volume": _parse_int(_get_field(row, col_map, "volume")),
                    "adjusted_close": _parse_float(_get_field(row, col_map, "adjusted_close")),
                    "dataset_source": "emery_sp500",
                    "survivorship_bias_audited": False,
                }
                rows_to_insert.append(record)
                tickers_found.add(record["ticker"])
                dates.append(row_date)
            except Exception as e:
                errors.append(f"Line {line_num}: {e}")

    # Batch upsert
    rows_loaded = _batch_upsert(rows_to_insert)
    rows_skipped = len(rows_to_insert) - rows_loaded

    result = {
        "dataset_source": "emery_sp500",
        "file_path": str(file_path),
        "rows_loaded": rows_loaded,
        "rows_skipped": rows_skipped,
        "date_range_start": str(min(dates)) if dates else None,
        "date_range_end": str(max(dates)) if dates else None,
        "tickers_found": sorted(tickers_found),
        "errors": errors[:50],
    }

    logger.info(
        f"Emery: loaded {rows_loaded} rows, "
        f"{len(tickers_found)} tickers, "
        f"date range {result['date_range_start']} to {result['date_range_end']}"
    )
    return result


# ---------------------------------------------------------------------------
# Price history stats
# ---------------------------------------------------------------------------

def get_price_history_stats() -> list[dict]:
    """Query Supabase for row counts and date ranges per dataset source.

    Returns a list of PriceHistoryStats-compatible dicts.
    """
    client = get_supabase()
    stats = []

    for source in ("dow_jones", "emery_sp500"):
        response = (
            client.table("price_history")
            .select("ticker, date, survivorship_bias_audited")
            .eq("dataset_source", source)
            .execute()
        )

        rows = response.data
        if not rows:
            stats.append({
                "dataset_source": source,
                "row_count": 0,
                "ticker_count": 0,
                "date_range_start": None,
                "date_range_end": None,
                "survivorship_audited_count": 0,
            })
            continue

        tickers = set()
        dates = []
        audited = 0
        for row in rows:
            tickers.add(row["ticker"])
            dates.append(row["date"])
            if row.get("survivorship_bias_audited"):
                audited += 1

        stats.append({
            "dataset_source": source,
            "row_count": len(rows),
            "ticker_count": len(tickers),
            "date_range_start": min(dates) if dates else None,
            "date_range_end": max(dates) if dates else None,
            "survivorship_audited_count": audited,
        })

    return stats


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_column_map(headers: dict[str, str]) -> dict[str, str]:
    """Map logical field names to actual CSV column names.

    Args:
        headers: dict of lowercased_header -> original_header
    """
    mappings = {
        "date": ["date"],
        "ticker": ["ticker", "symbol", "security"],
        "open": ["open"],
        "high": ["high"],
        "low": ["low"],
        "close": ["close"],
        "volume": ["volume", "vol"],
        "adjusted_close": ["adjusted close", "adj close", "adj_close", "adjusted_close"],
    }

    col_map = {}
    for field, candidates in mappings.items():
        for candidate in candidates:
            if candidate in headers:
                col_map[field] = headers[candidate]
                break

    return col_map


def _get_field(row: dict, col_map: dict[str, str], field: str) -> Optional[str]:
    """Get a field value from a row using the column map."""
    col_name = col_map.get(field)
    if col_name is None:
        return None
    return row.get(col_name, "").strip() or None


def _parse_date(value: Optional[str]) -> Optional[date]:
    """Parse a date string in common formats."""
    if not value:
        return None
    from datetime import datetime as dt
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y", "%m-%d-%Y"):
        try:
            return dt.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_float(value: Optional[str]) -> Optional[float]:
    """Parse a string to float, returning None on failure."""
    if not value:
        return None
    try:
        return float(value.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def _parse_int(value: Optional[str]) -> Optional[int]:
    """Parse a string to int, returning None on failure."""
    if not value:
        return None
    try:
        return int(float(value.replace(",", "")))
    except (ValueError, AttributeError):
        return None


def _batch_upsert(rows: list[dict]) -> int:
    """Batch upsert rows to price_history table.

    Uses batches of BATCH_SIZE to avoid payload limits.
    Handles duplicates gracefully via upsert on (ticker, date, dataset_source).

    Returns count of successfully upserted rows.
    """
    if not rows:
        return 0

    client = get_supabase()
    total_upserted = 0

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        try:
            client.table("price_history").upsert(
                batch,
                on_conflict="ticker,date,dataset_source",
            ).execute()
            total_upserted += len(batch)
        except Exception as e:
            logger.error(f"Batch upsert failed (rows {i}-{i+len(batch)}): {e}")

    return total_upserted
