"""Unit tests for the Reporting & Export service.

All tests use mock data. No database, no API calls.
"""

import os

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

import csv  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402

from app.services.reporting import ReportGenerator  # noqa: E402


# Shared generator instance (mock mode)
_gen = ReportGenerator(use_mock=True)

# A date that falls within the mock snapshot range (Feb 21, 2026 base)
_MOCK_DATE = "2026-02-21"
_MOCK_WEEK_START = "2026-02-16"
_MOCK_MONTH = "2026-02"


# ---------------------------------------------------------------------------
# Daily report
# ---------------------------------------------------------------------------

def test_daily_report_structure():
    """Daily report has metadata, pipeline_runs, pnl_summary keys."""
    report = _gen.generate_daily_report(_MOCK_DATE)

    assert "metadata" in report
    assert "pipeline_runs" in report
    assert "trades_executed" in report
    assert "pnl_summary" in report
    assert "alerts" in report
    assert "positions" in report

    # pnl_summary should have financial fields
    pnl = report["pnl_summary"]
    assert "portfolio_value" in pnl
    assert "daily_pnl" in pnl


# ---------------------------------------------------------------------------
# Weekly report
# ---------------------------------------------------------------------------

def test_weekly_report_aggregation():
    """Weekly report has daily_summaries list."""
    report = _gen.generate_weekly_report(_MOCK_WEEK_START)

    assert "daily_summaries" in report
    assert isinstance(report["daily_summaries"], list)
    assert len(report["daily_summaries"]) == 5  # Mon-Fri

    # Each daily summary has date and pnl
    for ds in report["daily_summaries"]:
        assert "date" in ds
        assert "pnl_summary" in ds
        assert "trades_count" in ds

    # Also has wasden verdicts and screening summary
    assert "wasden_verdicts" in report
    assert "screening_summary" in report
    assert "risk_events" in report


# ---------------------------------------------------------------------------
# Monthly report
# ---------------------------------------------------------------------------

def test_monthly_report_vs_spy():
    """Monthly report has returns_vs_spy dict with portfolio, spy, and alpha."""
    report = _gen.generate_monthly_report(_MOCK_MONTH)

    assert "returns_vs_spy" in report
    rvs = report["returns_vs_spy"]
    assert "portfolio_return_pct" in rvs
    assert "spy_return_pct" in rvs
    assert "alpha" in rvs

    # Alpha = portfolio - spy
    assert abs(rvs["alpha"] - (rvs["portfolio_return_pct"] - rvs["spy_return_pct"])) < 0.001

    # Other monthly fields
    assert "total_trades" in report
    assert "win_rate" in report
    assert "screening_funnel" in report
    assert "top_winners" in report
    assert "top_losers" in report


# ---------------------------------------------------------------------------
# Export: JSON
# ---------------------------------------------------------------------------

def test_export_json():
    """export_to_json returns a valid JSON string."""
    report = _gen.generate_daily_report(_MOCK_DATE)
    json_str = _gen.export_to_json(report)

    assert isinstance(json_str, str)
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)
    assert "metadata" in parsed


# ---------------------------------------------------------------------------
# Export: CSV
# ---------------------------------------------------------------------------

def test_export_csv():
    """export_to_csv returns valid CSV with headers."""
    report = _gen.generate_daily_report(_MOCK_DATE)

    # Export positions section (always has data in mock)
    csv_str = _gen.export_to_csv(report, section="positions")
    assert isinstance(csv_str, str)

    reader = csv.reader(io.StringIO(csv_str))
    rows = list(reader)
    # Should have a header row + data rows
    assert len(rows) >= 2, "CSV should have header + at least 1 data row"

    # Header should contain expected column names
    header = rows[0]
    assert "ticker" in header
    assert "status" in header


# ---------------------------------------------------------------------------
# Paper trading summary
# ---------------------------------------------------------------------------

def test_paper_trading_summary():
    """Paper trading summary has required sections."""
    report = _gen.generate_paper_trading_summary()

    assert "setup" in report
    assert "daily_log" in report
    assert "weekly_review" in report
    assert "monthly_assessment" in report

    # Setup section
    setup = report["setup"]
    assert setup["trading_mode"] == "paper"
    assert setup["initial_capital"] == 100_000.0
    assert "pilot_tickers" in setup

    # Daily log is a list
    assert isinstance(report["daily_log"], list)
    assert len(report["daily_log"]) > 0

    # Weekly review has trade stats
    wr = report["weekly_review"]
    assert "total_trades" in wr
    assert "win_rate" in wr
    assert "wasden_verdicts" in wr

    # Monthly assessment
    ma = report["monthly_assessment"]
    assert "current_portfolio_value" in ma
    assert "alpha" in ma


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------

def test_report_mock_mode():
    """Reports work without DB connection in mock mode."""
    gen = ReportGenerator(use_mock=True)

    # All report types should succeed without raising
    daily = gen.generate_daily_report(_MOCK_DATE)
    assert daily is not None

    weekly = gen.generate_weekly_report(_MOCK_WEEK_START)
    assert weekly is not None

    monthly = gen.generate_monthly_report(_MOCK_MONTH)
    assert monthly is not None

    summary = gen.generate_paper_trading_summary()
    assert summary is not None


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

def test_report_metadata():
    """All reports have metadata with report_type, generated_at, trading_mode."""
    daily = _gen.generate_daily_report(_MOCK_DATE)
    weekly = _gen.generate_weekly_report(_MOCK_WEEK_START)
    monthly = _gen.generate_monthly_report(_MOCK_MONTH)
    summary = _gen.generate_paper_trading_summary()

    for report in [daily, weekly, monthly, summary]:
        meta = report["metadata"]
        assert "report_type" in meta
        assert "generated_at" in meta
        assert "trading_mode" in meta
        assert meta["trading_mode"] == "paper"
        assert meta["generated_at"].endswith("Z")
