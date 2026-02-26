"""
5-Tier Screening Pipeline — Sprinkle Sauce.

Tier 1: Liquidity — market cap > $5B
Tier 2: Sprinkle Sauce — PEG < 2.0, FCF yield > 3%, Piotroski >= 5
Tier 3: Quant Models — composite > 0.55, no high model disagreement
Tier 4: Wasden Watch — VETO = fail, APPROVE/NEUTRAL = pass
Tier 5: Final Selection — top 5 ranked by composite_quant × wasden_confidence

Each tier returns per-ticker pass/fail with reasons and metrics.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from app.services.piotroski import compute_piotroski

logger = logging.getLogger("wasden_watch.screening_engine")

# Tier 1 thresholds
MIN_MARKET_CAP = 5_000_000_000  # $5B

# Tier 2 thresholds (Sprinkle Sauce)
MAX_PEG = 2.0
MIN_FCF_YIELD = 3.0  # stored as percentage (3.0 = 3%)
PIOTROSKI_THRESHOLD = 5  # out of 9


class ScreeningError(Exception):
    """Raised when the screening pipeline encounters a fatal error."""
    pass


def _tier1_liquidity(ticker: str, fundamentals: dict) -> dict:
    """Tier 1: Liquidity filter — market cap > $5B.

    Returns dict with keys: ticker, passed, fail_reasons, metrics.
    """
    market_cap = fundamentals.get("market_cap")
    metrics = {"market_cap": market_cap}
    fail_reasons = []

    if market_cap is None:
        fail_reasons.append("market_cap data not available")
    elif market_cap < MIN_MARKET_CAP:
        fail_reasons.append(
            f"market_cap ${market_cap:,.0f} < ${MIN_MARKET_CAP:,.0f}"
        )

    return {
        "ticker": ticker,
        "passed": len(fail_reasons) == 0,
        "fail_reasons": fail_reasons,
        "metrics": metrics,
    }


def _tier2_sprinkle_sauce(ticker: str, fundamentals: dict) -> dict:
    """Tier 2: Sprinkle Sauce — PEG, FCF yield, Piotroski.

    Returns dict with keys: ticker, passed, fail_reasons, metrics, piotroski.
    """
    peg = fundamentals.get("peg_ratio")
    fcf_yield = fundamentals.get("fcf_yield")
    fail_reasons = []
    metrics = {"peg_ratio": peg, "fcf_yield": fcf_yield}

    # PEG check
    if peg is None:
        fail_reasons.append("PEG ratio not available")
    elif peg >= MAX_PEG:
        fail_reasons.append(f"PEG {peg:.2f} >= {MAX_PEG}")
    elif peg <= 0:
        fail_reasons.append(f"PEG {peg:.2f} is non-positive (negative earnings growth)")

    # FCF yield check (stored as percentage, threshold is 3.0)
    if fcf_yield is None:
        fail_reasons.append("FCF yield not available")
    elif fcf_yield < MIN_FCF_YIELD:
        fail_reasons.append(f"FCF yield {fcf_yield:.2f}% < {MIN_FCF_YIELD}%")

    # Piotroski check
    piotroski = compute_piotroski(ticker, fundamentals)
    metrics["piotroski_score"] = piotroski.score
    metrics["piotroski_max"] = piotroski.max_possible
    metrics["piotroski_ratio"] = round(piotroski.ratio, 3)

    if not piotroski.data_available:
        fail_reasons.append("Piotroski: insufficient data (< 3 signals)")
    elif not piotroski.passes_threshold:
        fail_reasons.append(
            f"Piotroski {piotroski.score}/{piotroski.max_possible} "
            f"(ratio {piotroski.ratio:.2f} < {PIOTROSKI_THRESHOLD}/9)"
        )

    return {
        "ticker": ticker,
        "passed": len(fail_reasons) == 0,
        "fail_reasons": fail_reasons,
        "metrics": metrics,
        "piotroski": {
            "score": piotroski.score,
            "max_possible": piotroski.max_possible,
            "ratio": piotroski.ratio,
            "passes": piotroski.passes_threshold,
            "signals": [
                {
                    "name": s.name,
                    "value": s.value,
                    "data_available": s.data_available,
                    "detail": s.detail,
                }
                for s in piotroski.signals
            ],
        },
    }


def _tier3_quant(ticker: str, fundamentals: dict) -> dict:
    """Tier 3: Quant model filter — composite > 0.55 AND no high disagreement.

    Uses QuantModelOrchestrator (mock or real based on USE_MOCK_DATA).
    """
    from src.intelligence.quant_models import QuantModelOrchestrator
    from app.config import settings

    orchestrator = QuantModelOrchestrator(use_mock=settings.use_mock_data)
    scores = orchestrator.score_ticker(ticker)

    fail_reasons = []
    if scores["composite"] <= 0.55:
        fail_reasons.append(
            f"Quant composite {scores['composite']:.4f} <= 0.55 threshold"
        )
    if scores["high_disagreement_flag"]:
        fail_reasons.append(
            f"High model disagreement (std_dev={scores['std_dev']:.4f} > 0.50)"
        )

    return {
        "ticker": ticker,
        "passed": len(fail_reasons) == 0,
        "fail_reasons": fail_reasons,
        "metrics": {
            "quant_scores": scores,
            "composite": scores["composite"],
            "std_dev": scores["std_dev"],
            "high_disagreement_flag": scores["high_disagreement_flag"],
        },
    }


def _tier4_wasden(ticker: str, fundamentals: dict) -> dict:
    """Tier 4: Wasden Watch verdict — VETO=fail, APPROVE/NEUTRAL=pass.

    Uses VerdictGenerator (or mock verdicts in mock mode).
    """
    from app.config import settings

    if settings.use_mock_data:
        from src.pipeline.decision_pipeline import _get_mock_verdicts
        verdicts = _get_mock_verdicts()
        verdict_data = verdicts.get(
            ticker.upper(),
            {"verdict": "NEUTRAL", "confidence": 0.60, "reasoning": "No coverage", "mode": "framework_application"},
        )
    else:
        from src.intelligence.wasden_watch import VerdictGenerator, VerdictRequest
        generator = VerdictGenerator()
        request = VerdictRequest(ticker=ticker, fundamentals=fundamentals)
        response = generator.generate(request)
        verdict_data = {
            "verdict": response.verdict.verdict,
            "confidence": response.verdict.confidence,
            "reasoning": response.verdict.reasoning,
            "mode": response.verdict.mode,
        }

    fail_reasons = []
    if verdict_data["verdict"] == "VETO":
        fail_reasons.append(
            f"Wasden Watch VETO (confidence={verdict_data['confidence']:.2f}): "
            f"{verdict_data['reasoning'][:150]}"
        )

    return {
        "ticker": ticker,
        "passed": len(fail_reasons) == 0,
        "fail_reasons": fail_reasons,
        "metrics": {
            "wasden_verdict": verdict_data["verdict"],
            "wasden_confidence": verdict_data["confidence"],
            "wasden_mode": verdict_data["mode"],
        },
    }


def _tier5_final_selection(candidates: list[dict], tier3_results: list[dict], tier4_results: list[dict]) -> list[dict]:
    """Tier 5: Final selection — top 5 ranked by composite_quant x wasden_confidence.

    Args:
        candidates: List of dicts with 'ticker' and 'fundamentals'.
        tier3_results: Tier 3 results for quant composite lookup.
        tier4_results: Tier 4 results for wasden confidence lookup.

    Returns:
        Top 5 candidates sorted by ranking score.
    """
    # Build lookup dicts from tier results
    quant_lookup = {}
    for r in tier3_results:
        if r["passed"]:
            quant_lookup[r["ticker"]] = r["metrics"].get("composite", 0.5)

    wasden_lookup = {}
    for r in tier4_results:
        if r["passed"]:
            wasden_lookup[r["ticker"]] = r["metrics"].get("wasden_confidence", 0.5)

    # Score each candidate
    scored = []
    for c in candidates:
        ticker = c["ticker"]
        quant_composite = quant_lookup.get(ticker, 0.5)
        wasden_confidence = wasden_lookup.get(ticker, 0.5)
        rank_score = quant_composite * wasden_confidence
        scored.append({**c, "_rank_score": rank_score})

    # Sort descending by rank score, take top 5
    scored.sort(key=lambda x: x["_rank_score"], reverse=True)
    return scored[:5]


def run_screening_pipeline(
    tickers_fundamentals: dict[str, dict],
    run_id: Optional[str] = None,
) -> dict:
    """Run the full 5-tier screening pipeline.

    Args:
        tickers_fundamentals: dict mapping ticker -> fundamentals dict.
            Each fundamentals dict has keys matching Bloomberg column names.
        run_id: Optional screening run UUID. Generated if not provided.

    Returns:
        ScreeningPipelineResult-compatible dict with per-tier breakdowns.
    """
    run_id = run_id or str(uuid.uuid4())
    start_time = datetime.utcnow()
    all_tickers = list(tickers_fundamentals.keys())
    tier_results = {}

    logger.info(f"Screening pipeline {run_id}: starting with {len(all_tickers)} tickers")

    # --- Tier 1: Liquidity ---
    tier1_results = []
    tier1_passed = []
    for ticker in all_tickers:
        result = _tier1_liquidity(ticker, tickers_fundamentals[ticker])
        tier1_results.append(result)
        if result["passed"]:
            tier1_passed.append(ticker)

    tier_results["tier1"] = tier1_results
    logger.info(f"Tier 1 (Liquidity): {len(tier1_passed)}/{len(all_tickers)} passed")

    # --- Tier 2: Sprinkle Sauce ---
    tier2_results = []
    tier2_passed = []
    for ticker in tier1_passed:
        result = _tier2_sprinkle_sauce(ticker, tickers_fundamentals[ticker])
        tier2_results.append(result)
        if result["passed"]:
            tier2_passed.append(ticker)

    tier_results["tier2"] = tier2_results
    logger.info(f"Tier 2 (Sprinkle Sauce): {len(tier2_passed)}/{len(tier1_passed)} passed")

    # --- Tier 3: Quant Models ---
    tier3_results = []
    tier3_passed = []
    for ticker in tier2_passed:
        result = _tier3_quant(ticker, tickers_fundamentals[ticker])
        tier3_results.append(result)
        if result["passed"]:
            tier3_passed.append(ticker)

    tier_results["tier3"] = tier3_results
    logger.info(f"Tier 3 (Quant): {len(tier3_passed)}/{len(tier2_passed)} passed")

    # --- Tier 4: Wasden Watch ---
    tier4_results = []
    tier4_passed = []
    for ticker in tier3_passed:
        result = _tier4_wasden(ticker, tickers_fundamentals[ticker])
        tier4_results.append(result)
        if result["passed"]:
            tier4_passed.append(ticker)

    tier_results["tier4"] = tier4_results
    logger.info(f"Tier 4 (Wasden): {len(tier4_passed)}/{len(tier3_passed)} passed")

    # --- Tier 5: Final Selection ---
    final_candidate_dicts = [
        {"ticker": t, "fundamentals": tickers_fundamentals[t]}
        for t in tier4_passed
    ]
    final_selected = _tier5_final_selection(final_candidate_dicts, tier3_results, tier4_results)
    final_tickers = [c["ticker"] for c in final_selected]

    tier_results["tier5"] = [
        {
            "ticker": c["ticker"],
            "passed": c["ticker"] in final_tickers,
            "fail_reasons": [] if c["ticker"] in final_tickers else ["Not in top 5"],
            "metrics": {
                "rank_score": round(c.get("_rank_score", 0), 4) if c["ticker"] in final_tickers else None,
            },
        }
        for c in final_candidate_dicts
    ]
    logger.info(f"Tier 5 (Final): {len(final_tickers)}/{len(tier4_passed)} selected")

    elapsed = (datetime.utcnow() - start_time).total_seconds()

    # Build screening stages list for ScreeningRun compatibility
    stages = [
        {"stage_name": "Universe", "input_count": len(all_tickers), "output_count": len(all_tickers), "criteria": "Full ticker universe"},
        {"stage_name": "Tier 1: Liquidity", "input_count": len(all_tickers), "output_count": len(tier1_passed), "criteria": f"Market cap > ${MIN_MARKET_CAP / 1e9:.0f}B"},
        {"stage_name": "Tier 2: Sprinkle Sauce", "input_count": len(tier1_passed), "output_count": len(tier2_passed), "criteria": f"PEG < {MAX_PEG}, FCF yield > {MIN_FCF_YIELD}%, Piotroski >= {PIOTROSKI_THRESHOLD}"},
        {"stage_name": "Tier 3: Quant Models", "input_count": len(tier2_passed), "output_count": len(tier3_passed), "criteria": "Composite > 0.55, no high model disagreement"},
        {"stage_name": "Tier 4: Wasden Watch", "input_count": len(tier3_passed), "output_count": len(tier4_passed), "criteria": "Wasden verdict != VETO"},
        {"stage_name": "Tier 5: Final Selection", "input_count": len(tier4_passed), "output_count": len(final_tickers), "criteria": "Top 5 by composite_quant × wasden_confidence"},
    ]

    return {
        "id": run_id,
        "timestamp": start_time.isoformat() + "Z",
        "stages": stages,
        "final_candidates": [f"{t} US Equity" for t in final_tickers],
        "pipeline_run_ids": [],
        "duration_seconds": round(elapsed, 2),
        "model_used": "claude-haiku",
        "tier_results": tier_results,
        "data_freshness_summary": {},
    }
