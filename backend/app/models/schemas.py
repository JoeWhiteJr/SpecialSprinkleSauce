"""
Pydantic models for the Wasden Watch trading dashboard.
Based on the Decision Journal schema from PROJECT_STANDARDS_v2.md.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class WasdenVerdictEnum(str, Enum):
    APPROVE = "APPROVE"
    NEUTRAL = "NEUTRAL"
    VETO = "VETO"


class TradeAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    BLOCKED = "BLOCKED"
    ESCALATED = "ESCALATED"


class JuryVoteChoice(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class DebateOutcome(str, Enum):
    AGREEMENT = "agreement"
    DISAGREEMENT = "disagreement"


class RecommendationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


class PositionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class OverrideStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class DataFreshness(str, Enum):
    FRESH = "FRESH"
    RECENT = "RECENT"
    STALE = "STALE"
    EXPIRED = "EXPIRED"


class ReviewAction(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Decision Journal Sub-Models
# ---------------------------------------------------------------------------

class QuantScores(BaseModel):
    xgboost: float = Field(..., description="XGBoost model score")
    elastic_net: float = Field(..., description="Elastic Net model score")
    arima: float = Field(..., description="ARIMA model score")
    sentiment: float = Field(..., description="Sentiment model score")
    composite: float = Field(..., description="Composite score of all models")
    std_dev: float = Field(..., description="Standard deviation across model scores")
    high_disagreement_flag: bool = Field(
        ..., description="True when std_dev > 0.5"
    )


class WasdenVerdict(BaseModel):
    verdict: WasdenVerdictEnum
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    mode: str = Field(
        ..., description="direct_coverage or framework_application"
    )
    passages_retrieved: int


class DebateResult(BaseModel):
    outcome: DebateOutcome
    rounds: int = Field(..., ge=1)


class JuryVote(BaseModel):
    agent_id: int = Field(..., ge=1, le=10)
    vote: JuryVoteChoice
    reasoning: str
    focus_area: Optional[str] = Field(
        None,
        description="Agent specialty: fundamentals, macro, risk, technical, wasden_framework",
    )


class JuryResult(BaseModel):
    spawned: bool
    reason: Optional[str] = None
    votes: list[JuryVote] = Field(default_factory=list)
    final_count: Optional[dict] = Field(
        None, description='{"buy": int, "sell": int, "hold": int}'
    )
    decision: Optional[TradeAction] = None
    escalated_to_human: bool = False


class RiskCheck(BaseModel):
    """Risk rules engine output. SEPARATE from PreTradeValidation."""

    passed: bool
    checks_failed: list[str] = Field(default_factory=list)


class PreTradeValidation(BaseModel):
    """Pre-trade validation output. SEPARATE from RiskCheck. Never merge."""

    passed: bool
    checks_failed: list[str] = Field(default_factory=list)


class FinalDecision(BaseModel):
    action: TradeAction
    reason: str
    recommended_position_size: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of portfolio"
    )
    human_approval_required: bool
    human_approved: Optional[bool] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None


class Execution(BaseModel):
    executed: bool
    order_id: Optional[str] = None
    fill_price: Optional[float] = None
    slippage: Optional[float] = None


# ---------------------------------------------------------------------------
# Decision Journal Entry (Full Audit Trail)
# ---------------------------------------------------------------------------

class DecisionJournalEntry(BaseModel):
    id: str = Field(..., description="Unique journal entry ID")
    timestamp: str = Field(..., description="ISO-8601 timestamp")
    ticker: str = Field(..., description="Bloomberg format: TICKER US Equity")
    pipeline_run_id: str = Field(..., description="UUID of the pipeline run")
    quant_scores: QuantScores
    wasden_verdict: WasdenVerdict
    bull_case: str
    bear_case: str
    debate_result: DebateResult
    jury: JuryResult
    risk_check: RiskCheck
    pre_trade_validation: PreTradeValidation
    final_decision: FinalDecision
    execution: Execution


# ---------------------------------------------------------------------------
# Trade Recommendations
# ---------------------------------------------------------------------------

class TradeRecommendation(BaseModel):
    id: str
    timestamp: str
    ticker: str
    direction: TradeAction
    confidence: float = Field(..., ge=0.0, le=1.0)
    pipeline_run_id: str
    wasden_verdict: WasdenVerdictEnum
    quant_composite: float
    recommended_position_size: float
    status: RecommendationStatus
    review_note: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None


class RecommendationReview(BaseModel):
    action: ReviewAction
    note: str = ""


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

class PortfolioPosition(BaseModel):
    id: str
    ticker: str
    direction: str = Field(..., description="long or short")
    entry_price: float
    current_price: float
    quantity: int
    entry_date: str
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    pnl: float
    pnl_pct: float
    status: PositionStatus
    pipeline_run_id: Optional[str] = None


class DailySnapshot(BaseModel):
    date: str
    portfolio_value: float
    daily_pnl: float
    daily_pnl_pct: float
    cumulative_pnl: float
    cumulative_pnl_pct: float
    spy_value: float
    spy_daily_pnl_pct: float
    spy_cumulative_pnl_pct: float
    positions_count: int
    cash_balance: float


class PortfolioSummary(BaseModel):
    total_value: float
    cash_balance: float
    invested_value: float
    daily_pnl: float
    daily_pnl_pct: float
    total_pnl: float
    total_pnl_pct: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    open_positions: int
    closed_positions: int


# ---------------------------------------------------------------------------
# Debates
# ---------------------------------------------------------------------------

class DebateRound(BaseModel):
    round_number: int
    bull_argument: str
    bear_argument: str


class DebateTranscript(BaseModel):
    pipeline_run_id: str
    ticker: str
    timestamp: str
    rounds: list[DebateRound]
    outcome: DebateOutcome
    bull_model: str = "claude-sonnet"
    bear_model: str = "gemini-pro"
    jury_triggered: bool


class DebateSummary(BaseModel):
    pipeline_run_id: str
    ticker: str
    timestamp: str
    outcome: DebateOutcome
    rounds: int
    jury_triggered: bool


# ---------------------------------------------------------------------------
# Jury Stats
# ---------------------------------------------------------------------------

class JuryStats(BaseModel):
    total_jury_sessions: int
    total_votes_cast: int
    buy_votes: int
    sell_votes: int
    hold_votes: int
    agreement_rate: float = Field(
        ..., description="Fraction of sessions with 6+ majority"
    )
    escalation_count: int = Field(
        ..., description="Number of 5-5 ties escalated to human"
    )
    average_majority_size: float


# ---------------------------------------------------------------------------
# Bias Monitoring
# ---------------------------------------------------------------------------

class BiasMetric(BaseModel):
    id: str
    week_start: str
    week_end: str
    wasden_approve_count: int
    wasden_neutral_count: int
    wasden_veto_count: int
    model_agreement_rate: float
    sector_concentration: dict = Field(
        ..., description="Sector -> count mapping"
    )
    paper_pnl_vs_spy: float
    api_cost_actual: float
    api_cost_budget: float
    consecutive_loss_count: int
    veto_override_count: int


# ---------------------------------------------------------------------------
# Risk Alerts
# ---------------------------------------------------------------------------

class RiskAlert(BaseModel):
    id: str
    timestamp: str
    severity: AlertSeverity
    title: str
    message: str
    rule_violated: Optional[str] = None
    ticker: Optional[str] = None
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None


class ConsecutiveLossStreak(BaseModel):
    current_streak: int
    warning_threshold: int
    shutdown_threshold: int
    is_warning: bool
    is_shutdown: bool
    last_loss_date: Optional[str] = None
    streak_tickers: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Screening
# ---------------------------------------------------------------------------

class ScreeningStage(BaseModel):
    stage_name: str
    input_count: int
    output_count: int
    criteria: str


class ScreeningRun(BaseModel):
    id: str
    timestamp: str
    stages: list[ScreeningStage]
    final_candidates: list[str]
    pipeline_run_ids: list[str] = Field(
        default_factory=list,
        description="Pipeline run IDs generated for final candidates",
    )
    duration_seconds: float
    model_used: str = "claude-haiku"


# ---------------------------------------------------------------------------
# System Settings
# ---------------------------------------------------------------------------

class SystemSetting(BaseModel):
    key: str
    value: str
    category: str
    description: str
    editable: bool = False
    requires_approval: bool = True


class SettingUpdate(BaseModel):
    value: str


class ApiStatus(BaseModel):
    name: str
    connected: bool
    latency_ms: Optional[float] = None
    last_checked: str


class SystemSettingsResponse(BaseModel):
    settings: list[SystemSetting]
    api_statuses: list[ApiStatus]
    trading_mode: str


# ---------------------------------------------------------------------------
# Veto Override
# ---------------------------------------------------------------------------

class VetoOverride(BaseModel):
    id: str
    timestamp: str
    ticker: str
    original_verdict: str = "VETO"
    override_reason: str
    overridden_by: str
    pipeline_run_id: str
    outcome_tracked: bool = False
    status: OverrideStatus = OverrideStatus.PENDING


class VetoOverrideCreate(BaseModel):
    ticker: str
    override_reason: str
    overridden_by: str


# ---------------------------------------------------------------------------
# Bloomberg Fundamental
# ---------------------------------------------------------------------------

class BloombergFundamental(BaseModel):
    ticker: str
    pull_date: str
    bloomberg_field_code: str
    value: Optional[float] = None
    is_error: bool = False
    error_type: Optional[str] = None
    freshness: DataFreshness


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    trading_mode: str
    use_mock_data: bool
    db_connected: bool
    timestamp: str
