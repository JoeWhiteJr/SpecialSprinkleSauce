from fastapi import APIRouter, Path, HTTPException

from app.config import settings
from app.models.schemas import JuryResult, JuryStats
from app.mock.generators import generate_journal_entries, generate_jury_stats

router = APIRouter(prefix="/api/jury", tags=["jury"])


@router.get("/stats", response_model=JuryStats)
async def get_jury_stats():
    """Aggregate jury statistics: total votes, agreement rate, escalation count."""
    if settings.use_mock_data:
        return generate_jury_stats()

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = client.table("jury_stats").select("*").single().execute()
    return result.data


@router.get("/{pipeline_run_id}", response_model=JuryResult)
async def get_jury_votes(
    pipeline_run_id: str = Path(..., description="Pipeline run UUID"),
):
    """All 10 jury votes for a specific pipeline run."""
    if settings.use_mock_data:
        entries = generate_journal_entries()
        entry = next(
            (e for e in entries if e["pipeline_run_id"] == pipeline_run_id),
            None,
        )
        if entry is None:
            raise HTTPException(
                status_code=404,
                detail=f"Pipeline run {pipeline_run_id} not found",
            )
        jury = entry["jury"]
        if not jury["spawned"]:
            raise HTTPException(
                status_code=404,
                detail=f"No jury was spawned for pipeline run {pipeline_run_id}",
            )
        return jury

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = (
        client.table("jury_votes")
        .select("*")
        .eq("pipeline_run_id", pipeline_run_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=404,
            detail=f"No jury votes found for pipeline run {pipeline_run_id}",
        )
    return result.data
