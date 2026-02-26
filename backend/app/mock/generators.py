"""
Mock data generators for Wasden Watch trading dashboard.
All prices use real Bloomberg snapshot values from Feb 21, 2026.
Data is internally consistent: pipeline_run_ids, tickers, and dates
cross-reference correctly across journal entries, jury votes, debates, etc.
"""

import uuid
import random
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Real Bloomberg snapshot prices (Feb 21, 2026)
# ---------------------------------------------------------------------------

BLOOMBERG_PRICES: dict[str, float] = {
    "NVDA": 189.82,
    "PYPL": 41.65,
    "NFLX": 78.67,
    "TSM": 370.54,
    "XOM": 147.28,
    "AAPL": 264.58,
    "MSFT": 397.23,
    "AMZN": 210.11,
    "TSLA": 411.82,
    "AMD": 200.15,
}

PILOT_TICKERS = ["NVDA", "PYPL", "NFLX", "TSM", "XOM", "AAPL"]

# Stable UUIDs so cross-references are consistent
PIPELINE_RUN_IDS = {
    "NVDA_1": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    "PYPL_1": "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
    "NFLX_1": "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f",
    "TSM_1": "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f80",
    "XOM_1": "e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8091",
    "AAPL_1": "f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f809102",
}

JOURNAL_ENTRY_IDS = {
    "NVDA_1": "je-001",
    "PYPL_1": "je-002",
    "NFLX_1": "je-003",
    "TSM_1": "je-004",
    "XOM_1": "je-005",
    "AAPL_1": "je-006",
}

BASE_DATE = datetime(2026, 2, 21, 9, 30, 0)


def _ts(days_ago: int = 0, hours: int = 0) -> str:
    """Return ISO-8601 timestamp relative to BASE_DATE."""
    dt = BASE_DATE - timedelta(days=days_ago, hours=hours)
    return dt.isoformat() + "Z"


def _date_str(days_ago: int = 0) -> str:
    d = (BASE_DATE - timedelta(days=days_ago)).date()
    return d.isoformat()


# ---------------------------------------------------------------------------
# Portfolio Snapshots (30 days)
# ---------------------------------------------------------------------------

def generate_portfolio_snapshots() -> list[dict]:
    """30 daily portfolio snapshots starting at $100,000 with SPY comparison."""
    snapshots = []
    portfolio_value = 100_000.0
    spy_value = 100_000.0
    cumulative_pnl = 0.0
    spy_cumulative_pnl = 0.0

    random.seed(42)  # Reproducible

    for i in range(29, -1, -1):
        # Portfolio daily return: slight positive bias
        daily_return = random.gauss(0.0012, 0.008)
        daily_pnl = portfolio_value * daily_return
        portfolio_value += daily_pnl
        cumulative_pnl += daily_pnl

        # SPY daily return
        spy_return = random.gauss(0.0005, 0.007)
        spy_daily_pnl = spy_value * spy_return
        spy_value += spy_daily_pnl
        spy_cumulative_pnl += spy_daily_pnl

        snapshots.append({
            "date": _date_str(i),
            "portfolio_value": round(portfolio_value, 2),
            "daily_pnl": round(daily_pnl, 2),
            "daily_pnl_pct": round(daily_return * 100, 4),
            "cumulative_pnl": round(cumulative_pnl, 2),
            "cumulative_pnl_pct": round((cumulative_pnl / 100_000) * 100, 4),
            "spy_value": round(spy_value, 2),
            "spy_daily_pnl_pct": round(spy_return * 100, 4),
            "spy_cumulative_pnl_pct": round((spy_cumulative_pnl / 100_000) * 100, 4),
            "positions_count": random.randint(3, 6),
            "cash_balance": round(portfolio_value * random.uniform(0.15, 0.35), 2),
        })

    return snapshots


# ---------------------------------------------------------------------------
# Decision Journal Entries (6 entries for pilot tickers)
# ---------------------------------------------------------------------------

def generate_journal_entries() -> list[dict]:
    """6 decision journal entries for pilot tickers."""
    entries = []

    # Entry 1: NVDA - BUY, approved, executed
    entries.append({
        "id": JOURNAL_ENTRY_IDS["NVDA_1"],
        "timestamp": _ts(days_ago=5),
        "ticker": "NVDA US Equity",
        "pipeline_run_id": PIPELINE_RUN_IDS["NVDA_1"],
        "quant_scores": {
            "xgboost": 0.72, "elastic_net": 0.68, "arima": 0.65, "sentiment": 0.81,
            "composite": 0.715, "std_dev": 0.06, "high_disagreement_flag": False,
        },
        "wasden_verdict": {
            "verdict": "APPROVE", "confidence": 0.85,
            "reasoning": "Strong FCF yield relative to sector. Wasden covered NVDA extensively in Dec 2025 Weekender. AI capex cycle supports revenue growth thesis.",
            "mode": "direct_coverage", "passages_retrieved": 7,
        },
        "bull_case": "NVDA's data center revenue grew 94% YoY. AI infrastructure spending is accelerating with hyperscaler capex commitments totaling $320B in 2026. Blackwell architecture margins expanding. FCF yield of 2.8% exceeds sector median.",
        "bear_case": "NVDA trades at 45x forward earnings, pricing in perfection. Custom ASIC competition from Google TPU and Amazon Trainium threatens market share. China export restrictions limit TAM by ~15%. Cyclical semiconductor risk if AI spending plateaus.",
        "debate_result": {"outcome": "disagreement", "rounds": 2},
        "jury": {
            "spawned": True,
            "reason": "Bull/Bear debate reached disagreement after 2 rounds",
            "votes": _generate_jury_votes_for("NVDA", buy=7, sell=2, hold=1),
            "final_count": {"buy": 7, "sell": 2, "hold": 1},
            "decision": "BUY", "escalated_to_human": False,
        },
        "risk_check": {"passed": True, "checks_failed": []},
        "pre_trade_validation": {"passed": True, "checks_failed": []},
        "final_decision": {
            "action": "BUY", "reason": "Jury voted 7-2-1 BUY. Wasden APPROVE with 0.85 confidence. All risk checks passed.",
            "recommended_position_size": 0.08,
            "human_approval_required": True, "human_approved": True,
            "approved_by": "Jared", "approved_at": _ts(days_ago=5, hours=-1),
        },
        "execution": {
            "executed": True, "order_id": "ord-nvda-001",
            "fill_price": 188.45, "slippage": 0.0012,
        },
    })

    # Entry 2: PYPL - BUY, approved, executed
    entries.append({
        "id": JOURNAL_ENTRY_IDS["PYPL_1"],
        "timestamp": _ts(days_ago=4),
        "ticker": "PYPL US Equity",
        "pipeline_run_id": PIPELINE_RUN_IDS["PYPL_1"],
        "quant_scores": {
            "xgboost": 0.61, "elastic_net": 0.58, "arima": 0.54, "sentiment": 0.67,
            "composite": 0.60, "std_dev": 0.05, "high_disagreement_flag": False,
        },
        "wasden_verdict": {
            "verdict": "APPROVE", "confidence": 0.72,
            "reasoning": "Deep value play. Trading at 14x earnings, well below 5-year average of 35x. Venmo monetization accelerating. Wasden methodology favors mean reversion at these multiples.",
            "mode": "framework_application", "passages_retrieved": 3,
        },
        "bull_case": "PYPL is dramatically undervalued at 14x earnings. Venmo's path to profitability is clear. Share buybacks reducing float. New CEO executing well on margin expansion. FCF yield of 7.2% is compelling.",
        "bear_case": "Payment processing is commoditizing. Apple Pay, Google Pay, and BNPL competitors eroding moat. Revenue growth has decelerated to single digits. No clear catalyst for re-rating.",
        "debate_result": {"outcome": "agreement", "rounds": 2},
        "jury": {
            "spawned": False, "reason": None,
            "votes": [], "final_count": None,
            "decision": None, "escalated_to_human": False,
        },
        "risk_check": {"passed": True, "checks_failed": []},
        "pre_trade_validation": {"passed": True, "checks_failed": []},
        "final_decision": {
            "action": "BUY", "reason": "Bull/Bear reached agreement. Wasden APPROVE with 0.72 confidence. Value thesis compelling.",
            "recommended_position_size": 0.06,
            "human_approval_required": True, "human_approved": True,
            "approved_by": "Joe", "approved_at": _ts(days_ago=4, hours=-2),
        },
        "execution": {
            "executed": True, "order_id": "ord-pypl-001",
            "fill_price": 41.30, "slippage": 0.0008,
        },
    })

    # Entry 3: NFLX - HOLD, no execution
    entries.append({
        "id": JOURNAL_ENTRY_IDS["NFLX_1"],
        "timestamp": _ts(days_ago=3),
        "ticker": "NFLX US Equity",
        "pipeline_run_id": PIPELINE_RUN_IDS["NFLX_1"],
        "quant_scores": {
            "xgboost": 0.48, "elastic_net": 0.52, "arima": 0.45, "sentiment": 0.55,
            "composite": 0.50, "std_dev": 0.04, "high_disagreement_flag": False,
        },
        "wasden_verdict": {
            "verdict": "NEUTRAL", "confidence": 0.55,
            "reasoning": "NFLX fundamentals are improving but valuation is fair. Wasden has not directly covered NFLX recently. Framework application suggests wait for better entry.",
            "mode": "framework_application", "passages_retrieved": 2,
        },
        "bull_case": "Ad-supported tier driving subscriber growth. Password sharing crackdown working. Content spending efficiency improving. Revenue per member increasing.",
        "bear_case": "At 35x forward earnings, growth is priced in. Competition from Disney+, Amazon Prime intensifying. Content costs will re-accelerate. Subscriber growth plateauing in mature markets.",
        "debate_result": {"outcome": "agreement", "rounds": 1},
        "jury": {
            "spawned": False, "reason": None,
            "votes": [], "final_count": None,
            "decision": None, "escalated_to_human": False,
        },
        "risk_check": {"passed": True, "checks_failed": []},
        "pre_trade_validation": {"passed": True, "checks_failed": []},
        "final_decision": {
            "action": "HOLD", "reason": "Wasden NEUTRAL. Debate reached agreement on HOLD. Fair value, no compelling entry point.",
            "recommended_position_size": 0.0,
            "human_approval_required": False, "human_approved": None,
            "approved_by": None, "approved_at": None,
        },
        "execution": {"executed": False, "order_id": None, "fill_price": None, "slippage": None},
    })

    # Entry 4: TSM - BUY, jury tie, escalated to human
    entries.append({
        "id": JOURNAL_ENTRY_IDS["TSM_1"],
        "timestamp": _ts(days_ago=2),
        "ticker": "TSM US Equity",
        "pipeline_run_id": PIPELINE_RUN_IDS["TSM_1"],
        "quant_scores": {
            "xgboost": 0.64, "elastic_net": 0.71, "arima": 0.58, "sentiment": 0.43,
            "composite": 0.59, "std_dev": 0.11, "high_disagreement_flag": False,
        },
        "wasden_verdict": {
            "verdict": "APPROVE", "confidence": 0.78,
            "reasoning": "TSM is the irreplaceable semiconductor foundry. Wasden framework strongly favors monopolistic competitive advantages. Arizona fab diversifies geopolitical risk. Trading below intrinsic value.",
            "mode": "framework_application", "passages_retrieved": 4,
        },
        "bull_case": "TSM manufactures 90% of advanced chips. AI demand guarantees multi-year revenue growth. Arizona expansion reduces Taiwan risk. N3/N2 process nodes extend technology lead. ADR discount to local shares.",
        "bear_case": "Taiwan geopolitical risk is existential and unhedgeable. China invasion scenario would halt production. US CHIPS Act competitors (Intel, Samsung) closing gap. ADR structure limits shareholder rights. Sentiment score at 0.43 signals caution.",
        "debate_result": {"outcome": "disagreement", "rounds": 3},
        "jury": {
            "spawned": True,
            "reason": "Bull/Bear debate reached disagreement after 3 rounds",
            "votes": _generate_jury_votes_for("TSM", buy=5, sell=5, hold=0),
            "final_count": {"buy": 5, "sell": 5, "hold": 0},
            "decision": "ESCALATED", "escalated_to_human": True,
        },
        "risk_check": {"passed": True, "checks_failed": []},
        "pre_trade_validation": {"passed": True, "checks_failed": []},
        "final_decision": {
            "action": "BUY", "reason": "5-5 jury tie escalated to human. Jared reviewed full transcript and approved BUY with reduced position size.",
            "recommended_position_size": 0.05,
            "human_approval_required": True, "human_approved": True,
            "approved_by": "Jared", "approved_at": _ts(days_ago=2, hours=-3),
        },
        "execution": {
            "executed": True, "order_id": "ord-tsm-001",
            "fill_price": 369.80, "slippage": 0.002,
        },
    })

    # Entry 5: XOM - BLOCKED by Wasden VETO
    entries.append({
        "id": JOURNAL_ENTRY_IDS["XOM_1"],
        "timestamp": _ts(days_ago=1),
        "ticker": "XOM US Equity",
        "pipeline_run_id": PIPELINE_RUN_IDS["XOM_1"],
        "quant_scores": {
            "xgboost": 0.55, "elastic_net": 0.62, "arima": 0.48, "sentiment": 0.38,
            "composite": 0.508, "std_dev": 0.09, "high_disagreement_flag": False,
        },
        "wasden_verdict": {
            "verdict": "VETO", "confidence": 0.91,
            "reasoning": "Wasden explicitly warned about oil majors in Jan 2026 Weekender. Excess supply from OPEC+ production increases. Geopolitical discount already priced in. Energy sector overweight risk.",
            "mode": "direct_coverage", "passages_retrieved": 11,
        },
        "bull_case": "XOM's integrated model provides downstream hedge. Guyana production ramping. Shareholder returns (dividend + buyback) yield 6%. Pioneer acquisition creates Permian dominance.",
        "bear_case": "Wasden explicitly vetoed. OPEC+ discipline breaking. Oil prices trending toward $60/bbl on oversupply. Energy transition accelerating. Capital allocation questionable with Pioneer premium.",
        "debate_result": {"outcome": "agreement", "rounds": 1},
        "jury": {
            "spawned": False, "reason": None,
            "votes": [], "final_count": None,
            "decision": None, "escalated_to_human": False,
        },
        "risk_check": {"passed": True, "checks_failed": []},
        "pre_trade_validation": {"passed": True, "checks_failed": []},
        "final_decision": {
            "action": "BLOCKED", "reason": "Wasden VETO with 0.91 confidence. Highest authority in the system vetoed this trade.",
            "recommended_position_size": 0.0,
            "human_approval_required": False, "human_approved": None,
            "approved_by": None, "approved_at": None,
        },
        "execution": {"executed": False, "order_id": None, "fill_price": None, "slippage": None},
    })

    # Entry 6: AAPL - BUY, risk check failed
    entries.append({
        "id": JOURNAL_ENTRY_IDS["AAPL_1"],
        "timestamp": _ts(days_ago=0),
        "ticker": "AAPL US Equity",
        "pipeline_run_id": PIPELINE_RUN_IDS["AAPL_1"],
        "quant_scores": {
            "xgboost": 0.69, "elastic_net": 0.73, "arima": 0.61, "sentiment": 0.76,
            "composite": 0.6975, "std_dev": 0.05, "high_disagreement_flag": False,
        },
        "wasden_verdict": {
            "verdict": "APPROVE", "confidence": 0.80,
            "reasoning": "Wasden views AAPL as core holding. Services revenue creating durable margin expansion. iPhone cycle entering upgrade supercycle with AI features.",
            "mode": "direct_coverage", "passages_retrieved": 9,
        },
        "bull_case": "Services revenue at 25% margins growing 15% YoY. iPhone 18 AI features drive upgrade cycle. India manufacturing reduces China risk. Share buyback machine. Warren Buffett's largest holding validates thesis.",
        "bear_case": "Trading at 32x earnings, above 5-year average. China market share declining. AI features lag behind competitors. Regulatory risk from App Store antitrust globally. Hardware growth stagnating.",
        "debate_result": {"outcome": "disagreement", "rounds": 2},
        "jury": {
            "spawned": True,
            "reason": "Bull/Bear debate reached disagreement after 2 rounds",
            "votes": _generate_jury_votes_for("AAPL", buy=8, sell=1, hold=1),
            "final_count": {"buy": 8, "sell": 1, "hold": 1},
            "decision": "BUY", "escalated_to_human": False,
        },
        "risk_check": {
            "passed": False,
            "checks_failed": ["sector_concentration: Technology sector would exceed 40% of portfolio"],
        },
        "pre_trade_validation": {"passed": True, "checks_failed": []},
        "final_decision": {
            "action": "BLOCKED",
            "reason": "Risk check failed: Technology sector concentration would exceed 40%. Reduce existing tech exposure before adding AAPL.",
            "recommended_position_size": 0.0,
            "human_approval_required": False, "human_approved": None,
            "approved_by": None, "approved_at": None,
        },
        "execution": {"executed": False, "order_id": None, "fill_price": None, "slippage": None},
    })

    return entries


def _generate_jury_votes_for(
    ticker: str, buy: int, sell: int, hold: int
) -> list[dict]:
    """Generate 10 jury votes with the specified distribution."""
    focus_areas = [
        "fundamentals", "fundamentals", "fundamentals",
        "macro", "macro",
        "risk", "risk",
        "technical", "technical",
        "wasden_framework",
    ]

    votes_list: list[dict] = []
    vote_sequence = (
        ["BUY"] * buy + ["SELL"] * sell + ["HOLD"] * hold
    )
    # Shuffle but keep reproducible per ticker
    rng = random.Random(hash(ticker))
    rng.shuffle(vote_sequence)

    reasoning_templates = {
        "BUY": {
            "fundamentals": f"Strong fundamentals for {ticker}. Valuation metrics support entry at current levels. FCF generation is robust.",
            "macro": f"Macro environment favors {ticker}'s sector. Interest rate trajectory is supportive of growth.",
            "risk": f"Risk/reward skew is favorable for {ticker}. Downside scenarios are manageable with proper position sizing.",
            "technical": f"Technical setup for {ticker} shows bullish momentum. Price above key moving averages with increasing volume.",
            "wasden_framework": f"Applying Wasden's 5-bucket framework, {ticker} scores well across quality, value, and growth metrics.",
        },
        "SELL": {
            "fundamentals": f"Valuation stretched for {ticker}. Forward multiples above historical range. Margin compression risk.",
            "macro": f"Macro headwinds for {ticker}'s sector. Rising rates pressure valuations in this space.",
            "risk": f"Downside risk for {ticker} exceeds acceptable thresholds. Gap risk is elevated given current volatility.",
            "technical": f"Technical deterioration for {ticker}. Bearish divergence on RSI. Support levels weakening.",
            "wasden_framework": f"Wasden framework flags concerns for {ticker}. Quality metrics declining sequentially.",
        },
        "HOLD": {
            "fundamentals": f"Fundamentals for {ticker} are mixed. Some positive signals but not compelling enough for new entry.",
            "macro": f"Macro environment for {ticker} is uncertain. Prefer to wait for clarity before committing capital.",
            "risk": f"Risk assessment for {ticker} is neutral. No immediate threat but no compelling edge either.",
            "technical": f"Technical picture for {ticker} is consolidating. Wait for breakout confirmation before acting.",
            "wasden_framework": f"Wasden framework gives {ticker} a neutral reading. Insufficient conviction for action.",
        },
    }

    for i, vote in enumerate(vote_sequence):
        focus = focus_areas[i]
        votes_list.append({
            "agent_id": i + 1,
            "vote": vote,
            "reasoning": reasoning_templates[vote][focus],
            "focus_area": focus,
        })

    return votes_list


# ---------------------------------------------------------------------------
# Debate Transcripts (3 debates with 2-3 rounds each)
# ---------------------------------------------------------------------------

def generate_debate_transcripts() -> list[dict]:
    """3 debate transcripts for tickers that triggered jury."""
    transcripts = []

    # NVDA debate (2 rounds, disagreement -> jury)
    transcripts.append({
        "pipeline_run_id": PIPELINE_RUN_IDS["NVDA_1"],
        "ticker": "NVDA US Equity",
        "timestamp": _ts(days_ago=5),
        "rounds": [
            {
                "round_number": 1,
                "bull_argument": "NVDA's data center revenue grew 94% YoY to $18.4B in Q4. The AI infrastructure buildout is not a bubble — hyperscalers have committed $320B in 2026 capex. Blackwell GPU margins are expanding to 78%. The competitive moat in CUDA ecosystem is nearly impossible to replicate. At $189.82, NVDA trades at 35x forward earnings which is reasonable given 40%+ revenue growth.",
                "bear_argument": "The market is pricing in perfection at 35x forward earnings. Google's TPU v6 and Amazon's Trainium 3 are viable CUDA alternatives for inference workloads, which represent 60% of AI compute. China export restrictions remove ~15% of NVDA's addressable market permanently. Semiconductor cycles always revert — when hyperscaler capex normalizes, NVDA revenue will decelerate sharply.",
            },
            {
                "round_number": 2,
                "bull_argument": "Custom ASICs handle inference but NVDA dominates training, which is growing faster. The CUDA ecosystem has 4M+ developers — switching costs are enormous. China restrictions are already priced in. Revenue estimates have been revised UP 3 consecutive quarters. Blackwell supply is sold out through Q3 2026.",
                "bear_argument": "Training workloads will eventually saturate as foundation models mature. The real growth is in inference where NVDA faces genuine competition. Developer lock-in arguments were made about Intel x86 too. At this valuation, any miss on expectations causes 20%+ drawdown. Risk-adjusted return is poor.",
            },
        ],
        "outcome": "disagreement",
        "bull_model": "claude-sonnet",
        "bear_model": "gemini-pro",
        "jury_triggered": True,
    })

    # TSM debate (3 rounds, disagreement -> jury -> 5-5 tie -> escalated)
    transcripts.append({
        "pipeline_run_id": PIPELINE_RUN_IDS["TSM_1"],
        "ticker": "TSM US Equity",
        "timestamp": _ts(days_ago=2),
        "rounds": [
            {
                "round_number": 1,
                "bull_argument": "TSM manufactures over 90% of the world's advanced semiconductors (sub-7nm). There is no substitute. Every AI chip from NVDA, AMD, Apple, and Qualcomm depends on TSM. Arizona fab expansion de-risks the Taiwan geopolitical narrative. At $370.54, TSM trades at 22x forward earnings — a discount to the semiconductor sector average of 28x.",
                "bear_argument": "Taiwan Strait conflict risk is not a discount factor — it's an existential binary risk. If China blockades or invades Taiwan, TSM production halts entirely. Arizona fab is 2-3 years from meaningful volume and costs 40% more to operate. Intel Foundry Services and Samsung are closing the process gap. The ADR structure provides zero shareholder protection in a crisis.",
            },
            {
                "round_number": 2,
                "bull_argument": "US intelligence consensus puts Taiwan conflict probability at under 5% in the next 5 years. Arizona fab will produce 3nm chips by 2028, providing geographic diversification. Intel IFS is still 2 generations behind. TSM's technology lead is WIDENING, not closing. N2 process node in 2025 has no competitor equivalent until 2028.",
                "bear_argument": "Probability-weighted loss on a 5% Taiwan scenario is catastrophic — the position goes to zero. Arizona fab produces less than 5% of TSM capacity. Sentiment score of 0.43 confirms market nervousness about geopolitical risk. The ADR trades at a persistent discount to the Taiwan-listed shares for a reason.",
            },
            {
                "round_number": 3,
                "bull_argument": "Every portfolio has tail risks. By that logic, no defense contractor, no oil company, no global bank should be investable. TSM's monopoly on advanced manufacturing is the strongest competitive moat in technology. Buffett held TSM and only sold for portfolio concentration reasons, not fundamental thesis deterioration.",
                "bear_argument": "Comparing TSM's geopolitical risk to normal business risks is a false equivalence. A Taiwan crisis simultaneously destroys the stock AND the global semiconductor supply chain — there is no hedge. Buffett sold his entire position within one quarter. The sentiment score is the lowest of any candidate in this pipeline run.",
            },
        ],
        "outcome": "disagreement",
        "bull_model": "claude-sonnet",
        "bear_model": "gemini-pro",
        "jury_triggered": True,
    })

    # AAPL debate (2 rounds, disagreement -> jury)
    transcripts.append({
        "pipeline_run_id": PIPELINE_RUN_IDS["AAPL_1"],
        "ticker": "AAPL US Equity",
        "timestamp": _ts(days_ago=0),
        "rounds": [
            {
                "round_number": 1,
                "bull_argument": "AAPL's Services segment now generates $96B annually at 25%+ margins, creating a recurring revenue base that justifies premium valuation. iPhone 18 AI features (on-device Siri 2.0, generative photo/video) will drive the largest upgrade cycle since iPhone 6. India manufacturing ramp reduces China dependency. At $264.58, the $3.2T market cap is supported by $110B in annual FCF.",
                "bear_argument": "At 32x forward earnings, AAPL is priced for flawless execution. iPhone units have been flat for 3 years. China revenue declined 8% last quarter as Huawei gains share. The EU Digital Markets Act forces App Store sideloading, threatening the highest-margin business. AI features are 12-18 months behind Google and Samsung implementations.",
            },
            {
                "round_number": 2,
                "bull_argument": "iPhone installed base of 1.2B creates unmatched monetization opportunity through Services. The privacy-focused AI approach will win enterprise adoption. App Store threats are overblown — the 85% of users who have never sideloaded won't start now. Share buyback of $90B/year reduces float by 3-4% annually, creating mechanical EPS growth.",
                "bear_argument": "Buyback-driven EPS growth masks underlying business stagnation. Services growth is decelerating from 16% to 12%. The China market is structurally impaired as Huawei's Kirin chipsets reach parity. Regulatory headwinds are global, not just EU. At 32x, any earnings miss results in significant multiple compression.",
            },
        ],
        "outcome": "disagreement",
        "bull_model": "claude-sonnet",
        "bear_model": "gemini-pro",
        "jury_triggered": True,
    })

    return transcripts


# ---------------------------------------------------------------------------
# Trade Recommendations (5 pending + 3 completed)
# ---------------------------------------------------------------------------

def generate_recommendations() -> list[dict]:
    """5 pending + 3 completed trade recommendations."""
    recs = []

    # 5 pending
    pending_tickers = [
        ("MSFT", 0.74, "APPROVE", 0.08, "BUY"),
        ("AMZN", 0.68, "APPROVE", 0.07, "BUY"),
        ("TSLA", 0.52, "NEUTRAL", 0.04, "HOLD"),
        ("AMD", 0.71, "APPROVE", 0.06, "BUY"),
        ("NFLX", 0.50, "NEUTRAL", 0.0, "HOLD"),
    ]

    for i, (ticker, composite, verdict, size, direction) in enumerate(pending_tickers):
        recs.append({
            "id": f"rec-pending-{i+1:03d}",
            "timestamp": _ts(days_ago=random.randint(0, 2)),
            "ticker": f"{ticker} US Equity",
            "direction": direction,
            "confidence": composite,
            "pipeline_run_id": str(uuid.uuid4()),
            "wasden_verdict": verdict,
            "quant_composite": composite,
            "recommended_position_size": size,
            "status": "pending",
            "review_note": None,
            "reviewed_by": None,
            "reviewed_at": None,
        })

    # 3 completed (matching journal entries)
    completed = [
        ("NVDA", PIPELINE_RUN_IDS["NVDA_1"], 0.715, "APPROVE", 0.08, "BUY", "approved", "Strong conviction BUY. Jury 7-2-1.", "Jared"),
        ("PYPL", PIPELINE_RUN_IDS["PYPL_1"], 0.60, "APPROVE", 0.06, "BUY", "approved", "Value play approved.", "Joe"),
        ("XOM", PIPELINE_RUN_IDS["XOM_1"], 0.508, "VETO", 0.0, "BUY", "rejected", "Wasden VETO. Respecting highest authority.", "System"),
    ]

    for i, (ticker, run_id, composite, verdict, size, direction, status, note, reviewer) in enumerate(completed):
        recs.append({
            "id": f"rec-completed-{i+1:03d}",
            "timestamp": _ts(days_ago=5 - i),
            "ticker": f"{ticker} US Equity",
            "direction": direction,
            "confidence": composite,
            "pipeline_run_id": run_id,
            "wasden_verdict": verdict,
            "quant_composite": composite,
            "recommended_position_size": size,
            "status": status,
            "review_note": note,
            "reviewed_by": reviewer,
            "reviewed_at": _ts(days_ago=5 - i, hours=-1),
        })

    return recs


# ---------------------------------------------------------------------------
# Portfolio Positions (5 open, 3 closed)
# ---------------------------------------------------------------------------

def generate_positions() -> list[dict]:
    """8 portfolio positions (5 open, 3 closed)."""
    positions = []

    # 5 open positions
    open_positions = [
        ("NVDA", "long", 188.45, BLOOMBERG_PRICES["NVDA"], 53, 5, PIPELINE_RUN_IDS["NVDA_1"]),
        ("PYPL", "long", 41.30, BLOOMBERG_PRICES["PYPL"], 145, 4, PIPELINE_RUN_IDS["PYPL_1"]),
        ("TSM", "long", 369.80, BLOOMBERG_PRICES["TSM"], 14, 2, PIPELINE_RUN_IDS["TSM_1"]),
        ("MSFT", "long", 390.50, BLOOMBERG_PRICES["MSFT"], 20, 15, None),
        ("AMZN", "long", 205.30, BLOOMBERG_PRICES["AMZN"], 38, 12, None),
    ]

    for i, (ticker, direction, entry, current, qty, days, run_id) in enumerate(open_positions):
        pnl = (current - entry) * qty
        pnl_pct = ((current - entry) / entry) * 100
        positions.append({
            "id": f"pos-{i+1:03d}",
            "ticker": f"{ticker} US Equity",
            "direction": direction,
            "entry_price": entry,
            "current_price": current,
            "quantity": qty,
            "entry_date": _date_str(days),
            "exit_date": None,
            "exit_price": None,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "status": "open",
            "pipeline_run_id": run_id,
        })

    # 3 closed positions
    closed_positions = [
        ("AMD", "long", 192.10, 200.15, 30, 20, 8, None),
        ("NFLX", "long", 82.40, 78.67, 80, 18, 6, None),
        ("AAPL", "long", 258.20, 264.58, 25, 25, 10, None),
    ]

    for i, (ticker, direction, entry, exit_p, qty, entry_days, exit_days, run_id) in enumerate(closed_positions):
        pnl = (exit_p - entry) * qty
        pnl_pct = ((exit_p - entry) / entry) * 100
        positions.append({
            "id": f"pos-closed-{i+1:03d}",
            "ticker": f"{ticker} US Equity",
            "direction": direction,
            "entry_price": entry,
            "current_price": exit_p,
            "quantity": qty,
            "entry_date": _date_str(entry_days),
            "exit_date": _date_str(exit_days),
            "exit_price": exit_p,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "status": "closed",
            "pipeline_run_id": run_id,
        })

    return positions


# ---------------------------------------------------------------------------
# Risk Alerts (2 warning, 1 critical, 3 info)
# ---------------------------------------------------------------------------

def generate_risk_alerts() -> list[dict]:
    """6 risk alerts: 2 warning, 1 critical, 3 info."""
    alerts = [
        {
            "id": "alert-001",
            "timestamp": _ts(days_ago=0, hours=2),
            "severity": "critical",
            "title": "Sector Concentration Exceeded",
            "message": "Technology sector represents 42% of portfolio value, exceeding the 40% concentration limit. AAPL BUY blocked. Reduce tech exposure or request override.",
            "rule_violated": "sector_concentration",
            "ticker": "AAPL US Equity",
            "acknowledged": False,
            "acknowledged_by": None,
            "acknowledged_at": None,
        },
        {
            "id": "alert-002",
            "timestamp": _ts(days_ago=1),
            "severity": "warning",
            "title": "Consecutive Loss Warning",
            "message": "2 consecutive losing trades detected (NFLX, AMD closed positions). Warning threshold is 7. Monitor closely.",
            "rule_violated": "consecutive_loss_tracker",
            "ticker": None,
            "acknowledged": False,
            "acknowledged_by": None,
            "acknowledged_at": None,
        },
        {
            "id": "alert-003",
            "timestamp": _ts(days_ago=1, hours=3),
            "severity": "warning",
            "title": "Wasden Veto Overridden",
            "message": "XOM US Equity Wasden VETO was overridden by Jared. Override reason: 'Short-term energy sector catalyst from OPEC meeting.' Tracking outcome.",
            "rule_violated": "veto_override",
            "ticker": "XOM US Equity",
            "acknowledged": True,
            "acknowledged_by": "Joe",
            "acknowledged_at": _ts(days_ago=1, hours=1),
        },
        {
            "id": "alert-004",
            "timestamp": _ts(days_ago=2),
            "severity": "info",
            "title": "Jury Escalation to Human",
            "message": "TSM US Equity jury vote resulted in 5-5 tie. Escalated to Jared for manual decision per system rules.",
            "rule_violated": None,
            "ticker": "TSM US Equity",
            "acknowledged": True,
            "acknowledged_by": "Jared",
            "acknowledged_at": _ts(days_ago=2, hours=-1),
        },
        {
            "id": "alert-005",
            "timestamp": _ts(days_ago=3),
            "severity": "info",
            "title": "Screening Pipeline Completed",
            "message": "Daily screening funnel completed: 500 -> 118 -> 47 -> 14 -> 8 -> 5 final candidates. Duration: 342 seconds.",
            "rule_violated": None,
            "ticker": None,
            "acknowledged": True,
            "acknowledged_by": "System",
            "acknowledged_at": _ts(days_ago=3),
        },
        {
            "id": "alert-006",
            "timestamp": _ts(days_ago=5),
            "severity": "info",
            "title": "Paper Trading Mode Active",
            "message": "System is running in PAPER trading mode. All executions are simulated. No real money at risk.",
            "rule_violated": None,
            "ticker": None,
            "acknowledged": True,
            "acknowledged_by": "System",
            "acknowledged_at": _ts(days_ago=5),
        },
    ]
    return alerts


def generate_consecutive_loss_streak() -> dict:
    """Current consecutive loss streak tracker."""
    return {
        "current_streak": 2,
        "warning_threshold": 7,
        "shutdown_threshold": 7,
        "is_warning": False,
        "is_shutdown": False,
        "last_loss_date": _date_str(6),
        "streak_tickers": ["NFLX US Equity", "AMD US Equity"],
    }


# ---------------------------------------------------------------------------
# Bias Metrics (4 weeks)
# ---------------------------------------------------------------------------

def generate_bias_metrics() -> list[dict]:
    """4 weeks of bias monitoring data."""
    metrics = []
    for w in range(4):
        week_start = _date_str(7 * (3 - w) + 7)
        week_end = _date_str(7 * (3 - w))
        metrics.append({
            "id": f"bias-week-{w+1:02d}",
            "week_start": week_start,
            "week_end": week_end,
            "wasden_approve_count": [3, 4, 2, 3][w],
            "wasden_neutral_count": [2, 1, 3, 2][w],
            "wasden_veto_count": [1, 1, 2, 1][w],
            "model_agreement_rate": [0.78, 0.82, 0.71, 0.80][w],
            "sector_concentration": {
                "Technology": [3, 4, 2, 3][w],
                "Energy": [1, 0, 2, 1][w],
                "Consumer Discretionary": [1, 1, 1, 0][w],
                "Financials": [0, 1, 0, 1][w],
                "Semiconductors": [1, 0, 2, 1][w],
            },
            "paper_pnl_vs_spy": [1.2, -0.3, 0.8, 1.5][w],
            "api_cost_actual": [42.50, 38.20, 51.80, 45.60][w],
            "api_cost_budget": 37.50,  # $150/month / 4 weeks
            "consecutive_loss_count": [0, 1, 2, 2][w],
            "veto_override_count": [0, 0, 1, 0][w],
        })
    return metrics


# ---------------------------------------------------------------------------
# Screening Runs (3 runs)
# ---------------------------------------------------------------------------

def generate_screening_runs() -> list[dict]:
    """3 screening runs with funnel: 500 -> ~120 -> ~45 -> ~15 -> ~8 -> 5."""
    runs = []

    runs.append({
        "id": "screen-001",
        "timestamp": _ts(days_ago=0, hours=6),
        "stages": [
            {"stage_name": "Universe", "input_count": 500, "output_count": 500, "criteria": "S&P 500 constituents"},
            {"stage_name": "Liquidity Filter", "input_count": 500, "output_count": 118, "criteria": "ADV > $10M, market cap > $5B"},
            {"stage_name": "Fundamental Screen", "input_count": 118, "output_count": 47, "criteria": "PEG < 2.0, FCF yield > 3%, Piotroski >= 5"},
            {"stage_name": "Quant Model Filter", "input_count": 47, "output_count": 14, "criteria": "Composite score > 0.55, low disagreement"},
            {"stage_name": "Wasden Watch", "input_count": 14, "output_count": 8, "criteria": "Wasden verdict != VETO"},
            {"stage_name": "Final Selection", "input_count": 8, "output_count": 5, "criteria": "Top 5 by composite * Wasden confidence"},
        ],
        "final_candidates": ["NVDA US Equity", "MSFT US Equity", "AMZN US Equity", "AMD US Equity", "TSM US Equity"],
        "pipeline_run_ids": [
            PIPELINE_RUN_IDS["NVDA_1"],
            str(uuid.UUID("11111111-2222-3333-4444-555555555501")),
            str(uuid.UUID("11111111-2222-3333-4444-555555555502")),
            str(uuid.UUID("11111111-2222-3333-4444-555555555503")),
            PIPELINE_RUN_IDS["TSM_1"],
        ],
        "duration_seconds": 342.7,
        "model_used": "claude-haiku",
    })

    runs.append({
        "id": "screen-002",
        "timestamp": _ts(days_ago=1, hours=6),
        "stages": [
            {"stage_name": "Universe", "input_count": 500, "output_count": 500, "criteria": "S&P 500 constituents"},
            {"stage_name": "Liquidity Filter", "input_count": 500, "output_count": 122, "criteria": "ADV > $10M, market cap > $5B"},
            {"stage_name": "Fundamental Screen", "input_count": 122, "output_count": 44, "criteria": "PEG < 2.0, FCF yield > 3%, Piotroski >= 5"},
            {"stage_name": "Quant Model Filter", "input_count": 44, "output_count": 16, "criteria": "Composite score > 0.55, low disagreement"},
            {"stage_name": "Wasden Watch", "input_count": 16, "output_count": 9, "criteria": "Wasden verdict != VETO"},
            {"stage_name": "Final Selection", "input_count": 9, "output_count": 5, "criteria": "Top 5 by composite * Wasden confidence"},
        ],
        "final_candidates": ["PYPL US Equity", "NVDA US Equity", "XOM US Equity", "AAPL US Equity", "TSLA US Equity"],
        "pipeline_run_ids": [
            PIPELINE_RUN_IDS["PYPL_1"],
            PIPELINE_RUN_IDS["NVDA_1"],
            PIPELINE_RUN_IDS["XOM_1"],
            PIPELINE_RUN_IDS["AAPL_1"],
            str(uuid.UUID("11111111-2222-3333-4444-555555555504")),
        ],
        "duration_seconds": 318.4,
        "model_used": "claude-haiku",
    })

    runs.append({
        "id": "screen-003",
        "timestamp": _ts(days_ago=3, hours=6),
        "stages": [
            {"stage_name": "Universe", "input_count": 500, "output_count": 500, "criteria": "S&P 500 constituents"},
            {"stage_name": "Liquidity Filter", "input_count": 500, "output_count": 115, "criteria": "ADV > $10M, market cap > $5B"},
            {"stage_name": "Fundamental Screen", "input_count": 115, "output_count": 42, "criteria": "PEG < 2.0, FCF yield > 3%, Piotroski >= 5"},
            {"stage_name": "Quant Model Filter", "input_count": 42, "output_count": 13, "criteria": "Composite score > 0.55, low disagreement"},
            {"stage_name": "Wasden Watch", "input_count": 13, "output_count": 7, "criteria": "Wasden verdict != VETO"},
            {"stage_name": "Final Selection", "input_count": 7, "output_count": 5, "criteria": "Top 5 by composite * Wasden confidence"},
        ],
        "final_candidates": ["AMZN US Equity", "MSFT US Equity", "NVDA US Equity", "NFLX US Equity", "PYPL US Equity"],
        "pipeline_run_ids": [
            str(uuid.UUID("11111111-2222-3333-4444-555555555505")),
            str(uuid.UUID("11111111-2222-3333-4444-555555555506")),
            PIPELINE_RUN_IDS["NVDA_1"],
            PIPELINE_RUN_IDS["NFLX_1"],
            PIPELINE_RUN_IDS["PYPL_1"],
        ],
        "duration_seconds": 297.1,
        "model_used": "claude-haiku",
    })

    return runs


# ---------------------------------------------------------------------------
# System Settings
# ---------------------------------------------------------------------------

def generate_system_settings() -> list[dict]:
    """All system settings including risk constants."""
    settings = [
        # Risk constants (read-only, require approval)
        {"key": "MAX_POSITION_PCT", "value": "0.12", "category": "risk", "description": "Maximum single position as fraction of portfolio", "editable": False, "requires_approval": True},
        {"key": "RISK_PER_TRADE_PCT", "value": "0.015", "category": "risk", "description": "Maximum risk per trade as fraction of portfolio", "editable": False, "requires_approval": True},
        {"key": "MIN_CASH_RESERVE_PCT", "value": "0.10", "category": "risk", "description": "Minimum cash reserve as fraction of portfolio", "editable": False, "requires_approval": True},
        {"key": "MAX_CORRELATED_POSITIONS", "value": "3", "category": "risk", "description": "Maximum number of correlated positions allowed", "editable": False, "requires_approval": True},
        {"key": "CORRELATION_THRESHOLD", "value": "0.70", "category": "risk", "description": "Correlation coefficient threshold for position grouping", "editable": False, "requires_approval": True},
        {"key": "STRESS_CORRELATION_THRESHOLD", "value": "0.80", "category": "risk", "description": "Stress scenario correlation threshold", "editable": False, "requires_approval": True},
        {"key": "REGIME_CIRCUIT_BREAKER_SPY_DROP", "value": "0.05", "category": "risk", "description": "SPY 5-day rolling drop to trigger circuit breaker", "editable": False, "requires_approval": True},
        {"key": "DEFENSIVE_POSITION_REDUCTION", "value": "0.50", "category": "risk", "description": "Position reduction during defensive regime", "editable": False, "requires_approval": True},
        {"key": "DEFENSIVE_CASH_TARGET", "value": "0.40", "category": "risk", "description": "Target cash allocation during defensive regime", "editable": False, "requires_approval": True},
        {"key": "HIGH_MODEL_DISAGREEMENT_THRESHOLD", "value": "0.50", "category": "risk", "description": "Std dev threshold for high model disagreement flag", "editable": False, "requires_approval": True},
        {"key": "SLIPPAGE_ADV_THRESHOLD", "value": "0.01", "category": "risk", "description": "ADV fraction threshold for slippage modeling", "editable": False, "requires_approval": True},
        {"key": "SLIPPAGE_PER_ADV_PCT", "value": "0.001", "category": "risk", "description": "Slippage per 1% of ADV", "editable": False, "requires_approval": True},
        # System settings
        {"key": "CONSECUTIVE_LOSS_WARNING", "value": "7", "category": "system", "description": "Number of consecutive losses before warning triggers", "editable": False, "requires_approval": True},
        {"key": "API_MONTHLY_BUDGET", "value": "150.00", "category": "system", "description": "Monthly API cost budget in USD", "editable": True, "requires_approval": True},
        {"key": "SCREENING_UNIVERSE_SIZE", "value": "500", "category": "pipeline", "description": "Number of stocks in initial screening universe", "editable": True, "requires_approval": False},
        {"key": "FINAL_CANDIDATE_COUNT", "value": "5", "category": "pipeline", "description": "Number of stocks selected after full screening funnel", "editable": True, "requires_approval": False},
        {"key": "JURY_SIZE", "value": "10", "category": "pipeline", "description": "Number of agents in the jury ensemble", "editable": False, "requires_approval": True},
        {"key": "JURY_MAJORITY_THRESHOLD", "value": "6", "category": "pipeline", "description": "Minimum votes for a decisive jury outcome", "editable": False, "requires_approval": True},
        {"key": "DATA_STALE_DAYS", "value": "7", "category": "data", "description": "Days after which data is flagged as stale", "editable": True, "requires_approval": False},
        {"key": "DATA_EXPIRED_DAYS", "value": "30", "category": "data", "description": "Days after which data is excluded from live decisions", "editable": True, "requires_approval": False},
    ]
    return settings


# ---------------------------------------------------------------------------
# Veto Override Records (1 pending, 1 approved, 1 rejected)
# ---------------------------------------------------------------------------

def generate_veto_overrides() -> list[dict]:
    """3 veto override records."""
    overrides = [
        {
            "id": "override-001",
            "timestamp": _ts(days_ago=0),
            "ticker": "XOM US Equity",
            "original_verdict": "VETO",
            "override_reason": "Short-term catalyst: OPEC emergency meeting expected to announce production cuts. Energy sector momentum diverging from Wasden's medium-term bearish view.",
            "overridden_by": "Jared",
            "pipeline_run_id": PIPELINE_RUN_IDS["XOM_1"],
            "outcome_tracked": False,
            "status": "pending",
        },
        {
            "id": "override-002",
            "timestamp": _ts(days_ago=10),
            "ticker": "NFLX US Equity",
            "original_verdict": "VETO",
            "override_reason": "Wasden coverage was from 6 months ago. NFLX fundamentals have materially improved since then: ad tier revenue exceeded expectations, password sharing crackdown complete.",
            "overridden_by": "Joe",
            "pipeline_run_id": str(uuid.UUID("22222222-3333-4444-5555-666666666601")),
            "outcome_tracked": True,
            "status": "approved",
        },
        {
            "id": "override-003",
            "timestamp": _ts(days_ago=15),
            "ticker": "TSLA US Equity",
            "original_verdict": "VETO",
            "override_reason": "Robotaxi announcement imminent. Market is underpricing autonomous driving optionality.",
            "overridden_by": "Jared",
            "pipeline_run_id": str(uuid.UUID("22222222-3333-4444-5555-666666666602")),
            "outcome_tracked": True,
            "status": "rejected",
        },
    ]
    return overrides


# ---------------------------------------------------------------------------
# API Status (mock connectivity checks)
# ---------------------------------------------------------------------------

def generate_api_statuses() -> list[dict]:
    """Mock API connectivity statuses."""
    return [
        {"name": "Supabase", "connected": True, "latency_ms": 45.2, "last_checked": _ts()},
        {"name": "Claude API", "connected": True, "latency_ms": 320.5, "last_checked": _ts()},
        {"name": "Gemini API", "connected": True, "latency_ms": 280.1, "last_checked": _ts()},
        {"name": "Alpaca (Paper)", "connected": True, "latency_ms": 89.7, "last_checked": _ts()},
        {"name": "Alpaca (Live)", "connected": False, "latency_ms": None, "last_checked": _ts()},
        {"name": "Finnhub", "connected": True, "latency_ms": 156.3, "last_checked": _ts()},
        {"name": "NewsAPI", "connected": True, "latency_ms": 201.8, "last_checked": _ts()},
    ]


# ---------------------------------------------------------------------------
# Portfolio Summary (computed from positions + snapshots)
# ---------------------------------------------------------------------------

def generate_portfolio_summary() -> dict:
    """Computed portfolio summary."""
    positions = generate_positions()
    open_pos = [p for p in positions if p["status"] == "open"]
    closed_pos = [p for p in positions if p["status"] == "closed"]

    total_invested = sum(p["current_price"] * p["quantity"] for p in open_pos)
    total_pnl = sum(p["pnl"] for p in positions)
    winning = [p for p in closed_pos if p["pnl"] > 0]
    losing = [p for p in closed_pos if p["pnl"] <= 0]

    snapshots = generate_portfolio_snapshots()
    latest = snapshots[-1]

    return {
        "total_value": latest["portfolio_value"],
        "cash_balance": latest["cash_balance"],
        "invested_value": round(total_invested, 2),
        "daily_pnl": latest["daily_pnl"],
        "daily_pnl_pct": latest["daily_pnl_pct"],
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round((total_pnl / 100_000) * 100, 2),
        "win_rate": round(len(winning) / max(len(closed_pos), 1) * 100, 1),
        "total_trades": len(closed_pos),
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "open_positions": len(open_pos),
        "closed_positions": len(closed_pos),
    }


# ---------------------------------------------------------------------------
# Jury Stats (aggregate)
# ---------------------------------------------------------------------------

def generate_jury_stats() -> dict:
    """Aggregate jury statistics across all sessions."""
    entries = generate_journal_entries()
    jury_sessions = [e for e in entries if e["jury"]["spawned"]]

    total_votes = 0
    buy_votes = 0
    sell_votes = 0
    hold_votes = 0
    decisive_count = 0
    escalation_count = 0
    majority_sizes = []

    for entry in jury_sessions:
        jury = entry["jury"]
        votes = jury["votes"]
        total_votes += len(votes)
        fc = jury["final_count"]
        buy_votes += fc["buy"]
        sell_votes += fc["sell"]
        hold_votes += fc["hold"]

        max_votes = max(fc["buy"], fc["sell"], fc["hold"])
        majority_sizes.append(max_votes)

        if max_votes >= 6:
            decisive_count += 1
        if jury["escalated_to_human"]:
            escalation_count += 1

    total_sessions = len(jury_sessions)

    return {
        "total_jury_sessions": total_sessions,
        "total_votes_cast": total_votes,
        "buy_votes": buy_votes,
        "sell_votes": sell_votes,
        "hold_votes": hold_votes,
        "agreement_rate": round(decisive_count / max(total_sessions, 1), 2),
        "escalation_count": escalation_count,
        "average_majority_size": round(
            sum(majority_sizes) / max(len(majority_sizes), 1), 1
        ),
    }


# ---------------------------------------------------------------------------
# Piotroski Mock (Week 3)
# ---------------------------------------------------------------------------

MOCK_PIOTROSKI = {
    "NVDA": {"score": 7, "max_possible": 9, "ratio": 0.778, "passes": True},
    "PYPL": {"score": 5, "max_possible": 9, "ratio": 0.556, "passes": True},
    "NFLX": {"score": 6, "max_possible": 9, "ratio": 0.667, "passes": True},
    "TSM": {"score": 4, "max_possible": 4, "ratio": 1.0, "passes": True},
    "XOM": {"score": 3, "max_possible": 9, "ratio": 0.333, "passes": False},
    "AAPL": {"score": 8, "max_possible": 9, "ratio": 0.889, "passes": True},
    "MSFT": {"score": 7, "max_possible": 9, "ratio": 0.778, "passes": True},
    "AMZN": {"score": 6, "max_possible": 9, "ratio": 0.667, "passes": True},
    "TSLA": {"score": 4, "max_possible": 9, "ratio": 0.444, "passes": False},
    "AMD": {"score": 5, "max_possible": 9, "ratio": 0.556, "passes": True},
}

MOCK_SIGNALS = [
    {"name": "roa_positive", "value": 1, "data_available": True, "detail": "EPS > 0"},
    {"name": "operating_cash_flow_positive", "value": 1, "data_available": True, "detail": "FCF > 0"},
    {"name": "roa_improving", "value": 0, "data_available": False, "detail": "Prior period not available"},
    {"name": "accrual_quality", "value": 1, "data_available": True, "detail": "FCF>0 & OpMargin>0"},
    {"name": "leverage_decreasing", "value": 0, "data_available": False, "detail": "Prior period not available"},
    {"name": "current_ratio_improving", "value": 0, "data_available": False, "detail": "Prior period not available"},
    {"name": "no_dilution", "value": 0, "data_available": False, "detail": "Shares data not available"},
    {"name": "gross_margin_improving", "value": 0, "data_available": False, "detail": "Prior period not available"},
    {"name": "asset_turnover_improving", "value": 1, "data_available": True, "detail": "Revenue growth > 0"},
]


def generate_piotroski_mock(ticker: str) -> dict:
    """Generate mock Piotroski score for a ticker."""
    data = MOCK_PIOTROSKI.get(ticker, {"score": 5, "max_possible": 9, "ratio": 0.556, "passes": True})
    return {
        "ticker": ticker,
        "score": data["score"],
        "max_possible": data["max_possible"],
        "ratio": data["ratio"],
        "passes_threshold": data["passes"],
        "data_available": True,
        "signals": MOCK_SIGNALS,
    }


def generate_tier1_preview() -> list[dict]:
    """Preview Tier 1 liquidity filter results."""
    results = []
    mock_caps = {
        "NVDA": 4_650_000_000_000, "PYPL": 73_000_000_000,
        "NFLX": 340_000_000_000, "TSM": 960_000_000_000,
        "XOM": 508_000_000_000, "AAPL": 3_940_000_000_000,
    }
    for ticker in PILOT_TICKERS:
        cap = mock_caps.get(ticker, 50_000_000_000)
        passed = cap >= 5_000_000_000
        results.append({
            "ticker": ticker,
            "passed": passed,
            "fail_reasons": [] if passed else [f"market_cap ${cap:,.0f} < $5B"],
            "metrics": {"market_cap": cap},
        })
    return results


def generate_tier2_preview() -> list[dict]:
    """Preview Tier 2 Sprinkle Sauce filter results."""
    results = []
    mock_data = {
        "NVDA": {"peg": 1.22, "fcf_yield": 2.8, "piotroski": 7, "passed": False, "fail": "FCF yield 2.80% < 3%"},
        "PYPL": {"peg": 0.95, "fcf_yield": 8.1, "piotroski": 5, "passed": True, "fail": ""},
        "NFLX": {"peg": 1.65, "fcf_yield": 4.2, "piotroski": 6, "passed": True, "fail": ""},
        "TSM": {"peg": 1.35, "fcf_yield": 3.5, "piotroski": 4, "passed": True, "fail": ""},
        "XOM": {"peg": 3.10, "fcf_yield": 7.2, "piotroski": 3, "passed": False, "fail": "PEG 3.10 >= 2.0; Piotroski 3/9"},
        "AAPL": {"peg": 1.80, "fcf_yield": 3.8, "piotroski": 8, "passed": True, "fail": ""},
    }
    for ticker in PILOT_TICKERS:
        d = mock_data.get(ticker, {"peg": 1.5, "fcf_yield": 4.0, "piotroski": 5, "passed": True, "fail": ""})
        results.append({
            "ticker": ticker,
            "passed": d["passed"],
            "fail_reasons": [d["fail"]] if d["fail"] else [],
            "metrics": {
                "peg_ratio": d["peg"],
                "fcf_yield": d["fcf_yield"],
                "piotroski_score": d["piotroski"],
                "piotroski_max": 9,
                "piotroski_ratio": round(d["piotroski"] / 9, 3),
            },
        })
    return results


# ---------------------------------------------------------------------------
# Risk Engine Mocks (Week 8)
# ---------------------------------------------------------------------------

def generate_risk_check_mock(ticker: str = "NVDA", position_pct: float = 0.05) -> dict:
    """Mock risk check results for a proposed trade."""
    return {
        "passed": True,
        "checks_failed": [],
        "details": [
            {"check_name": "position_size", "passed": True, "detail": f"Proposed {position_pct:.1%} of portfolio", "value": position_pct, "threshold": 0.12},
            {"check_name": "cash_reserve", "passed": True, "detail": "Post-trade cash 30.0% of portfolio", "value": 0.30, "threshold": 0.10},
            {"check_name": "correlation", "passed": True, "detail": "0 correlated positions (threshold 0.70, max 3)", "value": 0, "threshold": 3},
            {"check_name": "stress_correlation", "passed": True, "detail": "0 tickers with stress correlation >= 0.80", "value": 0, "threshold": 0},
            {"check_name": "sector_concentration", "passed": True, "detail": "Technology sector: 25.0% of portfolio", "value": 0.25, "threshold": 0.40},
            {"check_name": "gap_risk", "passed": True, "detail": "Gap risk score 0.15", "value": 0.15, "threshold": 0.70},
            {"check_name": "model_disagreement", "passed": True, "detail": "Model std_dev 0.060", "value": 0.06, "threshold": 0.50},
        ],
    }


def generate_circuit_breaker_mock() -> dict:
    """Mock circuit breaker status (inactive)."""
    return {
        "active": False,
        "triggered_at": None,
        "spy_5day_return": -0.012,
        "actions_taken": [],
        "resolved_at": None,
        "resolved_by": None,
    }


def generate_stress_tests_mock() -> list[dict]:
    """Mock stress test results for all 5 scenarios."""
    scenarios = [
        {"name": "covid_crash", "desc": "COVID-19 pandemic crash", "period": "Feb-March 2020", "spy": -0.339, "days": 33, "loss": -0.284, "loss_dollar": -28400},
        {"name": "bear_2022", "desc": "2022 bear market", "period": "Jan-Oct 2022", "spy": -0.254, "days": 282, "loss": -0.218, "loss_dollar": -21800},
        {"name": "regional_banking", "desc": "Regional banking crisis", "period": "March 2023", "spy": -0.078, "days": 14, "loss": -0.062, "loss_dollar": -6200},
        {"name": "black_monday_1987", "desc": "Black Monday crash", "period": "October 19, 1987", "spy": -0.205, "days": 1, "loss": -0.192, "loss_dollar": -19200},
        {"name": "financial_crisis_2008", "desc": "2008 financial crisis", "period": "Oct 2007-March 2009", "spy": -0.568, "days": 517, "loss": -0.485, "loss_dollar": -48500},
    ]
    results = []
    for s in scenarios:
        results.append({
            "scenario_name": s["name"],
            "description": s["desc"],
            "period": s["period"],
            "spy_drawdown": s["spy"],
            "duration_days": s["days"],
            "portfolio_loss": s["loss_dollar"],
            "portfolio_loss_pct": s["loss"],
            "position_impacts": [
                {"ticker": "NVDA", "sector": "Technology", "current_value": 28473, "sector_multiplier": 0.85, "estimated_loss": round(s["spy"] * 0.85 * 28473, 2), "estimated_loss_pct": round(s["spy"] * 0.85 * 100, 2)},
                {"ticker": "PYPL", "sector": "Technology", "current_value": 12495, "sector_multiplier": 0.85, "estimated_loss": round(s["spy"] * 0.85 * 12495, 2), "estimated_loss_pct": round(s["spy"] * 0.85 * 100, 2)},
            ],
            "surviving": True,
        })
    return results


def generate_consecutive_loss_mock() -> dict:
    """Mock consecutive loss counter state."""
    return {
        "current_streak": -2,
        "consecutive_losses": 2,
        "warning_threshold": 7,
        "warning_active": False,
        "entries_paused": False,
        "paused_at": None,
        "streak_tickers": ["NFLX US Equity", "AMD US Equity"],
        "last_result_date": _ts(days_ago=6),
        "resumed_by": None,
        "resumed_at": None,
    }


def generate_orders_mock() -> list[dict]:
    """Mock order records."""
    return [
        {
            "id": "ord-001",
            "ticker": "NVDA",
            "side": "buy",
            "quantity": 150,
            "price": 189.82,
            "state": "filled",
            "alpaca_order_id": "sim-abc123def456",
            "fill_price": 189.84,
            "filled_quantity": 150,
            "slippage": 3.00,
            "risk_check_result": {"passed": True, "checks_failed": []},
            "pre_trade_result": {"passed": True, "checks_failed": []},
            "state_history": [
                {"from_state": "submitted", "to_state": "pending", "timestamp": _ts(days_ago=5), "reason": "simulated"},
                {"from_state": "pending", "to_state": "filled", "timestamp": _ts(days_ago=5), "reason": "simulated fill"},
            ],
            "created_at": _ts(days_ago=5),
            "updated_at": _ts(days_ago=5),
        },
        {
            "id": "ord-002",
            "ticker": "PYPL",
            "side": "buy",
            "quantity": 300,
            "price": 41.65,
            "state": "filled",
            "alpaca_order_id": "sim-def456ghi789",
            "fill_price": 41.66,
            "filled_quantity": 300,
            "slippage": 3.00,
            "risk_check_result": {"passed": True, "checks_failed": []},
            "pre_trade_result": {"passed": True, "checks_failed": []},
            "state_history": [
                {"from_state": "submitted", "to_state": "pending", "timestamp": _ts(days_ago=4), "reason": "simulated"},
                {"from_state": "pending", "to_state": "filled", "timestamp": _ts(days_ago=4), "reason": "simulated fill"},
            ],
            "created_at": _ts(days_ago=4),
            "updated_at": _ts(days_ago=4),
        },
        {
            "id": "ord-003",
            "ticker": "XOM",
            "side": "buy",
            "quantity": 50,
            "price": 147.28,
            "state": "rejected",
            "alpaca_order_id": None,
            "fill_price": None,
            "filled_quantity": 0,
            "slippage": None,
            "risk_check_result": {"passed": False, "checks_failed": ["sector_concentration"]},
            "pre_trade_result": {"passed": True, "checks_failed": []},
            "state_history": [
                {"from_state": "submitted", "to_state": "rejected", "timestamp": _ts(days_ago=2), "reason": "Risk check failed: sector_concentration"},
            ],
            "created_at": _ts(days_ago=2),
            "updated_at": _ts(days_ago=2),
        },
    ]


def generate_account_mock() -> dict:
    """Mock Alpaca account summary."""
    return {
        "portfolio_value": 100000.0,
        "cash": 35000.0,
        "buying_power": 70000.0,
        "equity": 100000.0,
        "trading_mode": "paper",
        "status": "ACTIVE",
        "simulated": True,
    }


# ---------------------------------------------------------------------------
# Quant Model Mock Generators (Week 5)
# ---------------------------------------------------------------------------

def generate_quant_scores_mock(ticker: str) -> dict:
    """Mock quant scores for a single ticker."""
    from src.intelligence.quant_models.mock_scores import get_mock_scores
    import statistics

    scores = get_mock_scores(ticker.upper())
    all_vals = list(scores.values())
    composite = statistics.mean(all_vals)
    std_dev = statistics.stdev(all_vals) if len(all_vals) > 1 else 0.0

    return {
        "xgboost": scores["xgboost"],
        "elastic_net": scores["elastic_net"],
        "arima": scores["arima"],
        "sentiment": scores["sentiment"],
        "composite": round(composite, 4),
        "std_dev": round(std_dev, 4),
        "high_disagreement_flag": std_dev > 0.5,
    }


def generate_quant_status_mock() -> dict:
    """Mock quant model status with manifests."""
    return {
        "models": {
            "xgboost": {
                "model_name": "XGBoostDirectionModel",
                "version": "1.0.0",
                "model_type": "classification",
                "target": "5-day forward return direction",
                "output_range": [0.0, 1.0],
                "parameters": {"n_estimators": 200, "max_depth": 6, "learning_rate": 0.1},
                "trained": False,
                "survivorship_bias_audited": False,
            },
            "elastic_net": {
                "model_name": "ElasticNetDirectionModel",
                "version": "1.0.0",
                "model_type": "regression_sigmoid",
                "target": "5-day forward return direction",
                "output_range": [0.0, 1.0],
                "parameters": {"alpha": 0.1, "l1_ratio": 0.5},
                "trained": False,
                "survivorship_bias_audited": False,
            },
            "arima": {
                "model_name": "ARIMAModel",
                "version": "1.0.0",
                "model_type": "time_series",
                "target": "5-day forward close price (directional confidence)",
                "output_range": [0.0, 1.0],
                "parameters": {"order": [5, 1, 0]},
                "trained": False,
                "survivorship_bias_audited": False,
            },
            "sentiment": {
                "model_name": "SentimentModel",
                "version": "1.0.0",
                "model_type": "sentiment_aggregation",
                "target": "News sentiment (bullish probability)",
                "output_range": [0.0, 1.0],
                "parameters": {"finnhub_weight": 0.6, "newsapi_weight": 0.4},
                "trained": True,
                "survivorship_bias_audited": False,
            },
        },
        "use_mock_data": True,
    }


# ---------------------------------------------------------------------------
# Pipeline Mock Generators (Week 7)
# ---------------------------------------------------------------------------

def generate_pipeline_run_mock(ticker: str = "NVDA") -> dict:
    """Mock a single pipeline run result."""
    from src.pipeline.mock_pipeline import MockDecisionPipeline

    pipeline = MockDecisionPipeline()
    price = BLOOMBERG_PRICES.get(ticker.upper(), 100.0)
    result = pipeline.run(ticker, price)
    # Add pipeline_runs-table compatible fields
    result["started_at"] = result.get("timestamp", _ts())
    result["completed_at"] = result.get("timestamp", _ts())
    result["status"] = "vetoed" if result.get("final_decision", {}).get("action") == "BLOCKED" and "VETO" in result.get("final_decision", {}).get("reason", "") else "completed"
    result["node_journal"] = result.get("node_journal", [])
    return result


def generate_pipeline_runs_mock() -> list[dict]:
    """Mock list of recent pipeline runs."""
    runs = []
    for ticker in PILOT_TICKERS:
        run = generate_pipeline_run_mock(ticker)
        run["id"] = PIPELINE_RUN_IDS.get(f"{ticker}_1", str(uuid.uuid4()))
        runs.append(run)
    return runs
