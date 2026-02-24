from fastapi import APIRouter, Path, HTTPException

from app.config import settings
from app.models.schemas import DebateSummary, DebateTranscript
from app.mock.generators import generate_debate_transcripts

router = APIRouter(prefix="/api/debates", tags=["debates"])


@router.get("", response_model=list[DebateSummary])
async def list_debates():
    """List debate summaries for all pipeline runs that had debates."""
    if settings.use_mock_data:
        transcripts = generate_debate_transcripts()
        summaries = []
        for t in transcripts:
            summaries.append({
                "pipeline_run_id": t["pipeline_run_id"],
                "ticker": t["ticker"],
                "timestamp": t["timestamp"],
                "outcome": t["outcome"],
                "rounds": len(t["rounds"]),
                "jury_triggered": t["jury_triggered"],
            })
        return summaries

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = (
        client.table("debates")
        .select("pipeline_run_id, ticker, timestamp, outcome, rounds, jury_triggered")
        .order("timestamp", desc=True)
        .execute()
    )
    return result.data


@router.get("/{pipeline_run_id}", response_model=DebateTranscript)
async def get_debate(
    pipeline_run_id: str = Path(..., description="Pipeline run UUID"),
):
    """Full debate transcript with all rounds for a given pipeline run."""
    if settings.use_mock_data:
        transcripts = generate_debate_transcripts()
        transcript = next(
            (t for t in transcripts if t["pipeline_run_id"] == pipeline_run_id),
            None,
        )
        if transcript is None:
            raise HTTPException(
                status_code=404,
                detail=f"Debate for pipeline run {pipeline_run_id} not found",
            )
        return transcript

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = (
        client.table("debates")
        .select("*")
        .eq("pipeline_run_id", pipeline_run_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=404,
            detail=f"Debate for pipeline run {pipeline_run_id} not found",
        )
    return result.data
