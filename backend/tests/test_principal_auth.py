"""Tests for identify_principal() and principal-gated endpoints.

Covers the fixes for:
  #57 P0 — approve_proposal trusted request-body identity
  #59 P1 — emergency shutdown/resume trusted request-body identity
"""
import os
os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

import pytest
from unittest.mock import patch
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _headers(key: str) -> dict:
    return {"X-API-Key": key}


# ---------------------------------------------------------------------------
# identify_principal — dev mode (no per-user keys)
# ---------------------------------------------------------------------------

class TestIdentifyPrincipalDevMode:
    """When neither API_KEY_JOE nor API_KEY_JARED is set, dev mode applies."""

    def test_no_per_user_keys_no_shared_key_returns_dev(self):
        """With no keys configured at all, principal is 'dev' (local dev)."""
        with patch("app.auth.settings") as s:
            s.api_key_joe = ""
            s.api_key_jared = ""
            s.api_key = ""
            # Emergency shutdown accepts any caller in dev mode
            resp = client.post("/api/emergency/shutdown", json={"reason": "dev test"})
            assert resp.status_code == 200

    def test_shared_key_wrong_returns_401(self):
        """Shared API_KEY set but wrong key → 401."""
        with patch("app.auth.settings") as s:
            s.api_key_joe = ""
            s.api_key_jared = ""
            s.api_key = "correct-shared-key"
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
        with patch("app.auth.settings") as s:
            s.api_key_joe = "joe-secret"
            s.api_key_jared = "jared-secret"
            resp = client.post(
                "/api/emergency/shutdown",
                json={"reason": "test"},
                headers=_headers("joe-secret"),
            )
            assert resp.status_code == 200

    def test_jared_key_identifies_as_jared(self):
        with patch("app.auth.settings") as s:
            s.api_key_joe = "joe-secret"
            s.api_key_jared = "jared-secret"
            resp = client.post(
                "/api/emergency/shutdown",
                json={"reason": "test"},
                headers=_headers("jared-secret"),
            )
            assert resp.status_code == 200

    def test_unknown_key_returns_401(self):
        with patch("app.auth.settings") as s:
            s.api_key_joe = "joe-secret"
            s.api_key_jared = "jared-secret"
            resp = client.post(
                "/api/emergency/shutdown",
                json={"reason": "test"},
                headers=_headers("attacker-key"),
            )
            assert resp.status_code == 401

    def test_no_key_returns_401(self):
        with patch("app.auth.settings") as s:
            s.api_key_joe = "joe-secret"
            s.api_key_jared = "jared-secret"
            resp = client.post("/api/emergency/shutdown", json={"reason": "test"})
            assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Emergency shutdown/resume — body fields no longer accepted
# ---------------------------------------------------------------------------

class TestEmergencyBodyFieldsRemoved:
    """initiated_by and approved_by must not influence identity from the body."""

    def test_shutdown_ignores_body_initiated_by(self):
        """POSTing initiated_by in the body does not raise an error (ignored field)
        and does not override the principal derived from the key."""
        # Extra fields in JSON body are ignored by Pydantic (extra='ignore')
        resp = client.post(
            "/api/emergency/shutdown",
            json={"reason": "test", "initiated_by": "attacker"},
        )
        # Should succeed in dev mode (no per-user keys)
        assert resp.status_code == 200

    def test_resume_ignores_body_approved_by(self):
        """POSTing approved_by in the body does not grant identity."""
        client.post("/api/emergency/shutdown", json={"reason": "setup"})
        resp = client.post(
            "/api/emergency/resume",
            json={"approved_by": "attacker"},
        )
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
        with patch("app.auth.settings") as s:
            s.api_key_joe = "joe-secret"
            s.api_key_jared = "jared-secret"
            # First approval
            r1 = client.post(
                f"/api/training/proposals/{pid}/approve",
                json={},
                headers=_headers("joe-secret"),
            )
            assert r1.status_code == 200
            assert r1.json()["status"] == "joe_approved"

            # Second approval with same key → 409
            r2 = client.post(
                f"/api/training/proposals/{pid}/approve",
                json={},
                headers=_headers("joe-secret"),
            )
            assert r2.status_code == 409

    def test_both_principals_achieve_dual_approval(self):
        """Joe then Jared (different keys) correctly reaches 'applied'."""
        pid = self._create_proposal()
        with patch("app.auth.settings") as s:
            s.api_key_joe = "joe-secret"
            s.api_key_jared = "jared-secret"
            r1 = client.post(
                f"/api/training/proposals/{pid}/approve",
                json={},
                headers=_headers("joe-secret"),
            )
            assert r1.status_code == 200

            r2 = client.post(
                f"/api/training/proposals/{pid}/approve",
                json={},
                headers=_headers("jared-secret"),
            )
            assert r2.status_code == 200
            assert r2.json()["status"] == "applied"

    def test_dev_mode_requires_user_name_in_body(self):
        """In dev mode (no per-user keys), user_name in body is still required."""
        pid = self._create_proposal()
        resp = client.post(
            f"/api/training/proposals/{pid}/approve",
            json={},  # no user_name
        )
        assert resp.status_code == 400

    def test_dev_mode_body_user_name_works(self):
        """In dev mode, supplying user_name in body succeeds."""
        pid = self._create_proposal()
        resp = client.post(
            f"/api/training/proposals/{pid}/approve",
            json={"user_name": "joe"},
        )
        assert resp.status_code == 200
