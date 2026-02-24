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
    from collections import defaultdict

    client = get_supabase()

    # Fetch all debate transcript rows ordered by created_at
    rows = (
        client.table("debate_transcripts")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    ).data or []

    # Group by pipeline_run_id
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[row["pipeline_run_id"]].append(row)

    # Check which pipeline runs have jury votes
    run_ids = list(groups.keys())
    jury_runs: set[str] = set()
    if run_ids:
        jury_rows = (
            client.table("jury_votes")
            .select("pipeline_run_id")
            .in_("pipeline_run_id", run_ids)
            .execute()
        ).data or []
        jury_runs = {r["pipeline_run_id"] for r in jury_rows}

    summaries = []
    for run_id, round_rows in groups.items():
        first = round_rows[0]
        summaries.append({
            "pipeline_run_id": run_id,
            "ticker": first["ticker"],
            "timestamp": first["created_at"],
            "outcome": first["outcome"] or "disagreement",
            "rounds": len(round_rows),
            "jury_triggered": run_id in jury_runs,
        })

    return summaries


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

    # Fetch all rounds for this pipeline run
    rows = (
        client.table("debate_transcripts")
        .select("*")
        .eq("pipeline_run_id", pipeline_run_id)
        .order("round_number", desc=False)
        .execute()
    ).data or []

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Debate for pipeline run {pipeline_run_id} not found",
        )

    first = rows[0]

    # Check if jury was triggered for this run
    jury_rows = (
        client.table("jury_votes")
        .select("id")
        .eq("pipeline_run_id", pipeline_run_id)
        .limit(1)
        .execute()
    ).data or []

    rounds = [
        {
            "round_number": r["round_number"],
            "bull_argument": r["bull_argument"],
            "bear_argument": r["bear_argument"],
        }
        for r in rows
    ]

    return {
        "pipeline_run_id": pipeline_run_id,
        "ticker": first["ticker"],
        "timestamp": first["created_at"],
        "rounds": rounds,
        "outcome": first["outcome"] or "disagreement",
        "bull_model": "claude-sonnet",
        "bear_model": "gemini-pro",
        "jury_triggered": len(jury_rows) > 0,
    }
