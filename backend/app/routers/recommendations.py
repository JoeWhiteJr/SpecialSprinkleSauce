from datetime import datetime, timezone
from fastapi import APIRouter, Path, Query, HTTPException
from typing import Optional

from app.config import settings
from app.models.schemas import TradeRecommendation, RecommendationReview
from app.mock.generators import generate_recommendations

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

# In-memory store for mock data mutations
_mock_recommendations: list[dict] | None = None


def _get_mock_recs() -> list[dict]:
    global _mock_recommendations
    if _mock_recommendations is None:
        _mock_recommendations = generate_recommendations()
    return _mock_recommendations


@router.get("", response_model=list[TradeRecommendation])
async def list_recommendations(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected, executed, expired"),
):
    """List trade recommendations, optionally filtered by status."""
    if settings.use_mock_data:
        recs = _get_mock_recs()
        if status:
            recs = [r for r in recs if r["status"] == status]
        return recs

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    query = client.table("recommendations").select("*")
    if status:
        query = query.eq("status", status)
    result = query.order("timestamp", desc=True).execute()
    return result.data


@router.post("/{rec_id}/review", response_model=TradeRecommendation)
async def review_recommendation(
    rec_id: str = Path(..., description="Recommendation ID"),
    review: RecommendationReview = ...,
):
    """Review a pending recommendation: approve or reject it."""
    if settings.use_mock_data:
        recs = _get_mock_recs()
        rec = next((r for r in recs if r["id"] == rec_id), None)
        if rec is None:
            raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found")
        if rec["status"] != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Recommendation {rec_id} is already {rec['status']}, cannot review",
            )
        rec["status"] = review.action.value
        rec["review_note"] = review.note
        rec["reviewed_by"] = "Dashboard User"
        rec["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        return rec

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = (
        client.table("recommendations")
        .update({
            "status": review.action.value,
            "review_note": review.note,
            "reviewed_by": "Dashboard User",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", rec_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found")
    return result.data[0]
