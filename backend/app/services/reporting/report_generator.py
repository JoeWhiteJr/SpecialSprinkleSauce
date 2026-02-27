"""
Report generator for the Wasden Watch trading dashboard.

Produces daily, weekly, monthly, and paper-trading-summary reports
by assembling data from mock generators (or, in production, from Supabase).
Supports JSON and CSV export.
"""

import csv
import io
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("wasden_watch.reporting")


class ReportGenerator:
    """Generate structured reports from portfolio, journal, and screening data."""

    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _now_iso(self) -> str:
        """Return current UTC timestamp in ISO-8601 format."""
        return datetime.utcnow().isoformat() + "Z"

    def _trading_mode(self) -> str:
        """Return the current TRADING_MODE from config."""
        from app.config import settings
        return settings.trading_mode

    def _mock_trades_for_date(self, date_str: str) -> list[dict]:
        """Extract executed trades from journal entries matching a date."""
        from app.mock.generators import generate_journal_entries

        entries = generate_journal_entries()
        trades = []
        for entry in entries:
            if not entry["execution"]["executed"]:
                continue
            # Compare date portion of the timestamp
            entry_date = entry["timestamp"][:10]
            if entry_date == date_str:
                trades.append({
                    "ticker": entry["ticker"],
                    "action": entry["final_decision"]["action"],
                    "fill_price": entry["execution"]["fill_price"],
                    "slippage": entry["execution"]["slippage"],
                    "order_id": entry["execution"]["order_id"],
                    "position_size": entry["final_decision"]["recommended_position_size"],
                    "timestamp": entry["timestamp"],
                })
        return trades

    def _mock_alerts_for_date(self, date_str: str) -> list[dict]:
        """Extract risk alerts matching a date."""
        from app.mock.generators import generate_risk_alerts

        alerts = generate_risk_alerts()
        return [
            a for a in alerts
            if a["timestamp"][:10] == date_str
        ]

    def _mock_positions(self) -> list[dict]:
        """Return current positions from mock data."""
        from app.mock.generators import generate_positions
        return generate_positions()

    def _mock_pnl_for_date(self, date_str: str) -> dict:
        """Extract PnL snapshot for a given date."""
        from app.mock.generators import generate_portfolio_snapshots

        snapshots = generate_portfolio_snapshots()
        for snap in snapshots:
            if snap["date"] == date_str:
                return {
                    "portfolio_value": snap["portfolio_value"],
                    "daily_pnl": snap["daily_pnl"],
                    "daily_pnl_pct": snap["daily_pnl_pct"],
                    "cumulative_pnl": snap["cumulative_pnl"],
                    "cumulative_pnl_pct": snap["cumulative_pnl_pct"],
                    "spy_daily_pnl_pct": snap["spy_daily_pnl_pct"],
                    "spy_cumulative_pnl_pct": snap["spy_cumulative_pnl_pct"],
                    "cash_balance": snap["cash_balance"],
                }
        # If date not found, return zeroed summary
        return {
            "portfolio_value": 100_000.0,
            "daily_pnl": 0.0,
            "daily_pnl_pct": 0.0,
            "cumulative_pnl": 0.0,
            "cumulative_pnl_pct": 0.0,
            "spy_daily_pnl_pct": 0.0,
            "spy_cumulative_pnl_pct": 0.0,
            "cash_balance": 35_000.0,
        }

    def _mock_pipeline_runs_for_date(self, date_str: str) -> list[dict]:
        """Extract screening/pipeline runs matching a date."""
        from app.mock.generators import generate_screening_runs

        runs = generate_screening_runs()
        return [
            r for r in runs
            if r["timestamp"][:10] == date_str
        ]

    # ------------------------------------------------------------------
    # Daily report
    # ------------------------------------------------------------------

    def generate_daily_report(self, date_str: str) -> dict:
        """
        Generate a daily report for the given date (YYYY-MM-DD).

        Returns a dict with: metadata, pipeline_runs, trades_executed,
        pnl_summary, alerts, positions.
        """
        logger.info("Generating daily report for %s (mock=%s)", date_str, self.use_mock)

        metadata = {
            "report_type": "daily",
            "date": date_str,
            "generated_at": self._now_iso(),
            "trading_mode": self._trading_mode(),
        }

        if self.use_mock:
            pipeline_runs = self._mock_pipeline_runs_for_date(date_str)
            trades = self._mock_trades_for_date(date_str)
            pnl = self._mock_pnl_for_date(date_str)
            alerts = self._mock_alerts_for_date(date_str)
            positions = self._mock_positions()
        else:
            # Production path: query Supabase
            # (stubbed — returns empty until DB integration)
            pipeline_runs = []
            trades = []
            pnl = self._mock_pnl_for_date(date_str)
            alerts = []
            positions = []

        return {
            "metadata": metadata,
            "pipeline_runs": pipeline_runs,
            "trades_executed": trades,
            "pnl_summary": pnl,
            "alerts": alerts,
            "positions": positions,
        }

    # ------------------------------------------------------------------
    # Weekly report
    # ------------------------------------------------------------------

    def generate_weekly_report(self, week_start: str) -> dict:
        """
        Generate a weekly report starting from week_start (YYYY-MM-DD, Monday).

        Aggregates 5 daily reports (Mon-Fri) and adds wasden verdicts,
        model performance, screening summary, and risk events.
        """
        logger.info("Generating weekly report for week starting %s", week_start)

        start_date = datetime.strptime(week_start, "%Y-%m-%d")

        # Aggregate 5 business days
        daily_summaries = []
        all_trades = []
        all_alerts = []
        for day_offset in range(5):
            day = start_date + timedelta(days=day_offset)
            day_str = day.strftime("%Y-%m-%d")
            daily = self.generate_daily_report(day_str)
            daily_summaries.append({
                "date": day_str,
                "pnl_summary": daily["pnl_summary"],
                "trades_count": len(daily["trades_executed"]),
                "alerts_count": len(daily["alerts"]),
            })
            all_trades.extend(daily["trades_executed"])
            all_alerts.extend(daily["alerts"])

        # Wasden verdict breakdown from journal entries
        wasden_verdicts = self._aggregate_wasden_verdicts(week_start)
        model_performance = self._aggregate_model_performance()
        screening_summary = self._aggregate_screening_summary(week_start)

        metadata = {
            "report_type": "weekly",
            "week_start": week_start,
            "week_end": (start_date + timedelta(days=4)).strftime("%Y-%m-%d"),
            "generated_at": self._now_iso(),
            "trading_mode": self._trading_mode(),
        }

        return {
            "metadata": metadata,
            "daily_summaries": daily_summaries,
            "wasden_verdicts": wasden_verdicts,
            "model_performance": model_performance,
            "screening_summary": screening_summary,
            "risk_events": all_alerts,
        }

    def _aggregate_wasden_verdicts(self, week_start: str) -> dict:
        """Count wasden verdicts from journal entries in the given week."""
        from app.mock.generators import generate_journal_entries

        entries = generate_journal_entries()
        start = datetime.strptime(week_start, "%Y-%m-%d")
        end = start + timedelta(days=5)

        approve = neutral = veto = 0
        for entry in entries:
            entry_date = datetime.fromisoformat(entry["timestamp"].replace("Z", ""))
            if start <= entry_date < end:
                verdict = entry["wasden_verdict"]["verdict"]
                if verdict == "APPROVE":
                    approve += 1
                elif verdict == "NEUTRAL":
                    neutral += 1
                elif verdict == "VETO":
                    veto += 1

        return {
            "approve": approve,
            "neutral": neutral,
            "veto": veto,
            "total": approve + neutral + veto,
        }

    def _aggregate_model_performance(self) -> dict:
        """Mock model performance metrics."""
        from app.mock.generators import generate_journal_entries

        entries = generate_journal_entries()
        composites = [e["quant_scores"]["composite"] for e in entries]
        avg_composite = sum(composites) / max(len(composites), 1)

        return {
            "average_composite_score": round(avg_composite, 4),
            "high_disagreement_count": sum(
                1 for e in entries if e["quant_scores"]["high_disagreement_flag"]
            ),
            "total_evaluations": len(entries),
        }

    def _aggregate_screening_summary(self, week_start: str) -> dict:
        """Summarize screening runs from the week."""
        from app.mock.generators import generate_screening_runs

        runs = generate_screening_runs()
        start = datetime.strptime(week_start, "%Y-%m-%d")
        end = start + timedelta(days=5)

        week_runs = []
        for run in runs:
            run_date = datetime.fromisoformat(run["timestamp"].replace("Z", ""))
            if start <= run_date < end:
                week_runs.append(run)

        return {
            "runs_count": len(week_runs),
            "total_candidates_screened": sum(
                run["stages"][0]["input_count"] for run in week_runs
            ) if week_runs else 0,
            "total_final_candidates": sum(
                len(run["final_candidates"]) for run in week_runs
            ) if week_runs else 0,
        }

    # ------------------------------------------------------------------
    # Monthly report
    # ------------------------------------------------------------------

    def generate_monthly_report(self, month: str) -> dict:
        """
        Generate a monthly report for the given month (YYYY-MM).

        Includes returns vs SPY, trade stats, risk events, screening
        funnel summary, model accuracy, top winners, and top losers.
        """
        logger.info("Generating monthly report for %s", month)

        from app.mock.generators import (
            generate_portfolio_snapshots,
            generate_portfolio_summary,
            generate_positions,
            generate_risk_alerts,
            generate_screening_runs,
        )

        snapshots = generate_portfolio_snapshots()
        summary = generate_portfolio_summary()
        positions = generate_positions()
        alerts = generate_risk_alerts()
        screening_runs = generate_screening_runs()

        # Filter snapshots for the given month
        month_snapshots = [s for s in snapshots if s["date"].startswith(month)]
        month_alerts = [a for a in alerts if a["timestamp"][:7] == month]

        # Returns vs SPY
        if month_snapshots:
            first = month_snapshots[0]
            last = month_snapshots[-1]
            portfolio_return = last["cumulative_pnl_pct"] - first["cumulative_pnl_pct"]
            spy_return = last["spy_cumulative_pnl_pct"] - first["spy_cumulative_pnl_pct"]
        else:
            portfolio_return = summary.get("total_pnl_pct", 0.0)
            spy_return = 0.0

        returns_vs_spy = {
            "portfolio_return_pct": round(portfolio_return, 4),
            "spy_return_pct": round(spy_return, 4),
            "alpha": round(portfolio_return - spy_return, 4),
        }

        # Trade stats
        closed = [p for p in positions if p["status"] == "closed"]
        winners = sorted(
            [p for p in closed if p["pnl"] > 0],
            key=lambda p: p["pnl"],
            reverse=True,
        )
        losers = sorted(
            [p for p in closed if p["pnl"] <= 0],
            key=lambda p: p["pnl"],
        )

        # Screening funnel summary
        if screening_runs:
            latest = screening_runs[0]
            funnel = {
                stage["stage_name"]: {
                    "input": stage["input_count"],
                    "output": stage["output_count"],
                }
                for stage in latest["stages"]
            }
        else:
            funnel = {}

        # Model accuracy (from mock composite scores)
        model_accuracy = self._aggregate_model_performance()

        metadata = {
            "report_type": "monthly",
            "month": month,
            "generated_at": self._now_iso(),
            "trading_mode": self._trading_mode(),
        }

        return {
            "metadata": metadata,
            "returns_vs_spy": returns_vs_spy,
            "total_trades": len(closed),
            "win_rate": summary["win_rate"],
            "risk_events_count": len(month_alerts),
            "screening_funnel": funnel,
            "model_accuracy": model_accuracy,
            "top_winners": [
                {"ticker": p["ticker"], "pnl": p["pnl"], "pnl_pct": p["pnl_pct"]}
                for p in winners[:3]
            ],
            "top_losers": [
                {"ticker": p["ticker"], "pnl": p["pnl"], "pnl_pct": p["pnl_pct"]}
                for p in losers[:3]
            ],
        }

    # ------------------------------------------------------------------
    # Paper trading summary
    # ------------------------------------------------------------------

    def generate_paper_trading_summary(self) -> dict:
        """
        Generate a paper trading summary matching the docs/paper_trading_log.md
        template structure.

        Sections: setup, daily_log, weekly_review, monthly_assessment.
        """
        logger.info("Generating paper trading summary")

        from app.mock.generators import (
            generate_portfolio_summary,
            generate_portfolio_snapshots,
            generate_journal_entries,
            generate_risk_alerts,
        )

        summary = generate_portfolio_summary()
        snapshots = generate_portfolio_snapshots()
        entries = generate_journal_entries()
        alerts = generate_risk_alerts()

        # Setup section
        setup = {
            "trading_mode": self._trading_mode(),
            "initial_capital": 100_000.0,
            "start_date": snapshots[0]["date"] if snapshots else None,
            "pilot_tickers": ["NVDA", "PYPL", "NFLX", "TSM", "XOM", "AAPL"],
            "risk_parameters": {
                "max_position_pct": 0.12,
                "min_cash_reserve_pct": 0.10,
                "consecutive_loss_warning": 7,
            },
        }

        # Daily log: last 5 snapshots
        daily_log = []
        recent_snapshots = snapshots[-5:] if len(snapshots) >= 5 else snapshots
        for snap in recent_snapshots:
            day_trades = self._mock_trades_for_date(snap["date"])
            day_alerts = [a for a in alerts if a["timestamp"][:10] == snap["date"]]
            daily_log.append({
                "date": snap["date"],
                "portfolio_value": snap["portfolio_value"],
                "daily_pnl": snap["daily_pnl"],
                "daily_pnl_pct": snap["daily_pnl_pct"],
                "trades_executed": len(day_trades),
                "alerts_triggered": len(day_alerts),
            })

        # Weekly review
        weekly_review = {
            "total_trades": summary["total_trades"],
            "win_rate": summary["win_rate"],
            "total_pnl": summary["total_pnl"],
            "total_pnl_pct": summary["total_pnl_pct"],
            "open_positions": summary["open_positions"],
            "journal_entries_count": len(entries),
            "wasden_verdicts": {
                "approve": sum(
                    1 for e in entries if e["wasden_verdict"]["verdict"] == "APPROVE"
                ),
                "neutral": sum(
                    1 for e in entries if e["wasden_verdict"]["verdict"] == "NEUTRAL"
                ),
                "veto": sum(
                    1 for e in entries if e["wasden_verdict"]["verdict"] == "VETO"
                ),
            },
        }

        # Monthly assessment
        latest = snapshots[-1] if snapshots else {}
        monthly_assessment = {
            "current_portfolio_value": latest.get("portfolio_value", 100_000.0),
            "cumulative_pnl": latest.get("cumulative_pnl", 0.0),
            "cumulative_pnl_pct": latest.get("cumulative_pnl_pct", 0.0),
            "spy_cumulative_pnl_pct": latest.get("spy_cumulative_pnl_pct", 0.0),
            "alpha": round(
                latest.get("cumulative_pnl_pct", 0.0)
                - latest.get("spy_cumulative_pnl_pct", 0.0),
                4,
            ),
            "risk_events_total": len(alerts),
            "critical_alerts": sum(1 for a in alerts if a["severity"] == "critical"),
        }

        metadata = {
            "report_type": "paper_trading_summary",
            "generated_at": self._now_iso(),
            "trading_mode": self._trading_mode(),
        }

        return {
            "metadata": metadata,
            "setup": setup,
            "daily_log": daily_log,
            "weekly_review": weekly_review,
            "monthly_assessment": monthly_assessment,
        }

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------

    def export_to_json(self, report: dict) -> str:
        """Serialize a report dict to a formatted JSON string."""
        return json.dumps(report, indent=2, default=str)

    def export_to_csv(self, report: dict, section: str = "trades") -> str:
        """
        Flatten a section of the report into CSV format.

        Supported sections depend on the report type:
        - "trades_executed" (daily report)
        - "positions" (daily report)
        - "daily_summaries" (weekly report)
        - "top_winners" / "top_losers" (monthly report)
        - "daily_log" (paper trading summary)

        Falls back to the given section key in the report dict.
        If the section is missing or empty, returns an empty CSV with
        just a header comment.
        """
        # Resolve common aliases
        section_key = section
        if section == "trades":
            # Try trades_executed first, fall back to section name
            section_key = "trades_executed" if "trades_executed" in report else section

        rows = report.get(section_key, [])

        if not rows or not isinstance(rows, list):
            return "# No data for section: {}\n".format(section_key)

        # Flatten nested dicts in rows — convert dict values to JSON strings
        flat_rows = []
        for row in rows:
            flat = {}
            for key, value in row.items():
                if isinstance(value, dict):
                    flat[key] = json.dumps(value, default=str)
                elif isinstance(value, list):
                    flat[key] = json.dumps(value, default=str)
                else:
                    flat[key] = value
            flat_rows.append(flat)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=flat_rows[0].keys())
        writer.writeheader()
        writer.writerows(flat_rows)
        return output.getvalue()
