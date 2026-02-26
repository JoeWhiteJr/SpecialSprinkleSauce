"""LangGraph decision pipeline — 10-node graph from quant scoring to final decision.

Wires together existing components:
- QuantModelOrchestrator (Week 5)
- VerdictGenerator (Week 4)
- DebateEngine, BullResearcher, BearResearcher (Week 6)
- JurySpawner, JuryAggregator (Week 6)
- Risk engine, Pre-trade validation (Week 8)
- DecisionArbiter (Week 7)
"""

import logging
import uuid
from datetime import datetime, timezone

from src.pipeline.state import TradingState

logger = logging.getLogger("wasden_watch.pipeline")


class DecisionPipeline:
    """Full 10-node decision pipeline orchestrator.

    Nodes:
        1. quant_scoring — QuantModelOrchestrator
        2. wasden_watch — VerdictGenerator
        3. bull_researcher — BullResearcher.generate_initial()
        4. bear_researcher — BearResearcher.generate_initial()
        5. debate — DebateEngine.run_debate()
        6. jury_spawn — JurySpawner.spawn_jury() (if disagreement)
        7. jury_aggregate — JuryAggregator.aggregate() (if jury spawned)
        8. risk_check — run_risk_checks()
        9. pre_trade_validation — run_pre_trade_validation() (SEPARATE)
        10. decision — DecisionArbiter.decide()

    Conditional edges:
        - wasden_watch: if vetoed → skip to decision
        - debate: if agreed → skip jury → risk_check
        - debate: if disagreement → jury_spawn
    """

    def __init__(self, use_mock: bool = True, random_seed: int = 42):
        self._use_mock = use_mock
        self._random_seed = random_seed

    def run(
        self,
        ticker: str,
        price: float,
        fundamentals: dict | None = None,
    ) -> dict:
        """Run the full decision pipeline for a single ticker.

        Args:
            ticker: Stock ticker symbol.
            price: Current price.
            fundamentals: Optional fundamentals dict.

        Returns:
            DecisionJournalEntry-compatible dict.
        """
        state = TradingState(
            pipeline_run_id=str(uuid.uuid4()),
            ticker=ticker.upper(),
            price=price,
            fundamentals=fundamentals or {},
        )

        logger.info(f"[{state.ticker}] Pipeline started — run_id={state.pipeline_run_id}")

        # Node 1: Quant scoring
        state = self._node_quant_scoring(state)

        # Node 2: Wasden Watch
        state = self._node_wasden_watch(state)

        # Short-circuit: Wasden VETO → skip to decision
        if state.wasden_vetoed:
            logger.info(f"[{state.ticker}] Wasden VETO — skipping debate/jury/risk")
            state = self._node_decision(state)
            return self._state_to_journal_entry(state)

        # Node 3-4: Bull and bear research
        state = self._node_bull_researcher(state)
        state = self._node_bear_researcher(state)

        # Node 5: Debate
        state = self._node_debate(state)

        # Conditional: Agreement → skip jury
        if state.debate_agreed:
            logger.info(f"[{state.ticker}] Debate agreement — skipping jury")
        else:
            # Node 6-7: Jury
            state = self._node_jury_spawn(state)
            state = self._node_jury_aggregate(state)

        # Node 8: Risk check
        state = self._node_risk_check(state)

        # Node 9: Pre-trade validation (SEPARATE from risk)
        state = self._node_pre_trade_validation(state)

        # Node 10: Decision
        state = self._node_decision(state)

        logger.info(
            f"[{state.ticker}] Pipeline complete — "
            f"action={state.final_action}, size={state.recommended_position_size}"
        )
        return self._state_to_journal_entry(state)

    def run_batch(self, tickers_data: list[dict]) -> list[dict]:
        """Run pipeline for multiple tickers.

        Args:
            tickers_data: List of dicts with 'ticker', 'price', and optional 'fundamentals'.

        Returns:
            List of DecisionJournalEntry-compatible dicts.
        """
        results = []
        for data in tickers_data:
            result = self.run(
                ticker=data["ticker"],
                price=data["price"],
                fundamentals=data.get("fundamentals"),
            )
            results.append(result)
        return results

    # --- Node implementations ---

    def _node_quant_scoring(self, state: TradingState) -> TradingState:
        """Node 1: Score ticker with quant models."""
        _log_node_start(state, "quant_scoring")

        if self._use_mock:
            from src.intelligence.quant_models import QuantModelOrchestrator
            orchestrator = QuantModelOrchestrator(use_mock=True)
            scores = orchestrator.score_ticker(state.ticker)
        else:
            from src.intelligence.quant_models import QuantModelOrchestrator
            orchestrator = QuantModelOrchestrator(use_mock=False)
            scores = orchestrator.score_ticker(state.ticker, fundamentals=state.fundamentals)

        state.quant_scores = scores
        state.quant_composite = scores["composite"]
        state.quant_std_dev = scores["std_dev"]
        state.high_disagreement_flag = scores["high_disagreement_flag"]

        _log_node_end(state, "quant_scoring", f"composite={scores['composite']}")
        return state

    def _node_wasden_watch(self, state: TradingState) -> TradingState:
        """Node 2: Generate Wasden Watch verdict."""
        _log_node_start(state, "wasden_watch")

        if self._use_mock:
            # Use deterministic mock verdicts based on ticker
            mock_verdicts = _get_mock_verdicts()
            verdict_data = mock_verdicts.get(
                state.ticker,
                {"verdict": "NEUTRAL", "confidence": 0.60, "reasoning": "No direct coverage", "mode": "framework_application"},
            )
        else:
            from src.intelligence.wasden_watch import VerdictGenerator, VerdictRequest
            generator = VerdictGenerator()
            request = VerdictRequest(
                ticker=state.ticker,
                fundamentals=state.fundamentals if state.fundamentals else None,
            )
            response = generator.generate(request)
            verdict_data = {
                "verdict": response.verdict.verdict,
                "confidence": response.verdict.confidence,
                "reasoning": response.verdict.reasoning,
                "mode": response.verdict.mode,
            }

        state.wasden_verdict = verdict_data["verdict"]
        state.wasden_confidence = verdict_data["confidence"]
        state.wasden_reasoning = verdict_data["reasoning"]
        state.wasden_mode = verdict_data.get("mode", "framework_application")
        state.wasden_vetoed = verdict_data["verdict"] == "VETO"

        _log_node_end(
            state, "wasden_watch",
            f"verdict={state.wasden_verdict}, vetoed={state.wasden_vetoed}",
        )
        return state

    def _node_bull_researcher(self, state: TradingState) -> TradingState:
        """Node 3: Generate bull case."""
        _log_node_start(state, "bull_researcher")

        if self._use_mock:
            state.bull_case = (
                f"Bull case for {state.ticker}: Strong quant composite ({state.quant_composite:.3f}), "
                f"favorable Wasden sentiment, and positive market momentum suggest upside potential."
            )
        else:
            from src.pipeline.debate import DebateContext
            from src.pipeline.debate.bull_researcher import BullResearcher
            from src.pipeline.debate.debate_llm_client import DebateLLMClient
            from src.intelligence.wasden_watch.config import WasdenWatchSettings

            settings = WasdenWatchSettings()
            client = DebateLLMClient(settings)
            researcher = BullResearcher(client)
            context = DebateContext(
                ticker=state.ticker,
                price=state.price,
                quant_scores=state.quant_scores,
                wasden_verdict=state.wasden_verdict,
                wasden_confidence=state.wasden_confidence,
                wasden_reasoning=state.wasden_reasoning,
                fundamentals=state.fundamentals,
            )
            state.bull_case = researcher.generate_initial(context)

        _log_node_end(state, "bull_researcher", f"{len(state.bull_case)} chars")
        return state

    def _node_bear_researcher(self, state: TradingState) -> TradingState:
        """Node 4: Generate bear case."""
        _log_node_start(state, "bear_researcher")

        if self._use_mock:
            state.bear_case = (
                f"Bear case for {state.ticker}: Elevated volatility (std_dev={state.quant_std_dev:.3f}), "
                f"potential macro headwinds, and valuation concerns warrant caution."
            )
        else:
            from src.pipeline.debate import DebateContext
            from src.pipeline.debate.bear_researcher import BearResearcher
            from src.pipeline.debate.debate_llm_client import DebateLLMClient
            from src.intelligence.wasden_watch.config import WasdenWatchSettings

            settings = WasdenWatchSettings()
            client = DebateLLMClient(settings)
            researcher = BearResearcher(client)
            context = DebateContext(
                ticker=state.ticker,
                price=state.price,
                quant_scores=state.quant_scores,
                wasden_verdict=state.wasden_verdict,
                wasden_confidence=state.wasden_confidence,
                wasden_reasoning=state.wasden_reasoning,
                fundamentals=state.fundamentals,
            )
            state.bear_case = researcher.generate_initial(context)

        _log_node_end(state, "bear_researcher", f"{len(state.bear_case)} chars")
        return state

    def _node_debate(self, state: TradingState) -> TradingState:
        """Node 5: Run debate and detect agreement."""
        _log_node_start(state, "debate")

        if self._use_mock:
            # Deterministic mock: agreement for high-composite, disagreement otherwise
            mock_debate = _get_mock_debate_outcomes()
            outcome = mock_debate.get(state.ticker, {"outcome": "agreement", "rounds": 3})
            state.debate_outcome = outcome["outcome"]
            state.debate_rounds = outcome["rounds"]
            state.debate_agreed = outcome["outcome"] == "agreement"
            state.debate_transcript = {
                "pipeline_run_id": state.pipeline_run_id,
                "ticker": state.ticker,
                "rounds": state.debate_rounds,
                "outcome": state.debate_outcome,
            }
        else:
            from src.pipeline.debate import DebateEngine, DebateContext

            engine = DebateEngine()
            context = DebateContext(
                ticker=state.ticker,
                price=state.price,
                quant_scores=state.quant_scores,
                wasden_verdict=state.wasden_verdict,
                wasden_confidence=state.wasden_confidence,
                wasden_reasoning=state.wasden_reasoning,
                fundamentals=state.fundamentals,
            )
            transcript = engine.run_debate(context, state.pipeline_run_id)
            state.debate_outcome = transcript.outcome.value
            state.debate_rounds = len(transcript.rounds)
            state.debate_agreed = transcript.outcome.value == "agreement"
            state.debate_transcript = {
                "pipeline_run_id": transcript.pipeline_run_id,
                "ticker": transcript.ticker,
                "rounds": len(transcript.rounds),
                "outcome": transcript.outcome.value,
            }

        _log_node_end(
            state, "debate",
            f"outcome={state.debate_outcome}, agreed={state.debate_agreed}",
        )
        return state

    def _node_jury_spawn(self, state: TradingState) -> TradingState:
        """Node 6: Spawn jury if debate disagreement."""
        _log_node_start(state, "jury_spawn")

        if self._use_mock:
            mock_votes = _get_mock_jury_votes(state.ticker)
            state.jury_spawned = True
            state.jury_votes = mock_votes
        else:
            # Jury spawn requires async — handled by caller
            state.jury_spawned = True
            logger.info(f"[{state.ticker}] Jury spawn would be async in live mode")

        _log_node_end(state, "jury_spawn", f"votes={len(state.jury_votes)}")
        return state

    def _node_jury_aggregate(self, state: TradingState) -> TradingState:
        """Node 7: Aggregate jury votes."""
        _log_node_start(state, "jury_aggregate")

        if self._use_mock:
            mock_results = _get_mock_jury_results(state.ticker)
            state.jury_result = mock_results
            state.jury_escalated = mock_results.get("escalated_to_human", False)
        else:
            from src.pipeline.jury import JuryAggregator
            from backend.app.models.schemas import JuryVote
            votes = [JuryVote(**v) for v in state.jury_votes]
            result = JuryAggregator.aggregate(votes)
            state.jury_result = {
                "spawned": result.spawned,
                "reason": result.reason,
                "final_count": result.final_count,
                "decision": result.decision.value if result.decision else None,
                "escalated_to_human": result.escalated_to_human,
            }
            state.jury_escalated = result.escalated_to_human

        _log_node_end(
            state, "jury_aggregate",
            f"escalated={state.jury_escalated}",
        )
        return state

    def _node_risk_check(self, state: TradingState) -> TradingState:
        """Node 8: Run risk checks."""
        _log_node_start(state, "risk_check")

        if self._use_mock:
            mock_risk = _get_mock_risk_results(state.ticker)
            state.risk_check = mock_risk
            state.risk_passed = mock_risk["passed"]
        else:
            from app.services.risk.risk_engine import RiskContext, run_risk_checks
            ctx = RiskContext(
                ticker=state.ticker,
                proposed_position_pct=state.recommended_position_size or 0.05,
                portfolio_value=100000.0,
                cash_balance=35000.0,
                model_std_dev=state.quant_std_dev,
            )
            result = run_risk_checks(ctx)
            state.risk_check = result
            state.risk_passed = result["passed"]

        _log_node_end(state, "risk_check", f"passed={state.risk_passed}")
        return state

    def _node_pre_trade_validation(self, state: TradingState) -> TradingState:
        """Node 9: Run pre-trade validation (SEPARATE from risk)."""
        _log_node_start(state, "pre_trade_validation")

        if self._use_mock:
            mock_ptv = _get_mock_pre_trade_results(state.ticker)
            state.pre_trade_validation = mock_ptv
            state.pre_trade_passed = mock_ptv["passed"]
        else:
            from app.services.risk.pre_trade_validation import PreTradeContext, run_pre_trade_validation
            ctx = PreTradeContext(
                ticker=state.ticker,
                side="buy",
                quantity=100,
                price=state.price,
                portfolio_value=100000.0,
            )
            result = run_pre_trade_validation(ctx)
            state.pre_trade_validation = result
            state.pre_trade_passed = result["passed"]

        _log_node_end(state, "pre_trade_validation", f"passed={state.pre_trade_passed}")
        return state

    def _node_decision(self, state: TradingState) -> TradingState:
        """Node 10: Final decision via DecisionArbiter."""
        _log_node_start(state, "decision")

        from src.pipeline.arbiter import DecisionArbiter
        state = DecisionArbiter.decide(state)

        _log_node_end(
            state, "decision",
            f"action={state.final_action}, size={state.recommended_position_size}",
        )
        return state

    def _state_to_journal_entry(self, state: TradingState) -> dict:
        """Convert final TradingState to a DecisionJournalEntry-compatible dict."""
        return {
            "id": f"je-{state.pipeline_run_id[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ticker": f"{state.ticker} US Equity",
            "pipeline_run_id": state.pipeline_run_id,
            "quant_scores": {
                "xgboost": state.quant_scores.get("xgboost", 0.0),
                "elastic_net": state.quant_scores.get("elastic_net", 0.0),
                "arima": state.quant_scores.get("arima", 0.0),
                "sentiment": state.quant_scores.get("sentiment", 0.0),
                "composite": state.quant_composite,
                "std_dev": state.quant_std_dev,
                "high_disagreement_flag": state.high_disagreement_flag,
            },
            "wasden_verdict": {
                "verdict": state.wasden_verdict,
                "confidence": state.wasden_confidence,
                "reasoning": state.wasden_reasoning,
                "mode": state.wasden_mode,
                "passages_retrieved": 0,
            },
            "bull_case": state.bull_case,
            "bear_case": state.bear_case,
            "debate_result": {
                "outcome": state.debate_outcome or "agreement",
                "rounds": state.debate_rounds,
            },
            "jury": {
                "spawned": state.jury_spawned,
                "reason": state.jury_result.get("reason") if state.jury_result else None,
                "votes": state.jury_votes,
                "final_count": state.jury_result.get("final_count") if state.jury_result else None,
                "decision": state.jury_result.get("decision") if state.jury_result else state.final_action,
                "escalated_to_human": state.jury_escalated,
            },
            "risk_check": {
                "passed": state.risk_passed,
                "checks_failed": state.risk_check.get("checks_failed", []),
            },
            "pre_trade_validation": {
                "passed": state.pre_trade_passed,
                "checks_failed": state.pre_trade_validation.get("checks_failed", []),
            },
            "final_decision": {
                "action": state.final_action,
                "reason": state.final_reason,
                "recommended_position_size": state.recommended_position_size,
                "human_approval_required": state.human_approval_required,
                "human_approved": None,
                "approved_by": None,
                "approved_at": None,
            },
            "execution": {
                "executed": False,
                "order_id": None,
                "fill_price": None,
                "slippage": None,
            },
            "node_journal": state.node_journal,
            "errors": state.errors,
        }


# --- Helper functions ---

def _log_node_start(state: TradingState, node_name: str) -> None:
    """Log node start and append to journal."""
    logger.info(f"[{state.ticker}] Node: {node_name} — START")
    state.node_journal.append({
        "node": node_name,
        "status": "started",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def _log_node_end(state: TradingState, node_name: str, detail: str = "") -> None:
    """Log node completion and update journal."""
    logger.info(f"[{state.ticker}] Node: {node_name} — DONE ({detail})")
    state.node_journal.append({
        "node": node_name,
        "status": "completed",
        "detail": detail,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def _get_mock_verdicts() -> dict:
    """Deterministic mock Wasden verdicts for pilot tickers."""
    return {
        "NVDA": {"verdict": "APPROVE", "confidence": 0.85, "reasoning": "Strong Wasden coverage — direct semiconductor thesis alignment with newsletter recommendations.", "mode": "direct_coverage"},
        "PYPL": {"verdict": "APPROVE", "confidence": 0.72, "reasoning": "Framework application suggests moderate bullish outlook based on fintech growth thesis.", "mode": "framework_application"},
        "NFLX": {"verdict": "NEUTRAL", "confidence": 0.55, "reasoning": "Mixed signals — strong content pipeline but valuation concerns noted in recent coverage.", "mode": "framework_application"},
        "TSM": {"verdict": "NEUTRAL", "confidence": 0.60, "reasoning": "Geopolitical risk factors offset strong fundamentals. Framework suggests caution.", "mode": "framework_application"},
        "XOM": {"verdict": "VETO", "confidence": 0.78, "reasoning": "Wasden framework strongly bearish on fossil fuel exposure — energy transition thesis.", "mode": "direct_coverage"},
        "AAPL": {"verdict": "APPROVE", "confidence": 0.80, "reasoning": "Consistent Wasden favorite — ecosystem strength and services growth align with framework.", "mode": "direct_coverage"},
        "MSFT": {"verdict": "APPROVE", "confidence": 0.82, "reasoning": "AI infrastructure play directly referenced in newsletter corpus.", "mode": "direct_coverage"},
        "AMZN": {"verdict": "APPROVE", "confidence": 0.75, "reasoning": "AWS growth and margin expansion align with framework criteria.", "mode": "framework_application"},
        "TSLA": {"verdict": "NEUTRAL", "confidence": 0.50, "reasoning": "High conviction disagreement in corpus — both strong bull and bear cases.", "mode": "framework_application"},
        "AMD": {"verdict": "APPROVE", "confidence": 0.77, "reasoning": "Semiconductor thesis alignment — AI chip demand narrative.", "mode": "direct_coverage"},
    }


def _get_mock_debate_outcomes() -> dict:
    """Deterministic mock debate outcomes."""
    return {
        "NVDA": {"outcome": "agreement", "rounds": 3},
        "PYPL": {"outcome": "agreement", "rounds": 3},
        "NFLX": {"outcome": "disagreement", "rounds": 3},
        "TSM": {"outcome": "disagreement", "rounds": 3},
        "XOM": {"outcome": "disagreement", "rounds": 3},
        "AAPL": {"outcome": "disagreement", "rounds": 3},
        "MSFT": {"outcome": "agreement", "rounds": 3},
        "AMZN": {"outcome": "agreement", "rounds": 3},
        "TSLA": {"outcome": "disagreement", "rounds": 3},
        "AMD": {"outcome": "agreement", "rounds": 3},
    }


def _get_mock_jury_votes(ticker: str) -> list[dict]:
    """Deterministic mock jury votes based on ticker."""
    vote_patterns = {
        "NFLX": ["HOLD"] * 6 + ["BUY"] * 3 + ["SELL"] * 1,
        "TSM": ["BUY"] * 5 + ["SELL"] * 5,  # 5-5 tie → escalation
        "XOM": ["SELL"] * 7 + ["HOLD"] * 2 + ["BUY"] * 1,
        "AAPL": ["BUY"] * 4 + ["HOLD"] * 3 + ["SELL"] * 3,  # risk fail path
        "TSLA": ["BUY"] * 5 + ["SELL"] * 5,  # 5-5 tie
    }
    votes_list = vote_patterns.get(ticker, ["BUY"] * 7 + ["HOLD"] * 2 + ["SELL"] * 1)

    focus_areas = [
        "fundamentals", "macro", "risk", "technical", "wasden_framework",
        "fundamentals", "macro", "risk", "technical", "wasden_framework",
    ]
    return [
        {
            "agent_id": i + 1,
            "vote": vote,
            "reasoning": f"Agent {i + 1} ({focus_areas[i]}) analysis for {ticker}",
            "focus_area": focus_areas[i],
        }
        for i, vote in enumerate(votes_list)
    ]


def _get_mock_jury_results(ticker: str) -> dict:
    """Deterministic mock jury aggregation results."""
    votes = _get_mock_jury_votes(ticker)
    from collections import Counter
    counts = Counter(v["vote"] for v in votes)

    buy_count = counts.get("BUY", 0)
    sell_count = counts.get("SELL", 0)
    hold_count = counts.get("HOLD", 0)
    final_count = {"buy": buy_count, "sell": sell_count, "hold": hold_count}

    # 5-5 tie → ESCALATED
    sorted_counts = counts.most_common()
    if len(sorted_counts) >= 2 and sorted_counts[0][1] == 5 and sorted_counts[1][1] == 5:
        return {
            "spawned": True,
            "reason": "5-5 jury tie — escalated to human decision",
            "final_count": final_count,
            "decision": "ESCALATED",
            "escalated_to_human": True,
        }

    # Decisive majority
    if sorted_counts and sorted_counts[0][1] >= 6:
        winner = sorted_counts[0][0]
        return {
            "spawned": True,
            "reason": f"Decisive {sorted_counts[0][1]}-vote majority for {winner}",
            "final_count": final_count,
            "decision": winner,
            "escalated_to_human": False,
        }

    return {
        "spawned": True,
        "reason": "No decisive majority — defaulting to HOLD",
        "final_count": final_count,
        "decision": "HOLD",
        "escalated_to_human": False,
    }


def _get_mock_risk_results(ticker: str) -> dict:
    """Deterministic mock risk check results."""
    # AAPL fails risk check in mock for testing the risk-block path
    if ticker == "AAPL":
        return {
            "passed": False,
            "checks_failed": ["sector_concentration"],
            "details": [
                {"check_name": "position_size", "passed": True, "detail": "Within limits"},
                {"check_name": "cash_reserve", "passed": True, "detail": "Sufficient"},
                {"check_name": "correlation", "passed": True, "detail": "OK"},
                {"check_name": "stress_correlation", "passed": True, "detail": "OK"},
                {"check_name": "sector_concentration", "passed": False, "detail": "Technology sector: 42% exceeds 40% limit"},
                {"check_name": "gap_risk", "passed": True, "detail": "OK"},
                {"check_name": "model_disagreement", "passed": True, "detail": "OK"},
            ],
        }
    return {
        "passed": True,
        "checks_failed": [],
        "details": [
            {"check_name": "position_size", "passed": True, "detail": "Within limits"},
            {"check_name": "cash_reserve", "passed": True, "detail": "Sufficient"},
            {"check_name": "correlation", "passed": True, "detail": "OK"},
            {"check_name": "stress_correlation", "passed": True, "detail": "OK"},
            {"check_name": "sector_concentration", "passed": True, "detail": "Within limits"},
            {"check_name": "gap_risk", "passed": True, "detail": "OK"},
            {"check_name": "model_disagreement", "passed": True, "detail": "OK"},
        ],
    }


def _get_mock_pre_trade_results(ticker: str) -> dict:
    """Deterministic mock pre-trade validation results."""
    return {
        "passed": True,
        "checks_failed": [],
        "details": [
            {"check_name": "quantity_sanity", "passed": True, "detail": "Within bounds"},
            {"check_name": "duplicate_detection", "passed": True, "detail": "No duplicates"},
            {"check_name": "portfolio_impact", "passed": True, "detail": "Within limits"},
            {"check_name": "dollar_sanity", "passed": True, "detail": "Within limits"},
        ],
    }
