"""
Reporting & Export router for the Wasden Watch trading dashboard.

Endpoints for daily, weekly, monthly reports, paper trading summary,
and JSON export downloads.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.config import settings
from app.services.reporting import ReportGenerator

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _get_generator() -> ReportGenerator:
    """Return a ReportGenerator configured for current mock/live mode."""
    return ReportGenerator(use_mock=settings.use_mock_data)


# ------------------------------------------------------------------
# Daily report
# ------------------------------------------------------------------

@router.get("/daily/{date}")
async def get_daily_report(date: str):
    """
    Generate a daily report for the given date.

    Date format: YYYY-MM-DD
    """
    # Basic date validation
    if len(date) != 10 or date[4] != "-" or date[7] != "-":
        raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format")

    gen = _get_generator()
    return gen.generate_daily_report(date)


# ------------------------------------------------------------------
# Weekly report
# ------------------------------------------------------------------

@router.get("/weekly/{week_start}")
async def get_weekly_report(week_start: str):
    """
    Generate a weekly report starting from week_start.

    Date format: YYYY-MM-DD (should be a Monday)
    """
    if len(week_start) != 10 or week_start[4] != "-" or week_start[7] != "-":
        raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format")

    gen = _get_generator()
    return gen.generate_weekly_report(week_start)


# ------------------------------------------------------------------
# Monthly report
# ------------------------------------------------------------------

@router.get("/monthly/{month}")
async def get_monthly_report(month: str):
    """
    Generate a monthly report.

    Month format: YYYY-MM
    """
    if len(month) != 7 or month[4] != "-":
        raise HTTPException(status_code=400, detail="Month must be in YYYY-MM format")

    gen = _get_generator()
    return gen.generate_monthly_report(month)


# ------------------------------------------------------------------
# Export as JSON download
# ------------------------------------------------------------------

@router.get("/export/{report_type}/{period}")
async def export_report(report_type: str, period: str):
    """
    Export a report as a downloadable JSON file.

    Supported report_type values: daily, weekly, monthly
    Period format depends on report_type:
    - daily: YYYY-MM-DD
    - weekly: YYYY-MM-DD
    - monthly: YYYY-MM
    """
    gen = _get_generator()

    if report_type == "daily":
        report = gen.generate_daily_report(period)
    elif report_type == "weekly":
        report = gen.generate_weekly_report(period)
    elif report_type == "monthly":
        report = gen.generate_monthly_report(period)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown report type: {report_type}. Use daily, weekly, or monthly.",
        )

    json_str = gen.export_to_json(report)
    filename = f"wasden_watch_{report_type}_{period}.json"

    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ------------------------------------------------------------------
# Paper trading summary
# ------------------------------------------------------------------

@router.get("/paper-trading-summary")
async def get_paper_trading_summary():
    """
    Generate the current paper trading summary.

    Matches the docs/paper_trading_log.md template structure with
    sections: setup, daily_log, weekly_review, monthly_assessment.
    """
    gen = _get_generator()
    return gen.generate_paper_trading_summary()
