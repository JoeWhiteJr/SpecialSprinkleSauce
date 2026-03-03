# Wasden Watch RAG Pipeline — Build Instructions

You are building the Wasden Watch RAG (Retrieval-Augmented Generation) pipeline for the SpecialSprinkleSauce trading dashboard. This is a self-contained module that reads 28 Wasden Weekender newsletter PDFs, chunks them into a vector store, and produces investment verdicts (APPROVE/NEUTRAL/VETO) for any given ticker by retrieving relevant newsletter passages and reasoning through them via LLM.

## IMPORTANT CONTEXT

- The PDF corpus is already in the repo at `data/wasden_corpus/` (28 PDFs + `newsletter_metadata.json`)
- The backend is FastAPI at `backend/app/main.py` — it already has 12 routers registered
- The wasden_watch module directory exists at `src/intelligence/wasden_watch/` (currently empty except `.gitkeep`)
- Environment variables for API keys are in `.env` at the project root — there are TWO keys for each provider (for round-robin rotation to double rate limits):
  - `CLAUDE_API_KEY_1`, `CLAUDE_API_KEY_2`
  - `GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`
- The existing backend config is in `backend/app/config.py` using pydantic-settings
- The existing CLI pattern is in `backend/app/cli/pipeline_cli.py`
- Requirements file is at `backend/requirements.txt`

## FILES TO CREATE

Create all of the following files. Do NOT skip any file. Do NOT create placeholder/stub implementations — every file must be fully functional.

### 1. `src/intelligence/wasden_watch/__init__.py`

Package exports. Re-export the key public interfaces:
- `VerdictGenerator` (from verdict_generator)
- `WasdenWatchSettings` (from config)
- `VerdictRequest`, `VerdictResponse`, `WasdenVerdict` (from models)
- `PDFProcessor` (from pdf_processor)
- `VectorStore` (from vector_store)

### 2. `src/intelligence/wasden_watch/models.py`

Pydantic models:

```python
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
```

### 3. `src/intelligence/wasden_watch/config.py`

Use pydantic-settings to load from environment:

```python
class WasdenWatchSettings(BaseSettings):
    # API Keys (2 of each for round-robin rotation)
    claude_api_key_1: str = ""
    claude_api_key_2: str = ""
    gemini_api_key_1: str = ""
    gemini_api_key_2: str = ""

    @property
    def claude_api_keys(self) -> list[str]:
        """Return list of non-empty Claude API keys."""
        return [k for k in [self.claude_api_key_1, self.claude_api_key_2] if k]

    @property
    def gemini_api_keys(self) -> list[str]:
        """Return list of non-empty Gemini API keys."""
        return [k for k in [self.gemini_api_key_1, self.gemini_api_key_2] if k]

    # Paths
    pdf_corpus_path: str = "data/wasden_corpus"
    metadata_path: str = "data/wasden_corpus/newsletter_metadata.json"
    chroma_persist_dir: str = "local/chroma_wasden_watch"

    # Chunking
    chunk_size_tokens: int = 600        # target: 500-800 range
    chunk_overlap_tokens: int = 100

    # Retrieval
    default_top_k: int = 10
    time_decay_half_life_days: int = 365

    # LLM
    claude_model: str = "claude-sonnet-4-20250514"
    gemini_model: str = "gemini-1.5-flash"
    max_tokens: int = 2048
    temperature: float = 0.3

    # Confidence bounds
    direct_coverage_confidence_min: float = 0.75
    direct_coverage_confidence_max: float = 0.95
    framework_confidence_min: float = 0.50
    framework_confidence_max: float = 0.75
    veto_min_confidence: float = 0.85
    fallback_max_confidence: float = 0.60

    # Mode thresholds
    direct_coverage_min_passages: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
    )
```

### 4. `src/intelligence/wasden_watch/pdf_processor.py`

PDF text extraction + chunking:
- Use `pymupdf` (imported as `fitz`) to extract text from each PDF
- Load metadata from `newsletter_metadata.json` to enrich each document
- Chunk using `tiktoken` (cl100k_base encoding) with the configured chunk_size and overlap
- Return list of `CorpusDocument` objects with their `chunks` populated
- Also return flat list of `TextChunk` objects ready for embedding
- Handle extraction errors gracefully (log warning, skip bad pages, continue)

Key method signatures:
```python
class PDFProcessor:
    def __init__(self, settings: WasdenWatchSettings): ...
    def process_corpus(self) -> tuple[list[CorpusDocument], list[TextChunk]]: ...
    def _extract_text(self, pdf_path: Path) -> str: ...
    def _chunk_text(self, text: str, filename: str, doc_date: date, title: str) -> list[TextChunk]: ...
```

### 5. `src/intelligence/wasden_watch/chart_describer.py`

Uses Claude Vision API to describe charts/images found in PDFs:
- Extract images from PDF pages using pymupdf
- Send each image to Claude's vision endpoint with a prompt asking for a financial description
- Return text descriptions that can be appended to the document's text before chunking
- This is optional/enhancement — if Claude API key is missing or call fails, log warning and return empty string
- Include rate limiting (1 request per second)

Key method:
```python
class ChartDescriber:
    def __init__(self, api_keys: list[str], model: str = "claude-sonnet-4-20250514"):
        # Uses itertools.cycle to rotate across available Claude keys
        self._key_cycle = itertools.cycle(api_keys) if api_keys else None
        ...
    def describe_charts(self, pdf_path: Path) -> list[str]: ...
    def _describe_image(self, image_bytes: bytes) -> str: ...
```

### 6. `src/intelligence/wasden_watch/vector_store.py`

ChromaDB vector store:
- Use ChromaDB with persistent storage at `chroma_persist_dir`
- Collection name: `wasden_weekender`
- Use `sentence-transformers` for embeddings (model: `all-MiniLM-L6-v2`)
- Implement time-decay scoring: `weight = 0.5 ^ ((today - doc_date).days / half_life_days)`
- On retrieval, multiply ChromaDB distance-based relevance by time_decay_weight to get final_score
- Sort results by final_score descending
- Support `ingest(chunks: list[TextChunk])` and `search(query: str, top_k: int) -> list[RetrievedPassage]`
- Track ingestion state: skip re-ingestion if collection already has the expected document count

Key methods:
```python
class VectorStore:
    def __init__(self, settings: WasdenWatchSettings): ...
    def ingest(self, chunks: list[TextChunk]) -> int: ...  # returns count ingested
    def search(self, query: str, top_k: int = 10) -> list[RetrievedPassage]: ...
    def stats(self) -> dict: ...  # total_chunks, date_range, collection_name
    def is_ingested(self) -> bool: ...
    def clear(self) -> None: ...
```

### 7. `src/intelligence/wasden_watch/prompt_templates.py`

**THIS FILE IS PROTECTED — implement exactly as specified.**

Contains two prompt templates:

**SYSTEM_PROMPT:**
```
You are the Wasden Watch analyst, an AI investment research assistant modeled after the analytical framework of the Wasden Weekender newsletter by Archimedes Insights and Analytics.

Your role is to evaluate individual stock tickers through the lens of the Wasden Weekender's analytical framework. You will be provided with relevant passages from the newsletter corpus and asked to render a verdict.

## The 5-Bucket Framework

The Wasden Weekender organizes market analysis into 5 key buckets:

1. **Macro Environment** — Fed policy, inflation, interest rates, GDP growth, employment data, consumer sentiment. How does the current macro backdrop affect this stock?

2. **Sector Dynamics** — Industry trends, competitive positioning, sector rotation, regulatory environment. Where does this stock sit within its sector's cycle?

3. **Valuation & Fundamentals** — P/E ratios, revenue growth, margins, cash flow, debt levels, earnings trajectory. Is the stock fairly valued given its fundamentals?

4. **Technical & Momentum** — Price action, moving averages, volume patterns, relative strength, support/resistance levels. What does the technical picture suggest?

5. **Risk & Catalysts** — Upcoming earnings, regulatory decisions, geopolitical risks, management changes, M&A activity. What could move this stock significantly in either direction?

## Verdict Guidelines

- **APPROVE**: The weight of evidence across the 5 buckets supports a positive investment thesis. Most buckets are favorable, and risks are manageable.
- **NEUTRAL**: Mixed signals across buckets. Some positive, some negative. Insufficient conviction to take a position. Wait for more clarity.
- **VETO**: Significant red flags in multiple buckets. Unfavorable risk/reward. Active reasons to avoid or exit the position.

## Confidence Calibration

Your confidence score must reflect your certainty in the verdict:
- 0.90-0.95: Very high confidence, strong evidence across most buckets
- 0.75-0.89: High confidence, clear directional signal with minor uncertainties
- 0.60-0.74: Moderate confidence, some conflicting signals
- 0.50-0.59: Low confidence, limited direct evidence, relying on framework extrapolation
- A VETO verdict requires minimum 0.85 confidence (you must be very sure to block a trade)
```

**VERDICT_PROMPT template** (format string with variables `{ticker}`, `{company_info}`, `{fundamentals_section}`, `{passages_section}`, `{mode_instruction}`):
```
Analyze the following stock and render a Wasden Watch verdict.

## Ticker: {ticker}
{company_info}

{fundamentals_section}

## Retrieved Newsletter Passages
{passages_section}

{mode_instruction}

## Required Output Format

Respond with ONLY valid JSON matching this schema:
{{
  "verdict": "APPROVE" | "NEUTRAL" | "VETO",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<2-4 paragraph analysis covering relevant buckets from the 5-bucket framework>"
}}

Do not include any text outside the JSON object.
```

**Mode instructions:**
- `direct_coverage`: "This ticker appears directly in {n} retrieved passages. Analyze the specific commentary and context from the newsletters."
- `framework_application`: "This ticker does not appear directly in the newsletter corpus. Apply the Wasden Weekender's 5-bucket analytical framework to evaluate it based on the macro, sector, and market context from the retrieved passages."

### 8. `src/intelligence/wasden_watch/llm_client.py`

Dual-LLM client with fallback AND round-robin key rotation:
- Primary: Anthropic Claude API (using `anthropic` Python SDK)
- Fallback: Google Gemini API (using `google-generativeai` SDK)
- **Key rotation:** Settings provides `claude_api_keys` and `gemini_api_keys` as lists (up to 2 each). Use `itertools.cycle` to round-robin across keys on each call. This doubles effective rate limits.
- If Claude call fails (any exception), log warning and try Gemini
- If Gemini is used, set `mode` to "fallback" and cap confidence at `fallback_max_confidence`
- Parse the JSON response, validate against WasdenVerdict schema
- Raise `VerdictParsingError` if JSON is malformed after both attempts

Key methods:
```python
class LLMClient:
    def __init__(self, settings: WasdenWatchSettings):
        self._claude_key_cycle = itertools.cycle(settings.claude_api_keys) if settings.claude_api_keys else None
        self._gemini_key_cycle = itertools.cycle(settings.gemini_api_keys) if settings.gemini_api_keys else None
        ...

    def generate_verdict(self, system_prompt: str, user_prompt: str) -> tuple[dict, str]: ...
        # Returns (parsed_json_dict, model_name_used)
    def _call_claude(self, system_prompt: str, user_prompt: str) -> str:
        # Get next key from cycle: key = next(self._claude_key_cycle)
        # Create fresh Anthropic client with that key each call
        ...
    def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        # Get next key from cycle: key = next(self._gemini_key_cycle)
        # Configure genai with that key each call
        ...
```

### 9. `src/intelligence/wasden_watch/verdict_generator.py`

Main orchestrator — the single entry point for getting a verdict:

```python
class VerdictGenerator:
    def __init__(self, settings: WasdenWatchSettings | None = None): ...
    def ensure_ingested(self) -> dict: ...  # ingest if needed, return stats
    def generate(self, request: VerdictRequest) -> VerdictResponse: ...
```

`generate()` flow:
1. Call `ensure_ingested()` to make sure vector store is populated
2. Search vector store for `f"{request.ticker} {request.company_name or ''} {request.sector or ''}"` with `top_k=request.top_k`
3. Determine mode: if ticker appears in >= `direct_coverage_min_passages` passage texts, use `direct_coverage`; else `framework_application`
4. Build the verdict prompt using `prompt_templates.py` templates
5. Call `llm_client.generate_verdict()`
6. Parse response, enforce confidence bounds based on mode
7. If VETO and confidence < `veto_min_confidence`, downgrade to NEUTRAL
8. Build and return `VerdictResponse`

### 10. `src/intelligence/wasden_watch/exceptions.py`

Custom exceptions:
```python
class WasdenWatchError(Exception):
    """Base exception for Wasden Watch module."""
    pass

class VectorStoreError(WasdenWatchError):
    """Raised when ChromaDB operations fail."""
    pass

class VerdictParsingError(WasdenWatchError):
    """Raised when LLM response cannot be parsed into a valid verdict."""
    pass

class PDFProcessingError(WasdenWatchError):
    """Raised when PDF extraction fails critically."""
    pass

class LLMError(WasdenWatchError):
    """Raised when both primary and fallback LLM calls fail."""
    pass
```

### 11. `src/intelligence/wasden_watch/journal_logger.py`

Optional Supabase verdict logging:
- If `SUPABASE_URL` and `SUPABASE_KEY` are set in environment, log each verdict to a `wasden_verdicts` table
- Fields: ticker, verdict, confidence, reasoning, mode, model_used, passages_retrieved, generated_at
- **MUST NEVER crash the caller** — wrap everything in try/except, log warnings on failure
- If Supabase is not configured, silently no-op

```python
class JournalLogger:
    def __init__(self): ...
    def log_verdict(self, response: VerdictResponse) -> bool: ...  # returns True if logged
```

### 12. `backend/app/routers/wasden_watch.py`

FastAPI router with prefix `/api/wasden-watch`:

Three endpoints:
- `POST /verdict` — Takes `VerdictRequest` body, returns `VerdictResponse`. This is the main endpoint.
- `GET /corpus/stats` — Returns vector store stats (total_chunks, date_range, etc.)
- `GET /corpus/search?query=...&top_k=5` — Debug endpoint to search the corpus directly, returns list of `RetrievedPassage`

Handle errors gracefully — catch `WasdenWatchError` and return appropriate HTTP status codes.

### 13. `backend/app/cli/wasden_cli.py`

CLI tool using `argparse` (NOT click/typer — keep it simple):

Commands:
- `ingest` — Process PDFs and ingest into vector store. Print stats when done.
- `verdict <TICKER>` — Generate a verdict for a ticker. Optional flags: `--company`, `--sector`, `--top-k`
- `stats` — Show vector store statistics
- `search <query>` — Search the corpus, print top passages. Optional `--top-k`
- `pilot` — Run verdicts for all 11 pilot tickers and print summary table

Pilot tickers: `NVDA, PYPL, NFLX, TSM, XOM, AAPL, MSFT, AMZN, TSLA, AMD, GOOGL`

Usage: `python -m app.cli.wasden_cli <command> [args]`

Print results in a clean, readable format. Use colored output if `colorama` is available (but don't require it).

### 14. Update `backend/app/main.py`

Add the wasden_watch router import and registration:
- Import: `from app.routers import wasden_watch as wasden_watch_router`
- Register: `app.include_router(wasden_watch_router.router)`
- Update the comment from "12 routers" to "13 routers"

### 15. Update `backend/requirements.txt`

Append these dependencies (do NOT remove existing ones):
```
# Wasden Watch RAG pipeline
pymupdf==1.25.3
chromadb==0.6.3
anthropic==0.43.0
google-generativeai==0.8.4
tiktoken==0.9.0
sentence-transformers==3.4.1
colorama==0.4.6
```

## CRITICAL IMPLEMENTATION RULES

1. **All imports must work.** Test that every file can be imported without errors. Use relative imports within the `wasden_watch` package (e.g., `from .models import ...`).

2. **No placeholders.** Every method must have a real implementation, not `pass` or `raise NotImplementedError`.

3. **The prompt_templates.py file is PROTECTED.** Implement the system prompt and verdict prompt exactly as specified above. Do not modify the 5-bucket framework text.

4. **Confidence clamping is mandatory.** The verdict_generator must enforce:
   - `direct_coverage` mode: confidence in [0.75, 0.95]
   - `framework_application` mode: confidence in [0.50, 0.75]
   - `fallback` mode: confidence capped at 0.60
   - VETO requires >= 0.85 confidence, otherwise downgrade to NEUTRAL

5. **Zero database dependency for core RAG.** The entire pipeline (PDF → chunks → vectors → verdict) must work with zero Supabase/Postgres. Only `journal_logger.py` touches Supabase, and it's optional.

6. **Time-decay formula:** `weight = 0.5 ^ ((today - doc_date).days / half_life_days)` where `half_life_days` defaults to 365.

7. **Chunk sizing:** Use tiktoken's `cl100k_base` encoding. Target 600 tokens per chunk with 100-token overlap. Acceptable range is 500-800 tokens.

8. **Error handling:** Use the custom exceptions from `exceptions.py`. The router should catch `WasdenWatchError` and return 500. `VerdictParsingError` should return 422.

9. **Logging:** Use Python's standard `logging` module. Logger name: `wasden_watch`. Log at INFO level for normal operations, WARNING for fallbacks and non-critical errors, ERROR for failures.

10. **The CLI must work from the backend directory:** `cd backend && python -m app.cli.wasden_cli stats`

## VERIFICATION CHECKLIST

After building everything, verify:

1. All files exist:
   - `src/intelligence/wasden_watch/__init__.py`
   - `src/intelligence/wasden_watch/models.py`
   - `src/intelligence/wasden_watch/config.py`
   - `src/intelligence/wasden_watch/pdf_processor.py`
   - `src/intelligence/wasden_watch/chart_describer.py`
   - `src/intelligence/wasden_watch/vector_store.py`
   - `src/intelligence/wasden_watch/prompt_templates.py`
   - `src/intelligence/wasden_watch/llm_client.py`
   - `src/intelligence/wasden_watch/verdict_generator.py`
   - `src/intelligence/wasden_watch/exceptions.py`
   - `src/intelligence/wasden_watch/journal_logger.py`
   - `backend/app/routers/wasden_watch.py`
   - `backend/app/cli/wasden_cli.py`

2. `backend/app/main.py` includes the wasden_watch router

3. `backend/requirements.txt` has all new dependencies

4. Run: `cd backend && pip install -r requirements.txt`

5. Run: `cd backend && python -c "from app.routers.wasden_watch import router; print('Router OK')"` — should print "Router OK"

6. Run: `cd backend && python -c "from src.intelligence.wasden_watch import VerdictGenerator; print('Import OK')"` — or verify the import path works given the project structure

7. Run: `cd backend && python -m app.cli.wasden_cli stats` — should work (may show empty store if not ingested yet)

Commit all changes with message: "feat: implement Wasden Watch RAG pipeline with PDF corpus, vector store, and verdict generation"
