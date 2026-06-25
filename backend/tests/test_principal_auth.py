"""Tests for identify_principal() and principal-gated endpoints.

Covers the fixes for:
  #57 P0 — approve_proposal trusted request-body identity
  #59 P1 — emergency shutdown/resume trusted request-body identity
"""
import os
os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _headers(key: str) -> dict:
    return {"X-API-Key": key}


def _patched_settings(*, joe: str = "", jared: str = "", shared: str = ""):
    """Return a mock settings object with the given key values."""
    s = MagicMock()
    s.api_key = shared
    s.api_key_joe = joe
    s.api_key_jared = jared
    return s


# ---------------------------------------------------------------------------
# identify_principal — dev mode (no per-user keys)
# ---------------------------------------------------------------------------

class TestIdentifyPrincipalDevMode:
    """When neither API_KEY_JOE nor API_KEY_JARED is set, dev mode applies."""

    def test_no_per_user_keys_no_shared_key_returns_dev(self):
        """With no keys configured at all, principal is 'dev' (local dev)."""
        with patch("app.auth.settings", _patched_settings()):
            resp = client.post("/api/emergency/shutdown", json={"reason": "dev test"})
            assert resp.status_code == 200

    def test_shared_key_wrong_returns_401(self):
        """Shared API_KEY set but wrong key → 401."""
        with patch("app.auth.settings", _patched_settings(shared="correct-shared-key")):
            resp = client.post(
                "/api/emergency/shutdown",
                json={"reason": "test"},
                headers=_headers("wrong-key"),
            )
            assert resp.status_code == 401


# ---------------------------------------------------------------------------
# identify_principal — production mode (per-user keys configured)
# ---------------------------------------------------------------------------

class TestIdentifyPrincipalProductionMode:
    """When per-user keys are configured, only matching keys are accepted."""

    def test_joe_key_identifies_as_joe(self):
        mock_s = _patched_settings(joe="joe-secret", jared="jared-secret")
        with patch("app.auth.settings", mock_s):
            resp = client.post(
                "/api/emergency/shutdown",
                json={"reason": "test"},
                headers=_headers("joe-secret"),
            )
            assert resp.status_code == 200

    def test_jared_key_identifies_as_jared(self):
        mock_s = _patched_settings(joe="joe-secret", jared="jared-secret")
        with patch("app.auth.settings", mock_s):
            resp = client.post(
                "/api/emergency/shutdown",
                json={"reason": "test"},
                headers=_headers("jared-secret"),
            )
            assert resp.status_code == 200

    def test_unknown_key_returns_401(self):
        mock_s = _patched_settings(joe="joe-secret", jared="jared-secret")
        with patch("app.auth.settings", mock_s):
            resp = client.post(
                "/api/emergency/shutdown",
                json={"reason": "test"},
                headers=_headers("attacker-key"),
            )
            assert resp.status_code == 401

    def test_no_key_returns_401(self):
        mock_s = _patched_settings(joe="joe-secret", jared="jared-secret")
        with patch("app.auth.settings", mock_s):
            resp = client.post("/api/emergency/shutdown", json={"reason": "test"})
            assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Emergency shutdown/resume — body fields no longer accepted
# ---------------------------------------------------------------------------

class TestEmergencyBodyFieldsRemoved:
    """initiated_by and approved_by must not influence identity from the body."""

    def test_shutdown_ignores_body_initiated_by(self):
        """Extra body fields are ignored; principal still comes from the key."""
        resp = client.post(
            "/api/emergency/shutdown",
            json={"reason": "test", "initiated_by": "attacker"},
        )
        assert resp.status_code == 200

    def test_resume_ignores_body_approved_by(self):
        """approved_by in body does not grant identity."""
        client.post("/api/emergency/shutdown", json={"reason": "setup"})
        resp = client.post("/api/emergency/resume", json={"approved_by": "attacker"})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Dual-approval block — same principal cannot fill both slots (issue #57)
# ---------------------------------------------------------------------------

class TestApprovalDuplicatePrevention:
    """Same principal must not be able to approve both slots."""

    def _create_proposal(self) -> str:
        from app.routers.training import _proposals
        import uuid
        pid = str(uuid.uuid4())
        _proposals[pid] = {
            "id": pid,
            "status": "pending",
            "category": "position_sizing",
            "parameter_name": "max_position_pct",
            "proposed_value": 0.10,
            "current_value": 0.12,
            "rationale": "test",
            "created_at": "2026-06-25T00:00:00Z",
        }
        return pid

    def test_joe_cannot_approve_twice_in_production_mode(self):
        """With per-user keys, joe's key can only fill the joe slot once."""
        pid = self._create_proposal()
        mock_s = _patched_settings(joe="joe-secret", jared="jared-secret")
        # check_approval returns missing=["jared"] so single approval doesn't
        # auto-apply (which would call apply_proposal and need more proposal fields)
        with patch("app.auth.settings", mock_s), \
             patch("app.routers.training._auto_tuner") as mock_tuner:
            mock_tuner.check_approval.return_value = {"missing": ["jared"]}

            r1 = client.post(
                f"/api/training/proposals/{pid}/approve",
                json={},
                headers=_headers("joe-secret"),
            )
            assert r1.status_code == 200
            assert r1.json()["status"] == "joe_approved"

            r2 = client.post(
                f"/api/training/proposals/{pid}/approve",
                json={},
                headers=_headers("joe-secret"),
            )
            assert r2.status_code == 409

    def test_both_principals_achieve_dual_approval(self):
        """Joe then Jared (different keys) correctly reaches 'applied'."""
        pid = self._create_proposal()
        mock_s = _patched_settings(joe="joe-secret", jared="jared-secret")
        with patch("app.auth.settings", mock_s), \
             patch("app.routers.training._auto_tuner") as mock_tuner:
            mock_tuner.check_approval.return_value = {"missing": ["jared"]}
            mock_tuner.apply_proposal.return_value = {"applied": True}

            r1 = client.post(
                f"/api/training/proposals/{pid}/approve",
                json={},
                headers=_headers("joe-secret"),
            )
            assert r1.status_code == 200

            # Second approver: check_approval now shows nothing missing
            mock_tuner.check_approval.return_value = {"missing": []}
            r2 = client.post(
                f"/api/training/proposals/{pid}/approve",
                json={},
                headers=_headers("jared-secret"),
            )
            assert r2.status_code == 200
            assert r2.json()["status"] == "applied"

    def test_dev_mode_requires_user_name_in_body(self):
        """In dev mode (no per-user keys), user_name in body is required."""
        pid = self._create_proposal()
        resp = client.post(
            f"/api/training/proposals/{pid}/approve",
            json={},
        )
        assert resp.status_code == 400

    def test_dev_mode_body_user_name_works(self):
        """In dev mode, supplying user_name in body succeeds."""
        pid = self._create_proposal()
        with patch("app.routers.training._auto_tuner") as mock_tuner:
            mock_tuner.check_approval.return_value = {"missing": ["jared"]}
            resp = client.post(
                f"/api/training/proposals/{pid}/approve",
                json={"user_name": "joe"},
            )
        assert resp.status_code == 200
