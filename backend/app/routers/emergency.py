"""
Emergency Shutdown Router — system-wide halt and resume endpoints.

Provides endpoints for emergency shutdown, resume, order cancellation,
and force paper mode. All endpoints work in mock mode.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.requests import Request

from app.audit import log_action
from app.rate_limit import limiter
from app.services.emergency.shutdown_manager import ShutdownManager

router = APIRouter(prefix="/api/emergency", tags=["emergency"])

# Module-level manager instance (reset per-request is not needed;
# in-memory state is intentional for the shutdown lifecycle)
_manager = ShutdownManager()


class ShutdownRequest(BaseModel):
    initiated_by: str
    reason: str


class ResumeRequest(BaseModel):
    approved_by: str


@router.post("/shutdown")
@limiter.limit("10/minute")
async def emergency_shutdown(request: Request, req: ShutdownRequest):
    """Trigger emergency shutdown — cancel all orders and halt trading."""
    log_action("emergency_shutdown", "/api/emergency/shutdown", req.initiated_by, req.reason)
    return _manager.emergency_shutdown(req.initiated_by, req.reason)


@router.post("/resume")
@limiter.limit("10/minute")
async def resume_trading(request: Request, req: ResumeRequest):
    """Resume trading after emergency shutdown."""
    log_action("resume_trading", "/api/emergency/resume", req.approved_by)
    try:
        return _manager.resume_trading(req.approved_by)
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
