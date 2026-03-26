"""GoalConfig and GoalState — data structures for goal-based trading."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class GoalConfig:
    """User-defined goal parameters. Immutable after creation.

    Example:
        GoalConfig.create(capital=1000, target_return_pct=0.02, timeframe_days=5, max_loss_pct=0.01)
        → "Turn $1,000 into $1,020 in 5 trading days, risking at most $10"
    """

    goal_id: str
    capital: float
    target_return_pct: float
    timeframe_days: int
    max_loss_pct: float
    target_dollar: float
    max_loss_dollar: float
    created_at: str

    @staticmethod
    def create(
        capital: float,
        target_return_pct: float,
        timeframe_days: int,
        max_loss_pct: float,
    ) -> GoalConfig:
        """Create a validated GoalConfig with computed fields.

        Args:
            capital: Dollar amount available (e.g., 1000.0).
            target_return_pct: Target return as decimal (e.g., 0.02 for 2%).
            timeframe_days: Trading days to achieve goal (1-90).
            max_loss_pct: Maximum acceptable loss as decimal (e.g., 0.01 for 1%).

        Raises:
            ValueError: If any parameter is out of range.
        """
        if capital <= 0:
            raise ValueError(f"capital must be positive, got {capital}")
        if target_return_pct <= 0:
            raise ValueError(f"target_return_pct must be positive, got {target_return_pct}")
        if not 1 <= timeframe_days <= 90:
            raise ValueError(f"timeframe_days must be 1-90, got {timeframe_days}")
        if max_loss_pct <= 0:
            raise ValueError(f"max_loss_pct must be positive, got {max_loss_pct}")

        return GoalConfig(
            goal_id=str(uuid.uuid4()),
            capital=capital,
            target_return_pct=target_return_pct,
            timeframe_days=timeframe_days,
            max_loss_pct=max_loss_pct,
            target_dollar=round(capital * target_return_pct, 2),
            max_loss_dollar=round(capital * max_loss_pct, 2),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    @property
    def daily_target_pct(self) -> float:
        """Linear daily target to stay on pace."""
        return self.target_return_pct / self.timeframe_days


# ---------------------------------------------------------------------------
# GoalState — mutable accumulator carried through the goal orchestrator
# ---------------------------------------------------------------------------

GOAL_STATUS_PLANNING = "planning"
GOAL_STATUS_ACTIVE = "active"
GOAL_STATUS_ACHIEVED = "achieved"
GOAL_STATUS_FAILED = "failed"
GOAL_STATUS_STOPPED = "stopped"

VALID_GOAL_STATUSES = {
    GOAL_STATUS_PLANNING,
    GOAL_STATUS_ACTIVE,
    GOAL_STATUS_ACHIEVED,
    GOAL_STATUS_FAILED,
    GOAL_STATUS_STOPPED,
}


@dataclass
class GoalTrade:
    """A single trade within a goal's trade plan."""

    ticker: str
    action: str  # "BUY" or "SELL"
    shares: int
    entry_price_est: float
    position_dollar: float
    stop_loss_price: float
    target_exit_price: float
    contribution_target_pct: float
    day_target: int  # which day of the timeframe to enter (1-indexed)
    status: str = "planned"  # planned, executed, closed, cancelled
    actual_pnl: float = 0.0
    actual_pnl_pct: float = 0.0


@dataclass
class GoalState:
    """Full state for a goal orchestrator run.

    Analogous to TradingState for the per-ticker pipeline, but operates
    at the portfolio level across multiple tickers and trades.
    """

    # Goal definition
    goal_id: str = ""
    config: GoalConfig | None = None

    # Screening output
    screening_run_id: str = ""
    candidates: list[str] = field(default_factory=list)

    # Per-ticker pipeline results (keyed by ticker)
    # Each value is a dict compatible with DecisionJournalEntry
    ticker_results: dict[str, dict] = field(default_factory=dict)

    # Stage 2: Portfolio debate
    portfolio_bull_case: str = ""
    portfolio_bear_case: str = ""
    portfolio_debate_outcome: str = ""  # "agreement" or "disagreement"
    portfolio_allocations: list[dict] = field(default_factory=list)
    # Each: {ticker, allocation_pct, allocation_dollar, rationale}

    # Goal arbiter output
    trade_plan: list[GoalTrade] = field(default_factory=list)

    # Progress tracking
    executed_trades: list[GoalTrade] = field(default_factory=list)
    cumulative_pnl: float = 0.0
    cumulative_pnl_pct: float = 0.0
    remaining_capital: float = 0.0
    remaining_target_pct: float = 0.0
    days_elapsed: int = 0
    status: str = GOAL_STATUS_PLANNING

    # Audit
    node_journal: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)

    def viable_tickers(self) -> list[str]:
        """Return tickers that passed per-ticker pipeline (not BLOCKED/ESCALATED)."""
        viable = []
        for ticker, result in self.ticker_results.items():
            action = result.get("final_action", "")
            if action not in ("BLOCKED", "ESCALATED"):
                viable.append(ticker)
        return viable
