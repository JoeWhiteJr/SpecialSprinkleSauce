"""Edge case tests for the Emergency Shutdown Manager.

Covers whitespace-only resume strings, special characters, rapid repeated
operations, history accumulation, status before any events, and large inputs.
All tests use mock mode. No database, no Alpaca API calls.
Each test creates a fresh ShutdownManager to avoid state leaking.
"""

import os

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

import pytest  # noqa: E402

from app.services.emergency.shutdown_manager import ShutdownManager  # noqa: E402


def _fresh_manager() -> ShutdownManager:
    """Return a fresh ShutdownManager with no prior state."""
    return ShutdownManager()


# ---------------------------------------------------------------------------
# resume_trading — approved_by validation edge cases
# ---------------------------------------------------------------------------

def test_resume_whitespace_only_string_raises():
    """approved_by with only spaces is rejected the same as an empty string."""
    mgr = _fresh_manager()
    mgr.emergency_shutdown(initiated_by="Joe", reason="Test")
    with pytest.raises(ValueError):
        mgr.resume_trading(approved_by="   ")


def test_resume_tab_only_string_raises():
    """approved_by with only a tab character is rejected."""
    mgr = _fresh_manager()
    mgr.emergency_shutdown(initiated_by="Joe", reason="Test")
    with pytest.raises(ValueError):
        mgr.resume_trading(approved_by="\t")


def test_resume_newline_only_string_raises():
    """approved_by with only a newline is rejected."""
    mgr = _fresh_manager()
    mgr.emergency_shutdown(initiated_by="Joe", reason="Test")
    with pytest.raises(ValueError):
        mgr.resume_trading(approved_by="\n")


def test_resume_very_long_string_succeeds():
    """approved_by with a very long (1000-char) name string is accepted."""
    mgr = _fresh_manager()
    mgr.emergency_shutdown(initiated_by="Joe", reason="Test")
    long_name = "A" * 1000
    result = mgr.resume_trading(approved_by=long_name)
    assert result["success"] is True
    assert mgr.is_shutdown_active() is False


def test_resume_name_with_special_characters_succeeds():
    """approved_by with special characters (e.g. unicode, punctuation) is accepted."""
    mgr = _fresh_manager()
    mgr.emergency_shutdown(initiated_by="Joe", reason="Test")
    result = mgr.resume_trading(approved_by="O'Reilly-Smith (CTO) 日本語")
    assert result["success"] is True


def test_resume_name_leading_trailing_whitespace_succeeds():
    """approved_by with surrounding whitespace but non-whitespace content is accepted."""
    mgr = _fresh_manager()
    mgr.emergency_shutdown(initiated_by="Joe", reason="Test")
    # "  Jared  " strips to "Jared" which is non-empty — should pass
    result = mgr.resume_trading(approved_by="  Jared  ")
    assert result["success"] is True
    assert mgr.is_shutdown_active() is False


# ---------------------------------------------------------------------------
# emergency_shutdown — reason edge cases
# ---------------------------------------------------------------------------

def test_shutdown_empty_reason_succeeds():
    """Empty string reason is accepted — reason field has no validation requirement."""
    mgr = _fresh_manager()
    result = mgr.emergency_shutdown(initiated_by="Joe", reason="")
    assert result["success"] is True
    assert result["reason"] == ""


def test_shutdown_reason_with_special_characters_succeeds():
    """Reason with special characters, newlines, and unicode is stored correctly."""
    mgr = _fresh_manager()
    reason = "Flash crash: SPY -5.1% @ 14:32 UTC\nTriggered by algo\n日本語テスト"
    result = mgr.emergency_shutdown(initiated_by="Joe", reason=reason)
    assert result["success"] is True
    assert result["reason"] == reason


def test_shutdown_very_long_reason_succeeds():
    """Reason string of 10 000 characters is accepted without truncation."""
    mgr = _fresh_manager()
    long_reason = "Market anomaly detected. " * 400  # ~10 000 chars
    result = mgr.emergency_shutdown(initiated_by="Joe", reason=long_reason)
    assert result["success"] is True
    assert result["reason"] == long_reason


def test_shutdown_initiated_by_empty_string_succeeds():
    """initiated_by='' is technically allowed — no validation on this field."""
    mgr = _fresh_manager()
    result = mgr.emergency_shutdown(initiated_by="", reason="Automated trigger")
    assert result["success"] is True


# ---------------------------------------------------------------------------
# Multiple rapid shutdowns
# ---------------------------------------------------------------------------

def test_three_rapid_shutdowns_all_succeed():
    """Three consecutive shutdowns without resume all return success."""
    mgr = _fresh_manager()
    r1 = mgr.emergency_shutdown(initiated_by="Joe", reason="Shutdown 1")
    r2 = mgr.emergency_shutdown(initiated_by="Jared", reason="Shutdown 2")
    r3 = mgr.emergency_shutdown(initiated_by="System", reason="Shutdown 3")
    assert r1["success"] is True
    assert r2["success"] is True
    assert r3["success"] is True
    assert mgr.is_shutdown_active() is True


def test_rapid_shutdown_resume_cycles_maintain_correct_state():
    """5 shutdown+resume cycles leave the manager in the resumed (inactive) state."""
    mgr = _fresh_manager()
    for i in range(5):
        mgr.emergency_shutdown(initiated_by="Joe", reason=f"Cycle {i}")
        mgr.resume_trading(approved_by="Jared")
    assert mgr.is_shutdown_active() is False


def test_rapid_shutdown_resume_history_count():
    """5 shutdown+resume cycles produce exactly 10 history entries."""
    mgr = _fresh_manager()
    for i in range(5):
        mgr.emergency_shutdown(initiated_by="Joe", reason=f"Cycle {i}")
        mgr.resume_trading(approved_by="Jared")
    history = mgr.get_shutdown_history()
    assert len(history) == 10


# ---------------------------------------------------------------------------
# History accumulation
# ---------------------------------------------------------------------------

def test_history_empty_on_fresh_manager():
    """Brand-new ShutdownManager has empty history."""
    mgr = _fresh_manager()
    assert mgr.get_shutdown_history() == []


def test_history_after_single_shutdown_has_one_entry():
    """One shutdown produces exactly one history entry with event_type='shutdown'."""
    mgr = _fresh_manager()
    mgr.emergency_shutdown(initiated_by="Joe", reason="Test")
    history = mgr.get_shutdown_history()
    assert len(history) == 1
    assert history[0]["event_type"] == "shutdown"


def test_history_entry_contains_all_required_fields():
    """Each history entry contains timestamp, initiated_by, reason, orders_cancelled,
    actions_taken, and event_type."""
    mgr = _fresh_manager()
    mgr.emergency_shutdown(initiated_by="Joe", reason="Full field test")
    entry = mgr.get_shutdown_history()[0]
    required_fields = {"timestamp", "initiated_by", "reason", "orders_cancelled",
                       "actions_taken", "event_type"}
    assert required_fields.issubset(entry.keys())


def test_history_returns_copy_not_internal_reference():
    """Mutating the returned history list must not affect the manager's internal state."""
    mgr = _fresh_manager()
    mgr.emergency_shutdown(initiated_by="Joe", reason="Test")
    history = mgr.get_shutdown_history()
    history.clear()  # mutate the returned list
    # Internal history should still have the entry
    assert len(mgr.get_shutdown_history()) == 1


def test_large_history_accumulation():
    """100 shutdown events accumulate correctly without data loss."""
    mgr = _fresh_manager()
    for i in range(100):
        mgr.emergency_shutdown(initiated_by=f"User{i}", reason=f"Event {i}")
    history = mgr.get_shutdown_history()
    assert len(history) == 100
    assert history[0]["initiated_by"] == "User0"
    assert history[99]["initiated_by"] == "User99"


# ---------------------------------------------------------------------------
# get_shutdown_status — no prior events
# ---------------------------------------------------------------------------

def test_status_before_any_events():
    """get_shutdown_status on a fresh manager has active=False and last_event=None."""
    mgr = _fresh_manager()
    status = mgr.get_shutdown_status()
    assert status["active"] is False
    assert status["last_event"] is None


def test_status_last_event_after_resume_shows_resume():
    """After shutdown + resume, last_event in status reflects the resume entry."""
    mgr = _fresh_manager()
    mgr.emergency_shutdown(initiated_by="Joe", reason="Drill")
    mgr.resume_trading(approved_by="Jared")
    status = mgr.get_shutdown_status()
    assert status["active"] is False
    assert status["last_event"]["event_type"] == "resume"


def test_status_trading_mode_reflects_env():
    """trading_mode in status matches the TRADING_MODE env var (paper)."""
    mgr = _fresh_manager()
    status = mgr.get_shutdown_status()
    assert status["trading_mode"] == "paper"


# ---------------------------------------------------------------------------
# cancel_all_orders — mock mode
# ---------------------------------------------------------------------------

def test_cancel_all_orders_returns_list_type():
    """cancel_all_orders in mock mode always returns a list."""
    mgr = _fresh_manager()
    result = mgr.cancel_all_orders()
    assert isinstance(result, list)


def test_cancel_all_orders_returns_empty_in_mock_mode():
    """cancel_all_orders in mock mode returns an empty list (no real orders)."""
    mgr = _fresh_manager()
    result = mgr.cancel_all_orders()
    assert result == []


def test_shutdown_result_orders_cancelled_is_zero_in_mock():
    """In mock mode, emergency_shutdown reports orders_cancelled = 0."""
    mgr = _fresh_manager()
    result = mgr.emergency_shutdown(initiated_by="Joe", reason="Mock test")
    assert result["orders_cancelled"] == 0


# ---------------------------------------------------------------------------
# force_paper_mode
# ---------------------------------------------------------------------------

def test_force_paper_mode_message_contains_restart():
    """force_paper_mode message mentions restart requirement."""
    mgr = _fresh_manager()
    result = mgr.force_paper_mode()
    assert "restart" in result["message"].lower()


def test_force_paper_mode_current_mode_is_paper():
    """force_paper_mode current_mode equals 'paper' in test env."""
    mgr = _fresh_manager()
    result = mgr.force_paper_mode()
    assert result["current_mode"] == "paper"


def test_force_paper_mode_called_during_shutdown_succeeds():
    """force_paper_mode can be called while shutdown is active."""
    mgr = _fresh_manager()
    mgr.emergency_shutdown(initiated_by="Joe", reason="Test")
    result = mgr.force_paper_mode()
    assert result["success"] is True
