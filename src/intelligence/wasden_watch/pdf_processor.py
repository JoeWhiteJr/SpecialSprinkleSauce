"""PDF text extraction and chunking for the Wasden Watch corpus."""

import json
import logging
from datetime import date
from pathlib import Path

import fitz  # pymupdf
import tiktoken

from .config import WasdenWatchSettings
from .exceptions import PDFProcessingError
from .models import CorpusDocument, TextChunk

logger = logging.getLogger("wasden_watch")


class PDFProcessor:
    """Extracts text from Wasden Weekender PDFs and chunks for embedding."""

    def __init__(self, settings: WasdenWatchSettings):
        self._settings = settings
        self._encoding = tiktoken.get_encoding("cl100k_base")

    def process_corpus(self) -> tuple[list[CorpusDocument], list[TextChunk]]:
        """Process all PDFs in the corpus directory.

        Returns:
            Tuple of (list of CorpusDocument, flat list of TextChunk).
        """
        corpus_path = Path(self._settings.pdf_corpus_path)
        metadata_path = Path(self._settings.metadata_path)

        if not corpus_path.exists():
            raise PDFProcessingError(f"Corpus directory not found: {corpus_path}")

        # Load metadata
        metadata_map: dict[str, dict] = {}
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                meta = json.load(f)
            for entry in meta.get("newsletters", []):
                metadata_map[entry["filename"]] = entry
            logger.info(f"Loaded metadata for {len(metadata_map)} newsletters")
        else:
            logger.warning(f"Metadata file not found: {metadata_path}")

        # Find all PDFs
        pdf_files = sorted(corpus_path.glob("*.pdf"))
        if not pdf_files:
            raise PDFProcessingError(f"No PDF files found in {corpus_path}")

        logger.info(f"Found {len(pdf_files)} PDFs in corpus")

        documents: list[CorpusDocument] = []
        all_chunks: list[TextChunk] = []

        for pdf_path in pdf_files:
            try:
                text = self._extract_text(pdf_path)
                if not text.strip():
                    logger.warning(f"No text extracted from {pdf_path.name}, skipping")
                    continue

                # Get metadata for this PDF
                meta_entry = metadata_map.get(pdf_path.name, {})
                doc_date = date.fromisoformat(meta_entry["date"]) if "date" in meta_entry else date(2020, 1, 1)
                title = meta_entry.get("title", pdf_path.stem)
                author = meta_entry.get("author", "Unknown")
                topics = meta_entry.get("topics", [])
                sectors = meta_entry.get("sectors", [])

                # Chunk the text
                chunks = self._chunk_text(text, pdf_path.name, doc_date, title)
                chunk_texts = [c.text for c in chunks]

                doc = CorpusDocument(
                    filename=pdf_path.name,
                    date=doc_date,
                    title=title,
                    author=author,
                    topics=topics,
                    sectors=sectors,
                    full_text=text,
                    chunks=chunk_texts,
                )
                documents.append(doc)
                all_chunks.extend(chunks)

                logger.info(f"Processed {pdf_path.name}: {len(chunks)} chunks, {len(self._encoding.encode(text))} tokens")

            except PDFProcessingError:
                raise
            except Exception as e:
                logger.warning(f"Error processing {pdf_path.name}: {e}")
                continue

        logger.info(f"Corpus processing complete: {len(documents)} documents, {len(all_chunks)} chunks")
        return documents, all_chunks

    def _extract_text(self, pdf_path: Path) -> str:
        """Extract text from a single PDF using pymupdf.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Extracted text as a single string.
        """
        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            raise PDFProcessingError(f"Failed to open PDF {pdf_path.name}: {e}")

        pages_text: list[str] = []
        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    pages_text.append(text)
            except Exception as e:
                logger.warning(f"Error extracting page {page_num} from {pdf_path.name}: {e}")
                continue

        doc.close()
        return "\n\n".join(pages_text)

    def _chunk_text(
        self, text: str, filename: str, doc_date: date, title: str
    ) -> list[TextChunk]:
        """Chunk text using tiktoken with configured size and overlap.

        Args:
            text: Full document text.
            filename: Source filename.
            doc_date: Document date.
            title: Document title.

        Returns:
            List of TextChunk objects.
        """
        tokens = self._encoding.encode(text)
        chunk_size = self._settings.chunk_size_tokens
        overlap = self._settings.chunk_overlap_tokens

        chunks: list[TextChunk] = []
        start = 0
        chunk_index = 0

        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self._encoding.decode(chunk_tokens)

            chunk = TextChunk(
                chunk_id=f"{filename}::chunk_{chunk_index}",
                text=chunk_text,
                source_filename=filename,
                source_date=doc_date,
                source_title=title,
                token_count=len(chunk_tokens),
            )
            chunks.append(chunk)
            chunk_index += 1

            # Move forward by chunk_size - overlap
            start += chunk_size - overlap
            if end >= len(tokens):
                break

        return chunks
