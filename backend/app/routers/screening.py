from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.schemas import ScreeningRun
from app.mock.generators import generate_screening_runs

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
