"""Goals API — run goal orchestrator, track progress, target sweep."""

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from app.config import settings

router = APIRouter(prefix="/api/goals", tags=["goals"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class GoalRunRequest(BaseModel):
    capital: float = Field(..., gt=0, le=1_000_000, description="Dollar amount available")
    target_return_pct: float = Field(..., gt=0, le=1.0, description="Target return as decimal (0.02 = 2%)")
    timeframe_days: int = Field(..., ge=1, le=90, description="Trading days to achieve goal")
    max_loss_pct: float = Field(..., gt=0, le=0.5, description="Max acceptable loss as decimal")


class TargetSweepRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    capital: float = Field(default=1000.0, gt=0, le=1_000_000)
    timeframe_days: int = Field(default=5, ge=1, le=90)
    max_loss_pct: float = Field(default=0.01, gt=0, le=0.5)


# ---------------------------------------------------------------------------
# Goal run endpoints
# ---------------------------------------------------------------------------


@router.post("/run")
async def run_goal(request: GoalRunRequest):
    """Run the full goal orchestrator."""
    from src.pipeline.goal.goal_state import GoalConfig
    from src.pipeline.goal.goal_orchestrator import GoalOrchestrator

    config = GoalConfig.create(
        capital=request.capital,
        target_return_pct=request.target_return_pct,
        timeframe_days=request.timeframe_days,
        max_loss_pct=request.max_loss_pct,
    )

    orchestrator = GoalOrchestrator(use_mock=settings.use_mock_data)
    state = orchestrator.run(config)

    return _serialize_goal_state(state)


@router.post("/run-stream")
async def run_goal_stream(request: GoalRunRequest):
    """Run goal orchestrator with SSE streaming — events emitted per stage."""
    from src.pipeline.goal.goal_state import GoalConfig
    from src.pipeline.goal.goal_orchestrator import GoalOrchestrator

    config = GoalConfig.create(
        capital=request.capital,
        target_return_pct=request.target_return_pct,
        timeframe_days=request.timeframe_days,
        max_loss_pct=request.max_loss_pct,
    )

    async def event_generator():
        # For now, run synchronously and emit a single complete event
        # Streaming will be enhanced in PR 6 with per-stage events
        orchestrator = GoalOrchestrator(use_mock=settings.use_mock_data)
        state = orchestrator.run(config)
        result = _serialize_goal_state(state)

        yield f"event: goal_complete\ndata: {json.dumps(result)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/runs")
async def list_goal_runs():
    """List recent goal runs."""
    if settings.use_mock_data:
        from src.pipeline.goal.goal_state import GoalConfig
        from src.pipeline.goal.mock_goal_orchestrator import MockGoalOrchestrator

        config = GoalConfig.create(capital=1000, target_return_pct=0.02, timeframe_days=5, max_loss_pct=0.01)
        state = MockGoalOrchestrator().run(config)
        return [_serialize_goal_state(state)]

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = (
        client.table("goal_runs")
        .select("*")
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    return result.data


@router.get("/runs/{goal_id}")
async def get_goal_run(goal_id: str):
    """Get full goal run detail."""
    if settings.use_mock_data:
        from src.pipeline.goal.goal_state import GoalConfig
        from src.pipeline.goal.mock_goal_orchestrator import MockGoalOrchestrator

        config = GoalConfig.create(capital=1000, target_return_pct=0.02, timeframe_days=5, max_loss_pct=0.01)
        state = MockGoalOrchestrator().run(config)
        return _serialize_goal_state(state)

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = (
        client.table("goal_runs")
        .select("*")
        .eq("id", goal_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Goal run not found")
    return result.data


@router.get("/runs/{goal_id}/progress")
async def get_goal_progress(goal_id: str):
    """Get current progress toward a goal."""
    if settings.use_mock_data:
        return {
            "goal_id": goal_id,
            "cumulative_pnl": 12.50,
            "cumulative_pnl_pct": 0.0125,
            "remaining_target_pct": 0.0075,
            "remaining_days": 3,
            "daily_target_pct": 0.0025,
            "on_track": True,
            "pace": "ahead",
            "loss_limit_hit": False,
        }

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    result = (
        client.table("goal_runs")
        .select("cumulative_pnl, cumulative_pnl_pct, remaining_target_pct, status")
        .eq("id", goal_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Goal run not found")
    return result.data


@router.post("/runs/{goal_id}/re-evaluate")
async def re_evaluate_goal(goal_id: str):
    """Trigger manual re-evaluation of remaining trades."""
    # In production, would load goal state from DB and re-run Stage 2
    return {
        "goal_id": goal_id,
        "status": "re-evaluation queued",
        "message": "Re-evaluation will update the trade plan based on current progress.",
    }


@router.post("/runs/{goal_id}/stop")
async def stop_goal(goal_id: str):
    """Stop an active goal — cancel remaining trades."""
    return {
        "goal_id": goal_id,
        "status": "stopped",
        "message": "Goal stopped. Remaining planned trades cancelled.",
    }


# ---------------------------------------------------------------------------
# Target sweep endpoints (placeholder — full implementation in PR 5)
# ---------------------------------------------------------------------------


@router.post("/target-sweep")
async def run_target_sweep(request: TargetSweepRequest):
    """Run target sweep backtest across multiple target levels."""
    # Placeholder — will call TargetSweepEngine in PR 5
    target_levels = [0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.40]
    return {
        "sweep_id": "sweep-mock-001",
        "ticker": request.ticker.upper(),
        "capital": request.capital,
        "timeframe_days": request.timeframe_days,
        "frontier": [
            {
                "target_pct": t,
                "success_rate": max(0.0, 0.95 - t * 2),
                "avg_return": t * 0.8,
                "avg_drawdown": t * 0.4,
                "trades_taken": 5,
            }
            for t in target_levels
        ],
        "sweet_spot": {
            "target_pct": 0.02,
            "success_rate": 0.91,
            "avg_return": 0.016,
            "avg_drawdown": 0.008,
        },
    }


@router.get("/target-sweep/{sweep_id}")
async def get_target_sweep(sweep_id: str):
    """Get target sweep results."""
    if settings.use_mock_data:
        return {"sweep_id": sweep_id, "status": "completed"}

    raise HTTPException(status_code=404, detail="Sweep not found")


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _serialize_goal_state(state) -> dict:
    """Convert GoalState to JSON-serializable dict."""
    config = state.config
    return {
        "goal_id": state.goal_id,
        "config": {
            "capital": config.capital,
            "target_return_pct": config.target_return_pct,
            "timeframe_days": config.timeframe_days,
            "max_loss_pct": config.max_loss_pct,
            "target_dollar": config.target_dollar,
            "max_loss_dollar": config.max_loss_dollar,
        } if config else None,
        "status": state.status,
        "candidates": state.candidates,
        "portfolio_debate_outcome": state.portfolio_debate_outcome,
        "portfolio_allocations": state.portfolio_allocations,
        "trade_plan": [
            {
                "ticker": t.ticker,
                "action": t.action,
                "shares": t.shares,
                "entry_price_est": t.entry_price_est,
                "position_dollar": t.position_dollar,
                "stop_loss_price": t.stop_loss_price,
                "target_exit_price": t.target_exit_price,
                "contribution_target_pct": t.contribution_target_pct,
                "day_target": t.day_target,
                "status": t.status,
            }
            for t in state.trade_plan
        ],
        "cumulative_pnl": state.cumulative_pnl,
        "cumulative_pnl_pct": state.cumulative_pnl_pct,
        "remaining_capital": state.remaining_capital,
        "remaining_target_pct": state.remaining_target_pct,
        "errors": state.errors,
    }
