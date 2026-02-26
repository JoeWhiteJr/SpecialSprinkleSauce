"""
5-Tier Screening Pipeline — Sprinkle Sauce.

Tier 1: Liquidity — market cap > $5B
Tier 2: Sprinkle Sauce — PEG < 2.0, FCF yield > 3%, Piotroski >= 5
Tier 3: STUB (quant models = Week 5)
Tier 4: STUB (Wasden Watch = wired in Week 7)
Tier 5: STUB (top 5 by composite × confidence)

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


def _tier3_stub(ticker: str, fundamentals: dict) -> dict:
    """Tier 3: STUB — Quant model filter (Week 5)."""
    return {
        "ticker": ticker,
        "passed": True,
        "fail_reasons": [],
        "metrics": {"stub": True, "note": "Quant models not yet implemented (Week 5)"},
    }


def _tier4_stub(ticker: str, fundamentals: dict) -> dict:
    """Tier 4: STUB — Wasden Watch verdict (Week 7)."""
    return {
        "ticker": ticker,
        "passed": True,
        "fail_reasons": [],
        "metrics": {"stub": True, "note": "Wasden Watch not yet wired (Week 7)"},
    }


def _tier5_stub(candidates: list[dict]) -> list[dict]:
    """Tier 5: STUB — Top 5 by composite × confidence (Week 7).

    For now, returns up to 5 candidates in original order.
    """
    return candidates[:5]


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

    # --- Tier 3: Quant Models (STUB) ---
    tier3_results = []
    tier3_passed = []
    for ticker in tier2_passed:
        result = _tier3_stub(ticker, tickers_fundamentals[ticker])
        tier3_results.append(result)
        if result["passed"]:
            tier3_passed.append(ticker)

    tier_results["tier3"] = tier3_results
    logger.info(f"Tier 3 (Quant — STUB): {len(tier3_passed)}/{len(tier2_passed)} passed")

    # --- Tier 4: Wasden Watch (STUB) ---
    tier4_results = []
    tier4_passed = []
    for ticker in tier3_passed:
        result = _tier4_stub(ticker, tickers_fundamentals[ticker])
        tier4_results.append(result)
        if result["passed"]:
            tier4_passed.append(ticker)

    tier_results["tier4"] = tier4_results
    logger.info(f"Tier 4 (Wasden — STUB): {len(tier4_passed)}/{len(tier3_passed)} passed")

    # --- Tier 5: Final Selection (STUB) ---
    final_candidate_dicts = [
        {"ticker": t, "fundamentals": tickers_fundamentals[t]}
        for t in tier4_passed
    ]
    final_selected = _tier5_stub(final_candidate_dicts)
    final_tickers = [c["ticker"] for c in final_selected]

    tier_results["tier5"] = [
        {
            "ticker": c["ticker"],
            "passed": c["ticker"] in final_tickers,
            "fail_reasons": [] if c["ticker"] in final_tickers else ["Not in top 5"],
            "metrics": {"stub": True},
        }
        for c in final_candidate_dicts
    ]
    logger.info(f"Tier 5 (Final — STUB): {len(final_tickers)}/{len(tier4_passed)} selected")

    elapsed = (datetime.utcnow() - start_time).total_seconds()

    # Build screening stages list for ScreeningRun compatibility
    stages = [
        {"stage_name": "Universe", "input_count": len(all_tickers), "output_count": len(all_tickers), "criteria": "Full ticker universe"},
        {"stage_name": "Tier 1: Liquidity", "input_count": len(all_tickers), "output_count": len(tier1_passed), "criteria": f"Market cap > ${MIN_MARKET_CAP / 1e9:.0f}B"},
        {"stage_name": "Tier 2: Sprinkle Sauce", "input_count": len(tier1_passed), "output_count": len(tier2_passed), "criteria": f"PEG < {MAX_PEG}, FCF yield > {MIN_FCF_YIELD}%, Piotroski >= {PIOTROSKI_THRESHOLD}"},
        {"stage_name": "Tier 3: Quant Models", "input_count": len(tier2_passed), "output_count": len(tier3_passed), "criteria": "STUB — Week 5"},
        {"stage_name": "Tier 4: Wasden Watch", "input_count": len(tier3_passed), "output_count": len(tier4_passed), "criteria": "STUB — Week 7"},
        {"stage_name": "Tier 5: Final Selection", "input_count": len(tier4_passed), "output_count": len(final_tickers), "criteria": "Top 5 by composite × confidence (STUB)"},
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
