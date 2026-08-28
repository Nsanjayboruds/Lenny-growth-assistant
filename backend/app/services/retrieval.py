"""
Retrieval service — pgvector similarity search.

Flow:
  1. Embed the user query using Ollama nomic-embed-text.
  2. Run cosine similarity search against transcript_chunks.
  3. Filter by score threshold.
  4. Return chunks with source metadata.
"""
from __future__ import annotations

import time
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.logging_config import get_logger
from app.providers.ollama import OllamaProvider
from app.schemas.schemas import SourceCitation

logger = get_logger(__name__)


class RetrievalService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._settings = get_settings()
        self._embedder = OllamaProvider()

    async def retrieve(self, query: str) -> list[SourceCitation]:
        """
        Retrieve the most relevant transcript chunks for a query.

        Returns an empty list (not an error) if embedding fails,
        letting the agent handle the insufficient-evidence case gracefully.
        """
        start = time.perf_counter()

        # Step 1: Embed query
        try:
            query_embedding = await self._embedder.embed(query)
        except Exception as e:
            logger.warning("retrieval.embed_failed", error=str(e))
            return []

        # Step 2: pgvector cosine similarity search
        top_k = self._settings.retrieval_top_k
        threshold = self._settings.retrieval_score_threshold

        try:
            # Using 1 - cosine_distance as similarity score (pgvector <=> is cosine distance)
            result = await self._db.execute(
                text("""
                    SELECT
                        tc.id,
                        tc.text,
                        tc.guest,
                        tc.episode_title,
                        tc.youtube_url,
                        1 - (tc.embedding <=> CAST(:embedding AS vector)) AS score
                    FROM transcript_chunks tc
                    WHERE tc.embedding IS NOT NULL
                      AND 1 - (tc.embedding <=> CAST(:embedding AS vector)) >= :threshold
                    ORDER BY tc.embedding <=> CAST(:embedding AS vector)
                    LIMIT :top_k
                """),
                {
                    "embedding": str(query_embedding),
                    "threshold": threshold,
                    "top_k": top_k,
                },
            )
            rows = result.fetchall()
        except Exception as e:
            logger.error("retrieval.db_failed", error=str(e))
            return []

        elapsed = time.perf_counter() - start
        logger.info(
            "retrieval.complete",
            query_preview=query[:80],
            chunks_found=len(rows),
            elapsed_ms=round(elapsed * 1000),
        )

        citations = [
            SourceCitation(
                episode_title=row.episode_title,
                guest=row.guest,
                youtube_url=row.youtube_url,
                chunk_text=row.text,
                score=round(float(row.score), 4),
            )
            for row in rows
        ]
        return citations


def build_context_string(citations: list[SourceCitation]) -> str:
    """
    Build a context string from retrieved citations to inject into the LLM prompt.
    Each citation is clearly labeled with its source.
    """
    if not citations:
        return ""

    parts = []
    for i, c in enumerate(citations, 1):
        source_label = f"[Source {i}] {c.episode_title} — Guest: {c.guest}"
        parts.append(f"{source_label}\n{c.chunk_text}")

    return "\n\n---\n\n".join(parts)
