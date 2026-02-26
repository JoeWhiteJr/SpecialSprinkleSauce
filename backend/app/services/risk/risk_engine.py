"""
Risk Engine — 7 sequential risk checks per PROJECT_STANDARDS_v2.md Section 8.

Check order:
1. Position size (MAX_POSITION_PCT)
2. Cash reserve (MIN_CASH_RESERVE_PCT)
3. Correlation (30-day rolling, threshold 0.70)
4. Stress correlation (worst 10 days, threshold 0.80)
5. Sector concentration
6. Gap risk score
7. Model disagreement (std_dev > 0.50)

Returns RiskCheck with pass/fail and per-check detail.
This module is SEPARATE from pre_trade_validation. Never merge.
"""

import logging
from dataclasses import dataclass, field

from app.services.risk.constants import (
    MAX_POSITION_PCT,
    MIN_CASH_RESERVE_PCT,
    CORRELATION_THRESHOLD,
    STRESS_CORRELATION_THRESHOLD,
    MAX_CORRELATED_POSITIONS,
    HIGH_MODEL_DISAGREEMENT_THRESHOLD,
)

logger = logging.getLogger("wasden_watch.risk_engine")


@dataclass
class RiskContext:
    """All inputs needed for the 7 risk checks."""
    ticker: str
    proposed_position_pct: float  # fraction of portfolio
    portfolio_value: float
    cash_balance: float
    # Existing positions: list of {ticker, sector, position_pct}
    existing_positions: list[dict] = field(default_factory=list)
    # 30-day rolling correlations: {ticker: correlation_coefficient}
    correlations: dict[str, float] = field(default_factory=dict)
    # Stress correlations (worst 10 days): {ticker: correlation_coefficient}
    stress_correlations: dict[str, float] = field(default_factory=dict)
    # Sector of proposed ticker
    sector: str = ""
    # Sector concentration limits: {sector: max_pct}
    sector_limits: dict[str, float] = field(default_factory=dict)
    # Default sector concentration limit if not in sector_limits
    default_sector_limit: float = 0.40
    # Gap risk score for the ticker (0.0 - 1.0)
    gap_risk_score: float = 0.0
    gap_risk_threshold: float = 0.70
    # Model scores std_dev
    model_std_dev: float = 0.0


@dataclass
class RiskCheckDetail:
    """Result of a single risk check."""
    check_name: str
    passed: bool
    detail: str
    value: float | None = None
    threshold: float | None = None


def _check_position_size(ctx: RiskContext) -> RiskCheckDetail:
    """Check 1: Position size <= MAX_POSITION_PCT."""
    passed = ctx.proposed_position_pct <= MAX_POSITION_PCT
    return RiskCheckDetail(
        check_name="position_size",
        passed=passed,
        detail=(
            f"Proposed {ctx.proposed_position_pct:.1%} of portfolio"
            + ("" if passed else f" exceeds max {MAX_POSITION_PCT:.1%}")
        ),
        value=ctx.proposed_position_pct,
        threshold=MAX_POSITION_PCT,
    )


def _check_cash_reserve(ctx: RiskContext) -> RiskCheckDetail:
    """Check 2: Cash reserve >= MIN_CASH_RESERVE_PCT after trade."""
    proposed_cost = ctx.proposed_position_pct * ctx.portfolio_value
    remaining_cash = ctx.cash_balance - proposed_cost
    remaining_pct = remaining_cash / ctx.portfolio_value if ctx.portfolio_value > 0 else 0
    passed = remaining_pct >= MIN_CASH_RESERVE_PCT
    return RiskCheckDetail(
        check_name="cash_reserve",
        passed=passed,
        detail=(
            f"Post-trade cash {remaining_pct:.1%} of portfolio"
            + ("" if passed else f" below min {MIN_CASH_RESERVE_PCT:.1%}")
        ),
        value=remaining_pct,
        threshold=MIN_CASH_RESERVE_PCT,
    )


def _check_correlation(ctx: RiskContext) -> RiskCheckDetail:
    """Check 3: 30-day rolling correlation check."""
    correlated = [
        t for t, c in ctx.correlations.items()
        if c >= CORRELATION_THRESHOLD
    ]
    # Count existing correlated positions
    correlated_positions = [
        p for p in ctx.existing_positions
        if p["ticker"] in correlated
    ]
    passed = len(correlated_positions) < MAX_CORRELATED_POSITIONS
    return RiskCheckDetail(
        check_name="correlation",
        passed=passed,
        detail=(
            f"{len(correlated_positions)} correlated positions "
            f"(threshold {CORRELATION_THRESHOLD}, max {MAX_CORRELATED_POSITIONS})"
            + ("" if passed else f": {[p['ticker'] for p in correlated_positions]}")
        ),
        value=float(len(correlated_positions)),
        threshold=float(MAX_CORRELATED_POSITIONS),
    )


def _check_stress_correlation(ctx: RiskContext) -> RiskCheckDetail:
    """Check 4: Stress correlation (worst 10 days)."""
    high_stress = [
        (t, c) for t, c in ctx.stress_correlations.items()
        if c >= STRESS_CORRELATION_THRESHOLD
    ]
    passed = len(high_stress) == 0
    return RiskCheckDetail(
        check_name="stress_correlation",
        passed=passed,
        detail=(
            f"{len(high_stress)} tickers with stress correlation >= "
            f"{STRESS_CORRELATION_THRESHOLD}"
            + ("" if passed else f": {[t for t, _ in high_stress]}")
        ),
        value=float(len(high_stress)),
        threshold=0.0,
    )


def _check_sector_concentration(ctx: RiskContext) -> RiskCheckDetail:
    """Check 5: Sector concentration."""
    if not ctx.sector:
        return RiskCheckDetail(
            check_name="sector_concentration",
            passed=True,
            detail="Sector not specified, skipping check",
        )

    # Sum position % for same sector
    sector_pct = sum(
        p.get("position_pct", 0)
        for p in ctx.existing_positions
        if p.get("sector") == ctx.sector
    )
    sector_pct += ctx.proposed_position_pct

    limit = ctx.sector_limits.get(ctx.sector, ctx.default_sector_limit)
    passed = sector_pct <= limit
    return RiskCheckDetail(
        check_name="sector_concentration",
        passed=passed,
        detail=(
            f"{ctx.sector} sector: {sector_pct:.1%} of portfolio"
            + ("" if passed else f" exceeds limit {limit:.1%}")
        ),
        value=sector_pct,
        threshold=limit,
    )


def _check_gap_risk(ctx: RiskContext) -> RiskCheckDetail:
    """Check 6: Gap risk score."""
    passed = ctx.gap_risk_score < ctx.gap_risk_threshold
    return RiskCheckDetail(
        check_name="gap_risk",
        passed=passed,
        detail=(
            f"Gap risk score {ctx.gap_risk_score:.2f}"
            + ("" if passed else f" >= threshold {ctx.gap_risk_threshold:.2f}")
        ),
        value=ctx.gap_risk_score,
        threshold=ctx.gap_risk_threshold,
    )


def _check_model_disagreement(ctx: RiskContext) -> RiskCheckDetail:
    """Check 7: Model disagreement (std_dev > threshold)."""
    passed = ctx.model_std_dev <= HIGH_MODEL_DISAGREEMENT_THRESHOLD
    return RiskCheckDetail(
        check_name="model_disagreement",
        passed=passed,
        detail=(
            f"Model std_dev {ctx.model_std_dev:.3f}"
            + ("" if passed else f" > threshold {HIGH_MODEL_DISAGREEMENT_THRESHOLD}")
        ),
        value=ctx.model_std_dev,
        threshold=HIGH_MODEL_DISAGREEMENT_THRESHOLD,
    )


# Ordered check functions matching PROJECT_STANDARDS Section 8 order
RISK_CHECKS = [
    _check_position_size,
    _check_cash_reserve,
    _check_correlation,
    _check_stress_correlation,
    _check_sector_concentration,
    _check_gap_risk,
    _check_model_disagreement,
]


def run_risk_checks(ctx: RiskContext) -> dict:
    """Run all 7 risk checks sequentially.

    Returns dict compatible with RiskCheck schema:
        - passed: bool (all checks passed)
        - checks_failed: list[str] (names of failed checks)
        - details: list[RiskCheckDetail-compatible dicts]
    """
    details = []
    checks_failed = []

    for check_fn in RISK_CHECKS:
        result = check_fn(ctx)
        details.append({
            "check_name": result.check_name,
            "passed": result.passed,
            "detail": result.detail,
            "value": result.value,
            "threshold": result.threshold,
        })
        if not result.passed:
            checks_failed.append(result.check_name)
            logger.warning(
                f"Risk check FAILED for {ctx.ticker}: "
                f"{result.check_name} — {result.detail}"
            )

    all_passed = len(checks_failed) == 0

    if all_passed:
        logger.info(f"All 7 risk checks PASSED for {ctx.ticker}")
    else:
        logger.warning(
            f"Risk checks for {ctx.ticker}: "
            f"{len(checks_failed)}/7 failed — {checks_failed}"
        )

    return {
        "passed": all_passed,
        "checks_failed": checks_failed,
        "details": details,
    }
