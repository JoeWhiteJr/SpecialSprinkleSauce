from fastapi import APIRouter

from app.config import settings
from app.models.schemas import BiasMetric
from app.mock.generators import generate_bias_metrics

router = APIRouter(prefix="/api/bias", tags=["bias"])


@router.get("/metrics", response_model=list[BiasMetric])
async def get_latest_bias_metrics():
    """Latest week's bias monitoring data."""
    if settings.use_mock_data:
        metrics = generate_bias_metrics()
        # Return only the most recent week
        return [metrics[-1]] if metrics else []

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = (
        client.table("bias_metrics")
        .select("*")
        .order("week_end", desc=True)
        .limit(1)
        .execute()
    )
    return result.data


@router.get("/history", response_model=list[BiasMetric])
async def get_bias_history():
    """All weeks of bias monitoring data."""
    if settings.use_mock_data:
        return generate_bias_metrics()

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = (
        client.table("bias_metrics")
        .select("*")
        .order("week_end", desc=True)
        .execute()
    )
    return result.data
