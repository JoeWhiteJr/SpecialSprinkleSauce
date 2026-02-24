from datetime import datetime, timezone
from fastapi import APIRouter, Path, Query, HTTPException
from typing import Optional

from app.config import settings
from app.models.schemas import RiskAlert, ConsecutiveLossStreak
from app.mock.generators import generate_risk_alerts, generate_consecutive_loss_streak

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

# In-memory store for mock data mutations
_mock_alerts: list[dict] | None = None


def _get_mock_alerts() -> list[dict]:
    global _mock_alerts
    if _mock_alerts is None:
        _mock_alerts = generate_risk_alerts()
    return _mock_alerts


@router.get("", response_model=list[RiskAlert])
async def list_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity: info, warning, critical"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledged status"),
):
    """List risk alerts, optionally filtered by severity and/or acknowledged status."""
    if settings.use_mock_data:
        alerts = _get_mock_alerts()
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]
        if acknowledged is not None:
            alerts = [a for a in alerts if a["acknowledged"] == acknowledged]
        return alerts

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    query = client.table("risk_alerts").select("*")
    if severity:
        query = query.eq("severity", severity)
    if acknowledged is not None:
        query = query.eq("acknowledged", acknowledged)
    result = query.order("timestamp", desc=True).execute()
    return result.data


@router.get("/streak", response_model=ConsecutiveLossStreak)
async def get_loss_streak():
    """Current consecutive loss streak tracker state."""
    if settings.use_mock_data:
        return generate_consecutive_loss_streak()

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = client.table("consecutive_loss_tracker").select("*").single().execute()
    return result.data


@router.post("/{alert_id}/acknowledge", response_model=RiskAlert)
async def acknowledge_alert(
    alert_id: str = Path(..., description="Alert ID"),
):
    """Mark a risk alert as acknowledged."""
    if settings.use_mock_data:
        alerts = _get_mock_alerts()
        alert = next((a for a in alerts if a["id"] == alert_id), None)
        if alert is None:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        if alert["acknowledged"]:
            raise HTTPException(
                status_code=400, detail=f"Alert {alert_id} is already acknowledged"
            )
        alert["acknowledged"] = True
        alert["acknowledged_by"] = "Dashboard User"
        alert["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
        return alert

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = (
        client.table("risk_alerts")
        .update({
            "acknowledged": True,
            "acknowledged_by": "Dashboard User",
            "acknowledged_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", alert_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return result.data[0]
