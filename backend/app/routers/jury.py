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
    from collections import defaultdict, Counter

    client = get_supabase()
    result = client.table("jury_votes").select("*").execute()
    all_votes = result.data or []

    total_votes_cast = len(all_votes)
    buy_votes = sum(1 for v in all_votes if v.get("vote") == "BUY")
    sell_votes = sum(1 for v in all_votes if v.get("vote") == "SELL")
    hold_votes = sum(1 for v in all_votes if v.get("vote") == "HOLD")

    # Group by pipeline_run_id for session-level stats
    sessions: dict[str, list[dict]] = defaultdict(list)
    for v in all_votes:
        sessions[v["pipeline_run_id"]].append(v)

    total_jury_sessions = len(sessions)
    agreement_count = 0
    escalation_count = 0
    majority_sizes: list[int] = []

    for run_id, votes in sessions.items():
        counts = Counter(v["vote"] for v in votes)
        sorted_counts = counts.most_common()
        max_count = sorted_counts[0][1] if sorted_counts else 0
        majority_sizes.append(max_count)

        if max_count >= 6:
            agreement_count += 1

        # 5-5 tie: top two counts are equal at 5
        if len(sorted_counts) >= 2 and sorted_counts[0][1] == 5 and sorted_counts[1][1] == 5:
            escalation_count += 1

    agreement_rate = agreement_count / total_jury_sessions if total_jury_sessions > 0 else 0
    average_majority_size = sum(majority_sizes) / len(majority_sizes) if majority_sizes else 0

    return {
        "total_jury_sessions": total_jury_sessions,
        "total_votes_cast": total_votes_cast,
        "buy_votes": buy_votes,
        "sell_votes": sell_votes,
        "hold_votes": hold_votes,
        "agreement_rate": round(agreement_rate, 4),
        "escalation_count": escalation_count,
        "average_majority_size": round(average_majority_size, 2),
    }


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
