"""
Backtesting router — run historical simulations and retrieve results.

Mock-first: in mock mode, the engine runs with synthetic data (fast, ~100ms).
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.backtesting.backtest_engine import BacktestEngine

router = APIRouter(prefix="/api/backtesting", tags=["backtesting"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class BacktestRunRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    strategy: str = "sma_crossover"


# ---------------------------------------------------------------------------
# In-memory store for mock runs
# ---------------------------------------------------------------------------

_mock_run_store: dict[str, dict] = {}


def _run_mock_backtest(ticker: str, strategy: str) -> dict:
    """Execute a backtest with mock data and return the full result dict."""
    engine = BacktestEngine(initial_capital=100_000.0, slippage_model=True)
    ohlcv = engine.generate_mock_ohlcv(ticker, num_days=252)
    signals = engine.generate_mock_signals(ticker, ohlcv)
    result = engine.run(ohlcv, signals)

    run_id = str(uuid.uuid4())
    run_data = {
        "run_id": run_id,
        "ticker": ticker,
        "strategy": strategy,
        "status": "completed",
        "created_at": datetime.utcnow().isoformat(),
        "initial_capital": result.initial_capital,
        "final_equity": result.final_equity,
        "total_trades": result.total_trades,
        "metrics": result.metrics,
        "equity_curve": result.equity_curve,
        "trades": result.trades,
    }
    _mock_run_store[run_id] = run_data
    return run_data


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/run")
async def run_backtest(request: BacktestRunRequest):
    """Run a new backtest simulation.

    In mock mode, runs the engine with synthetic OHLCV data and SMA crossover
    signals. Execution is fast (~100ms) since data is generated in-memory.
    """
    if settings.use_mock_data:
        return _run_mock_backtest(request.ticker, request.strategy)

    # Production: would load real OHLCV from Supabase price_history table
    # and apply the selected strategy. For now, fall back to mock.
    return _run_mock_backtest(request.ticker, request.strategy)


@router.get("/runs")
async def list_backtest_runs():
    """List recent backtest runs.

    In mock mode, returns 3 pre-computed runs for pilot tickers.
    """
    if settings.use_mock_data:
        # Return stored runs, or generate 3 default ones
        if not _mock_run_store:
            for ticker in ["NVDA", "AAPL", "NFLX"]:
                _run_mock_backtest(ticker, "sma_crossover")

        runs = sorted(
            _mock_run_store.values(),
            key=lambda r: r["created_at"],
            reverse=True,
        )
        # Return summary (without full equity_curve and trades for list view)
        return [
            {
                "run_id": r["run_id"],
                "ticker": r["ticker"],
                "strategy": r["strategy"],
                "status": r["status"],
                "created_at": r["created_at"],
                "initial_capital": r["initial_capital"],
                "final_equity": r["final_equity"],
                "total_trades": r["total_trades"],
                "metrics": r["metrics"],
            }
            for r in runs
        ]

    # Production: query Supabase
    return []


@router.get("/runs/{run_id}")
async def get_backtest_run(run_id: str):
    """Get full backtest result including equity curve and trade list."""
    if settings.use_mock_data:
        if run_id not in _mock_run_store:
            raise HTTPException(status_code=404, detail="Backtest run not found")
        return _mock_run_store[run_id]

    # Production: query Supabase
    raise HTTPException(status_code=404, detail="Backtest run not found")


@router.get("/strategies")
async def list_strategies():
    """List available backtesting strategies."""
    if settings.use_mock_data:
        return [
            {
                "id": "sma_crossover",
                "name": "SMA Crossover",
                "description": (
                    "Buy when 20-day SMA crosses above 50-day SMA, "
                    "sell when it crosses below. Classic trend-following strategy."
                ),
            },
            {
                "id": "quant_composite",
                "name": "Quant Composite",
                "description": (
                    "Combined signal from Piotroski F-Score, PEG ratio, "
                    "and FCF yield. Fundamental-driven with quantitative thresholds."
                ),
            },
            {
                "id": "mean_reversion",
                "name": "Mean Reversion",
                "description": (
                    "Buy when price drops 2+ standard deviations below 20-day mean, "
                    "sell when it reverts to the mean. Contrarian approach."
                ),
            },
        ]

    # Production: could be stored in DB or config
    return [
        {
            "id": "sma_crossover",
            "name": "SMA Crossover",
            "description": (
                "Buy when 20-day SMA crosses above 50-day SMA, "
                "sell when it crosses below. Classic trend-following strategy."
            ),
        },
        {
            "id": "quant_composite",
            "name": "Quant Composite",
            "description": (
                "Combined signal from Piotroski F-Score, PEG ratio, "
                "and FCF yield. Fundamental-driven with quantitative thresholds."
            ),
        },
        {
            "id": "mean_reversion",
            "name": "Mean Reversion",
            "description": (
                "Buy when price drops 2+ standard deviations below 20-day mean, "
                "sell when it reverts to the mean. Contrarian approach."
            ),
        },
    ]
