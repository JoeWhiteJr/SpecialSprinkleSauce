"""Main orchestrator for the Wasden Watch RAG verdict pipeline."""

import logging
from datetime import datetime, timezone

from .config import WasdenWatchSettings
from .journal_logger import JournalLogger
from .llm_client import LLMClient
from .models import (
    RetrievedPassage,
    VerdictRequest,
    VerdictResponse,
    WasdenVerdict,
)
from .pdf_processor import PDFProcessor
from .prompt_templates import MODE_INSTRUCTIONS, SYSTEM_PROMPT, VERDICT_PROMPT
from .vector_store import VectorStore

logger = logging.getLogger("wasden_watch")


class VerdictGenerator:
    """Single entry point for generating Wasden Watch verdicts."""

    def __init__(self, settings: WasdenWatchSettings | None = None):
        self._settings = settings or WasdenWatchSettings()
        self._vector_store = VectorStore(self._settings)
        self._llm_client = LLMClient(self._settings)
        self._pdf_processor = PDFProcessor(self._settings)
        self._journal_logger = JournalLogger()

    def ensure_ingested(self) -> dict:
        """Ingest PDF corpus into vector store if not already done.

        Returns:
            Vector store stats dict.
        """
        if not self._vector_store.is_ingested():
            logger.info("Vector store is empty, starting ingestion")
            documents, chunks = self._pdf_processor.process_corpus()
            ingested = self._vector_store.ingest(chunks)
            logger.info(f"Ingested {ingested} chunks from {len(documents)} documents")
        else:
            logger.info("Vector store already populated, skipping ingestion")

        return self._vector_store.stats()

    def generate(self, request: VerdictRequest) -> VerdictResponse:
        """Generate a Wasden Watch verdict for a ticker.

        Args:
            request: VerdictRequest with ticker info.

        Returns:
            VerdictResponse with verdict, reasoning, and metadata.
        """
        # Step 1: Ensure corpus is ingested
        corpus_stats = self.ensure_ingested()

        # Step 2: Search vector store
        query = f"{request.ticker} {request.company_name or ''} {request.sector or ''}".strip()
        passages = self._vector_store.search(query, top_k=request.top_k)

        # Step 3: Determine mode
        ticker_upper = request.ticker.upper()
        direct_count = sum(
            1 for p in passages if ticker_upper in p.text.upper()
        )
        if direct_count >= self._settings.direct_coverage_min_passages:
            mode = "direct_coverage"
        else:
            mode = "framework_application"

        logger.info(
            f"Ticker {request.ticker}: {direct_count} direct mentions, "
            f"mode={mode}, {len(passages)} passages retrieved"
        )

        # Step 4: Build prompt
        company_info = ""
        if request.company_name:
            company_info += f"\n**Company:** {request.company_name}"
        if request.sector:
            company_info += f"\n**Sector:** {request.sector}"

        fundamentals_section = ""
        if request.fundamentals:
            fundamentals_section = "## Key Fundamentals\n"
            for key, value in request.fundamentals.items():
                fundamentals_section += f"- **{key}:** {value}\n"

        passages_section = self._format_passages(passages)

        if mode == "direct_coverage":
            mode_instruction = MODE_INSTRUCTIONS["direct_coverage"].format(n=direct_count)
        else:
            mode_instruction = MODE_INSTRUCTIONS["framework_application"]

        user_prompt = VERDICT_PROMPT.format(
            ticker=request.ticker,
            company_info=company_info,
            fundamentals_section=fundamentals_section,
            passages_section=passages_section,
            mode_instruction=mode_instruction,
        )

        # Step 5: Call LLM
        result_dict, model_used = self._llm_client.generate_verdict(SYSTEM_PROMPT, user_prompt)

        # Step 6: Check if fallback was used (Gemini model)
        is_fallback = model_used == self._settings.gemini_model
        if is_fallback:
            mode = "fallback"

        # Step 7: Parse and enforce confidence bounds
        raw_confidence = float(result_dict.get("confidence", 0.5))
        confidence = self._clamp_confidence(raw_confidence, mode)

        verdict_str = result_dict.get("verdict", "NEUTRAL").upper()
        if verdict_str not in ("APPROVE", "NEUTRAL", "VETO"):
            verdict_str = "NEUTRAL"

        # Step 8: VETO requires >= veto_min_confidence, otherwise downgrade
        if verdict_str == "VETO" and confidence < self._settings.veto_min_confidence:
            logger.warning(
                f"VETO for {request.ticker} has confidence {confidence:.2f} "
                f"< {self._settings.veto_min_confidence}, downgrading to NEUTRAL"
            )
            verdict_str = "NEUTRAL"

        reasoning = result_dict.get("reasoning", "No reasoning provided.")

        # Build verdict
        verdict = WasdenVerdict(
            verdict=verdict_str,
            confidence=confidence,
            reasoning=reasoning,
            mode=mode,
            passages_retrieved=len(passages),
            key_passages=passages[:5],  # Include top 5 passages
        )

        response = VerdictResponse(
            ticker=request.ticker,
            verdict=verdict,
            generated_at=datetime.now(timezone.utc),
            model_used=model_used,
            corpus_stats=corpus_stats,
        )

        # Log to journal (optional, never crashes)
        self._journal_logger.log_verdict(response)

        return response

    def _clamp_confidence(self, confidence: float, mode: str) -> float:
        """Clamp confidence to bounds based on mode.

        Args:
            confidence: Raw confidence from LLM.
            mode: Verdict mode (direct_coverage, framework_application, fallback).

        Returns:
            Clamped confidence value.
        """
        if mode == "direct_coverage":
            return max(
                self._settings.direct_coverage_confidence_min,
                min(confidence, self._settings.direct_coverage_confidence_max),
            )
        elif mode == "framework_application":
            return max(
                self._settings.framework_confidence_min,
                min(confidence, self._settings.framework_confidence_max),
            )
        elif mode == "fallback":
            return min(confidence, self._settings.fallback_max_confidence)
        return confidence

    def _format_passages(self, passages: list[RetrievedPassage]) -> str:
        """Format retrieved passages for the verdict prompt.

        Args:
            passages: List of retrieved passages.

        Returns:
            Formatted string of passages.
        """
        if not passages:
            return "*No relevant passages found in the newsletter corpus.*"

        sections = []
        for i, p in enumerate(passages, 1):
            sections.append(
                f"### Passage {i} (Score: {p.final_score:.3f})\n"
                f"**Source:** {p.source_title} ({p.source_date})\n"
                f"**File:** {p.source_filename}\n\n"
                f"{p.text}"
            )
        return "\n\n---\n\n".join(sections)
