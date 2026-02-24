from fastapi import APIRouter, Path, Query, HTTPException
from typing import Optional

from app.config import settings
from app.models.schemas import DecisionJournalEntry
from app.mock.generators import generate_journal_entries

router = APIRouter(prefix="/api/journal", tags=["journal"])


@router.get("", response_model=list[DecisionJournalEntry])
async def list_journal_entries(
    ticker: Optional[str] = Query(None, description="Filter by ticker (e.g. NVDA)"),
    start_date: Optional[str] = Query(None, description="Filter entries from this date (ISO-8601)"),
    end_date: Optional[str] = Query(None, description="Filter entries until this date (ISO-8601)"),
    final_action: Optional[str] = Query(None, description="Filter by final decision action: BUY, SELL, HOLD, BLOCKED"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Pagination limit"),
):
    """List decision journal entries with pagination and filters."""
    if settings.use_mock_data:
        entries = generate_journal_entries()

        if ticker:
            ticker_upper = ticker.upper()
            entries = [
                e for e in entries
                if ticker_upper in e["ticker"].upper()
            ]

        if start_date:
            entries = [e for e in entries if e["timestamp"] >= start_date]

        if end_date:
            entries = [e for e in entries if e["timestamp"] <= end_date]

        if final_action:
            action_upper = final_action.upper()
            entries = [
                e for e in entries
                if e["final_decision"]["action"] == action_upper
            ]

        # Sort by timestamp descending (most recent first)
        entries.sort(key=lambda e: e["timestamp"], reverse=True)

        # Paginate
        return entries[offset : offset + limit]

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    query = client.table("decision_journal").select("*")
    if ticker:
        query = query.ilike("ticker", f"%{ticker}%")
    if start_date:
        query = query.gte("timestamp", start_date)
    if end_date:
        query = query.lte("timestamp", end_date)
    if final_action:
        query = query.eq("final_decision->>action", final_action.upper())
    result = (
        query.order("timestamp", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data


@router.get("/{entry_id}", response_model=DecisionJournalEntry)
async def get_journal_entry(
    entry_id: str = Path(..., description="Journal entry ID"),
):
    """Get full detail for a single decision journal entry."""
    if settings.use_mock_data:
        entries = generate_journal_entries()
        entry = next((e for e in entries if e["id"] == entry_id), None)
        if entry is None:
            raise HTTPException(
                status_code=404, detail=f"Journal entry {entry_id} not found"
            )
        return entry

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = (
        client.table("decision_journal")
        .select("*")
        .eq("id", entry_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=404, detail=f"Journal entry {entry_id} not found"
        )
    return result.data
