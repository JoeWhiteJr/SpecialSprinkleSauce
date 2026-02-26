"""FastAPI router for the Wasden Watch RAG pipeline."""

import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

# Add project root to path so src.intelligence can be imported
_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.intelligence.wasden_watch.config import WasdenWatchSettings
from src.intelligence.wasden_watch.exceptions import (
    VerdictParsingError,
    WasdenWatchError,
)
from src.intelligence.wasden_watch.models import (
    RetrievedPassage,
    VerdictRequest,
    VerdictResponse,
)
from src.intelligence.wasden_watch.vector_store import VectorStore
from src.intelligence.wasden_watch.verdict_generator import VerdictGenerator

logger = logging.getLogger("wasden_watch")

router = APIRouter(prefix="/api/wasden-watch", tags=["wasden-watch"])

# Lazy-initialized singletons
_generator: VerdictGenerator | None = None
_settings: WasdenWatchSettings | None = None


def _get_settings() -> WasdenWatchSettings:
    global _settings
    if _settings is None:
        _settings = WasdenWatchSettings()
    return _settings


def _get_generator() -> VerdictGenerator:
    global _generator
    if _generator is None:
        _generator = VerdictGenerator(_get_settings())
    return _generator


@router.post("/verdict", response_model=VerdictResponse)
async def generate_verdict(request: VerdictRequest) -> Any:
    """Generate a Wasden Watch verdict for a ticker."""
    try:
        generator = _get_generator()
        response = generator.generate(request)
        return response
    except VerdictParsingError as e:
        logger.error(f"Verdict parsing error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except WasdenWatchError as e:
        logger.error(f"Wasden Watch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/corpus/stats")
async def corpus_stats() -> dict:
    """Return vector store statistics."""
    try:
        settings = _get_settings()
        store = VectorStore(settings)
        return store.stats()
    except WasdenWatchError as e:
        logger.error(f"Error getting corpus stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/corpus/search")
async def corpus_search(
    query: str = Query(..., description="Search query"),
    top_k: int = Query(5, ge=1, le=50, description="Number of results"),
) -> list[dict]:
    """Debug endpoint to search the corpus directly."""
    try:
        settings = _get_settings()
        store = VectorStore(settings)

        if not store.is_ingested():
            raise HTTPException(
                status_code=404,
                detail="Corpus not yet ingested. Run ingestion first.",
            )

        passages = store.search(query, top_k=top_k)
        return [p.model_dump() for p in passages]
    except HTTPException:
        raise
    except WasdenWatchError as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
