"""
CLI entry point for data pipeline batch/backfill operations.

Usage:
    python -m app.cli.pipeline_cli bloomberg path/to/JMWFM_Bloomberg_2026-02-25.xlsx
    python -m app.cli.pipeline_cli load-prices --source dow_jones path/to/file.csv
    python -m app.cli.pipeline_cli load-prices --source emery_sp500 path/to/file.csv
    python -m app.cli.pipeline_cli freshness
"""

import argparse
import json
import logging
import sys

# Configure logging before imports that use it
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("wasden_watch.cli")


def cmd_bloomberg(args):
    """Run Bloomberg Excel pipeline."""
    from app.services.bloomberg_pipeline import run_bloomberg_pipeline

    report = run_bloomberg_pipeline(args.file, upload=not args.dry_run)
    print(json.dumps(report, indent=2, default=str))

    if report.get("failed_tickers", 0) > 0:
        logger.warning(f"{report['failed_tickers']} tickers had errors")
        sys.exit(1)


def cmd_load_prices(args):
    """Load historical price dataset."""
    from app.services.data_loader import load_dow_jones_csv, load_emery_dataset

    if args.source == "dow_jones":
        result = load_dow_jones_csv(args.file)
    elif args.source == "emery_sp500":
        result = load_emery_dataset(args.file)
    else:
        logger.error(f"Unknown source: {args.source}")
        sys.exit(1)

    print(json.dumps(result, indent=2, default=str))

    if result.get("errors"):
        logger.warning(f"{len(result['errors'])} errors during load")


def cmd_freshness(args):
    """Print freshness report."""
    from app.services.bloomberg_pipeline import get_freshness_report

    report = get_freshness_report()
    print(json.dumps(report, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(
        description="Wasden Watch Data Pipeline CLI",
        prog="python -m app.cli.pipeline_cli",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # bloomberg subcommand
    bb = subparsers.add_parser("bloomberg", help="Parse and upload Bloomberg Excel export")
    bb.add_argument("file", help="Path to JMWFM_Bloomberg_YYYY-MM-DD.xlsx")
    bb.add_argument("--dry-run", action="store_true", help="Parse only, skip Supabase upload")
    bb.set_defaults(func=cmd_bloomberg)

    # load-prices subcommand
    lp = subparsers.add_parser("load-prices", help="Load historical price dataset")
    lp.add_argument("file", help="Path to CSV file")
    lp.add_argument(
        "--source",
        required=True,
        choices=["dow_jones", "emery_sp500"],
        help="Dataset source identifier",
    )
    lp.set_defaults(func=cmd_load_prices)

    # freshness subcommand
    fr = subparsers.add_parser("freshness", help="Print Bloomberg data freshness report")
    fr.set_defaults(func=cmd_freshness)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
