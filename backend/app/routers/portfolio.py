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
    query = client.table("portfolio_positions").select("*")
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
        client.table("portfolio_daily_snapshot")
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

    # Latest daily snapshot for top-level values
    snap = (
        client.table("portfolio_daily_snapshot")
        .select("*")
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    snapshot = snap.data[0] if snap.data else {}

    total_value = snapshot.get("total_value", 0)
    daily_pnl = snapshot.get("daily_pnl", 0)
    total_pnl = snapshot.get("cumulative_pnl", 0)
    cash_balance = snapshot.get("cash_balance", 0)

    # All positions for trade statistics
    pos_result = client.table("portfolio_positions").select("*").execute()
    positions = pos_result.data or []

    open_positions = sum(1 for p in positions if p.get("status") == "open")
    closed_positions = sum(1 for p in positions if p.get("status") == "closed")
    total_trades = len(positions)

    closed = [p for p in positions if p.get("status") == "closed"]
    winning_trades = sum(1 for p in closed if (p.get("pnl") or 0) > 0)
    losing_trades = sum(1 for p in closed if (p.get("pnl") or 0) <= 0)
    win_rate = winning_trades / total_trades if total_trades > 0 else 0

    invested_value = sum(
        (p.get("current_price") or 0) * (p.get("shares") or 0)
        for p in positions if p.get("status") == "open"
    )

    daily_pnl_pct = daily_pnl / total_value if total_value else 0
    cost_basis = total_value - total_pnl
    total_pnl_pct = total_pnl / cost_basis if cost_basis > 0 else 0

    return {
        "total_value": total_value,
        "cash_balance": cash_balance,
        "invested_value": invested_value,
        "daily_pnl": daily_pnl,
        "daily_pnl_pct": round(daily_pnl_pct, 4),
        "total_pnl": total_pnl,
        "total_pnl_pct": round(total_pnl_pct, 4),
        "win_rate": round(win_rate, 4),
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "open_positions": open_positions,
        "closed_positions": closed_positions,
    }
