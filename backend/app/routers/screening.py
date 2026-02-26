from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.schemas import ScreeningRun
from app.mock.generators import (
    generate_screening_runs,
    generate_piotroski_mock,
    generate_tier1_preview,
    generate_tier2_preview,
)

router = APIRouter(prefix="/api/screening", tags=["screening"])


@router.get("/latest", response_model=ScreeningRun)
async def get_latest_screening():
    """Most recent screening run with full funnel data."""
    if settings.use_mock_data:
        runs = generate_screening_runs()
        if not runs:
            raise HTTPException(status_code=404, detail="No screening runs found")
        # Return the most recent by timestamp
        runs.sort(key=lambda r: r["timestamp"], reverse=True)
        return runs[0]

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = (
        client.table("screening_runs")
        .select("*")
        .order("timestamp", desc=True)
        .limit(1)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="No screening runs found")
    return result.data


@router.get("/history", response_model=list[ScreeningRun])
async def get_screening_history():
    """All screening runs."""
    if settings.use_mock_data:
        runs = generate_screening_runs()
        runs.sort(key=lambda r: r["timestamp"], reverse=True)
        return runs

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = (
        client.table("screening_runs")
        .select("*")
        .order("timestamp", desc=True)
        .execute()
    )
    return result.data


@router.post("/run")
async def run_screening():
    """Trigger a new screening pipeline run."""
    if settings.use_mock_data:
        runs = generate_screening_runs()
        return runs[0]

    # In production, would use screening_engine.run_screening_pipeline()
    # with data from data_source_chain.fetch_ticker_fundamentals()
    # For now, return mock until universe data is available
    runs = generate_screening_runs()
    return runs[0]


@router.get("/{run_id}/details")
async def get_screening_details(run_id: str):
    """Get detailed per-tier results for a screening run."""
    if settings.use_mock_data:
        runs = generate_screening_runs()
        for run in runs:
            if run["id"] == run_id:
                return run
        raise HTTPException(status_code=404, detail="Screening run not found")

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = (
        client.table("screening_runs")
        .select("*")
        .eq("id", run_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Screening run not found")
    return result.data


@router.get("/piotroski/{ticker}")
async def get_piotroski_score(ticker: str):
    """Get Piotroski F-Score for a single ticker."""
    if settings.use_mock_data:
        return generate_piotroski_mock(ticker)

    from app.services.data_source_chain import fetch_ticker_fundamentals
    from app.services.piotroski import compute_piotroski

    data = fetch_ticker_fundamentals(ticker)
    result = compute_piotroski(ticker, data["fields"])
    return {
        "ticker": result.ticker,
        "score": result.score,
        "max_possible": result.max_possible,
        "ratio": result.ratio,
        "passes_threshold": result.passes_threshold,
        "data_available": result.data_available,
        "signals": [
            {
                "name": s.name,
                "value": s.value,
                "data_available": s.data_available,
                "detail": s.detail,
            }
            for s in result.signals
        ],
    }


@router.get("/tier1/preview")
async def get_tier1_preview():
    """Preview Tier 1 (liquidity) filter results for pilot tickers."""
    if settings.use_mock_data:
        return generate_tier1_preview()

    return generate_tier1_preview()


@router.get("/tier2/preview")
async def get_tier2_preview():
    """Preview Tier 2 (Sprinkle Sauce) filter results for pilot tickers."""
    if settings.use_mock_data:
        return generate_tier2_preview()

    return generate_tier2_preview()
