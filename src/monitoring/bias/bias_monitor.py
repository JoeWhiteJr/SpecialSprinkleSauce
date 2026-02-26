"""Bias monitor — tracks systematic biases in pipeline decisions for weekly reporting.

Monitors Wasden veto rates, sector concentration, model agreement trends, jury escalation,
and action distribution. Generates alerts when any metric is anomalous.

Feeds the weekly bias_monitoring_report.md per PROJECT_STANDARDS_v2.md Section 10.
"""

import logging
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger("wasden_watch.monitoring.bias")

# ------------------------------------------------------------------
# Alert thresholds
# ------------------------------------------------------------------
VETO_RATE_TOO_RESTRICTIVE = 0.50  # > 50% veto rate
VETO_RATE_TOO_PERMISSIVE = 0.05   # < 5% veto rate
SECTOR_CONCENTRATION_LIMIT = 0.40  # single sector > 40% of BUY decisions
ESCALATION_RATE_LIMIT = 0.20       # > 20% jury escalation rate
WIN_RATE_FLOOR = 0.50              # rolling 30-day win rate below 50%


@dataclass
class DecisionSnapshot:
    """Minimal record of a pipeline decision for bias tracking."""

    ticker: str
    action: str  # BUY, SELL, HOLD, BLOCKED, ESCALATED
    timestamp: str
    wasden_verdict: str  # APPROVE, NEUTRAL, VETO
    wasden_confidence: float = 0.0
    quant_composite: float = 0.0
    quant_std_dev: float = 0.0
    sector: str = ""
    recommended_position_size: float = 0.0
    jury_spawned: bool = False
    jury_escalated: bool = False
    debate_outcome: str = ""  # agreement or disagreement
    is_win: Optional[bool] = None  # set after trade closes


class BiasMonitor:
    """Tracks and reports systematic biases in pipeline decisions.

    Ingests pipeline decisions and provides aggregated bias metrics,
    trend analysis, and anomaly alerts for the weekly monitoring report.
    """

    def __init__(self) -> None:
        self._decisions: list[DecisionSnapshot] = []
        logger.info("BiasMonitor initialized")

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def add_decision(self, journal_entry: dict) -> DecisionSnapshot:
        """Ingest a pipeline decision from a decision journal dict.

        Args:
            journal_entry: Dict matching the DecisionJournalEntry schema
                           from PROJECT_STANDARDS_v2.md Section 4.

        Returns:
            The created DecisionSnapshot.
        """
        final = journal_entry.get("final_decision", {})
        quant = journal_entry.get("quant_scores", {})
        wasden = journal_entry.get("wasden_verdict", {})
        jury = journal_entry.get("jury", {})
        debate = journal_entry.get("debate_result", {})

        snapshot = DecisionSnapshot(
            ticker=journal_entry.get("ticker", ""),
            action=final.get("action", "HOLD"),
            timestamp=journal_entry.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            wasden_verdict=wasden.get("verdict", ""),
            wasden_confidence=wasden.get("confidence", 0.0),
            quant_composite=quant.get("composite", 0.0),
            quant_std_dev=quant.get("std_dev", 0.0),
            sector=journal_entry.get("sector", ""),
            recommended_position_size=final.get("recommended_position_size", 0.0),
            jury_spawned=jury.get("spawned", False),
            jury_escalated=jury.get("escalated_to_human", False),
            debate_outcome=debate.get("outcome", ""),
        )
        self._decisions.append(snapshot)
        logger.info(
            "Decision ingested: %s %s (wasden=%s)",
            snapshot.action,
            snapshot.ticker,
            snapshot.wasden_verdict,
        )
        return snapshot

    def mark_trade_result(self, ticker: str, pipeline_run_id: str, is_win: bool) -> None:
        """Mark a previously ingested decision with its trade outcome.

        Args:
            ticker: The ticker to update.
            pipeline_run_id: Not used for matching yet (future DB key).
            is_win: Whether the trade was profitable.
        """
        # Mark the most recent unresolved decision for this ticker
        for d in reversed(self._decisions):
            if d.ticker == ticker and d.is_win is None and d.action in ("BUY", "SELL"):
                d.is_win = is_win
                logger.info("Trade result marked: %s %s win=%s", d.action, ticker, is_win)
                return
        logger.warning("No unresolved decision found for %s to mark result", ticker)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def veto_rate(self) -> dict:
        """Wasden verdict distribution: % VETO vs APPROVE vs NEUTRAL."""
        if not self._decisions:
            return {"veto": 0.0, "approve": 0.0, "neutral": 0.0, "total": 0}

        verdicts = Counter(d.wasden_verdict for d in self._decisions)
        total = len(self._decisions)
        return {
            "veto": round(verdicts.get("VETO", 0) / total, 4),
            "approve": round(verdicts.get("APPROVE", 0) / total, 4),
            "neutral": round(verdicts.get("NEUTRAL", 0) / total, 4),
            "total": total,
            "counts": dict(verdicts),
        }

    def quant_wasden_agreement(self) -> dict:
        """How often the quant composite direction agrees with Wasden verdict.

        Agreement: quant > 0.5 + APPROVE, or quant < 0.5 + VETO.
        """
        if not self._decisions:
            return {"agreement_rate": 0.0, "total": 0}

        agreements = 0
        evaluated = 0
        for d in self._decisions:
            if d.wasden_verdict not in ("APPROVE", "VETO"):
                continue
            evaluated += 1
            quant_bullish = d.quant_composite > 0.5
            wasden_bullish = d.wasden_verdict == "APPROVE"
            if quant_bullish == wasden_bullish:
                agreements += 1

        rate = agreements / evaluated if evaluated > 0 else 0.0
        return {
            "agreement_rate": round(rate, 4),
            "agreements": agreements,
            "disagreements": evaluated - agreements,
            "total": evaluated,
        }

    def sector_concentration(self) -> dict:
        """Distribution of BUY decisions across sectors."""
        buy_decisions = [d for d in self._decisions if d.action == "BUY" and d.sector]
        if not buy_decisions:
            return {"sectors": {}, "total_buys": 0, "max_sector_pct": 0.0}

        sector_counts = Counter(d.sector for d in buy_decisions)
        total = len(buy_decisions)
        sector_pcts = {s: round(c / total, 4) for s, c in sector_counts.items()}
        max_pct = max(sector_pcts.values()) if sector_pcts else 0.0

        return {
            "sectors": sector_pcts,
            "sector_counts": dict(sector_counts),
            "total_buys": total,
            "max_sector_pct": round(max_pct, 4),
            "max_sector": max(sector_counts, key=sector_counts.get) if sector_counts else "",
        }

    def model_agreement_trend(self) -> dict:
        """Trend of quant model std_dev across decisions over time.

        High std_dev = high disagreement among models.
        """
        if not self._decisions:
            return {"mean_std_dev": 0.0, "trend": "stable", "values": []}

        std_devs = [d.quant_std_dev for d in self._decisions]
        mean_std = sum(std_devs) / len(std_devs)

        # Simple trend: compare first half to second half
        if len(std_devs) >= 4:
            mid = len(std_devs) // 2
            first_half_mean = sum(std_devs[:mid]) / mid
            second_half_mean = sum(std_devs[mid:]) / (len(std_devs) - mid)
            if second_half_mean > first_half_mean * 1.1:
                trend = "increasing"
            elif second_half_mean < first_half_mean * 0.9:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        # Count high-disagreement flags
        high_disagreement_count = sum(1 for s in std_devs if s > 0.5)

        return {
            "mean_std_dev": round(mean_std, 4),
            "trend": trend,
            "high_disagreement_count": high_disagreement_count,
            "high_disagreement_rate": round(
                high_disagreement_count / len(std_devs), 4
            ) if std_devs else 0.0,
            "total": len(std_devs),
        }

    def debate_outcome_distribution(self) -> dict:
        """Percentage of debates ending in agreement vs disagreement."""
        debates = [d for d in self._decisions if d.debate_outcome]
        if not debates:
            return {"agreement": 0.0, "disagreement": 0.0, "total": 0}

        outcomes = Counter(d.debate_outcome for d in debates)
        total = len(debates)
        return {
            "agreement": round(outcomes.get("agreement", 0) / total, 4),
            "disagreement": round(outcomes.get("disagreement", 0) / total, 4),
            "total": total,
            "counts": dict(outcomes),
        }

    def jury_escalation_rate(self) -> dict:
        """Percentage of jury sessions that escalate (5-5 ties)."""
        jury_sessions = [d for d in self._decisions if d.jury_spawned]
        if not jury_sessions:
            return {"escalation_rate": 0.0, "escalated": 0, "total_jury_sessions": 0}

        escalated = sum(1 for d in jury_sessions if d.jury_escalated)
        total = len(jury_sessions)
        return {
            "escalation_rate": round(escalated / total, 4),
            "escalated": escalated,
            "total_jury_sessions": total,
        }

    def action_distribution(self) -> dict:
        """Percentage breakdown: BUY / SELL / HOLD / BLOCKED / ESCALATED."""
        if not self._decisions:
            return {"distribution": {}, "total": 0}

        counts = Counter(d.action for d in self._decisions)
        total = len(self._decisions)
        pcts = {action: round(count / total, 4) for action, count in counts.items()}
        return {
            "distribution": pcts,
            "counts": dict(counts),
            "total": total,
        }

    def position_size_distribution(self) -> dict:
        """Statistics on recommended position sizes for BUY/SELL decisions."""
        sizes = [
            d.recommended_position_size
            for d in self._decisions
            if d.action in ("BUY", "SELL") and d.recommended_position_size > 0
        ]
        if not sizes:
            return {"mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0, "std_dev": 0.0, "count": 0}

        sizes_sorted = sorted(sizes)
        n = len(sizes_sorted)
        mean = sum(sizes_sorted) / n
        median = (
            sizes_sorted[n // 2]
            if n % 2 == 1
            else (sizes_sorted[n // 2 - 1] + sizes_sorted[n // 2]) / 2
        )
        variance = sum((s - mean) ** 2 for s in sizes_sorted) / n if n > 1 else 0.0
        std_dev = math.sqrt(variance)

        return {
            "mean": round(mean, 6),
            "median": round(median, 6),
            "min": round(sizes_sorted[0], 6),
            "max": round(sizes_sorted[-1], 6),
            "std_dev": round(std_dev, 6),
            "count": n,
        }

    # ------------------------------------------------------------------
    # Reports and Alerts
    # ------------------------------------------------------------------

    def generate_bias_report(self) -> dict:
        """Generate comprehensive bias report with all metrics.

        Returns:
            Dict with all bias metrics suitable for weekly report.
        """
        return {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total_decisions": len(self._decisions),
            "veto_rate": self.veto_rate(),
            "quant_wasden_agreement": self.quant_wasden_agreement(),
            "sector_concentration": self.sector_concentration(),
            "model_agreement_trend": self.model_agreement_trend(),
            "debate_outcome_distribution": self.debate_outcome_distribution(),
            "jury_escalation_rate": self.jury_escalation_rate(),
            "action_distribution": self.action_distribution(),
            "position_size_distribution": self.position_size_distribution(),
            "alerts": self.check_alerts(),
        }

    def check_alerts(self) -> list[str]:
        """Check all metrics for anomalous values.

        Returns:
            List of alert strings for any metric outside expected bounds.
        """
        alerts: list[str] = []

        # Veto rate alerts
        veto = self.veto_rate()
        veto_pct = veto.get("veto", 0.0)
        if veto["total"] >= 5:  # Only alert with enough data
            if veto_pct > VETO_RATE_TOO_RESTRICTIVE:
                alerts.append(
                    f"ALERT: Wasden veto rate {veto_pct:.1%} exceeds {VETO_RATE_TOO_RESTRICTIVE:.0%} "
                    f"— system may be too restrictive"
                )
            elif veto_pct < VETO_RATE_TOO_PERMISSIVE:
                alerts.append(
                    f"ALERT: Wasden veto rate {veto_pct:.1%} below {VETO_RATE_TOO_PERMISSIVE:.0%} "
                    f"— system may be too permissive"
                )

        # Sector concentration alert
        sector = self.sector_concentration()
        if sector["total_buys"] >= 5 and sector["max_sector_pct"] > SECTOR_CONCENTRATION_LIMIT:
            alerts.append(
                f"ALERT: Sector '{sector['max_sector']}' accounts for "
                f"{sector['max_sector_pct']:.1%} of BUY decisions "
                f"(limit: {SECTOR_CONCENTRATION_LIMIT:.0%})"
            )

        # Jury escalation alert
        jury = self.jury_escalation_rate()
        if jury["total_jury_sessions"] >= 3 and jury["escalation_rate"] > ESCALATION_RATE_LIMIT:
            alerts.append(
                f"ALERT: Jury escalation rate {jury['escalation_rate']:.1%} exceeds "
                f"{ESCALATION_RATE_LIMIT:.0%} — system reaching too many 5-5 ties"
            )

        # Win rate alert (rolling 30-day window)
        resolved = [d for d in self._decisions if d.is_win is not None]
        if len(resolved) >= 10:
            recent = resolved[-30:]
            wins = sum(1 for d in recent if d.is_win)
            win_rate = wins / len(recent)
            if win_rate < WIN_RATE_FLOOR:
                alerts.append(
                    f"ALERT: Rolling 30-decision win rate {win_rate:.1%} "
                    f"below {WIN_RATE_FLOOR:.0%} floor"
                )

        if alerts:
            for alert in alerts:
                logger.warning(alert)
        else:
            logger.info("Bias check: all metrics within normal bounds")

        return alerts

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def decisions(self) -> list[DecisionSnapshot]:
        """All ingested decisions."""
        return list(self._decisions)
