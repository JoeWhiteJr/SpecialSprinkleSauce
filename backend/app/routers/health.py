from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import settings
from app.models.schemas import HealthResponse
from app.services.supabase_client import check_connection

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check():
    """System health check. Returns trading mode, DB status, and timestamp."""
    db_connected = check_connection() if not settings.use_mock_data else False
    return HealthResponse(
        status="healthy",
        trading_mode=settings.trading_mode,
        use_mock_data=settings.use_mock_data,
        db_connected=db_connected,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
