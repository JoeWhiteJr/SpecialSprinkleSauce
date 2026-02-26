"""Wasden Watch RAG Pipeline — newsletter-based investment verdict generation."""

from .config import WasdenWatchSettings
from .models import VerdictRequest, VerdictResponse, WasdenVerdict
from .pdf_processor import PDFProcessor
from .vector_store import VectorStore
from .verdict_generator import VerdictGenerator

__all__ = [
    "VerdictGenerator",
    "WasdenWatchSettings",
    "VerdictRequest",
    "VerdictResponse",
    "WasdenVerdict",
    "PDFProcessor",
    "VectorStore",
]
