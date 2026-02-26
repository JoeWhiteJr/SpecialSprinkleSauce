"""
Stress testing — 5 crash scenarios per PROJECT_STANDARDS_v2.md Section 9.

Scenarios:
1. COVID crash (Feb-March 2020, SPY -33.9%)
2. 2022 bear market (SPY -25.4%)
3. Regional banking crisis (March 2023, SPY -7.8%)
4. 1987 Black Monday (SPY -20.5% single day)
5. 2008 financial crisis (SPY -56.8%)

Each scenario has sector impact multipliers for more realistic modeling.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("wasden_watch.stress_test")


@dataclass
class StressScenario:
    """A historical crash scenario for stress testing."""
    name: str
    description: str
    period: str
    spy_drawdown: float  # negative decimal (e.g., -0.339)
    duration_days: int
    sector_multipliers: dict[str, float] = field(default_factory=dict)


# Sector multipliers: how much worse/better each sector performed vs SPY
# > 1.0 = worse than SPY, < 1.0 = better than SPY
SCENARIOS = [
    StressScenario(
        name="covid_crash",
        description="COVID-19 pandemic market crash",
        period="Feb-March 2020",
        spy_drawdown=-0.339,
        duration_days=33,
        sector_multipliers={
            "Technology": 0.85,
            "Energy": 1.60,
            "Healthcare": 0.70,
            "Financials": 1.30,
            "Consumer Discretionary": 1.20,
            "Consumer Staples": 0.65,
            "Utilities": 0.80,
            "Real Estate": 1.15,
            "Industrials": 1.25,
            "Materials": 1.10,
            "Communication Services": 0.90,
        },
    ),
    StressScenario(
        name="bear_2022",
        description="2022 bear market (inflation + rate hikes)",
        period="Jan-Oct 2022",
        spy_drawdown=-0.254,
        duration_days=282,
        sector_multipliers={
            "Technology": 1.40,
            "Energy": -0.50,  # Energy was positive in 2022
            "Healthcare": 0.80,
            "Financials": 0.90,
            "Consumer Discretionary": 1.50,
            "Consumer Staples": 0.60,
            "Utilities": 0.65,
            "Real Estate": 1.20,
            "Industrials": 0.95,
            "Materials": 0.85,
            "Communication Services": 1.60,
        },
    ),
    StressScenario(
        name="regional_banking",
        description="Regional banking crisis (SVB, Signature, First Republic)",
        period="March 2023",
        spy_drawdown=-0.078,
        duration_days=14,
        sector_multipliers={
            "Technology": 0.60,
            "Energy": 1.20,
            "Healthcare": 0.80,
            "Financials": 3.50,  # Banks hit hardest
            "Consumer Discretionary": 0.90,
            "Consumer Staples": 0.50,
            "Utilities": 0.70,
            "Real Estate": 1.80,
            "Industrials": 0.85,
            "Materials": 0.90,
            "Communication Services": 0.75,
        },
    ),
    StressScenario(
        name="black_monday_1987",
        description="Black Monday — single-day crash",
        period="October 19, 1987",
        spy_drawdown=-0.205,
        duration_days=1,
        sector_multipliers={
            "Technology": 1.10,
            "Energy": 1.00,
            "Healthcare": 0.90,
            "Financials": 1.30,
            "Consumer Discretionary": 1.15,
            "Consumer Staples": 0.85,
            "Utilities": 0.80,
            "Real Estate": 1.05,
            "Industrials": 1.10,
            "Materials": 1.05,
            "Communication Services": 1.00,
        },
    ),
    StressScenario(
        name="financial_crisis_2008",
        description="2008 global financial crisis",
        period="Oct 2007 - March 2009",
        spy_drawdown=-0.568,
        duration_days=517,
        sector_multipliers={
            "Technology": 0.85,
            "Energy": 1.05,
            "Healthcare": 0.70,
            "Financials": 1.80,
            "Consumer Discretionary": 1.10,
            "Consumer Staples": 0.55,
            "Utilities": 0.60,
            "Real Estate": 1.50,
            "Industrials": 1.20,
            "Materials": 1.15,
            "Communication Services": 0.95,
        },
    ),
]


def run_stress_test(
    scenario: StressScenario,
    positions: list[dict],
    portfolio_value: float,
) -> dict:
    """Run a single stress test scenario against current positions.

    Args:
        scenario: The crash scenario to simulate.
        positions: Current positions, each with keys:
            ticker, sector, current_value (dollar value)
        portfolio_value: Total portfolio value.

    Returns:
        Dict with scenario results including per-position impacts.
    """
    position_impacts = []
    total_loss = 0.0

    for pos in positions:
        sector = pos.get("sector", "Unknown")
        multiplier = scenario.sector_multipliers.get(sector, 1.0)
        position_value = pos.get("current_value", 0)

        # Estimated loss = SPY drawdown × sector multiplier × position value
        estimated_loss = scenario.spy_drawdown * multiplier * position_value

        position_impacts.append({
            "ticker": pos["ticker"],
            "sector": sector,
            "current_value": position_value,
            "sector_multiplier": multiplier,
            "estimated_loss": round(estimated_loss, 2),
            "estimated_loss_pct": round(scenario.spy_drawdown * multiplier * 100, 2),
        })
        total_loss += estimated_loss

    portfolio_loss_pct = total_loss / portfolio_value if portfolio_value > 0 else 0

    return {
        "scenario_name": scenario.name,
        "description": scenario.description,
        "period": scenario.period,
        "spy_drawdown": scenario.spy_drawdown,
        "duration_days": scenario.duration_days,
        "portfolio_loss": round(total_loss, 2),
        "portfolio_loss_pct": round(portfolio_loss_pct, 4),
        "position_impacts": position_impacts,
        "surviving": portfolio_value + total_loss > 0,
    }


def run_all_stress_tests(
    positions: list[dict],
    portfolio_value: float,
) -> list[dict]:
    """Run all 5 crash scenarios against current positions.

    Returns list of stress test results, one per scenario.
    """
    results = []
    for scenario in SCENARIOS:
        result = run_stress_test(scenario, positions, portfolio_value)
        results.append(result)
        logger.info(
            f"Stress test '{scenario.name}': "
            f"portfolio loss {result['portfolio_loss_pct']:.1%} "
            f"(${abs(result['portfolio_loss']):,.2f})"
        )
    return results
