"""Training Lab API — experiment tracking, parameter sweeps, approvals, export."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.services.training.experiment_service import ExperimentService
from app.services.training.sweep_runner import SweepRunner
from app.services.training.auto_tuner import AutoTuner, PARAMETER_BOUNDS
from app.services.training.export_service import ExportService

router = APIRouter(prefix="/api/training", tags=["training"])

# ---------------------------------------------------------------------------
# Shared service instances (mock mode for now)
# ---------------------------------------------------------------------------

_experiments = ExperimentService()
_sweep_runner = SweepRunner(use_mock=True)
_auto_tuner = AutoTuner()
_export = ExportService()

# In-memory proposal store (will move to Supabase)
_proposals: dict[str, dict[str, Any]] = {}
_history: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ExperimentCreateRequest(BaseModel):
    user_name: str = Field(..., pattern="^(joe|jared)$")
    experiment_type: str
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    data_source: str = "mock"
    phase: str = "pre_server"


class ExperimentUpdateRequest(BaseModel):
    results: dict[str, Any] | None = None
    notes: str | None = None
    status: str | None = None


class SweepRunRequest(BaseModel):
    parameter_name: str
    data_source: str = "mock"
    optimize_metric: str = "win_rate"
    custom_values: list[float] | None = None


class AutoTuneRequest(BaseModel):
    category: str = Field(..., description="Parameter category to auto-tune")
    data_source: str = "mock"
    optimize_metric: str = "win_rate"


class ApprovalRequest(BaseModel):
    user_name: str = Field(..., pattern="^(joe|jared)$")


class SnapshotCreateRequest(BaseModel):
    model_name: str
    metrics: dict[str, Any]
    parameters: dict[str, Any] = Field(default_factory=dict)
    artifact_path: str | None = None
    is_baseline: bool = False
    data_source: str | None = None
    data_range: str | None = None


class StressTestRequest(BaseModel):
    regime: str
    data_source: str = "mock"


class EnsembleWeightSweepRequest(BaseModel):
    data_source: str = "mock"
    grid_step: float = Field(default=0.1, gt=0, le=0.5)


class PipelineRunRequest(BaseModel):
    data_source: str = "mock"
    models: list[str] = Field(default_factory=lambda: ["xgboost", "elastic_net", "arima", "sentiment"])


# ---------------------------------------------------------------------------
# Experiments CRUD
# ---------------------------------------------------------------------------


@router.post("/experiments")
async def create_experiment(request: ExperimentCreateRequest) -> dict[str, Any]:
    """Create a new experiment record."""
    return _experiments.create_experiment(
        user_name=request.user_name,
        experiment_type=request.experiment_type,
        name=request.name,
        description=request.description,
        parameters=request.parameters,
        data_source=request.data_source,
        phase=request.phase,
    )


@router.get("/experiments")
async def list_experiments(
    user_name: str | None = None,
    phase: str | None = None,
    status: str | None = None,
    experiment_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    """List experiments with optional filters."""
    return _experiments.list_experiments(
        user_name=user_name,
        phase=phase,
        status=status,
        experiment_type=experiment_type,
        limit=limit,
    )


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str) -> dict[str, Any]:
    """Get a single experiment with snapshots."""
    exp = _experiments.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


@router.put("/experiments/{experiment_id}")
async def update_experiment(
    experiment_id: str, request: ExperimentUpdateRequest
) -> dict[str, Any]:
    """Update experiment results, notes, or status."""
    exp = _experiments.update_experiment(
        experiment_id=experiment_id,
        results=request.results,
        notes=request.notes,
        status=request.status,
    )
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


@router.post("/experiments/{experiment_id}/snapshots")
async def create_snapshot(
    experiment_id: str, request: SnapshotCreateRequest
) -> dict[str, Any]:
    """Save a model snapshot for an experiment."""
    try:
        return _experiments.create_snapshot(
            experiment_id=experiment_id,
            model_name=request.model_name,
            metrics=request.metrics,
            parameters=request.parameters,
            artifact_path=request.artifact_path,
            is_baseline=request.is_baseline,
            data_source=request.data_source,
            data_range=request.data_range,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Parameter Sweeps
# ---------------------------------------------------------------------------


@router.post("/sweeps")
async def run_sweep(request: SweepRunRequest) -> dict[str, Any]:
    """Run a parameter sweep and return results."""
    try:
        result = _sweep_runner.run_parameter_sweep(
            parameter_name=request.parameter_name,
            data_source=request.data_source,
            optimize_metric=request.optimize_metric,
            custom_values=request.custom_values,
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sweeps/ensemble")
async def run_ensemble_sweep(request: EnsembleWeightSweepRequest) -> list[dict[str, Any]]:
    """Run ensemble weight grid search constrained to sum=1.0."""
    return _sweep_runner.run_ensemble_weight_sweep(
        data_source=request.data_source,
        grid_step=request.grid_step,
    )


@router.post("/sweeps/stress-test")
async def run_stress_test(request: StressTestRequest) -> dict[str, Any]:
    """Run models against a specific market regime."""
    try:
        return _sweep_runner.run_stress_test(
            regime=request.regime,
            data_source=request.data_source,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sweeps/stress-regimes")
async def get_stress_regimes() -> dict[str, dict[str, str]]:
    """List available stress test regimes."""
    return _sweep_runner.get_stress_regimes()


# ---------------------------------------------------------------------------
# Auto-Tuning & Proposals
# ---------------------------------------------------------------------------


@router.get("/parameters")
async def list_parameters(
    category: str | None = None,
) -> dict[str, Any]:
    """List all tunable parameters with their bounds."""
    params = PARAMETER_BOUNDS
    if category:
        params = {k: v for k, v in params.items() if v.category == category}

    return {
        name: {
            "min_value": bound.min_value,
            "max_value": bound.max_value,
            "step_size": bound.step_size,
            "category": bound.category,
            "description": bound.description,
        }
        for name, bound in params.items()
    }


@router.post("/auto-tune")
async def auto_tune(request: AutoTuneRequest) -> list[dict[str, Any]]:
    """Run auto-tune sweeps for all parameters in a category.

    Returns a list of proposals with before/after metrics.
    """
    from app.services.training.auto_tuner import get_parameters_by_category

    params = get_parameters_by_category(request.category)
    if not params:
        raise HTTPException(status_code=400, detail=f"No parameters in category: {request.category}")

    proposals: list[dict[str, Any]] = []
    for param_name in params:
        result = _sweep_runner.run_parameter_sweep(
            parameter_name=param_name,
            data_source=request.data_source,
            optimize_metric=request.optimize_metric,
        )
        if result.best_value is not None and result.data_points:
            # Get the current "default" value metrics (first data point as proxy)
            current_dp = result.data_points[0]
            best_dp = next(dp for dp in result.data_points if dp.value == result.best_value)

            proposal = _auto_tuner.create_proposal(
                parameter_name=param_name,
                current_value=current_dp.value,
                proposed_value=result.best_value,
                metric_before={request.optimize_metric: getattr(current_dp, request.optimize_metric, 0)},
                metric_after={request.optimize_metric: getattr(best_dp, request.optimize_metric, 0)},
                reason="Auto-tune sweep found optimal value",
            )
            import uuid
            proposal["id"] = str(uuid.uuid4())
            _proposals[proposal["id"]] = proposal
            proposals.append(proposal)

    return proposals


@router.get("/proposals")
async def list_proposals(
    status: str | None = None,
) -> list[dict[str, Any]]:
    """List parameter change proposals."""
    results = list(_proposals.values())
    if status:
        results = [p for p in results if p.get("status") == status]
    results.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    return results


@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str, request: ApprovalRequest
) -> dict[str, Any]:
    """Approve a parameter change proposal."""
    proposal = _proposals.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()

    if request.user_name == "joe":
        proposal["joe_approved_at"] = now
        if proposal.get("jared_approved_at"):
            proposal["status"] = "applied"
            proposal["applied_at"] = now
        else:
            proposal["status"] = "joe_approved"
    elif request.user_name == "jared":
        proposal["jared_approved_at"] = now
        if proposal.get("joe_approved_at"):
            proposal["status"] = "applied"
            proposal["applied_at"] = now
        else:
            proposal["status"] = "jared_approved"

    # For non-risk params, single approval is enough
    if not _auto_tuner.check_approval(proposal)["missing"]:
        if proposal["status"] not in ("applied", "rejected", "rolled_back"):
            proposal["status"] = "applied"
            proposal["applied_at"] = now
            history_entry = _auto_tuner.apply_proposal(proposal, request.user_name)
            _history.append(history_entry)

    return proposal


@router.post("/proposals/{proposal_id}/reject")
async def reject_proposal(proposal_id: str) -> dict[str, Any]:
    """Reject a parameter change proposal."""
    proposal = _proposals.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    proposal["status"] = "rejected"
    return proposal


@router.post("/proposals/{proposal_id}/rollback")
async def rollback_proposal(proposal_id: str) -> dict[str, Any]:
    """Rollback an applied parameter change."""
    proposal = _proposals.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.get("status") != "applied":
        raise HTTPException(status_code=400, detail="Can only rollback applied proposals")

    from datetime import datetime, timezone

    proposal["status"] = "rolled_back"
    proposal["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
    return proposal


@router.get("/history")
async def get_parameter_history() -> list[dict[str, Any]]:
    """Get the full parameter change history."""
    return sorted(_history, key=lambda h: h.get("created_at", ""), reverse=True)


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


@router.get("/compare")
async def compare_experiments(
    ids: str = Query(..., description="Comma-separated experiment IDs"),
) -> list[dict[str, Any]]:
    """Side-by-side comparison of experiments."""
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    return _experiments.compare_experiments(id_list)


@router.get("/compare-users")
async def compare_users(
    experiment_type: str = Query(..., description="Experiment type to compare"),
) -> dict[str, list[dict[str, Any]]]:
    """Compare Joe's vs Jared's results for the same experiment type."""
    return _experiments.compare_users(experiment_type)


@router.get("/baselines")
async def get_baselines() -> list[dict[str, Any]]:
    """Get all baseline model snapshots."""
    return _experiments.get_baselines()


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


@router.get("/export/experiments")
async def export_experiments(
    format: str = Query(default="csv", pattern="^(csv|xlsx)$"),
    user_name: str | None = None,
    phase: str | None = None,
) -> Response:
    """Export experiments to CSV or Excel."""
    experiments = _experiments.list_experiments(
        user_name=user_name, phase=phase, limit=1000
    )

    if format == "xlsx":
        content = _export.export_experiments_excel(experiments)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=experiments.xlsx"},
        )

    content = _export.export_experiments_csv(experiments)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=experiments.csv"},
    )


@router.get("/export/sweeps/{experiment_id}")
async def export_sweeps(
    experiment_id: str,
    format: str = Query(default="csv", pattern="^(csv|xlsx)$"),
) -> Response:
    """Export sweep results to CSV or Excel."""
    exp = _experiments.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    # Use experiment results as sweep data
    sweep_data = exp.get("results", {})

    if format == "xlsx":
        content = _export.export_sweeps_excel(sweep_data)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=sweep_{experiment_id[:8]}.xlsx"},
        )

    content = _export.export_sweeps_csv(sweep_data)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=sweep_{experiment_id[:8]}.csv"},
    )
