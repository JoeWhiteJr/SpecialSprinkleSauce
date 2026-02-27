"""
Rebalancing router — portfolio drift analysis and rebalance trade generation.

Endpoints:
- GET  /drift    — current portfolio drift analysis
- GET  /targets  — current target allocation weights
- PUT  /targets  — update target weights
- POST /preview  — preview rebalance trades (dry run)
- POST /execute  — execute rebalance trades
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.requests import Request

from app.audit import log_action
from app.config import settings
from app.rate_limit import limiter
from app.mock.generators import PILOT_TICKERS
from app.services.rebalancing.rebalance_engine import RebalanceEngine
from app.services.risk.constants import MAX_POSITION_PCT

router = APIRouter(prefix="/api/rebalancing", tags=["rebalancing"])

# Module-level engine instance for mock/in-memory state
_engine = RebalanceEngine()


# ------------------------------------------------------------------
# Request / response models
# ------------------------------------------------------------------


class TargetWeightsRequest(BaseModel):
    weights: dict[str, float]


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.get("/drift")
async def get_drift():
    """Current portfolio drift analysis against target weights.

    Calculates the difference between current position weights and
    target allocation weights for every held ticker.
    """
    if settings.use_mock_data:
        # Set default equal-weight targets if none configured
        if not _engine.get_target_weights():
            equal_weight = min(1.0 / len(PILOT_TICKERS), MAX_POSITION_PCT)
            _engine.set_target_weights({t: equal_weight for t in PILOT_TICKERS})

        positions = _engine.generate_mock_positions()
        portfolio_value = sum(p["market_value"] for p in positions)
        # Add cash component
        portfolio_value = max(portfolio_value, 100_000.0)
        drift = _engine.calculate_drift(positions, portfolio_value)
        drift["rebalance_needed"] = _engine.check_rebalance_needed(
            positions, portfolio_value
        )
        return drift

    # Production: fetch real positions from Supabase / broker
    raise HTTPException(
        status_code=501,
        detail="Live drift calculation not yet implemented",
    )


@router.get("/targets")
async def get_targets():
    """Current target allocation weights.

    Returns the configured target weights for the portfolio. If none
    have been set, returns default equal-weight targets for pilot tickers.
    """
    if settings.use_mock_data:
        weights = _engine.get_target_weights()
        if not weights:
            equal_weight = min(1.0 / len(PILOT_TICKERS), MAX_POSITION_PCT)
            weights = {t: equal_weight for t in PILOT_TICKERS}
        cash_weight = round(1.0 - sum(weights.values()), 6)
        return {
            "weights": weights,
            "cash_weight": cash_weight,
            "ticker_count": len(weights),
        }

    raise HTTPException(
        status_code=501,
        detail="Live target weights not yet implemented",
    )


@router.put("/targets")
async def update_targets(body: TargetWeightsRequest):
    """Update target allocation weights.

    Validates that all weights are non-negative, sum <= 1.0, and no
    single weight exceeds MAX_POSITION_PCT (12%).
    """
    if settings.use_mock_data:
        try:
            _engine.set_target_weights(body.weights)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        weights = _engine.get_target_weights()
        cash_weight = round(1.0 - sum(weights.values()), 6)
        return {
            "weights": weights,
            "cash_weight": cash_weight,
            "ticker_count": len(weights),
            "status": "updated",
        }

    raise HTTPException(
        status_code=501,
        detail="Live target weight updates not yet implemented",
    )


@router.post("/preview")
async def preview_rebalance():
    """Preview rebalance trades (dry run).

    Generates trades needed to bring the portfolio back to target weights
    without actually executing them. Respects risk constraints.
    """
    if settings.use_mock_data:
        # Set default targets if none configured
        if not _engine.get_target_weights():
            equal_weight = min(1.0 / len(PILOT_TICKERS), MAX_POSITION_PCT)
            _engine.set_target_weights({t: equal_weight for t in PILOT_TICKERS})

        positions = _engine.generate_mock_positions()
        portfolio_value = sum(p["market_value"] for p in positions)
        portfolio_value = max(portfolio_value, 100_000.0)
        trades = _engine.generate_rebalance_trades(positions, portfolio_value)
        drift = _engine.calculate_drift(positions, portfolio_value)
        return {
            "trades": trades,
            "trade_count": len(trades),
            "drift_summary": drift,
            "dry_run": True,
        }

    raise HTTPException(
        status_code=501,
        detail="Live rebalance preview not yet implemented",
    )


@router.post("/execute")
@limiter.limit("10/minute")
async def execute_rebalance(request: Request):
    """Execute rebalance trades.

    Generates and executes trades to bring the portfolio back to target
    weights. In mock mode, returns simulated execution results.
    """
    log_action("execute_rebalance", "/api/rebalancing/execute", details=f"trading_mode={settings.trading_mode}")
    if settings.use_mock_data:
        # Set default targets if none configured
        if not _engine.get_target_weights():
            equal_weight = min(1.0 / len(PILOT_TICKERS), MAX_POSITION_PCT)
            _engine.set_target_weights({t: equal_weight for t in PILOT_TICKERS})

        positions = _engine.generate_mock_positions()
        portfolio_value = sum(p["market_value"] for p in positions)
        portfolio_value = max(portfolio_value, 100_000.0)
        trades = _engine.generate_rebalance_trades(positions, portfolio_value)

        # Simulate execution results
        executed = []
        for trade in trades:
            executed.append({
                **trade,
                "status": "filled",
                "fill_price": trade["estimated_value"] / trade["quantity"]
                if trade["quantity"] > 0
                else 0,
                "slippage_pct": 0.001,
            })

        return {
            "trades": executed,
            "trade_count": len(executed),
            "status": "executed" if executed else "no_trades_needed",
            "trading_mode": settings.trading_mode,
            "dry_run": False,
        }

    raise HTTPException(
        status_code=501,
        detail="Live rebalance execution not yet implemented",
    )
