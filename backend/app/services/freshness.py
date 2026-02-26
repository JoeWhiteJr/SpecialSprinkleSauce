"""
Shared freshness module — single source of truth for data freshness grading.

Extracted from bloomberg_pipeline.py to be reusable across screening,
data pipeline, and risk modules.
"""

from datetime import date
from typing import Optional

from app.models.schemas import DataFreshness

# Freshness thresholds (days)
FRESH_HOURS = 24
RECENT_DAYS = 7
STALE_DAYS = 30


def compute_freshness(pull_date: date, reference_date: Optional[date] = None) -> DataFreshness:
    """Compute data freshness grade based on age.

    FRESH: <24 hours — full weight
    RECENT: 1-7 days — full weight, flagged in logs
    STALE: 7-30 days — weight reduced by 50%
    EXPIRED: >30 days — excluded from live decisions
    """
    ref = reference_date or date.today()
    age_days = (ref - pull_date).days

    if age_days < 1:
        return DataFreshness.FRESH
    elif age_days <= RECENT_DAYS:
        return DataFreshness.RECENT
    elif age_days <= STALE_DAYS:
        return DataFreshness.STALE
    else:
        return DataFreshness.EXPIRED


def freshness_weight(freshness: DataFreshness) -> float:
    """Return weight multiplier for a freshness grade.

    FRESH/RECENT: 1.0 (full weight)
    STALE: 0.5 (reduced weight)
    EXPIRED: 0.0 (excluded)
    """
    if freshness in (DataFreshness.FRESH, DataFreshness.RECENT):
        return 1.0
    elif freshness == DataFreshness.STALE:
        return 0.5
    else:
        return 0.0


def apply_freshness_filter(
    records: list[dict],
    pull_date_key: str = "pull_date",
    reference_date: Optional[date] = None,
    exclude_expired: bool = True,
) -> list[dict]:
    """Filter records by freshness, optionally excluding expired data.

    Each record must have a date field (specified by pull_date_key) as a
    date object or ISO string.

    Returns filtered list with 'freshness' and 'freshness_weight' added to
    each record.
    """
    ref = reference_date or date.today()
    result = []

    for record in records:
        pd = record[pull_date_key]
        if isinstance(pd, str):
            pd = date.fromisoformat(pd)

        grade = compute_freshness(pd, ref)
        weight = freshness_weight(grade)

        if exclude_expired and grade == DataFreshness.EXPIRED:
            continue

        enriched = {**record, "freshness": grade, "freshness_weight": weight}
        result.append(enriched)

    return result
