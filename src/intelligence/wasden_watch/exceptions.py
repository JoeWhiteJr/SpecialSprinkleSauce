"""Custom exceptions for the Wasden Watch RAG pipeline."""


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
