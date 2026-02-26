"""TradingState — state object carried through all LangGraph decision pipeline nodes."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NodeJournalEntry:
    """Record of a single pipeline node's execution."""
    node_name: str
    started_at: str = ""
    completed_at: str = ""
    duration_ms: float = 0.0
    status: str = "pending"
    detail: str = ""


@dataclass
class TradingState:
    """Full state carried through the LangGraph decision pipeline.

    Each node reads from and writes to this state object.
    """

    # Identity
    pipeline_run_id: str = ""
    ticker: str = ""
    price: float = 0.0
    fundamentals: dict = field(default_factory=dict)

    # Quant scores (from QuantModelOrchestrator)
    quant_scores: dict = field(default_factory=dict)
    quant_composite: float = 0.0
    quant_std_dev: float = 0.0
    high_disagreement_flag: bool = False

    # Wasden Watch verdict
    wasden_verdict: str = ""
    wasden_confidence: float = 0.0
    wasden_reasoning: str = ""
    wasden_mode: str = ""
    wasden_vetoed: bool = False

    # Research
    bull_case: str = ""
    bear_case: str = ""

    # Debate
    debate_outcome: str = ""
    debate_rounds: int = 0
    debate_transcript: Optional[dict] = None
    debate_agreed: bool = False

    # Jury
    jury_spawned: bool = False
    jury_votes: list = field(default_factory=list)
    jury_result: Optional[dict] = None
    jury_escalated: bool = False

    # Risk (from risk_engine — SEPARATE from pre_trade)
    risk_check: dict = field(default_factory=dict)
    risk_passed: bool = True

    # Pre-trade validation (SEPARATE from risk_check — zero cross-imports)
    pre_trade_validation: dict = field(default_factory=dict)
    pre_trade_passed: bool = True

    # Decision (from DecisionArbiter)
    final_action: str = ""
    final_reason: str = ""
    recommended_position_size: float = 0.0
    human_approval_required: bool = False

    # Audit trail
    node_journal: list = field(default_factory=list)
    errors: list = field(default_factory=list)
