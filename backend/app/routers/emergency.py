"""
Emergency Shutdown Router — system-wide halt and resume endpoints.

Provides endpoints for emergency shutdown, resume, order cancellation,
and force paper mode. All endpoints work in mock mode.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette.requests import Request

from app.audit import log_action
from app.auth import identify_principal
from app.rate_limit import limiter
from app.services.emergency.shutdown_manager import ShutdownManager

router = APIRouter(prefix="/api/emergency", tags=["emergency"])

# Module-level manager instance (reset per-request is not needed;
# in-memory state is intentional for the shutdown lifecycle)
_manager = ShutdownManager()


class ShutdownRequest(BaseModel):
    reason: str
    # initiated_by is derived from the authenticated principal (X-API-Key).
    # Removed from request body to prevent identity self-assertion (issue #59).


class ResumeRequest(BaseModel):
    pass
    # approved_by is derived from the authenticated principal (X-API-Key).
    # Removed from request body to prevent identity self-assertion (issue #59).


@router.post("/shutdown")
@limiter.limit("10/minute")
async def emergency_shutdown(
    request: Request,
    req: ShutdownRequest,
    principal: str = Depends(identify_principal),
):
    """Trigger emergency shutdown — cancel all orders and halt trading."""
    log_action("emergency_shutdown", "/api/emergency/shutdown", principal, req.reason)
    return _manager.emergency_shutdown(principal, req.reason)


@router.post("/resume")
@limiter.limit("10/minute")
async def resume_trading(
    request: Request,
    req: ResumeRequest,
    principal: str = Depends(identify_principal),
):
    """Resume trading after emergency shutdown."""
    log_action("resume_trading", "/api/emergency/resume", principal)
    try:
        return _manager.resume_trading(principal)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status")
async def get_shutdown_status():
    """Get current emergency shutdown status."""
    return _manager.get_shutdown_status()


@router.get("/history")
async def get_shutdown_history():
    """Get shutdown/resume event history."""
    return _manager.get_shutdown_history()


@router.post("/cancel-all-orders")
@limiter.limit("10/minute")
async def cancel_all_orders(request: Request):
    """Cancel all open orders without triggering full shutdown."""
    log_action("cancel_all_orders", "/api/emergency/cancel-all-orders")
    cancelled = _manager.cancel_all_orders()
    return {
        "success": True,
        "orders_cancelled": len(cancelled),
        "details": cancelled,
    }


@router.post("/force-paper-mode")
@limiter.limit("10/minute")
async def force_paper_mode(request: Request):
    """Request switch to paper trading mode (requires restart)."""
    log_action("force_paper_mode", "/api/emergency/force-paper-mode")
    return _manager.force_paper_mode()
