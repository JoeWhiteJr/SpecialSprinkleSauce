"""Pipeline API — run decisions, view pipeline runs and audit trails."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.mock.generators import generate_pipeline_run_mock, generate_pipeline_runs_mock

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


class PipelineRunRequest(BaseModel):
    ticker: str
    price: float | None = None
    fundamentals: dict | None = None


class PipelineBatchRequest(BaseModel):
    tickers: list[PipelineRunRequest]


@router.post("/run")
async def run_pipeline(request: PipelineRunRequest):
    """Run full decision pipeline for a single ticker."""
    if settings.use_mock_data:
        return generate_pipeline_run_mock(request.ticker)

    from src.pipeline.decision_pipeline import DecisionPipeline

    pipeline = DecisionPipeline(use_mock=False)
    price = request.price or 0.0
    return pipeline.run(request.ticker, price, request.fundamentals)


@router.post("/run-batch")
async def run_pipeline_batch(request: PipelineBatchRequest):
    """Run decision pipeline for multiple tickers."""
    if settings.use_mock_data:
        return [generate_pipeline_run_mock(t.ticker) for t in request.tickers]

    from src.pipeline.decision_pipeline import DecisionPipeline

    pipeline = DecisionPipeline(use_mock=False)
    tickers_data = [
        {"ticker": t.ticker, "price": t.price or 0.0, "fundamentals": t.fundamentals}
        for t in request.tickers
    ]
    return pipeline.run_batch(tickers_data)


@router.get("/runs")
async def list_pipeline_runs():
    """List recent pipeline runs."""
    if settings.use_mock_data:
        return generate_pipeline_runs_mock()

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = (
        client.table("pipeline_runs")
        .select("*")
        .order("started_at", desc=True)
        .limit(20)
        .execute()
    )
    return result.data


@router.get("/runs/{run_id}")
async def get_pipeline_run(run_id: str):
    """Get full pipeline run detail."""
    if settings.use_mock_data:
        runs = generate_pipeline_runs_mock()
        for run in runs:
            if run["id"] == run_id:
                return run
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = (
        client.table("pipeline_runs")
        .select("*")
        .eq("id", run_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return result.data


@router.get("/runs/{run_id}/nodes")
async def get_pipeline_nodes(run_id: str):
    """Get per-node audit trail for a pipeline run."""
    if settings.use_mock_data:
        runs = generate_pipeline_runs_mock()
        for run in runs:
            if run["id"] == run_id:
                return run.get("node_journal", [])
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = (
        client.table("pipeline_runs")
        .select("node_journal")
        .eq("id", run_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return result.data.get("node_journal", [])
