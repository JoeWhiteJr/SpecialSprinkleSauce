"""Configuration for the Wasden Watch RAG pipeline using pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root: SpecialSprinkleSauce/ (3 levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


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

    # Paths (resolved from project root)
    pdf_corpus_path: str = str(_PROJECT_ROOT / "data" / "wasden_corpus")
    metadata_path: str = str(_PROJECT_ROOT / "data" / "wasden_corpus" / "newsletter_metadata.json")
    chroma_persist_dir: str = str(_PROJECT_ROOT / "local" / "chroma_wasden_watch")

    # Chunking
    chunk_size_tokens: int = 600        # target: 500-800 range
    chunk_overlap_tokens: int = 100

    # Retrieval
    default_top_k: int = 10
    time_decay_half_life_days: int = 365

    # LLM
    claude_model: str = "claude-sonnet-4-20250514"
    gemini_model: str = "gemini-2.5-flash"
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
        env_file=str(_PROJECT_ROOT / ".env"),
        env_prefix="",
        extra="ignore",
    )
