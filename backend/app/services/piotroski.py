"""
Piotroski F-Score manual calculator.

Computes the 9 binary Piotroski signals from Bloomberg fundamental data.
When only a single snapshot is available (typical for our daily pipeline),
only 3-4 signals are computable. Uses proportional threshold: score / max_possible >= 5/9.

Bloomberg EQS formula documented in KNOWLEDGE_BASE_v2.md Section 9.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger("wasden_watch.piotroski")


@dataclass
class PiotroskiSignal:
    """A single Piotroski binary signal."""
    name: str
    description: str
    value: int  # 0 or 1
    data_available: bool
    detail: str  # human-readable explanation


@dataclass
class PiotroskiScore:
    """Full Piotroski F-Score result."""
    ticker: str
    score: int
    max_possible: int
    ratio: float  # score / max_possible
    passes_threshold: bool  # ratio >= 5/9
    signals: list[PiotroskiSignal]
    data_available: bool  # True if at least 3 signals computable


# The 9 standard Piotroski signals
SIGNAL_NAMES = [
    "roa_positive",
    "operating_cash_flow_positive",
    "roa_improving",
    "accrual_quality",
    "leverage_decreasing",
    "current_ratio_improving",
    "no_dilution",
    "gross_margin_improving",
    "asset_turnover_improving",
]

# Proportional threshold (equivalent to 5/9)
THRESHOLD_RATIO = 5 / 9


def compute_piotroski(
    ticker: str,
    fundamentals: dict,
    prior_fundamentals: dict | None = None,
) -> PiotroskiScore:
    """Compute Piotroski F-Score from Bloomberg fundamentals.

    Args:
        ticker: Stock ticker
        fundamentals: Current period Bloomberg fundamentals dict with keys:
            - roe, eps, fcf, market_cap, gross_margin, current_ratio,
              debt_to_equity, operating_margin, revenue_growth
        prior_fundamentals: Prior period fundamentals (optional). When None,
            only single-snapshot signals are computed.

    Returns:
        PiotroskiScore with per-signal detail.
    """
    signals = []
    has_prior = prior_fundamentals is not None

    # Signal 1: ROA > 0 (proxy via EPS and market cap → ROA estimate)
    eps = fundamentals.get("eps")
    if eps is not None:
        val = 1 if eps > 0 else 0
        signals.append(PiotroskiSignal(
            name="roa_positive",
            description="Net income positive (EPS > 0)",
            value=val,
            data_available=True,
            detail=f"EPS = {eps:.2f}",
        ))
    else:
        signals.append(PiotroskiSignal(
            name="roa_positive", description="Net income positive",
            value=0, data_available=False, detail="EPS data not available",
        ))

    # Signal 2: Operating Cash Flow > 0 (proxy via FCF)
    fcf = fundamentals.get("fcf")
    if fcf is not None:
        val = 1 if fcf > 0 else 0
        signals.append(PiotroskiSignal(
            name="operating_cash_flow_positive",
            description="Operating cash flow positive (FCF > 0)",
            value=val,
            data_available=True,
            detail=f"FCF = {fcf:,.0f}",
        ))
    else:
        signals.append(PiotroskiSignal(
            name="operating_cash_flow_positive",
            description="Operating cash flow positive",
            value=0, data_available=False, detail="FCF data not available",
        ))

    # Signal 3: ROA improving (requires prior period)
    if has_prior and eps is not None and prior_fundamentals.get("eps") is not None:
        prior_eps = prior_fundamentals["eps"]
        val = 1 if eps > prior_eps else 0
        signals.append(PiotroskiSignal(
            name="roa_improving", description="ROA improving YoY",
            value=val, data_available=True,
            detail=f"EPS {prior_eps:.2f} → {eps:.2f}",
        ))
    else:
        signals.append(PiotroskiSignal(
            name="roa_improving", description="ROA improving YoY",
            value=0, data_available=False, detail="Prior period not available",
        ))

    # Signal 4: Accrual quality (OCF > Net Income, proxy: FCF > 0 and positive margin)
    operating_margin = fundamentals.get("operating_margin")
    if fcf is not None and operating_margin is not None:
        val = 1 if fcf > 0 and operating_margin > 0 else 0
        signals.append(PiotroskiSignal(
            name="accrual_quality",
            description="Cash flow exceeds accruals (FCF > 0 & operating margin > 0)",
            value=val,
            data_available=True,
            detail=f"FCF={fcf:,.0f}, OpMargin={operating_margin:.1f}%",
        ))
    else:
        signals.append(PiotroskiSignal(
            name="accrual_quality", description="Accrual quality",
            value=0, data_available=False, detail="Insufficient data",
        ))

    # Signal 5: Leverage decreasing (requires prior period)
    dte = fundamentals.get("debt_to_equity")
    if has_prior and dte is not None and prior_fundamentals.get("debt_to_equity") is not None:
        prior_dte = prior_fundamentals["debt_to_equity"]
        val = 1 if dte < prior_dte else 0
        signals.append(PiotroskiSignal(
            name="leverage_decreasing", description="Leverage decreasing",
            value=val, data_available=True,
            detail=f"D/E {prior_dte:.2f} → {dte:.2f}",
        ))
    else:
        signals.append(PiotroskiSignal(
            name="leverage_decreasing", description="Leverage decreasing",
            value=0, data_available=False, detail="Prior period not available",
        ))

    # Signal 6: Current ratio improving (requires prior period)
    cr = fundamentals.get("current_ratio")
    if has_prior and cr is not None and prior_fundamentals.get("current_ratio") is not None:
        prior_cr = prior_fundamentals["current_ratio"]
        val = 1 if cr > prior_cr else 0
        signals.append(PiotroskiSignal(
            name="current_ratio_improving", description="Current ratio improving",
            value=val, data_available=True,
            detail=f"CR {prior_cr:.2f} → {cr:.2f}",
        ))
    else:
        signals.append(PiotroskiSignal(
            name="current_ratio_improving", description="Current ratio improving",
            value=0, data_available=False, detail="Prior period not available",
        ))

    # Signal 7: No dilution (requires prior period shares outstanding — not in our data)
    signals.append(PiotroskiSignal(
        name="no_dilution", description="No equity dilution",
        value=0, data_available=False,
        detail="Shares outstanding data not available in Bloomberg snapshot",
    ))

    # Signal 8: Gross margin improving (requires prior period)
    gm = fundamentals.get("gross_margin")
    if has_prior and gm is not None and prior_fundamentals.get("gross_margin") is not None:
        prior_gm = prior_fundamentals["gross_margin"]
        val = 1 if gm > prior_gm else 0
        signals.append(PiotroskiSignal(
            name="gross_margin_improving", description="Gross margin improving",
            value=val, data_available=True,
            detail=f"GM {prior_gm:.1f}% → {gm:.1f}%",
        ))
    else:
        signals.append(PiotroskiSignal(
            name="gross_margin_improving", description="Gross margin improving",
            value=0, data_available=False, detail="Prior period not available",
        ))

    # Signal 9: Asset turnover improving (requires prior period revenue & total assets)
    rev_growth = fundamentals.get("revenue_growth")
    if rev_growth is not None:
        val = 1 if rev_growth > 0 else 0
        signals.append(PiotroskiSignal(
            name="asset_turnover_improving",
            description="Asset turnover improving (revenue growth > 0)",
            value=val,
            data_available=True,
            detail=f"Revenue growth = {rev_growth:.1f}%",
        ))
    else:
        signals.append(PiotroskiSignal(
            name="asset_turnover_improving",
            description="Asset turnover improving",
            value=0, data_available=False, detail="Revenue growth not available",
        ))

    # Compute score using only available signals
    available_signals = [s for s in signals if s.data_available]
    max_possible = len(available_signals)
    score = sum(s.value for s in available_signals)
    ratio = score / max_possible if max_possible > 0 else 0.0
    passes = ratio >= THRESHOLD_RATIO

    logger.info(
        f"Piotroski {ticker}: {score}/{max_possible} "
        f"(ratio={ratio:.2f}, threshold={THRESHOLD_RATIO:.2f}, "
        f"passes={passes})"
    )

    return PiotroskiScore(
        ticker=ticker,
        score=score,
        max_possible=max_possible,
        ratio=ratio,
        passes_threshold=passes,
        signals=signals,
        data_available=max_possible >= 3,
    )
