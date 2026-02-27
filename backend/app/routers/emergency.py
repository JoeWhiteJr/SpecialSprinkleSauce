"""
Emergency Shutdown Router — system-wide halt and resume endpoints.

Provides endpoints for emergency shutdown, resume, order cancellation,
and force paper mode. All endpoints work in mock mode.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
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
async def emergency_shutdown(req: ShutdownRequest):
    """Trigger emergency shutdown — cancel all orders and halt trading."""
    if settings.use_mock_data:
        return _manager.emergency_shutdown(req.initiated_by, req.reason)

    return _manager.emergency_shutdown(req.initiated_by, req.reason)


@router.post("/resume")
async def resume_trading(req: ResumeRequest):
    """Resume trading after emergency shutdown."""
    if settings.use_mock_data:
        try:
            return _manager.resume_trading(req.approved_by)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    try:
        return _manager.resume_trading(req.approved_by)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status")
async def get_shutdown_status():
    """Get current emergency shutdown status."""
    if settings.use_mock_data:
        return _manager.get_shutdown_status()

    return _manager.get_shutdown_status()


@router.get("/history")
async def get_shutdown_history():
    """Get shutdown/resume event history."""
    if settings.use_mock_data:
        return _manager.get_shutdown_history()

    return _manager.get_shutdown_history()


@router.post("/cancel-all-orders")
async def cancel_all_orders():
    """Cancel all open orders without triggering full shutdown."""
    if settings.use_mock_data:
        cancelled = _manager.cancel_all_orders()
        return {
            "success": True,
            "orders_cancelled": len(cancelled),
            "details": cancelled,
        }

    cancelled = _manager.cancel_all_orders()
    return {
        "success": True,
        "orders_cancelled": len(cancelled),
        "details": cancelled,
    }


@router.post("/force-paper-mode")
async def force_paper_mode():
    """Request switch to paper trading mode (requires restart)."""
    if settings.use_mock_data:
        return _manager.force_paper_mode()

    return _manager.force_paper_mode()
