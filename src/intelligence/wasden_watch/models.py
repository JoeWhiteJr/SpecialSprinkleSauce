"""Pydantic models for the Wasden Watch RAG pipeline."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class CorpusDocument(BaseModel):
    """A single newsletter with extracted text."""
    filename: str
    date: date
    title: str
    author: str
    topics: list[str]
    sectors: list[str]
    full_text: str
    chunks: list[str] = []


class TextChunk(BaseModel):
    """A chunk of text from a newsletter, ready for embedding."""
    chunk_id: str          # f"{filename}::chunk_{i}"
    text: str
    source_filename: str
    source_date: date
    source_title: str
    token_count: int


class RetrievedPassage(BaseModel):
    """A passage retrieved from the vector store with relevance score."""
    text: str
    source_filename: str
    source_date: date
    source_title: str
    relevance_score: float
    time_decay_weight: float
    final_score: float     # relevance_score * time_decay_weight


class VerdictRequest(BaseModel):
    """Input to the verdict generator."""
    ticker: str
    company_name: str | None = None
    sector: str | None = None
    fundamentals: dict | None = None  # optional dict of key metrics
    top_k: int = 10


class WasdenVerdict(BaseModel):
    """The verdict output."""
    verdict: Literal["APPROVE", "NEUTRAL", "VETO"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    mode: Literal["direct_coverage", "framework_application", "fallback"]
    passages_retrieved: int
    key_passages: list[RetrievedPassage] = []


class VerdictResponse(BaseModel):
    """Full response wrapper."""
    ticker: str
    verdict: WasdenVerdict
    generated_at: datetime
    model_used: str
    corpus_stats: dict  # total_docs, total_chunks, date_range
