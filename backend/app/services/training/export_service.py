"""Export Service — CSV and Excel export for experiment data.

Generates downloadable files from experiment records, sweep results,
and comparison data. Uses csv module for CSV and openpyxl for Excel.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from typing import Any

logger = logging.getLogger("wasden_watch.training.export_service")


class ExportService:
    """Exports experiment and sweep data to CSV or Excel format."""

    def export_experiments_csv(
        self, experiments: list[dict[str, Any]]
    ) -> str:
        """Export experiments to CSV string."""
        if not experiments:
            return ""

        output = io.StringIO()
        fieldnames = [
            "id", "user_name", "experiment_type", "name", "status",
            "phase", "data_source", "parameters", "results", "notes",
            "created_at", "updated_at",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for exp in experiments:
            row = {**exp}
            row["parameters"] = json.dumps(exp.get("parameters", {}))
            row["results"] = json.dumps(exp.get("results", {}))
            writer.writerow(row)

        return output.getvalue()

    def export_sweeps_csv(
        self, sweep_data: dict[str, Any]
    ) -> str:
        """Export parameter sweep results to CSV string."""
        output = io.StringIO()
        fieldnames = [
            "parameter_name", "value", "win_rate", "sharpe_ratio",
            "max_drawdown", "accuracy", "profit_factor", "sortino_ratio",
            "total_trades",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        param_name = sweep_data.get("parameter_name", "")
        for point in sweep_data.get("results_per_value", []):
            writer.writerow({"parameter_name": param_name, **point})

        return output.getvalue()

    def export_comparison_csv(
        self, experiments: list[dict[str, Any]]
    ) -> str:
        """Export side-by-side comparison to CSV."""
        if not experiments:
            return ""

        output = io.StringIO()
        fieldnames = [
            "id", "name", "user_name", "experiment_type",
            "parameters", "results", "status", "created_at",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for exp in experiments:
            row = {**exp}
            row["parameters"] = json.dumps(exp.get("parameters", {}))
            row["results"] = json.dumps(exp.get("results", {}))
            writer.writerow(row)

        return output.getvalue()

    def export_experiments_excel(
        self, experiments: list[dict[str, Any]]
    ) -> bytes:
        """Export experiments to Excel (.xlsx) bytes.

        Returns raw bytes suitable for a StreamingResponse.
        Falls back to CSV bytes if openpyxl is not installed.
        """
        try:
            from openpyxl import Workbook
        except ImportError:
            logger.warning("openpyxl not installed — falling back to CSV")
            return self.export_experiments_csv(experiments).encode("utf-8")

        wb = Workbook()
        ws = wb.active
        ws.title = "Experiments"

        headers = [
            "ID", "User", "Type", "Name", "Status", "Phase",
            "Data Source", "Parameters", "Results", "Notes",
            "Created At", "Updated At",
        ]
        ws.append(headers)

        for exp in experiments:
            ws.append([
                exp.get("id", ""),
                exp.get("user_name", ""),
                exp.get("experiment_type", ""),
                exp.get("name", ""),
                exp.get("status", ""),
                exp.get("phase", ""),
                exp.get("data_source", ""),
                json.dumps(exp.get("parameters", {})),
                json.dumps(exp.get("results", {})),
                exp.get("notes", ""),
                exp.get("created_at", ""),
                exp.get("updated_at", ""),
            ])

        # Auto-width columns
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()

    def export_sweeps_excel(
        self, sweep_data: dict[str, Any]
    ) -> bytes:
        """Export sweep results to Excel bytes."""
        try:
            from openpyxl import Workbook
        except ImportError:
            return self.export_sweeps_csv(sweep_data).encode("utf-8")

        wb = Workbook()
        ws = wb.active
        ws.title = "Parameter Sweep"

        headers = [
            "Parameter", "Value", "Win Rate", "Sharpe Ratio",
            "Max Drawdown", "Accuracy", "Profit Factor",
            "Sortino Ratio", "Total Trades",
        ]
        ws.append(headers)

        param_name = sweep_data.get("parameter_name", "")
        for point in sweep_data.get("results_per_value", []):
            ws.append([
                param_name,
                point.get("value", 0),
                point.get("win_rate", 0),
                point.get("sharpe_ratio", 0),
                point.get("max_drawdown", 0),
                point.get("accuracy", 0),
                point.get("profit_factor", 0),
                point.get("sortino_ratio", 0),
                point.get("total_trades", 0),
            ])

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 30)

        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()
