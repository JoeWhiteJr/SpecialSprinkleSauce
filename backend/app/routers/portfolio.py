from fastapi import APIRouter, Query
from typing import Optional

from app.config import settings
from app.models.schemas import PortfolioPosition, DailySnapshot, PortfolioSummary
from app.mock.generators import (
    generate_positions,
    generate_portfolio_snapshots,
    generate_portfolio_summary,
)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/positions", response_model=list[PortfolioPosition])
async def get_positions(
    status: Optional[str] = Query(None, description="Filter by status: open or closed"),
):
    """All portfolio positions, optionally filtered by status."""
    if settings.use_mock_data:
        positions = generate_positions()
        if status:
            positions = [p for p in positions if p["status"] == status]
        return positions

    # Supabase query path
    from app.services.supabase_client import get_supabase

    client = get_supabase()
    query = client.table("positions").select("*")
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return result.data


@router.get("/pnl", response_model=list[DailySnapshot])
async def get_pnl():
    """30-day daily portfolio snapshot array for the P&L chart."""
    if settings.use_mock_data:
        return generate_portfolio_snapshots()

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = (
        client.table("portfolio_snapshots")
        .select("*")
        .order("date", desc=False)
        .limit(30)
        .execute()
    )
    return result.data


@router.get("/summary", response_model=PortfolioSummary)
async def get_summary():
    """Portfolio summary: total value, daily P&L, total P&L, win rate, positions count."""
    if settings.use_mock_data:
        return generate_portfolio_summary()

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = client.table("portfolio_summary").select("*").single().execute()
    return result.data
