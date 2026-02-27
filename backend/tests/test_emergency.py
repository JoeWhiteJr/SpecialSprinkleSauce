"""Unit tests for the Emergency Shutdown Manager.

All tests use mock mode. No database, no Alpaca API calls.
Each test creates a fresh ShutdownManager to avoid state leaking.
"""

import os

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

from app.services.emergency.shutdown_manager import ShutdownManager  # noqa: E402


def _fresh_manager() -> ShutdownManager:
    """Return a fresh ShutdownManager with no prior state."""
    return ShutdownManager()


# ---------------------------------------------------------------------------
# Test: emergency shutdown in mock mode
# ---------------------------------------------------------------------------

def test_emergency_shutdown_mock():
    """Emergency shutdown sets active and returns success."""
    mgr = _fresh_manager()
    result = mgr.emergency_shutdown(initiated_by="Joe", reason="Test shutdown")
    assert result["success"] is True
    assert result["initiated_by"] == "Joe"
    assert result["reason"] == "Test shutdown"
    assert isinstance(result["orders_cancelled"], int)
    assert isinstance(result["actions_taken"], list)
    assert len(result["actions_taken"]) > 0
    assert result["timestamp"] is not None


# ---------------------------------------------------------------------------
# Test: shutdown blocks trading
# ---------------------------------------------------------------------------

def test_shutdown_blocks_trading():
    """is_shutdown_active() returns True after shutdown."""
    mgr = _fresh_manager()
    assert mgr.is_shutdown_active() is False
    mgr.emergency_shutdown(initiated_by="Jared", reason="Market crash")
    assert mgr.is_shutdown_active() is True


# ---------------------------------------------------------------------------
# Test: resume requires name
# ---------------------------------------------------------------------------

def test_resume_requires_name():
    """Resume with empty string raises ValueError."""
    mgr = _fresh_manager()
    mgr.emergency_shutdown(initiated_by="Joe", reason="Test")
    try:
        mgr.resume_trading(approved_by="")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "approved_by" in str(e).lower() or "required" in str(e).lower()


# ---------------------------------------------------------------------------
# Test: resume clears shutdown
# ---------------------------------------------------------------------------

def test_resume_clears_shutdown():
    """is_shutdown_active() returns False after resume."""
    mgr = _fresh_manager()
    mgr.emergency_shutdown(initiated_by="Joe", reason="Drill")
    assert mgr.is_shutdown_active() is True
    mgr.resume_trading(approved_by="Jared")
    assert mgr.is_shutdown_active() is False


# ---------------------------------------------------------------------------
# Test: cancel all orders in mock mode
# ---------------------------------------------------------------------------

def test_cancel_all_orders_mock():
    """cancel_all_orders returns a list (empty in mock mode)."""
    mgr = _fresh_manager()
    result = mgr.cancel_all_orders()
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Test: shutdown history accumulates
# ---------------------------------------------------------------------------

def test_shutdown_history_accumulates():
    """Shutdown + resume = 2 events in history."""
    mgr = _fresh_manager()
    mgr.emergency_shutdown(initiated_by="Joe", reason="Emergency")
    mgr.resume_trading(approved_by="Jared")
    history = mgr.get_shutdown_history()
    assert len(history) == 2
    assert history[0]["event_type"] == "shutdown"
    assert history[1]["event_type"] == "resume"


# ---------------------------------------------------------------------------
# Test: force paper mode
# ---------------------------------------------------------------------------

def test_force_paper_mode():
    """Force paper mode returns status with message."""
    mgr = _fresh_manager()
    result = mgr.force_paper_mode()
    assert result["success"] is True
    assert "restart" in result["message"].lower()
    assert result["current_mode"] == "paper"


# ---------------------------------------------------------------------------
# Test: shutdown status
# ---------------------------------------------------------------------------

def test_shutdown_status():
    """get_shutdown_status returns correct active state."""
    mgr = _fresh_manager()

    status = mgr.get_shutdown_status()
    assert status["active"] is False
    assert status["last_event"] is None
    assert status["trading_mode"] == "paper"

    mgr.emergency_shutdown(initiated_by="Joe", reason="Check status")
    status = mgr.get_shutdown_status()
    assert status["active"] is True
    assert status["last_event"] is not None
    assert status["last_event"]["event_type"] == "shutdown"


# ---------------------------------------------------------------------------
# Test: double shutdown (idempotent)
# ---------------------------------------------------------------------------

def test_double_shutdown():
    """Second shutdown still works — idempotent behavior."""
    mgr = _fresh_manager()
    result1 = mgr.emergency_shutdown(initiated_by="Joe", reason="First")
    result2 = mgr.emergency_shutdown(initiated_by="Jared", reason="Second")
    assert result1["success"] is True
    assert result2["success"] is True
    assert mgr.is_shutdown_active() is True
    history = mgr.get_shutdown_history()
    assert len(history) == 2


# ---------------------------------------------------------------------------
# Test: resume without shutdown (graceful)
# ---------------------------------------------------------------------------

def test_resume_without_shutdown():
    """Resume when not in shutdown is graceful — sets active to False (already False)."""
    mgr = _fresh_manager()
    assert mgr.is_shutdown_active() is False
    result = mgr.resume_trading(approved_by="Joe")
    assert result["success"] is True
    assert mgr.is_shutdown_active() is False
