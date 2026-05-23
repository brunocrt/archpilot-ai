"""Retrieval service for pgvector-backed document chunk search."""
from __future__ import annotations

import logging
from typing import List, Tuple

from sqlalchemy.orm import Session

from ..domain import models
from ..utils.embeddings import get_embedding

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    async def retrieve(self, question: str, top_k: int = 5) -> List[Tuple[models.DocumentChunk, float]]:
        """Retrieve relevant chunks for the given question."""
        query_embedding = await get_embedding(question)
        if query_embedding is None:
            logger.warning("No embedding for query; returning most recent chunks")
            chunks = (
                self.db.query(models.DocumentChunk)
                .order_by(models.DocumentChunk.id.desc())
                .limit(top_k)
                .all()
            )
            return [(chunk, 0.0) for chunk in chunks]

        distance = models.DocumentChunk.embedding.cosine_distance(query_embedding)
        rows = (
            self.db.query(models.DocumentChunk, distance.label("distance"))
            .filter(models.DocumentChunk.embedding != None)  # noqa: E711
            .order_by(distance)
            .limit(top_k)
            .all()
        )
        return [(chunk, 1.0 - float(chunk_distance)) for chunk, chunk_distance in rows]
