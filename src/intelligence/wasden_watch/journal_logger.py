"""Optional Supabase verdict logging for the Wasden Watch pipeline."""

import logging
import os

from .models import VerdictResponse

logger = logging.getLogger("wasden_watch")


class JournalLogger:
    """Logs verdicts to Supabase wasden_verdicts table.

    Silently no-ops if Supabase is not configured.
    MUST NEVER crash the caller.
    """

    def __init__(self):
        self._client = None
        self._enabled = False

        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_KEY", "") or os.getenv("SUPABASE_SERVICE_KEY", "")

        if supabase_url and supabase_key:
            try:
                from supabase import create_client
                self._client = create_client(supabase_url, supabase_key)
                self._enabled = True
                logger.info("JournalLogger initialized with Supabase")
            except Exception as e:
                logger.warning(f"Failed to initialize Supabase client for journal logging: {e}")
        else:
            logger.info("Supabase not configured, verdict logging disabled")

    def log_verdict(self, response: VerdictResponse) -> bool:
        """Log a verdict response to Supabase.

        Args:
            response: The VerdictResponse to log.

        Returns:
            True if successfully logged, False otherwise.
        """
        if not self._enabled or self._client is None:
            return False

        try:
            row = {
                "ticker": response.ticker,
                "verdict": response.verdict.verdict,
                "confidence": response.verdict.confidence,
                "reasoning": response.verdict.reasoning,
                "mode": response.verdict.mode,
                "model_used": response.model_used,
                "passages_retrieved": response.verdict.passages_retrieved,
                "generated_at": response.generated_at.isoformat(),
            }

            self._client.table("wasden_verdicts").insert(row).execute()
            logger.info(f"Verdict logged for {response.ticker}")
            return True

        except Exception as e:
            logger.warning(f"Failed to log verdict for {response.ticker}: {e}")
            return False
