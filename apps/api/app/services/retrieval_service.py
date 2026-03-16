"""
Retrieval service for searching relevant document chunks.

Given a user query, this service generates an embedding for the query and
computes similarity scores against all stored document chunks.  It returns
the top‑k most similar chunks along with their scores.

Note: This MVP implementation performs the similarity search in Python by
loading all embeddings into memory.  In production you should leverage
database vector search (e.g. pgvector) for efficiency.
"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import anyio

from sqlalchemy.orm import Session

from ..utils.embeddings import get_embedding
from ..domain import models

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    async def retrieve(self, question: str, top_k: int = 5) -> List[Tuple[models.DocumentChunk, float]]:
        """Retrieve relevant chunks for the given question.

        :param question: The query string
        :param top_k: Number of chunks to return
        :return: List of (chunk, similarity score) tuples sorted by descending score
        """
        query_embedding = await get_embedding(question)
        if query_embedding is None:
            # If embeddings are unavailable, return most recent chunks
            logger.warning("No embedding for query; returning most recent chunks")
            chunks = (
                self.db.query(models.DocumentChunk)
                .order_by(models.DocumentChunk.id.desc())
                .limit(top_k)
                .all()
            )
            return [(chunk, 0.0) for chunk in chunks]

        # Retrieve all chunks with embeddings
        all_chunks = self.db.query(models.DocumentChunk).filter(models.DocumentChunk.embedding != None).all()  # noqa: E711
        scored: List[Tuple[models.DocumentChunk, float]] = []
        for chunk in all_chunks:
            emb = chunk.embedding  # type: ignore[assignment]
            if not emb:
                continue
            score = dot_product(query_embedding, emb) / (magnitude(query_embedding) * magnitude(emb))
            scored.append((chunk, score))

        # Sort by score descending and take top_k
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]


def dot_product(a: List[float], b: List[float]) -> float:
    return float(sum(x * y for x, y in zip(a, b)))


def magnitude(v: List[float]) -> float:
    return float(sum(x * x for x in v)) ** 0.5