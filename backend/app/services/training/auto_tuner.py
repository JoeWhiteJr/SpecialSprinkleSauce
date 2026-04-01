"""Auto-Tuning Engine with bounded parameter ranges and dual-approval gates.

The AutoTuner defines safe bounds for every tunable parameter and enforces
that risk constants require dual approval from both Joe and Jared.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("wasden_watch.training.auto_tuner")


@dataclass(frozen=True)
class ParameterBound:
    """Defines the allowed range for a tunable parameter."""

    min_value: float
    max_value: float
    step_size: float
    category: str
    description: str


# Every tunable parameter with its safe bounds
PARAMETER_BOUNDS: dict[str, ParameterBound] = {
    # --- Ensemble Weights ---
    "ensemble.xgboost_weight": ParameterBound(0.0, 1.0, 0.05, "ensemble_weight", "XGBoost weight in ensemble composite"),
    "ensemble.elastic_net_weight": ParameterBound(0.0, 1.0, 0.05, "ensemble_weight", "Elastic Net weight in ensemble composite"),
    "ensemble.arima_weight": ParameterBound(0.0, 1.0, 0.05, "ensemble_weight", "ARIMA weight in ensemble composite"),
    "ensemble.sentiment_weight": ParameterBound(0.0, 1.0, 0.05, "ensemble_weight", "Sentiment weight in ensemble composite"),
    # --- Screening Thresholds ---
    "screening.max_peg": ParameterBound(1.0, 5.0, 0.5, "screening_threshold", "Maximum PEG ratio for Tier 2"),
    "screening.min_fcf_yield": ParameterBound(1.0, 10.0, 0.5, "screening_threshold", "Minimum FCF yield % for Tier 2"),
    "screening.piotroski_threshold": ParameterBound(3, 8, 1, "screening_threshold", "Minimum Piotroski F-Score for Tier 2"),
    "screening.composite_threshold": ParameterBound(0.40, 0.75, 0.05, "screening_threshold", "Minimum composite score for Tier 3"),
    # --- Model Hyperparameters ---
    "xgboost.n_estimators": ParameterBound(50, 500, 50, "model_hyperparam", "Number of boosting rounds"),
    "xgboost.max_depth": ParameterBound(2, 10, 1, "model_hyperparam", "Maximum tree depth"),
    "xgboost.learning_rate": ParameterBound(0.01, 0.3, 0.01, "model_hyperparam", "Learning rate / shrinkage"),
    "elastic_net.alpha": ParameterBound(0.001, 1.0, 0.01, "model_hyperparam", "Regularization strength"),
    "elastic_net.l1_ratio": ParameterBound(0.0, 1.0, 0.1, "model_hyperparam", "L1 vs L2 balance"),
    "arima.p": ParameterBound(0, 5, 1, "model_hyperparam", "Autoregressive order"),
    "arima.d": ParameterBound(0, 2, 1, "model_hyperparam", "Differencing order"),
    "arima.q": ParameterBound(0, 5, 1, "model_hyperparam", "Moving average order"),
    # --- Sentiment Source Weights ---
    "sentiment.finnhub_weight": ParameterBound(0.0, 1.0, 0.1, "sentiment_weight", "Finnhub sentiment source weight"),
    "sentiment.newsapi_weight": ParameterBound(0.0, 1.0, 0.1, "sentiment_weight", "NewsAPI sentiment source weight"),
    # --- Risk Constants (PROTECTED — require dual approval) ---
    "risk.max_position_pct": ParameterBound(0.05, 0.20, 0.01, "risk_constant", "Maximum position size as % of portfolio"),
    "risk.risk_per_trade_pct": ParameterBound(0.005, 0.03, 0.005, "risk_constant", "Maximum risk per trade as % of portfolio"),
    "risk.min_cash_reserve_pct": ParameterBound(0.05, 0.25, 0.01, "risk_constant", "Minimum cash reserve %"),
    "risk.correlation_threshold": ParameterBound(0.50, 0.90, 0.05, "risk_constant", "Maximum correlation between positions"),
    "risk.high_model_disagreement_threshold": ParameterBound(0.30, 0.70, 0.05, "risk_constant", "Std dev threshold for high disagreement"),
    # --- Goal Parameters ---
    "goal.target_return_pct": ParameterBound(0.005, 0.10, 0.005, "goal_param", "Goal target return %"),
    "goal.max_loss_pct": ParameterBound(0.005, 0.10, 0.005, "goal_param", "Goal maximum loss %"),
    "goal.deviation_trigger_pct": ParameterBound(0.10, 0.50, 0.05, "goal_param", "Progress tracker deviation trigger"),
    "goal.pace_tolerance": ParameterBound(0.10, 0.40, 0.05, "goal_param", "Progress tracker pace tolerance"),
}


def get_sweep_values(parameter_name: str) -> list[float]:
    """Generate the list of values to test for a parameter sweep."""
    bound = PARAMETER_BOUNDS.get(parameter_name)
    if not bound:
        raise ValueError(f"Unknown parameter: {parameter_name}")

    values: list[float] = []
    current = bound.min_value
    while current <= bound.max_value + (bound.step_size / 2):
        values.append(round(current, 6))
        current += bound.step_size
    return values


def validate_bound(parameter_name: str, value: float) -> None:
    """Raise ValueError if value is outside the defined bounds."""
    bound = PARAMETER_BOUNDS.get(parameter_name)
    if not bound:
        raise ValueError(f"Unknown parameter: {parameter_name}")
    if value < bound.min_value or value > bound.max_value:
        raise ValueError(
            f"{parameter_name} = {value} is outside bounds "
            f"[{bound.min_value}, {bound.max_value}]"
        )


def requires_dual_approval(parameter_name: str) -> bool:
    """Check if a parameter change requires approval from both Joe and Jared."""
    bound = PARAMETER_BOUNDS.get(parameter_name)
    return bound is not None and bound.category == "risk_constant"


def get_parameters_by_category(category: str) -> dict[str, ParameterBound]:
    """Return all parameters in a given category."""
    return {
        name: bound
        for name, bound in PARAMETER_BOUNDS.items()
        if bound.category == category
    }


class AutoTuner:
    """Orchestrates parameter tuning with bounded ranges and approval gates.

    Usage (mock mode — no DB required):
        tuner = AutoTuner()
        values = tuner.get_sweep_values("xgboost.n_estimators")
        # ... run sweep externally ...
        proposal = tuner.create_proposal(
            parameter_name="xgboost.n_estimators",
            current_value=200,
            proposed_value=300,
            metric_before={"win_rate": 0.58},
            metric_after={"win_rate": 0.64},
            reason="Grid search found 300 trees optimal",
        )
    """

    def get_sweep_values(self, parameter_name: str) -> list[float]:
        """Get the bounded range of values to test."""
        return get_sweep_values(parameter_name)

    def validate(self, parameter_name: str, value: float) -> None:
        """Validate a value is within bounds."""
        validate_bound(parameter_name, value)

    def create_proposal(
        self,
        parameter_name: str,
        current_value: float,
        proposed_value: float,
        metric_before: dict[str, Any],
        metric_after: dict[str, Any],
        reason: str = "",
        experiment_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a parameter change proposal.

        Returns a proposal dict suitable for DB insertion or mock use.
        """
        validate_bound(parameter_name, proposed_value)
        bound = PARAMETER_BOUNDS[parameter_name]

        return {
            "parameter_name": parameter_name,
            "parameter_category": bound.category,
            "current_value": current_value,
            "proposed_value": proposed_value,
            "metric_before": metric_before,
            "metric_after": metric_after,
            "reason": reason,
            "experiment_id": experiment_id,
            "status": "pending",
            "requires_dual_approval": requires_dual_approval(parameter_name),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def check_approval(self, proposal: dict[str, Any]) -> dict[str, Any]:
        """Check if a proposal has sufficient approvals to be applied.

        Returns dict with `can_apply` bool and `missing` list of user names.
        """
        needs_dual = requires_dual_approval(proposal.get("parameter_name", ""))
        joe_ok = proposal.get("joe_approved_at") is not None
        jared_ok = proposal.get("jared_approved_at") is not None

        if needs_dual:
            missing = []
            if not joe_ok:
                missing.append("joe")
            if not jared_ok:
                missing.append("jared")
            return {"can_apply": len(missing) == 0, "missing": missing}

        # Non-risk params only need one approval
        return {"can_apply": joe_ok or jared_ok, "missing": []}

    def apply_proposal(self, proposal: dict[str, Any], applied_by: str) -> dict[str, Any]:
        """Apply an approved proposal. Returns a history entry.

        Raises ValueError if approvals are insufficient.
        """
        check = self.check_approval(proposal)
        if not check["can_apply"]:
            raise ValueError(
                f"Cannot apply: missing approval from {check['missing']}"
            )

        return {
            "parameter_name": proposal["parameter_name"],
            "old_value": proposal["current_value"],
            "new_value": proposal["proposed_value"],
            "applied_by": applied_by,
            "metric_before": proposal["metric_before"],
            "metric_after": proposal["metric_after"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
