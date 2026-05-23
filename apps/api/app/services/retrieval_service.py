"""Retrieval service for pgvector-backed document chunk search."""
from __future__ import annotations

import logging
import re
from typing import List, Tuple
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..domain import models
from ..utils.embeddings import get_embedding

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    async def retrieve(
        self,
        question: str,
        top_k: int = 5,
        project_id: UUID | None = None,
    ) -> List[Tuple[models.DocumentChunk, float]]:
        """Retrieve relevant chunks for the given question."""
        query_embedding = await get_embedding(question)
        if query_embedding is None:
            logger.warning("No embedding for query; using keyword retrieval")
            chunks = self._keyword_search(question, top_k, project_id=project_id)
            if not chunks:
                query = self.db.query(models.DocumentChunk).join(models.DocumentChunk.document)
                if project_id:
                    query = query.filter(models.Document.project_id == project_id)
                chunks = query.order_by(models.Document.uploaded_at.desc()).limit(top_k).all()
            return [(chunk, 0.0) for chunk in chunks]

        distance = models.DocumentChunk.embedding.cosine_distance(query_embedding)
        query = self.db.query(models.DocumentChunk, distance.label("distance")).join(
            models.DocumentChunk.document
        )
        if project_id:
            query = query.filter(models.Document.project_id == project_id)
        rows = (
            query.filter(models.DocumentChunk.embedding != None)  # noqa: E711
            .order_by(distance)
            .limit(top_k)
            .all()
        )
        return [(chunk, 1.0 - float(chunk_distance)) for chunk, chunk_distance in rows]

    def _keyword_search(
        self,
        question: str,
        top_k: int,
        project_id: UUID | None = None,
    ) -> List[models.DocumentChunk]:
        terms = [
            term
            for term in re.findall(r"[a-z0-9]+", question.lower())
            if len(term) > 3
            and term
            not in {"about", "archpilot", "does", "that", "this", "what", "when", "where", "which", "why"}
        ]
        if not terms:
            return []
        filters = [models.DocumentChunk.content.ilike(f"%{term}%") for term in terms]
        query = self.db.query(models.DocumentChunk).join(models.DocumentChunk.document)
        if project_id:
            query = query.filter(models.Document.project_id == project_id)
        return (
            query.filter(or_(*filters))
            .order_by(models.Document.uploaded_at.desc(), models.DocumentChunk.chunk_index)
            .limit(top_k)
            .all()
        )
