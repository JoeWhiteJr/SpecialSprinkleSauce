"""Data pipeline endpoints for Bloomberg ingestion and historical dataset loading."""

import logging
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import settings
from app.models.schemas import (
    BloombergValidationReport,
    DatasetLoadResult,
    DatasetSource,
    FreshnessReport,
    PriceHistoryStats,
    TickerFreshness,
    DataFreshness,
)

logger = logging.getLogger("wasden_watch.data_pipeline")

router = APIRouter(prefix="/api/data", tags=["data-pipeline"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class PriceHistoryLoadRequest(BaseModel):
    """Request body for loading a price history dataset."""
    source: DatasetSource
    file_path: str


# ---------------------------------------------------------------------------
# POST /api/data/bloomberg/upload
# ---------------------------------------------------------------------------

@router.post("/bloomberg/upload", response_model=BloombergValidationReport)
async def upload_bloomberg(file: UploadFile = File(...)):
    """Upload a Bloomberg Excel export (.xlsx) for parsing and ingestion.

    Accepts multipart form file upload. Parses the Values sheet,
    validates all fields, computes freshness grades, and upserts to Supabase.

    Filename convention: JMWFM_Bloomberg_YYYY-MM-DD.xlsx
    """
    if settings.use_mock_data:
        return BloombergValidationReport(
            filename=file.filename or "mock.xlsx",
            pull_date=date.today(),
            total_tickers=0,
            successful_tickers=0,
            failed_tickers=0,
            uploaded_to_supabase=False,
            errors_summary=["Mock data mode — upload skipped"],
        )

    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="File must be an .xlsx Excel file")

    # Save uploaded file to temp location
    import tempfile
    tmp_dir = Path(tempfile.mkdtemp())
    tmp_path = tmp_dir / Path(file.filename).name

    try:
        contents = await file.read()
        tmp_path.write_bytes(contents)

        from app.services.bloomberg_pipeline import run_bloomberg_pipeline
        report = run_bloomberg_pipeline(str(tmp_path), upload=True)

        return BloombergValidationReport(**report)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Bloomberg upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")
    finally:
        # Clean up temp file
        if tmp_path.exists():
            tmp_path.unlink()
        if tmp_dir.exists():
            tmp_dir.rmdir()


# ---------------------------------------------------------------------------
# POST /api/data/price-history/load
# ---------------------------------------------------------------------------

@router.post("/price-history/load", response_model=DatasetLoadResult)
async def load_price_history(request: PriceHistoryLoadRequest):
    """Load a historical price dataset from a CSV file on the server.

    Specify the dataset source (dow_jones or emery_sp500) and the
    server-side file path to the CSV.
    """
    if settings.use_mock_data:
        return DatasetLoadResult(
            dataset_source=request.source,
            file_path=request.file_path,
            rows_loaded=0,
            errors=["Mock data mode — load skipped"],
        )

    file_path = Path(request.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")

    try:
        from app.services.data_loader import load_dow_jones_csv, load_emery_dataset

        if request.source == DatasetSource.DOW_JONES:
            result = load_dow_jones_csv(str(file_path))
        elif request.source == DatasetSource.EMERY_SP500:
            result = load_emery_dataset(str(file_path))
        else:
            raise HTTPException(status_code=400, detail=f"Unknown source: {request.source}")

        return DatasetLoadResult(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Dataset load failed: {e}")
        raise HTTPException(status_code=500, detail=f"Load error: {e}")


# ---------------------------------------------------------------------------
# GET /api/data/bloomberg/freshness
# ---------------------------------------------------------------------------

@router.get("/bloomberg/freshness", response_model=FreshnessReport)
async def bloomberg_freshness():
    """Return freshness status for all Bloomberg data by ticker.

    Grades: FRESH (<24h), RECENT (1-7d), STALE (7-30d), EXPIRED (>30d).
    """
    if settings.use_mock_data:
        # Return sample freshness for pilot tickers
        pilot_tickers = ["NVDA", "PYPL", "NFLX", "TSM", "XOM", "AAPL", "MSFT", "AMZN", "TSLA", "AMD"]
        return FreshnessReport(
            report_date=date.today(),
            tickers=[
                TickerFreshness(
                    ticker=t,
                    pull_date=date.today(),
                    freshness=DataFreshness.FRESH,
                    days_old=0,
                )
                for t in pilot_tickers
            ],
            fresh_count=len(pilot_tickers),
        )

    try:
        from app.services.bloomberg_pipeline import get_freshness_report
        report = get_freshness_report()
        return FreshnessReport(**report)
    except Exception as e:
        logger.error(f"Freshness report failed: {e}")
        raise HTTPException(status_code=500, detail=f"Freshness report error: {e}")


# ---------------------------------------------------------------------------
# GET /api/data/price-history/stats
# ---------------------------------------------------------------------------

@router.get("/price-history/stats", response_model=list[PriceHistoryStats])
async def price_history_stats():
    """Return row counts and date ranges per historical dataset source."""
    if settings.use_mock_data:
        return [
            PriceHistoryStats(
                dataset_source=DatasetSource.DOW_JONES,
                row_count=0,
                ticker_count=0,
            ),
            PriceHistoryStats(
                dataset_source=DatasetSource.EMERY_SP500,
                row_count=0,
                ticker_count=0,
            ),
        ]

    try:
        from app.services.data_loader import get_price_history_stats
        stats = get_price_history_stats()
        return [PriceHistoryStats(**s) for s in stats]
    except Exception as e:
        logger.error(f"Price history stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stats error: {e}")
