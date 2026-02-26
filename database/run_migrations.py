#!/usr/bin/env python3
"""
Migration runner for Wasden Watch database.

Reads DATABASE_URL from environment (or .env file), connects via psycopg2,
and runs all migration files in order followed by seed data.

Usage:
    pip install psycopg2-binary python-dotenv
    python database/run_migrations.py

Or with DATABASE_URL set directly:
    DATABASE_URL=postgresql://... python database/run_migrations.py
"""

import os
import sys
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
SEED_DIR = Path(__file__).parent / "seed"

MIGRATION_FILES = [
    "001_decision_journal.sql",
    "002_trade_recommendations.sql",
    "003_portfolio_positions.sql",
    "004_portfolio_daily_snapshot.sql",
    "005_jury_votes.sql",
    "006_debate_transcripts.sql",
    "007_veto_overrides.sql",
    "008_risk_alerts.sql",
    "009_consecutive_loss_tracker.sql",
    "010_bias_metrics.sql",
    "011_bloomberg_fundamentals.sql",
    "012_watchlist_screening_settings.sql",
    "013_rls_policies.sql",
    "014_price_history.sql",
    "015_wasden_verdicts.sql",
]

SEED_FILES = [
    "001_seed.sql",
]


def load_env():
    """Try to load DATABASE_URL from .env file if not already set."""
    if os.getenv("DATABASE_URL"):
        return

    # Walk up from this script to find .env
    for parent in [Path(__file__).parent.parent, Path.cwd()]:
        env_path = parent / ".env"
        if env_path.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_path)
                return
            except ImportError:
                # Manual parse as fallback
                for line in env_path.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key == "DATABASE_URL":
                            os.environ["DATABASE_URL"] = value
                            return


def run():
    load_env()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL is not set.")
        print("Set it as an environment variable or in a .env file.")
        print("Example: DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres")
        sys.exit(1)

    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 is not installed.")
        print("Install it with: pip install psycopg2-binary")
        sys.exit(1)

    # Mask password in output
    display_url = database_url
    if "@" in display_url:
        pre_at = display_url.split("@")[0]
        if ":" in pre_at:
            protocol_user = pre_at.rsplit(":", 1)[0]
            display_url = protocol_user + ":***@" + database_url.split("@", 1)[1]

    print(f"Connecting to: {display_url}")
    conn = psycopg2.connect(database_url)
    conn.autocommit = True
    cur = conn.cursor()

    # Run migrations
    print(f"\n{'=' * 50}")
    print("Running migrations")
    print(f"{'=' * 50}")

    for filename in MIGRATION_FILES:
        filepath = MIGRATIONS_DIR / filename
        if not filepath.exists():
            print(f"  SKIP  {filename} (file not found)")
            continue
        try:
            sql = filepath.read_text()
            cur.execute(sql)
            print(f"  OK    {filename}")
        except psycopg2.errors.DuplicateTable:
            conn.rollback()
            conn.autocommit = True
            print(f"  SKIP  {filename} (table already exists)")
        except Exception as e:
            conn.rollback()
            conn.autocommit = True
            print(f"  FAIL  {filename}: {e}")

    # Run seed files
    print(f"\n{'=' * 50}")
    print("Running seed data")
    print(f"{'=' * 50}")

    for filename in SEED_FILES:
        filepath = SEED_DIR / filename
        if not filepath.exists():
            print(f"  SKIP  {filename} (file not found)")
            continue
        try:
            sql = filepath.read_text()
            cur.execute(sql)
            print(f"  OK    {filename}")
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            conn.autocommit = True
            print(f"  SKIP  {filename} (seed data already exists)")
        except Exception as e:
            conn.rollback()
            conn.autocommit = True
            print(f"  FAIL  {filename}: {e}")

    # Report table counts
    print(f"\n{'=' * 50}")
    print("Table row counts")
    print(f"{'=' * 50}")

    tables = [
        "decision_journal", "trade_recommendations", "portfolio_positions",
        "portfolio_daily_snapshot", "jury_votes", "debate_transcripts",
        "veto_overrides", "risk_alerts", "consecutive_loss_tracker",
        "bias_metrics", "bloomberg_fundamentals", "watchlist",
        "screening_settings", "system_settings", "price_history",
        "wasden_verdicts",
    ]

    for table in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"  {table:40s} {count:>6} rows")
        except Exception:
            conn.rollback()
            conn.autocommit = True
            print(f"  {table:40s}   (not found)")

    cur.close()
    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    run()
