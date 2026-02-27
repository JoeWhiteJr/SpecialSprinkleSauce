import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from starlette.requests import Request

from app.audit import log_action
from app.config import settings
from app.rate_limit import limiter
from app.mock.generators import (
    generate_orders_mock,
    generate_account_mock,
)

router = APIRouter(prefix="/api/execution", tags=["execution"])


class OrderRequest(BaseModel):
    ticker: str
    side: str = "buy"
    quantity: int
    price: float

    @field_validator("side")
    @classmethod
    def validate_side(cls, v):
        if v.lower() not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")
        return v.lower()

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v):
        if v <= 0 or v > 100000:
            raise ValueError("quantity must be between 1 and 100,000")
        return v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError("price must be positive")
        return v

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v):
        if not v.isalpha() or len(v) > 10:
            raise ValueError("ticker must be alphabetic and at most 10 characters")
        return v.upper()


class ValidateRequest(BaseModel):
    ticker: str
    side: str = "buy"
    quantity: int
    price: float
    portfolio_value: float = 100_000.0


@router.post("/order")
@limiter.limit("10/minute")
async def submit_order(request: Request, req: OrderRequest):
    """Submit order (pre-trade validation + risk check + Alpaca)."""
    log_action("submit_order", "/api/execution/order", details=f"ticker={req.ticker} side={req.side} qty={req.quantity}")
    if settings.use_mock_data:
        orders = generate_orders_mock()
        return orders[0]  # Return first mock order as response

    from app.services.risk.pre_trade_validation import PreTradeContext, run_pre_trade_validation
    from app.services.risk.risk_engine import RiskContext, run_risk_checks
    from app.services.execution.order_state_machine import Order, order_to_dict
    from app.services.execution.alpaca_client import AlpacaClient

    # Pre-trade validation
    ptc = PreTradeContext(
        ticker=req.ticker,
        side=req.side,
        quantity=req.quantity,
        price=req.price,
        portfolio_value=100_000,
    )
    ptv_result = run_pre_trade_validation(ptc)
    if not ptv_result["passed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Pre-trade validation failed: {ptv_result['checks_failed']}",
        )

    # Risk checks
    position_pct = (req.quantity * req.price) / 100_000
    rc = RiskContext(
        ticker=req.ticker,
        proposed_position_pct=position_pct,
        portfolio_value=100_000,
        cash_balance=35_000,
    )
    risk_result = run_risk_checks(rc)
    if not risk_result["passed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Risk checks failed: {risk_result['checks_failed']}",
        )

    # Submit to Alpaca
    order = Order(
        id=str(uuid.uuid4()),
        ticker=req.ticker,
        side=req.side,
        quantity=req.quantity,
        price=req.price,
        risk_check_result=risk_result,
        pre_trade_result=ptv_result,
    )
    client = AlpacaClient()
    order = client.submit_order(order)
    return order_to_dict(order)


@router.get("/orders")
async def list_orders():
    """List all orders."""
    if settings.use_mock_data:
        return generate_orders_mock()
    return []


@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get single order detail."""
    if settings.use_mock_data:
        orders = generate_orders_mock()
        for o in orders:
            if o["id"] == order_id:
                return o
        raise HTTPException(status_code=404, detail="Order not found")
    raise HTTPException(status_code=404, detail="Order not found")


@router.get("/account")
async def get_account():
    """Alpaca account summary."""
    if settings.use_mock_data:
        return generate_account_mock()

    from app.services.execution.alpaca_client import AlpacaClient
    client = AlpacaClient()
    return client.get_account()


@router.post("/validate")
async def validate_only(req: ValidateRequest):
    """Run pre-trade validation only (no execution)."""
    if settings.use_mock_data:
        return {
            "passed": True,
            "checks_failed": [],
            "details": [
                {"check_name": "quantity_sanity", "passed": True, "detail": f"Quantity {req.quantity} within bounds"},
                {"check_name": "duplicate_detection", "passed": True, "detail": "No duplicate orders detected"},
                {"check_name": "portfolio_impact", "passed": True, "detail": f"Trade ${req.quantity * req.price:,.2f}"},
                {"check_name": "dollar_sanity", "passed": True, "detail": "Within max position size"},
            ],
        }

    from app.services.risk.pre_trade_validation import PreTradeContext, run_pre_trade_validation
    ptc = PreTradeContext(
        ticker=req.ticker,
        side=req.side,
        quantity=req.quantity,
        price=req.price,
        portfolio_value=req.portfolio_value,
    )
    return run_pre_trade_validation(ptc)
