"""Prompt templates for Stage 2 portfolio-level debate."""

# ---------------------------------------------------------------------------
# System prompts — portfolio strategist roles
# ---------------------------------------------------------------------------

PORTFOLIO_BULL_SYSTEM_PROMPT = """\
You are a portfolio strategist arguing for the most EFFECTIVE allocation to hit a financial target.
Your job is to recommend which stocks to buy, how much capital to allocate to each, and why this
mix maximizes the probability of achieving the return target within the given timeframe.
Be aggressive but rational — reference the per-ticker analysis data provided.
Keep your argument to 3-5 concise paragraphs."""

PORTFOLIO_BEAR_SYSTEM_PROMPT = """\
You are a risk-focused portfolio strategist arguing for the SAFEST allocation that can still hit the target.
Your job is to recommend a conservative allocation that minimizes drawdown risk while still being
achievable within the timeframe. Favor diversification and lower-volatility picks.
Be cautious but realistic — reference the per-ticker analysis data provided.
Keep your argument to 3-5 concise paragraphs."""

PORTFOLIO_REBUTTAL_SYSTEM_PROMPT = """\
You are a portfolio strategist defending your allocation recommendation.
You have seen the opposing strategist's allocation proposal. Rebut their key points while
strengthening your own proposal. Address their strongest objections directly.
Keep your rebuttal to 2-3 concise paragraphs."""

# ---------------------------------------------------------------------------
# User prompts
# ---------------------------------------------------------------------------

PORTFOLIO_INITIAL_PROMPT = """\
## Goal
- Capital: ${capital:,.2f}
- Target: +{target_pct:.1%} (${target_dollar:,.2f}) in {timeframe_days} trading days
- Max acceptable loss: -{max_loss_pct:.1%} (${max_loss_dollar:,.2f})
- Daily pace: +{daily_target_pct:.3%} per day

## Candidate Analysis Results
{candidates_section}

Recommend a specific allocation (percentages that sum to 100% or less) across these candidates.
For each ticker, specify allocation_pct and a one-sentence rationale.

Respond with your reasoning FIRST, then end with a JSON allocation table:
```json
{{"allocations": [{{"ticker": "NVDA", "allocation_pct": 40, "rationale": "..."}}]}}
```"""

PORTFOLIO_REBUTTAL_PROMPT = """\
## Previous Aggressive Allocation
{prev_bull_argument}

## Previous Conservative Allocation
{prev_bear_argument}

Rebut the opposing allocation and strengthen your own proposal. End with your revised JSON allocation."""

# ---------------------------------------------------------------------------
# Agreement detection — picks consensus allocation
# ---------------------------------------------------------------------------

PORTFOLIO_AGREEMENT_SYSTEM_PROMPT = """\
You are a neutral portfolio analyst evaluating two allocation proposals for the same goal.
Determine the consensus allocation — blend the two proposals, favoring agreement where both
strategists overlap. If they fundamentally disagree on a ticker, lean toward the safer option.

You MUST respond with valid JSON only:
{{"allocations": [{{"ticker": "NVDA", "allocation_pct": 40, "rationale": "..."}}], "reasoning": "brief explanation"}}

Allocations must sum to 100% or less. Only include tickers both strategists considered."""

PORTFOLIO_AGREEMENT_USER_PROMPT = """\
## Goal
- Capital: ${capital:,.2f} | Target: +{target_pct:.1%} in {timeframe_days} days | Max loss: -{max_loss_pct:.1%}

## Aggressive Allocation Proposal
{final_bull_argument}

## Conservative Allocation Proposal
{final_bear_argument}

Determine the consensus allocation. Respond with JSON only."""


def format_candidates_section(ticker_results: dict[str, dict]) -> str:
    """Format per-ticker pipeline results into a readable section for the debate."""
    if not ticker_results:
        return "No candidates available."

    lines = []
    for ticker, result in ticker_results.items():
        action = result.get("final_action", "N/A")
        quant = result.get("quant_scores", {})
        composite = quant.get("composite", 0.0)
        std_dev = quant.get("std_dev", 0.0)
        wasden = result.get("wasden_verdict", {})
        verdict = wasden.get("verdict", "N/A") if isinstance(wasden, dict) else wasden
        confidence = wasden.get("confidence", 0.0) if isinstance(wasden, dict) else 0.0
        price = result.get("price", 0.0)
        position_size = result.get("recommended_position_size", 0.0)

        lines.append(f"### {ticker} (${price:.2f})")
        lines.append(f"- Pipeline action: {action}")
        lines.append(f"- Quant composite: {composite:.3f} (std_dev: {std_dev:.3f})")
        lines.append(f"- Wasden verdict: {verdict} (confidence: {confidence:.2f})")
        lines.append(f"- Recommended position: {position_size:.1%}")
        lines.append("")

    return "\n".join(lines)
