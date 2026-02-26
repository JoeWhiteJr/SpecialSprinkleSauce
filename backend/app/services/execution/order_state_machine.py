"""
Order State Machine — enforces legal state transitions.

States: SUBMITTED → PENDING → FILLED / PARTIALLY_FILLED / REJECTED / EXPIRED
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger("wasden_watch.order_state_machine")


class OrderState(str, Enum):
    SUBMITTED = "submitted"
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


# Legal state transitions
VALID_TRANSITIONS: dict[OrderState, set[OrderState]] = {
    OrderState.SUBMITTED: {OrderState.PENDING, OrderState.REJECTED},
    OrderState.PENDING: {
        OrderState.FILLED,
        OrderState.PARTIALLY_FILLED,
        OrderState.REJECTED,
        OrderState.EXPIRED,
        OrderState.CANCELLED,
    },
    OrderState.PARTIALLY_FILLED: {
        OrderState.FILLED,
        OrderState.CANCELLED,
    },
    # Terminal states — no transitions out
    OrderState.FILLED: set(),
    OrderState.REJECTED: set(),
    OrderState.EXPIRED: set(),
    OrderState.CANCELLED: set(),
}


class InvalidTransitionError(Exception):
    """Raised when an illegal state transition is attempted."""

    def __init__(self, order_id: str, from_state: OrderState, to_state: OrderState):
        self.order_id = order_id
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid transition for order {order_id}: "
            f"{from_state.value} → {to_state.value}"
        )


@dataclass
class StateTransition:
    """A recorded state transition."""
    from_state: OrderState
    to_state: OrderState
    timestamp: str
    reason: Optional[str] = None


@dataclass
class Order:
    """An order with state history tracking."""
    id: str
    ticker: str
    side: str  # "buy" or "sell"
    quantity: int
    price: float
    state: OrderState = OrderState.SUBMITTED
    alpaca_order_id: Optional[str] = None
    fill_price: Optional[float] = None
    filled_quantity: int = 0
    slippage: Optional[float] = None
    risk_check_result: Optional[dict] = None
    pre_trade_result: Optional[dict] = None
    state_history: list[StateTransition] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.utcnow().isoformat() + "Z"
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


def transition_order(
    order: Order,
    new_state: OrderState,
    reason: Optional[str] = None,
) -> Order:
    """Transition an order to a new state, enforcing valid transitions.

    Args:
        order: The order to transition.
        new_state: Target state.
        reason: Optional reason for the transition.

    Returns:
        Updated order.

    Raises:
        InvalidTransitionError: If the transition is not legal.
    """
    valid = VALID_TRANSITIONS.get(order.state, set())
    if new_state not in valid:
        raise InvalidTransitionError(order.id, order.state, new_state)

    now = datetime.utcnow().isoformat() + "Z"

    order.state_history.append(StateTransition(
        from_state=order.state,
        to_state=new_state,
        timestamp=now,
        reason=reason,
    ))

    logger.info(
        f"Order {order.id} ({order.ticker}): "
        f"{order.state.value} → {new_state.value}"
        + (f" ({reason})" if reason else "")
    )

    order.state = new_state
    order.updated_at = now
    return order


def order_to_dict(order: Order) -> dict:
    """Convert Order to API-friendly dict."""
    return {
        "id": order.id,
        "ticker": order.ticker,
        "side": order.side,
        "quantity": order.quantity,
        "price": order.price,
        "state": order.state.value,
        "alpaca_order_id": order.alpaca_order_id,
        "fill_price": order.fill_price,
        "filled_quantity": order.filled_quantity,
        "slippage": order.slippage,
        "risk_check_result": order.risk_check_result,
        "pre_trade_result": order.pre_trade_result,
        "state_history": [
            {
                "from_state": t.from_state.value,
                "to_state": t.to_state.value,
                "timestamp": t.timestamp,
                "reason": t.reason,
            }
            for t in order.state_history
        ],
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }
