"""Goal Arbiter — distributes capital across trades to hit the target return.

CRITICAL: This module reads PROTECTED constants (MAX_POSITION_PCT, RISK_PER_TRADE_PCT)
but never modifies them. The user's max_loss_pct can only be STRICTER than system
constants, never looser.

Like DecisionArbiter, this module has ZERO imports from risk_engine or
pre_trade_validation. Separation is enforced by test.
"""

from __future__ import annotations

import logging
import math

from app.services.risk.constants import MAX_POSITION_PCT, RISK_PER_TRADE_PCT

from .goal_state import GoalConfig, GoalState, GoalTrade

logger = logging.getLogger("wasden_watch.pipeline.goal_arbiter")


class GoalArbiter:
    """Sizes positions across trades to accumulate toward the goal target.

    Three-layer sizing:
        1. Capital allocation from Stage 2 portfolio debate
        2. Pipeline constraint (per-ticker risk limits)
        3. Loss limit enforcement (stricter-wins: user vs. system)
    """

    @staticmethod
    def build_trade_plan(
        goal_state: GoalState,
    ) -> list[GoalTrade]:
        """Build a concrete trade plan from portfolio allocations and pipeline results.

        Args:
            goal_state: GoalState with config, portfolio_allocations, and
                        ticker_results populated.

        Returns:
            List of GoalTrade objects with share counts, targets, and stop-losses.
        """
        config = goal_state.config
        if config is None:
            raise ValueError("GoalState.config must be set before building trade plan")

        allocations = goal_state.portfolio_allocations
        ticker_results = goal_state.ticker_results
        viable = goal_state.viable_tickers()

        if not allocations or not viable:
            logger.info("[GoalArbiter] No viable allocations — returning empty trade plan")
            return []

        trades: list[GoalTrade] = []
        remaining_capital = config.capital
        day_counter = 1

        for alloc in allocations:
            ticker = alloc.get("ticker", "")
            if ticker not in viable:
                logger.info(f"[GoalArbiter] Skipping {ticker} — not viable")
                continue

            result = ticker_results.get(ticker, {})
            pipeline_position_size = result.get("recommended_position_size", 0.0)

            # Skip tickers with zero position recommendation
            if pipeline_position_size <= 0:
                logger.info(f"[GoalArbiter] Skipping {ticker} — pipeline size is 0")
                continue

            allocation_pct = alloc.get("allocation_pct", 0.0) / 100.0
            if allocation_pct <= 0:
                continue

            trade = _size_single_trade(
                config=config,
                ticker=ticker,
                allocation_pct=allocation_pct,
                pipeline_position_size=pipeline_position_size,
                remaining_capital=remaining_capital,
                result=result,
                day_target=day_counter,
            )

            if trade is not None:
                trades.append(trade)
                remaining_capital -= trade.position_dollar
                day_counter = min(day_counter + 1, config.timeframe_days)

        logger.info(
            f"[GoalArbiter] Trade plan: {len(trades)} trades, "
            f"${config.capital - remaining_capital:.2f} allocated of ${config.capital:.2f}"
        )
        return trades

    @staticmethod
    def effective_max_loss_per_trade(
        config: GoalConfig,
        position_dollar: float,
    ) -> float:
        """Calculate effective max loss — whichever is stricter wins.

        Args:
            config: The goal configuration with user's max_loss_pct.
            position_dollar: Dollar value of the specific trade.

        Returns:
            The stricter of user's proportional loss limit vs. system RISK_PER_TRADE_PCT.
        """
        # User's max loss proportional to this trade's share of capital
        user_max_loss = config.max_loss_pct * position_dollar

        # System's RISK_PER_TRADE_PCT applied to total capital
        system_max_loss = RISK_PER_TRADE_PCT * config.capital

        return min(user_max_loss, system_max_loss)


def _size_single_trade(
    config: GoalConfig,
    ticker: str,
    allocation_pct: float,
    pipeline_position_size: float,
    remaining_capital: float,
    result: dict,
    day_target: int,
) -> GoalTrade | None:
    """Size a single trade within the 3-layer framework.

    Layer 1: Capital allocation from Stage 2 debate
    Layer 2: Pipeline constraint (per-ticker risk engine limits)
    Layer 3: Loss limit enforcement (stricter-wins)
    """
    # Layer 1: Goal allocation
    goal_allocation = config.capital * allocation_pct

    # Layer 2: Pipeline constraint
    pipeline_dollar = pipeline_position_size * config.capital

    # Effective position = min of all constraints
    effective_dollar = min(goal_allocation, pipeline_dollar, remaining_capital)

    # Enforce MAX_POSITION_PCT hard cap
    max_position_dollar = MAX_POSITION_PCT * config.capital
    effective_dollar = min(effective_dollar, max_position_dollar)

    if effective_dollar <= 0:
        return None

    # Get estimated entry price from pipeline result
    entry_price = result.get("price", 0.0)
    if entry_price <= 0:
        logger.warning(f"[GoalArbiter] {ticker} has no valid price — skipping")
        return None

    # Calculate shares (floor to whole shares)
    shares = math.floor(effective_dollar / entry_price)
    if shares <= 0:
        return None

    # Recalculate actual position dollar based on whole shares
    actual_position = shares * entry_price

    # Layer 3: Loss limit → stop-loss price
    effective_max_loss = GoalArbiter.effective_max_loss_per_trade(config, actual_position)
    stop_loss_pct = effective_max_loss / actual_position if actual_position > 0 else 0.01
    stop_loss_price = round(entry_price * (1 - stop_loss_pct), 2)

    # Target exit price — what would this trade contribute toward the goal?
    contribution_pct = (allocation_pct * config.target_return_pct)
    target_exit_price = round(entry_price * (1 + contribution_pct), 2)

    action = _resolve_action(result)

    return GoalTrade(
        ticker=ticker,
        action=action,
        shares=shares,
        entry_price_est=entry_price,
        position_dollar=round(actual_position, 2),
        stop_loss_price=stop_loss_price,
        target_exit_price=target_exit_price,
        contribution_target_pct=round(contribution_pct, 6),
        day_target=day_target,
    )


def _resolve_action(result: dict) -> str:
    """Determine trade action from pipeline result."""
    action = result.get("final_action", "HOLD")
    if action in ("BUY", "SELL"):
        return action
    return "BUY"  # Default to BUY for goal-based trades that passed pipeline
