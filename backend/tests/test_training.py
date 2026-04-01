"""Tests for Training Lab — auto-tuner, sweep runner, experiment service, export."""

import pytest

from app.services.training.auto_tuner import (
    AutoTuner,
    PARAMETER_BOUNDS,
    get_sweep_values,
    validate_bound,
    requires_dual_approval,
    get_parameters_by_category,
)
from app.services.training.sweep_runner import SweepRunner
from app.services.training.experiment_service import ExperimentService
from app.services.training.export_service import ExportService


# ===========================================================================
# AutoTuner tests
# ===========================================================================


class TestAutoTunerBounds:
    """Test parameter bounds validation."""

    def test_all_bounds_have_required_fields(self):
        for name, bound in PARAMETER_BOUNDS.items():
            assert bound.min_value < bound.max_value, f"{name}: min >= max"
            assert bound.step_size > 0, f"{name}: step_size <= 0"
            assert bound.category, f"{name}: missing category"
            assert bound.description, f"{name}: missing description"

    def test_get_sweep_values_produces_valid_range(self):
        values = get_sweep_values("xgboost.max_depth")
        assert len(values) > 0
        assert values[0] == 2  # min
        assert values[-1] == 10  # max
        assert all(values[i] <= values[i + 1] for i in range(len(values) - 1))

    def test_get_sweep_values_unknown_param_raises(self):
        with pytest.raises(ValueError, match="Unknown parameter"):
            get_sweep_values("nonexistent.param")

    def test_validate_bound_within_range(self):
        validate_bound("xgboost.max_depth", 6)  # should not raise

    def test_validate_bound_below_min_raises(self):
        with pytest.raises(ValueError, match="outside bounds"):
            validate_bound("xgboost.max_depth", 0)

    def test_validate_bound_above_max_raises(self):
        with pytest.raises(ValueError, match="outside bounds"):
            validate_bound("xgboost.max_depth", 20)

    def test_requires_dual_approval_risk_constant(self):
        assert requires_dual_approval("risk.max_position_pct") is True
        assert requires_dual_approval("risk.risk_per_trade_pct") is True

    def test_requires_dual_approval_non_risk(self):
        assert requires_dual_approval("xgboost.max_depth") is False
        assert requires_dual_approval("ensemble.xgboost_weight") is False

    def test_get_parameters_by_category(self):
        risk_params = get_parameters_by_category("risk_constant")
        assert len(risk_params) >= 2
        assert all(b.category == "risk_constant" for b in risk_params.values())

    def test_get_parameters_by_category_empty(self):
        result = get_parameters_by_category("nonexistent")
        assert result == {}


class TestAutoTunerProposals:
    """Test proposal creation and approval flow."""

    def setup_method(self):
        self.tuner = AutoTuner()

    def test_create_proposal(self):
        proposal = self.tuner.create_proposal(
            parameter_name="xgboost.max_depth",
            current_value=6,
            proposed_value=5,
            metric_before={"win_rate": 0.60},
            metric_after={"win_rate": 0.65},
            reason="Better generalization",
        )
        assert proposal["parameter_name"] == "xgboost.max_depth"
        assert proposal["status"] == "pending"
        assert proposal["requires_dual_approval"] is False

    def test_create_proposal_risk_constant_requires_dual(self):
        proposal = self.tuner.create_proposal(
            parameter_name="risk.max_position_pct",
            current_value=0.12,
            proposed_value=0.10,
            metric_before={"win_rate": 0.60},
            metric_after={"win_rate": 0.62},
        )
        assert proposal["requires_dual_approval"] is True

    def test_create_proposal_out_of_bounds_raises(self):
        with pytest.raises(ValueError, match="outside bounds"):
            self.tuner.create_proposal(
                parameter_name="xgboost.max_depth",
                current_value=6,
                proposed_value=50,
                metric_before={},
                metric_after={},
            )

    def test_check_approval_non_risk_single_ok(self):
        proposal = {"parameter_name": "xgboost.max_depth", "joe_approved_at": "2026-01-01", "jared_approved_at": None}
        result = self.tuner.check_approval(proposal)
        assert result["can_apply"] is True

    def test_check_approval_risk_needs_both(self):
        proposal = {"parameter_name": "risk.max_position_pct", "joe_approved_at": "2026-01-01", "jared_approved_at": None}
        result = self.tuner.check_approval(proposal)
        assert result["can_apply"] is False
        assert "jared" in result["missing"]

    def test_check_approval_risk_both_approved(self):
        proposal = {"parameter_name": "risk.max_position_pct", "joe_approved_at": "2026-01-01", "jared_approved_at": "2026-01-01"}
        result = self.tuner.check_approval(proposal)
        assert result["can_apply"] is True

    def test_apply_proposal_success(self):
        proposal = {
            "parameter_name": "xgboost.max_depth",
            "current_value": 6,
            "proposed_value": 5,
            "metric_before": {"win_rate": 0.60},
            "metric_after": {"win_rate": 0.65},
            "joe_approved_at": "2026-01-01",
            "jared_approved_at": None,
        }
        history = self.tuner.apply_proposal(proposal, "joe")
        assert history["old_value"] == 6
        assert history["new_value"] == 5
        assert history["applied_by"] == "joe"

    def test_apply_proposal_risk_without_dual_raises(self):
        proposal = {
            "parameter_name": "risk.max_position_pct",
            "current_value": 0.12,
            "proposed_value": 0.10,
            "metric_before": {},
            "metric_after": {},
            "joe_approved_at": "2026-01-01",
            "jared_approved_at": None,
        }
        with pytest.raises(ValueError, match="missing approval"):
            self.tuner.apply_proposal(proposal, "joe")


# ===========================================================================
# SweepRunner tests
# ===========================================================================


class TestSweepRunner:
    """Test parameter sweep execution."""

    def setup_method(self):
        self.runner = SweepRunner(use_mock=True)

    def test_run_parameter_sweep_returns_results(self):
        result = self.runner.run_parameter_sweep("xgboost.max_depth")
        assert result.parameter_name == "xgboost.max_depth"
        assert len(result.data_points) > 0
        assert result.best_value is not None
        assert result.best_metric_value is not None

    def test_sweep_data_points_have_all_metrics(self):
        result = self.runner.run_parameter_sweep("xgboost.learning_rate")
        for dp in result.data_points:
            assert 0 <= dp.win_rate <= 1.0
            assert dp.max_drawdown >= 0
            assert dp.total_trades > 0

    def test_sweep_unknown_param_raises(self):
        with pytest.raises(ValueError, match="Unknown parameter"):
            self.runner.run_parameter_sweep("fake.param")

    def test_sweep_to_dict(self):
        result = self.runner.run_parameter_sweep("xgboost.n_estimators")
        d = result.to_dict()
        assert "parameter_name" in d
        assert "values_tested" in d
        assert "results_per_value" in d
        assert "best_value" in d
        assert len(d["values_tested"]) == len(d["results_per_value"])

    def test_ensemble_weight_sweep(self):
        results = self.runner.run_ensemble_weight_sweep(grid_step=0.25)
        assert len(results) > 0
        for r in results:
            assert "weights" in r
            assert abs(sum(r["weights"].values()) - 1.0) < 0.01

    def test_stress_test_known_regime(self):
        result = self.runner.run_stress_test("covid_2020")
        assert result["regime"] == "covid_2020"
        assert "model_results" in result
        assert "xgboost" in result["model_results"]

    def test_stress_test_unknown_regime_raises(self):
        with pytest.raises(ValueError, match="Unknown regime"):
            self.runner.run_stress_test("fake_regime")

    def test_get_stress_regimes(self):
        regimes = self.runner.get_stress_regimes()
        assert "covid_2020" in regimes
        assert "crash_2008" in regimes


# ===========================================================================
# ExperimentService tests
# ===========================================================================


class TestExperimentService:
    """Test experiment CRUD operations."""

    def setup_method(self):
        self.svc = ExperimentService()

    def test_create_experiment(self):
        exp = self.svc.create_experiment(
            user_name="joe",
            experiment_type="hyperparameter_sweep",
            name="Test sweep",
        )
        assert exp["id"]
        assert exp["user_name"] == "joe"
        assert exp["status"] == "pending"

    def test_create_experiment_invalid_user_raises(self):
        with pytest.raises(ValueError, match="user_name"):
            self.svc.create_experiment(user_name="unknown", experiment_type="baseline", name="test")

    def test_create_experiment_invalid_type_raises(self):
        with pytest.raises(ValueError, match="experiment_type"):
            self.svc.create_experiment(user_name="joe", experiment_type="invalid", name="test")

    def test_get_experiment(self):
        exp = self.svc.create_experiment(user_name="joe", experiment_type="baseline", name="test")
        fetched = self.svc.get_experiment(exp["id"])
        assert fetched is not None
        assert fetched["name"] == "test"

    def test_get_experiment_not_found(self):
        assert self.svc.get_experiment("nonexistent") is None

    def test_list_experiments_filter_by_user(self):
        self.svc.create_experiment(user_name="joe", experiment_type="baseline", name="joe1")
        self.svc.create_experiment(user_name="jared", experiment_type="baseline", name="jared1")
        joe_exps = self.svc.list_experiments(user_name="joe")
        assert all(e["user_name"] == "joe" for e in joe_exps)

    def test_update_experiment(self):
        exp = self.svc.create_experiment(user_name="joe", experiment_type="baseline", name="test")
        updated = self.svc.update_experiment(exp["id"], results={"win_rate": 0.65}, status="completed")
        assert updated["results"]["win_rate"] == 0.65
        assert updated["status"] == "completed"

    def test_update_experiment_invalid_status_raises(self):
        exp = self.svc.create_experiment(user_name="joe", experiment_type="baseline", name="test")
        with pytest.raises(ValueError, match="status"):
            self.svc.update_experiment(exp["id"], status="invalid")

    def test_create_snapshot(self):
        exp = self.svc.create_experiment(user_name="joe", experiment_type="baseline", name="test")
        snap = self.svc.create_snapshot(
            experiment_id=exp["id"],
            model_name="xgboost",
            metrics={"win_rate": 0.65},
            is_baseline=True,
        )
        assert snap["model_name"] == "xgboost"
        assert snap["is_baseline"] is True

    def test_create_snapshot_invalid_experiment_raises(self):
        with pytest.raises(ValueError, match="not found"):
            self.svc.create_snapshot(experiment_id="nonexistent", model_name="xgboost", metrics={})

    def test_compare_users(self):
        self.svc.create_experiment(user_name="joe", experiment_type="weight_tuning", name="joe wt")
        self.svc.create_experiment(user_name="jared", experiment_type="weight_tuning", name="jared wt")
        result = self.svc.compare_users("weight_tuning")
        assert len(result["joe"]) >= 1
        assert len(result["jared"]) >= 1

    def test_get_baselines(self):
        exp = self.svc.create_experiment(user_name="joe", experiment_type="baseline", name="base")
        self.svc.create_snapshot(exp["id"], "xgboost", {"win_rate": 0.60}, is_baseline=True)
        self.svc.create_snapshot(exp["id"], "arima", {"win_rate": 0.55}, is_baseline=False)
        baselines = self.svc.get_baselines()
        assert len(baselines) == 1
        assert baselines[0]["model_name"] == "xgboost"


# ===========================================================================
# ExportService tests
# ===========================================================================


class TestExportService:
    """Test CSV and Excel export."""

    def setup_method(self):
        self.export = ExportService()
        self.sample_experiments = [
            {
                "id": "exp-001",
                "user_name": "joe",
                "experiment_type": "baseline",
                "name": "Test",
                "status": "completed",
                "phase": "pre_server",
                "data_source": "mock",
                "parameters": {"depth": 6},
                "results": {"win_rate": 0.65},
                "notes": "Good results",
                "created_at": "2026-03-25T10:00:00Z",
                "updated_at": "2026-03-25T10:05:00Z",
            }
        ]

    def test_export_experiments_csv(self):
        csv_str = self.export.export_experiments_csv(self.sample_experiments)
        assert "exp-001" in csv_str
        assert "joe" in csv_str
        assert "win_rate" in csv_str

    def test_export_experiments_csv_empty(self):
        assert self.export.export_experiments_csv([]) == ""

    def test_export_sweeps_csv(self):
        sweep = {
            "parameter_name": "xgboost.max_depth",
            "results_per_value": [
                {"value": 2, "win_rate": 0.55, "sharpe_ratio": 0.9, "max_drawdown": 0.20, "accuracy": 0.55, "profit_factor": 1.1, "sortino_ratio": 1.0, "total_trades": 100},
                {"value": 6, "win_rate": 0.65, "sharpe_ratio": 1.2, "max_drawdown": 0.15, "accuracy": 0.65, "profit_factor": 1.5, "sortino_ratio": 1.4, "total_trades": 120},
            ],
        }
        csv_str = self.export.export_sweeps_csv(sweep)
        assert "xgboost.max_depth" in csv_str
        assert "0.65" in csv_str

    def test_export_experiments_excel_fallback(self):
        # openpyxl may or may not be installed — test either path
        result = self.export.export_experiments_excel(self.sample_experiments)
        assert isinstance(result, bytes)
        assert len(result) > 0
