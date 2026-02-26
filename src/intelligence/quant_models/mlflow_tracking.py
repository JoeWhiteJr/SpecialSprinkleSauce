"""MLflow integration for model versioning and experiment tracking.

Bridges the existing manifests.py system with MLflow's experiment tracking,
model registry, and run comparison capabilities.  Operates in "offline" mode
by default (local ``mlruns/`` directory) so no MLflow server is required.

If the ``mlflow`` package is not installed the module degrades gracefully:
all public methods become safe no-ops and a warning is logged once.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("wasden_watch.quant_models.mlflow_tracking")

# ---------------------------------------------------------------------------
# Lazy MLflow import — graceful degradation when not installed
# ---------------------------------------------------------------------------
try:
    import mlflow
    from mlflow.tracking import MlflowClient

    _MLFLOW_AVAILABLE = True
except ImportError:  # pragma: no cover
    mlflow = None  # type: ignore[assignment]
    MlflowClient = None  # type: ignore[assignment,misc]
    _MLFLOW_AVAILABLE = False
    logger.warning(
        "mlflow is not installed. ModelTracker will operate in no-op mode. "
        "Install with: pip install 'mlflow>=2.10.0'"
    )


def _is_available() -> bool:
    """Return True when mlflow is importable."""
    return _MLFLOW_AVAILABLE


class ModelTracker:
    """Thin wrapper around MLflow for Wasden Watch quant-model lifecycle.

    Args:
        tracking_uri: MLflow tracking URI.  Defaults to local file store.
        experiment_name: MLflow experiment name.  Created if missing.
    """

    def __init__(
        self,
        tracking_uri: str = "mlruns",
        experiment_name: str = "wasden-watch-quant",
    ) -> None:
        self._tracking_uri = tracking_uri
        self._experiment_name = experiment_name
        self._available = _is_available()

        if not self._available:
            logger.warning("ModelTracker initialised in no-op mode (mlflow not installed).")
            return

        mlflow.set_tracking_uri(self._tracking_uri)
        mlflow.set_experiment(self._experiment_name)
        self._client = MlflowClient(tracking_uri=self._tracking_uri)
        logger.info("ModelTracker ready — uri=%s experiment=%s", self._tracking_uri, self._experiment_name)

    # ------------------------------------------------------------------
    # Training runs
    # ------------------------------------------------------------------
    def log_training_run(
        self,
        model_name: str,
        params: dict[str, Any],
        metrics: dict[str, float],
        artifacts_dir: str | None = None,
        model_version: str = "0.1.0-mock",
        tier: str = "tier1",
        survivorship_bias_audited: bool = False,
    ) -> str | None:
        """Log a full training run to MLflow.

        Args:
            model_name: Logical model name (e.g. "XGBoostDirectionModel").
            params: Hyperparameters to log.
            metrics: Metric name -> value (accuracy, Sharpe, RMSE, etc.).
            artifacts_dir: Optional dir of model artifacts to upload.
            model_version: Semantic version string stored as tag.
            tier: Model tier tag ("tier1" or "tier2").
            survivorship_bias_audited: Training data audit status.

        Returns:
            MLflow run_id, or None in no-op mode.
        """
        if not self._available:
            logger.debug("log_training_run no-op: mlflow not available")
            return None

        with mlflow.start_run(run_name=f"train-{model_name}") as run:
            mlflow.set_tag("model_name", model_name)
            mlflow.set_tag("model_version", model_version)
            mlflow.set_tag("tier", tier)
            mlflow.set_tag("survivorship_bias_audited", str(survivorship_bias_audited))
            mlflow.set_tag("run_type", "training")

            for key, value in params.items():
                mlflow.log_param(key, value)
            for key, value in metrics.items():
                mlflow.log_metric(key, float(value))
            if artifacts_dir is not None:
                mlflow.log_artifacts(artifacts_dir)

            logger.info("Logged training run for %s — run_id=%s, metrics=%s", model_name, run.info.run_id, metrics)
            return run.info.run_id

    # ------------------------------------------------------------------
    # Validation runs
    # ------------------------------------------------------------------
    def log_validation_run(
        self,
        model_name: str,
        validation_type: str,
        metrics: dict[str, float],
        params: dict[str, Any] | None = None,
    ) -> str | None:
        """Log a walk-forward or cross-validation result.

        Args:
            model_name: Logical model name.
            validation_type: E.g. "walk_forward", "cross_validation", "holdout".
            metrics: Metric name -> value mapping.
            params: Optional extra parameters (fold count, window size, etc.).

        Returns:
            MLflow run_id, or None in no-op mode.
        """
        if not self._available:
            logger.debug("log_validation_run no-op: mlflow not available")
            return None

        with mlflow.start_run(run_name=f"validate-{model_name}-{validation_type}") as run:
            mlflow.set_tag("model_name", model_name)
            mlflow.set_tag("run_type", "validation")
            mlflow.set_tag("validation_type", validation_type)

            if params:
                for key, value in params.items():
                    mlflow.log_param(key, value)
            for key, value in metrics.items():
                mlflow.log_metric(key, float(value))

            logger.info("Logged validation run (%s) for %s — run_id=%s", validation_type, model_name, run.info.run_id)
            return run.info.run_id

    # ------------------------------------------------------------------
    # Ensemble scoring
    # ------------------------------------------------------------------
    def log_ensemble_run(
        self,
        ticker: str,
        model_scores: dict[str, float],
        composite: float,
        std_dev: float,
        high_disagreement: bool,
    ) -> str | None:
        """Log a single ensemble scoring event for a ticker.

        Args:
            ticker: Stock ticker symbol.
            model_scores: Individual model name -> score mapping.
            composite: Weighted average composite score.
            std_dev: Standard deviation across model scores.
            high_disagreement: Whether std_dev exceeds the disagreement threshold.

        Returns:
            MLflow run_id, or None in no-op mode.
        """
        if not self._available:
            logger.debug("log_ensemble_run no-op: mlflow not available")
            return None

        with mlflow.start_run(run_name=f"ensemble-{ticker}") as run:
            mlflow.set_tag("run_type", "ensemble")
            mlflow.set_tag("ticker", ticker)
            mlflow.set_tag("high_disagreement", str(high_disagreement))

            for model_name, score in model_scores.items():
                mlflow.log_metric(f"score_{model_name}", float(score))
            mlflow.log_metric("composite", float(composite))
            mlflow.log_metric("std_dev", float(std_dev))

            logger.info(
                "Logged ensemble run for %s — composite=%.4f std_dev=%.4f disagreement=%s",
                ticker, composite, std_dev, high_disagreement,
            )
            return run.info.run_id

    # ------------------------------------------------------------------
    # Model registry
    # ------------------------------------------------------------------
    def register_model(
        self,
        model_name: str,
        run_id: str,
        stage: str = "Staging",
    ) -> str | None:
        """Register a model version in the MLflow Model Registry.

        Stage transitions: None -> Staging -> Production.

        Args:
            model_name: Registry name for the model.
            run_id: MLflow run_id that produced the model artifact.
            stage: Target stage ("Staging" or "Production").

        Returns:
            Registered model version string, or None in no-op mode.
        """
        if not self._available:
            logger.debug("register_model no-op: mlflow not available")
            return None

        if stage not in ("Staging", "Production"):
            logger.error("Invalid stage '%s' — must be 'Staging' or 'Production'", stage)
            return None

        artifact_uri = f"runs:/{run_id}/model"
        result = mlflow.register_model(model_uri=artifact_uri, name=model_name)
        version = result.version

        self._client.transition_model_version_stage(name=model_name, version=version, stage=stage)
        logger.info("Registered %s version %s in stage '%s' (run_id=%s)", model_name, version, stage, run_id)
        return str(version)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def get_best_run(
        self,
        model_name: str,
        metric: str = "accuracy",
        ascending: bool = False,
    ) -> dict | None:
        """Return the best run for a model ordered by a given metric.

        Args:
            model_name: Logical model name to filter on (tag model_name).
            metric: Metric key to order by.
            ascending: If True, return the run with the lowest metric value.

        Returns:
            Dict with run_id, params, metrics, tags — or None.
        """
        if not self._available:
            logger.debug("get_best_run no-op: mlflow not available")
            return None

        experiment = self._client.get_experiment_by_name(self._experiment_name)
        if experiment is None:
            logger.warning("Experiment '%s' not found", self._experiment_name)
            return None

        order = "ASC" if ascending else "DESC"
        runs = self._client.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string=f"tags.model_name = '{model_name}'",
            order_by=[f"metrics.{metric} {order}"],
            max_results=1,
        )
        if not runs:
            logger.info("No runs found for model_name='%s'", model_name)
            return None

        best = runs[0]
        return {
            "run_id": best.info.run_id,
            "params": dict(best.data.params),
            "metrics": dict(best.data.metrics),
            "tags": dict(best.data.tags),
        }

    def compare_runs(self, run_ids: list[str]) -> dict[str, dict] | None:
        """Compare multiple MLflow runs side by side.

        Args:
            run_ids: List of run IDs to compare.

        Returns:
            Mapping of run_id -> {params, metrics, tags}, or None in no-op mode.
        """
        if not self._available:
            logger.debug("compare_runs no-op: mlflow not available")
            return None

        comparison: dict[str, dict] = {}
        for run_id in run_ids:
            try:
                run = self._client.get_run(run_id)
                comparison[run_id] = {
                    "params": dict(run.data.params),
                    "metrics": dict(run.data.metrics),
                    "tags": dict(run.data.tags),
                }
            except Exception:
                logger.warning("Could not fetch run %s — skipping", run_id)

        return comparison

    # ------------------------------------------------------------------
    # Manifest bridge
    # ------------------------------------------------------------------
    def sync_from_manifests(self, manifests: list[dict]) -> list[str]:
        """Import existing manifests as MLflow runs.

        Takes the output of generate_initial_manifests() and logs each
        manifest as an MLflow run so the two tracking systems stay in sync.

        Args:
            manifests: List of manifest dicts from generate_initial_manifests().

        Returns:
            List of created MLflow run_id values.  Empty list in no-op mode.
        """
        if not self._available:
            logger.debug("sync_from_manifests no-op: mlflow not available")
            return []

        run_ids: list[str] = []
        for manifest in manifests:
            model_name = manifest.get("model_name", "unknown")
            version = manifest.get("version", "0.0.0")
            params = manifest.get("parameters", {})
            validation = manifest.get("validation_results", {})
            audited = manifest.get("survivorship_bias_audited", False)
            notes = manifest.get("notes", "")
            tier = "tier2" if "Tier 2" in notes else "tier1"

            with mlflow.start_run(run_name=f"manifest-sync-{model_name}") as run:
                mlflow.set_tag("model_name", model_name)
                mlflow.set_tag("model_version", version)
                mlflow.set_tag("tier", tier)
                mlflow.set_tag("survivorship_bias_audited", str(audited))
                mlflow.set_tag("run_type", "manifest_sync")
                mlflow.set_tag("synced_at", datetime.now(timezone.utc).isoformat())

                if notes:
                    mlflow.set_tag("notes", notes)
                for field in ("trained_date", "training_data_range", "holdout_period"):
                    val = manifest.get(field)
                    if val:
                        mlflow.set_tag(field, str(val))

                for key, value in params.items():
                    mlflow.log_param(key, value)
                for key, value in validation.items():
                    if isinstance(value, (int, float)):
                        mlflow.log_metric(key, float(value))

                run_ids.append(run.info.run_id)
                logger.info("Synced manifest for %s (version=%s) — run_id=%s", model_name, version, run.info.run_id)

        logger.info("Manifest sync complete — %d manifests synced to MLflow", len(run_ids))
        return run_ids
