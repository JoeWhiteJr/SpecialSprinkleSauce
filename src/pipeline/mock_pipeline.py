"""Mock decision pipeline — assembles full DecisionJournalEntry without calling any LLMs."""

import uuid
from datetime import datetime, timezone

from src.intelligence.quant_models.mock_scores import get_mock_scores
from src.pipeline.decision_pipeline import (
    _get_mock_debate_outcomes,
    _get_mock_jury_results,
    _get_mock_jury_votes,
    _get_mock_pre_trade_results,
    _get_mock_risk_results,
    _get_mock_verdicts,
)


class MockDecisionPipeline:
    """Assembles full pipeline output from mock data — no LLM calls, no API calls.

    Designed for testing and development. Produces deterministic results.
    """

    def run(
        self,
        ticker: str,
        price: float,
        fundamentals: dict | None = None,
    ) -> dict:
        """Run mock pipeline for a single ticker.

        Args:
            ticker: Stock ticker symbol.
            price: Current price.
            fundamentals: Optional fundamentals dict (ignored in mock).

        Returns:
            DecisionJournalEntry-compatible dict.
        """
        ticker = ticker.upper()
        pipeline_run_id = str(uuid.uuid4())

        # Quant scores
        scores = get_mock_scores(ticker)
        all_scores = list(scores.values())
        import statistics
        composite = statistics.mean(all_scores)
        std_dev = statistics.stdev(all_scores) if len(all_scores) > 1 else 0.0
        high_disagreement = std_dev > 0.5

        # Wasden verdict
        verdicts = _get_mock_verdicts()
        verdict = verdicts.get(
            ticker,
            {"verdict": "NEUTRAL", "confidence": 0.60, "reasoning": "No coverage", "mode": "framework_application"},
        )
        wasden_vetoed = verdict["verdict"] == "VETO"

        # Short-circuit on veto
        if wasden_vetoed:
            return self._build_veto_entry(
                ticker, pipeline_run_id, scores, composite, std_dev, high_disagreement, verdict,
            )

        # Bull/bear cases
        bull_case = f"Bull case for {ticker}: Composite {composite:.3f} suggests upside."
        bear_case = f"Bear case for {ticker}: Std dev {std_dev:.3f} suggests uncertainty."

        # Debate
        debate_outcomes = _get_mock_debate_outcomes()
        debate = debate_outcomes.get(ticker, {"outcome": "agreement", "rounds": 3})
        debate_agreed = debate["outcome"] == "agreement"

        # Jury (only if disagreement)
        jury_votes = []
        jury_result = {"spawned": False, "reason": "Debate agreement", "decision": None, "escalated_to_human": False, "final_count": None}
        jury_escalated = False
        if not debate_agreed:
            jury_votes = _get_mock_jury_votes(ticker)
            jury_result = _get_mock_jury_results(ticker)
            jury_escalated = jury_result.get("escalated_to_human", False)

        # Risk + pre-trade
        risk = _get_mock_risk_results(ticker)
        ptv = _get_mock_pre_trade_results(ticker)

        # Decision
        if jury_escalated:
            action, reason = "ESCALATED", "5-5 jury tie — escalated to human"
            position_size = 0.0
            human_required = True
        elif not risk["passed"]:
            action = "BLOCKED"
            reason = f"Risk failed: {', '.join(risk['checks_failed'])}"
            position_size = 0.0
            human_required = False
        elif not ptv["passed"]:
            action = "BLOCKED"
            reason = f"Pre-trade failed: {', '.join(ptv['checks_failed'])}"
            position_size = 0.0
            human_required = False
        else:
            # Determine action from jury or debate
            if jury_result.get("decision") and jury_result["decision"] not in ("ESCALATED", None):
                action = jury_result["decision"]
            elif composite > 0.6:
                action = "BUY"
            elif composite < 0.4:
                action = "SELL"
            else:
                action = "HOLD"

            position_size = 0.12 * verdict["confidence"] * (1 - std_dev)
            if high_disagreement:
                position_size *= 0.5
            position_size = min(position_size, 0.12)
            reason = f"Quant: {composite:.3f}, Wasden: {verdict['verdict']}"
            human_required = False

        return {
            "id": f"je-{pipeline_run_id[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ticker": f"{ticker} US Equity",
            "pipeline_run_id": pipeline_run_id,
            "quant_scores": {
                "xgboost": scores["xgboost"],
                "elastic_net": scores["elastic_net"],
                "arima": scores["arima"],
                "sentiment": scores["sentiment"],
                "composite": round(composite, 4),
                "std_dev": round(std_dev, 4),
                "high_disagreement_flag": high_disagreement,
            },
            "wasden_verdict": {
                "verdict": verdict["verdict"],
                "confidence": verdict["confidence"],
                "reasoning": verdict["reasoning"],
                "mode": verdict["mode"],
                "passages_retrieved": 0,
            },
            "bull_case": bull_case,
            "bear_case": bear_case,
            "debate_result": {
                "outcome": debate["outcome"],
                "rounds": debate["rounds"],
            },
            "jury": {
                "spawned": not debate_agreed,
                "reason": jury_result.get("reason"),
                "votes": jury_votes,
                "final_count": jury_result.get("final_count"),
                "decision": jury_result.get("decision") or action,
                "escalated_to_human": jury_escalated,
            },
            "risk_check": {"passed": risk["passed"], "checks_failed": risk.get("checks_failed", [])},
            "pre_trade_validation": {"passed": ptv["passed"], "checks_failed": ptv.get("checks_failed", [])},
            "final_decision": {
                "action": action,
                "reason": reason,
                "recommended_position_size": round(position_size, 4),
                "human_approval_required": human_required,
                "human_approved": None,
                "approved_by": None,
                "approved_at": None,
            },
            "execution": {"executed": False, "order_id": None, "fill_price": None, "slippage": None},
        }

    def _build_veto_entry(
        self, ticker, pipeline_run_id, scores, composite, std_dev, high_disagreement, verdict,
    ) -> dict:
        """Build journal entry for a Wasden VETO (bypasses debate/jury/risk)."""
        return {
            "id": f"je-{pipeline_run_id[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ticker": f"{ticker} US Equity",
            "pipeline_run_id": pipeline_run_id,
            "quant_scores": {
                "xgboost": scores["xgboost"],
                "elastic_net": scores["elastic_net"],
                "arima": scores["arima"],
                "sentiment": scores["sentiment"],
                "composite": round(composite, 4),
                "std_dev": round(std_dev, 4),
                "high_disagreement_flag": high_disagreement,
            },
            "wasden_verdict": {
                "verdict": "VETO",
                "confidence": verdict["confidence"],
                "reasoning": verdict["reasoning"],
                "mode": verdict["mode"],
                "passages_retrieved": 0,
            },
            "bull_case": "",
            "bear_case": "",
            "debate_result": {"outcome": "agreement", "rounds": 0},
            "jury": {
                "spawned": False,
                "reason": "Wasden VETO — debate/jury skipped",
                "votes": [],
                "final_count": None,
                "decision": "BLOCKED",
                "escalated_to_human": False,
            },
            "risk_check": {"passed": True, "checks_failed": []},
            "pre_trade_validation": {"passed": True, "checks_failed": []},
            "final_decision": {
                "action": "BLOCKED",
                "reason": f"Wasden VETO: {verdict['reasoning'][:200]}",
                "recommended_position_size": 0.0,
                "human_approval_required": False,
                "human_approved": None,
                "approved_by": None,
                "approved_at": None,
            },
            "execution": {"executed": False, "order_id": None, "fill_price": None, "slippage": None},
        }

    def run_batch(self, tickers_data: list[dict]) -> list[dict]:
        """Run mock pipeline for multiple tickers."""
        return [
            self.run(d["ticker"], d["price"], d.get("fundamentals"))
            for d in tickers_data
        ]
