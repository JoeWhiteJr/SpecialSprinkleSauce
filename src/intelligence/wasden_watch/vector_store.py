"""ChromaDB vector store for the Wasden Watch newsletter corpus."""

import logging
from datetime import date

import chromadb
from chromadb.utils import embedding_functions

from .config import WasdenWatchSettings
from .exceptions import VectorStoreError
from .models import RetrievedPassage, TextChunk

logger = logging.getLogger("wasden_watch")


class VectorStore:
    """ChromaDB-backed vector store with time-decay scoring."""

    COLLECTION_NAME = "wasden_weekender"

    def __init__(self, settings: WasdenWatchSettings):
        self._settings = settings
        try:
            self._client = chromadb.PersistentClient(
                path=settings.chroma_persist_dir
            )
            self._embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                embedding_function=self._embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            raise VectorStoreError(f"Failed to initialize ChromaDB: {e}")

    def ingest(self, chunks: list[TextChunk]) -> int:
        """Ingest text chunks into the vector store.

        Args:
            chunks: List of TextChunk objects to ingest.

        Returns:
            Number of chunks ingested.
        """
        if not chunks:
            logger.warning("No chunks to ingest")
            return 0

        # Skip re-ingestion if already populated with expected count
        if self.is_ingested() and self._collection.count() >= len(chunks):
            logger.info(
                f"Collection already has {self._collection.count()} chunks, "
                f"skipping ingestion of {len(chunks)} chunks"
            )
            return 0

        # Clear existing data if re-ingesting
        if self._collection.count() > 0:
            logger.info("Clearing existing collection for re-ingestion")
            self.clear()

        logger.info(f"Ingesting {len(chunks)} chunks into ChromaDB")

        # ChromaDB has batch limits, process in batches of 500
        batch_size = 500
        total_ingested = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]

            ids = [c.chunk_id for c in batch]
            documents = [c.text for c in batch]
            metadatas = [
                {
                    "source_filename": c.source_filename,
                    "source_date": c.source_date.isoformat(),
                    "source_title": c.source_title,
                    "token_count": c.token_count,
                }
                for c in batch
            ]

            try:
                self._collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                )
                total_ingested += len(batch)
                logger.info(f"Ingested batch {i // batch_size + 1}: {len(batch)} chunks")
            except Exception as e:
                raise VectorStoreError(f"Failed to ingest batch at offset {i}: {e}")

        logger.info(f"Ingestion complete: {total_ingested} chunks total")
        return total_ingested

    def search(self, query: str, top_k: int = 10) -> list[RetrievedPassage]:
        """Search the corpus with time-decay weighted scoring.

        Args:
            query: Search query string.
            top_k: Number of results to return.

        Returns:
            List of RetrievedPassage sorted by final_score descending.
        """
        if self._collection.count() == 0:
            logger.warning("Vector store is empty, cannot search")
            return []

        # Retrieve more than top_k to allow for re-ranking after time decay
        fetch_k = min(top_k * 3, self._collection.count())

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=fetch_k,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            raise VectorStoreError(f"Search failed: {e}")

        passages: list[RetrievedPassage] = []
        today = date.today()
        half_life = self._settings.time_decay_half_life_days

        documents = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []

        for doc_text, metadata, distance in zip(documents, metadatas, distances):
            # ChromaDB cosine distance is in [0, 2], convert to relevance score
            relevance_score = max(0.0, 1.0 - distance)

            doc_date = date.fromisoformat(metadata["source_date"])
            days_old = (today - doc_date).days
            time_decay_weight = 0.5 ** (days_old / half_life)

            final_score = relevance_score * time_decay_weight

            passage = RetrievedPassage(
                text=doc_text,
                source_filename=metadata["source_filename"],
                source_date=doc_date,
                source_title=metadata["source_title"],
                relevance_score=relevance_score,
                time_decay_weight=time_decay_weight,
                final_score=final_score,
            )
            passages.append(passage)

        # Sort by final_score descending and return top_k
        passages.sort(key=lambda p: p.final_score, reverse=True)
        return passages[:top_k]

    def stats(self) -> dict:
        """Return vector store statistics.

        Returns:
            Dict with total_chunks, date_range, collection_name.
        """
        count = self._collection.count()
        result = {
            "total_chunks": count,
            "collection_name": self.COLLECTION_NAME,
            "date_range": None,
        }

        if count > 0:
            # Get date range from metadata
            try:
                all_metadata = self._collection.get(include=["metadatas"])
                dates = []
                for meta in all_metadata["metadatas"]:
                    if "source_date" in meta:
                        dates.append(meta["source_date"])
                if dates:
                    dates.sort()
                    result["date_range"] = {
                        "earliest": dates[0],
                        "latest": dates[-1],
                    }
            except Exception as e:
                logger.warning(f"Failed to compute date range: {e}")

        return result

    def is_ingested(self) -> bool:
        """Check if the collection has any documents."""
        return self._collection.count() > 0

    def clear(self) -> None:
        """Delete and recreate the collection."""
        try:
            self._client.delete_collection(self.COLLECTION_NAME)
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                embedding_function=self._embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("Vector store cleared")
        except Exception as e:
            raise VectorStoreError(f"Failed to clear collection: {e}")
