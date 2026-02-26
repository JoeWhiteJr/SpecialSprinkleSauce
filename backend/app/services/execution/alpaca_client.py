"""
Alpaca execution client — enforces TRADING_MODE at every call.

Supports paper and live modes with separate API keys.
Integrates slippage model for paper trading accuracy.
"""

import logging
import uuid
from typing import Optional

from app.config import settings
from app.services.risk.slippage import calculate_slippage
from app.services.execution.order_state_machine import (
    Order,
    OrderState,
    transition_order,
)

logger = logging.getLogger("wasden_watch.alpaca_client")


class AlpacaClient:
    """Alpaca trading client with TRADING_MODE enforcement."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Lazy-init Alpaca REST client with TRADING_MODE enforcement."""
        if self._client is not None:
            return self._client

        # TRADING_MODE enforcement
        if settings.trading_mode not in ("paper", "live"):
            raise RuntimeError(
                f"TRADING_MODE='{settings.trading_mode}' is invalid. "
                "Must be 'paper' or 'live'."
            )

        if settings.trading_mode == "paper":
            api_key = settings.alpaca_paper_api_key
            secret_key = settings.alpaca_paper_secret_key
            base_url = "https://paper-api.alpaca.markets"
        else:
            api_key = settings.alpaca_live_api_key
            secret_key = settings.alpaca_live_secret_key
            base_url = "https://api.alpaca.markets"

        if not api_key or not secret_key:
            logger.warning(
                f"Alpaca {settings.trading_mode} API keys not configured. "
                "Orders will be simulated."
            )
            return None

        try:
            import alpaca_trade_api as tradeapi
            self._client = tradeapi.REST(
                api_key, secret_key, base_url, api_version="v2"
            )
            logger.info(f"Alpaca client initialized (mode={settings.trading_mode})")
            return self._client
        except ImportError:
            logger.warning("alpaca-trade-api not installed. Using mock mode.")
            return None

    def submit_order(
        self,
        order: Order,
        avg_daily_volume: int = 0,
    ) -> Order:
        """Submit an order to Alpaca.

        Args:
            order: Order with state SUBMITTED.
            avg_daily_volume: ADV for slippage calculation.

        Returns:
            Updated Order with state transitioned.
        """
        client = self._get_client()

        # Calculate slippage estimate
        slippage = calculate_slippage(order.quantity, order.price, avg_daily_volume)
        order.slippage = slippage

        if client is None:
            # Simulate order (no Alpaca keys or mock mode)
            logger.info(
                f"SIMULATED order: {order.side} {order.quantity} {order.ticker} "
                f"@ ${order.price:.2f} (slippage: ${slippage:.2f})"
            )
            order.alpaca_order_id = f"sim-{uuid.uuid4().hex[:12]}"
            order = transition_order(order, OrderState.PENDING, "simulated")
            # Immediately fill simulated orders
            order.fill_price = order.price + (slippage / order.quantity if order.quantity > 0 else 0)
            order.filled_quantity = order.quantity
            order = transition_order(order, OrderState.FILLED, "simulated fill")
            return order

        try:
            alpaca_order = client.submit_order(
                symbol=order.ticker,
                qty=order.quantity,
                side=order.side,
                type="market",
                time_in_force="day",
            )
            order.alpaca_order_id = str(alpaca_order.id)
            order = transition_order(order, OrderState.PENDING, "submitted to Alpaca")
            logger.info(
                f"Order submitted to Alpaca: {order.alpaca_order_id} "
                f"({order.side} {order.quantity} {order.ticker})"
            )
        except Exception as e:
            logger.error(f"Alpaca order submission failed: {e}")
            order = transition_order(order, OrderState.REJECTED, str(e))

        return order

    def get_order_status(self, alpaca_order_id: str) -> Optional[dict]:
        """Get order status from Alpaca."""
        client = self._get_client()
        if client is None:
            return None

        try:
            order = client.get_order(alpaca_order_id)
            return {
                "id": str(order.id),
                "status": order.status,
                "filled_qty": int(order.filled_qty or 0),
                "filled_avg_price": float(order.filled_avg_price or 0),
                "symbol": order.symbol,
                "side": order.side,
                "qty": int(order.qty),
            }
        except Exception as e:
            logger.error(f"Failed to get Alpaca order status: {e}")
            return None

    def get_account(self) -> dict:
        """Get Alpaca account summary."""
        client = self._get_client()
        if client is None:
            # Return mock account for paper mode without keys
            return {
                "portfolio_value": 100000.0,
                "cash": 35000.0,
                "buying_power": 70000.0,
                "equity": 100000.0,
                "trading_mode": settings.trading_mode,
                "status": "ACTIVE",
                "simulated": True,
            }

        try:
            account = client.get_account()
            return {
                "portfolio_value": float(account.portfolio_value),
                "cash": float(account.cash),
                "buying_power": float(account.buying_power),
                "equity": float(account.equity),
                "trading_mode": settings.trading_mode,
                "status": account.status,
                "simulated": False,
            }
        except Exception as e:
            logger.error(f"Failed to get Alpaca account: {e}")
            return {"error": str(e), "trading_mode": settings.trading_mode}

    def get_positions(self) -> list[dict]:
        """Get all open positions from Alpaca."""
        client = self._get_client()
        if client is None:
            return []

        try:
            positions = client.list_positions()
            return [
                {
                    "ticker": p.symbol,
                    "quantity": int(p.qty),
                    "market_value": float(p.market_value),
                    "avg_entry_price": float(p.avg_entry_price),
                    "current_price": float(p.current_price),
                    "unrealized_pl": float(p.unrealized_pl),
                    "unrealized_plpc": float(p.unrealized_plpc),
                    "side": p.side,
                }
                for p in positions
            ]
        except Exception as e:
            logger.error(f"Failed to get Alpaca positions: {e}")
            return []
