"""Integration tests for Week 10 cross-service API endpoints."""
import os
os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestEmergencyEndpoints:
    def test_get_status(self):
        resp = client.get("/api/emergency/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "active" in data or "is_shutdown" in data

    def test_shutdown_and_resume(self):
        resp = client.post("/api/emergency/shutdown", json={"initiated_by": "test", "reason": "integration test"})
        assert resp.status_code == 200
        resp = client.post("/api/emergency/resume", json={"approved_by": "test"})
        assert resp.status_code == 200

    def test_get_history(self):
        resp = client.get("/api/emergency/history")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestBacktestingEndpoints:
    def test_run_backtest(self):
        resp = client.post("/api/backtesting/run", json={
            "ticker": "NVDA", "start_date": "2024-01-01", "end_date": "2024-12-31", "strategy": "sprinkle_sauce_v1"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "metrics" in data

    def test_list_runs(self):
        resp = client.get("/api/backtesting/runs")
        assert resp.status_code == 200

    def test_list_strategies(self):
        resp = client.get("/api/backtesting/strategies")
        assert resp.status_code == 200


class TestRebalancingEndpoints:
    def test_get_drift(self):
        resp = client.get("/api/rebalancing/drift")
        assert resp.status_code == 200
        assert "rebalance_needed" in resp.json()

    def test_get_targets(self):
        resp = client.get("/api/rebalancing/targets")
        assert resp.status_code == 200

    def test_preview_rebalance(self):
        resp = client.post("/api/rebalancing/preview")
        assert resp.status_code == 200


class TestReportsEndpoints:
    def test_daily_report(self):
        resp = client.get("/api/reports/daily/2024-12-15")
        assert resp.status_code == 200

    def test_paper_trading_summary(self):
        resp = client.get("/api/reports/paper-trading-summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "setup" in data or "current" in data


class TestNotificationsEndpoints:
    def test_list_notifications(self):
        resp = client.get("/api/notifications")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_channels(self):
        resp = client.get("/api/notifications/channels")
        assert resp.status_code == 200
