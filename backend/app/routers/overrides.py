from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import uuid

from app.config import settings
from app.models.schemas import VetoOverride, VetoOverrideCreate
from app.mock.generators import generate_veto_overrides

router = APIRouter(prefix="/api/overrides", tags=["overrides"])

# In-memory store for mock data mutations
_mock_overrides: list[dict] | None = None


def _get_mock_overrides() -> list[dict]:
    global _mock_overrides
    if _mock_overrides is None:
        _mock_overrides = generate_veto_overrides()
    return _mock_overrides


@router.get("", response_model=list[VetoOverride])
async def list_overrides(
    status: Optional[str] = Query(
        None,
        description="Filter by status: pending, approved, rejected, completed",
    ),
):
    """List veto override records, optionally filtered by status."""
    if settings.use_mock_data:
        overrides = _get_mock_overrides()
        if status:
            overrides = [o for o in overrides if o["status"] == status]
        return overrides

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    query = client.table("veto_overrides").select("*")
    if status:
        query = query.eq("status", status)
    result = query.order("timestamp", desc=True).execute()
    return result.data


@router.post("", response_model=VetoOverride, status_code=201)
async def create_override(override: VetoOverrideCreate):
    """Create a new veto override request."""
    if settings.use_mock_data:
        new_override = {
            "id": f"override-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ticker": override.ticker,
            "original_verdict": "VETO",
            "override_reason": override.override_reason,
            "overridden_by": override.overridden_by,
            "pipeline_run_id": str(uuid.uuid4()),
            "outcome_tracked": False,
            "status": "pending",
        }
        _get_mock_overrides().append(new_override)
        return new_override

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    data = {
        "id": f"override-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ticker": override.ticker,
        "original_verdict": "VETO",
        "override_reason": override.override_reason,
        "overridden_by": override.overridden_by,
        "pipeline_run_id": str(uuid.uuid4()),
        "outcome_tracked": False,
        "status": "pending",
    }
    result = client.table("veto_overrides").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create override")
    return result.data[0]
