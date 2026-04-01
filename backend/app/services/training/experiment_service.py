"""Experiment Service — CRUD, comparison, and user attribution.

Manages experiment records with mock storage for development and
Supabase integration when the database is available.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("wasden_watch.training.experiment_service")

VALID_EXPERIMENT_TYPES = {
    "hyperparameter_sweep",
    "weight_tuning",
    "threshold_optimization",
    "stress_test",
    "goal_calibration",
    "baseline",
    "paper_validation",
}

VALID_PHASES = {
    "pre_server",
    "server_setup",
    "weight_tuning",
    "stress_test",
    "goal_calibration",
    "paper_trading",
}

VALID_STATUSES = {"pending", "running", "completed", "failed", "cancelled"}
VALID_DATA_SOURCES = {"mock", "emery", "dow_jones", "custom"}
VALID_USERS = {"joe", "jared"}


class ExperimentService:
    """Manages experiment lifecycle with in-memory mock store.

    In production, methods will delegate to Supabase. For now, the
    in-memory store lets both the backend tests and frontend work
    without a database connection.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._snapshots: dict[str, list[dict[str, Any]]] = {}

    def create_experiment(
        self,
        user_name: str,
        experiment_type: str,
        name: str,
        description: str = "",
        parameters: dict[str, Any] | None = None,
        data_source: str = "mock",
        phase: str = "pre_server",
    ) -> dict[str, Any]:
        """Create a new experiment record."""
        if user_name not in VALID_USERS:
            raise ValueError(f"user_name must be one of {VALID_USERS}")
        if experiment_type not in VALID_EXPERIMENT_TYPES:
            raise ValueError(f"experiment_type must be one of {VALID_EXPERIMENT_TYPES}")
        if data_source not in VALID_DATA_SOURCES:
            raise ValueError(f"data_source must be one of {VALID_DATA_SOURCES}")
        if phase not in VALID_PHASES:
            raise ValueError(f"phase must be one of {VALID_PHASES}")

        now = datetime.now(timezone.utc).isoformat()
        experiment = {
            "id": str(uuid.uuid4()),
            "user_name": user_name,
            "experiment_type": experiment_type,
            "name": name,
            "description": description,
            "parameters": parameters or {},
            "results": {},
            "notes": "",
            "status": "pending",
            "phase": phase,
            "data_source": data_source,
            "mlflow_run_id": None,
            "created_at": now,
            "updated_at": now,
        }

        self._store[experiment["id"]] = experiment
        self._snapshots[experiment["id"]] = []
        logger.info("Created experiment %s: %s by %s", experiment["id"][:8], name, user_name)
        return experiment

    def get_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        """Get a single experiment by ID."""
        exp = self._store.get(experiment_id)
        if exp:
            exp["snapshots"] = self._snapshots.get(experiment_id, [])
        return exp

    def list_experiments(
        self,
        user_name: str | None = None,
        phase: str | None = None,
        status: str | None = None,
        experiment_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List experiments with optional filters."""
        results = list(self._store.values())

        if user_name:
            results = [e for e in results if e["user_name"] == user_name]
        if phase:
            results = [e for e in results if e["phase"] == phase]
        if status:
            results = [e for e in results if e["status"] == status]
        if experiment_type:
            results = [e for e in results if e["experiment_type"] == experiment_type]

        results.sort(key=lambda e: e["created_at"], reverse=True)
        return results[:limit]

    def update_experiment(
        self,
        experiment_id: str,
        results: dict[str, Any] | None = None,
        notes: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any] | None:
        """Update an experiment's results, notes, or status."""
        exp = self._store.get(experiment_id)
        if not exp:
            return None

        if results is not None:
            exp["results"] = results
        if notes is not None:
            exp["notes"] = notes
        if status is not None:
            if status not in VALID_STATUSES:
                raise ValueError(f"status must be one of {VALID_STATUSES}")
            exp["status"] = status

        exp["updated_at"] = datetime.now(timezone.utc).isoformat()
        return exp

    def create_snapshot(
        self,
        experiment_id: str,
        model_name: str,
        metrics: dict[str, Any],
        parameters: dict[str, Any] | None = None,
        artifact_path: str | None = None,
        is_baseline: bool = False,
        data_source: str | None = None,
        data_range: str | None = None,
    ) -> dict[str, Any]:
        """Save a model snapshot for an experiment."""
        if experiment_id not in self._store:
            raise ValueError(f"Experiment {experiment_id} not found")

        snapshot = {
            "id": str(uuid.uuid4()),
            "experiment_id": experiment_id,
            "model_name": model_name,
            "metrics": metrics,
            "parameters": parameters or {},
            "artifact_path": artifact_path,
            "is_baseline": is_baseline,
            "data_source": data_source,
            "data_range": data_range,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self._snapshots.setdefault(experiment_id, []).append(snapshot)
        return snapshot

    def compare_experiments(
        self, experiment_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Side-by-side comparison of multiple experiments."""
        results = []
        for eid in experiment_ids:
            exp = self.get_experiment(eid)
            if exp:
                results.append({
                    "id": exp["id"],
                    "name": exp["name"],
                    "user_name": exp["user_name"],
                    "experiment_type": exp["experiment_type"],
                    "parameters": exp["parameters"],
                    "results": exp["results"],
                    "status": exp["status"],
                    "created_at": exp["created_at"],
                })
        return results

    def compare_users(
        self, experiment_type: str
    ) -> dict[str, list[dict[str, Any]]]:
        """Compare Joe's vs Jared's results for the same experiment type."""
        all_exps = self.list_experiments(experiment_type=experiment_type, limit=100)
        return {
            "joe": [e for e in all_exps if e["user_name"] == "joe"],
            "jared": [e for e in all_exps if e["user_name"] == "jared"],
        }

    def get_baselines(self) -> list[dict[str, Any]]:
        """Get all baseline model snapshots across experiments."""
        baselines = []
        for snapshots in self._snapshots.values():
            baselines.extend(s for s in snapshots if s.get("is_baseline"))
        baselines.sort(key=lambda s: s["created_at"], reverse=True)
        return baselines
