"""Retrieval service for pgvector-backed document chunk search."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from ..domain import models
from ..utils.embeddings import get_embedding

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievalMatch:
    chunk: models.DocumentChunk
    score: float
    signal: str


class RetrievalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    async def retrieve(
        self,
        question: str,
        top_k: int = 5,
        project_id: UUID | None = None,
        document_filename: str | None = None,
        content_type: str | None = None,
    ) -> List[RetrievalMatch]:
        """Retrieve relevant chunks using hybrid vector and keyword signals."""
        candidate_limit = max(top_k * 8, 20)
        keyword_results = self._keyword_search(
            question,
            candidate_limit,
            project_id=project_id,
            document_filename=document_filename,
            content_type=content_type,
        )
        query_embedding = await get_embedding(question)
        if query_embedding is None:
            logger.warning("No embedding for query; using keyword retrieval")
            if keyword_results:
                return self._rerank(question, keyword_results, top_k)
            return self._latest_chunks(top_k, project_id, document_filename, content_type)

        distance = models.DocumentChunk.embedding.cosine_distance(query_embedding)
        query = self.db.query(models.DocumentChunk, distance.label("distance")).join(
            models.DocumentChunk.document
        )
        query = self._apply_filters(query, project_id, document_filename, content_type)
        rows = (
            query.filter(models.DocumentChunk.embedding != None)  # noqa: E711
            .order_by(distance)
            .limit(candidate_limit)
            .all()
        )
        vector_results = [
            RetrievalMatch(chunk=chunk, score=max(0.0, 1.0 - float(chunk_distance)), signal="vector")
            for chunk, chunk_distance in rows
        ]
        return self._rerank(
            question,
            self._merge_results(vector_results, keyword_results),
            top_k,
        )

    def _keyword_search(
        self,
        question: str,
        top_k: int,
        project_id: UUID | None = None,
        document_filename: str | None = None,
        content_type: str | None = None,
    ) -> List[RetrievalMatch]:
        terms = self._question_terms(question)
        if not terms:
            return []
        filters = [models.DocumentChunk.content.ilike(f"%{term}%") for term in terms]
        query = self.db.query(models.DocumentChunk).join(models.DocumentChunk.document)
        query = self._apply_filters(query, project_id, document_filename, content_type)
        candidates = (
            query.filter(or_(*filters))
            .order_by(models.Document.uploaded_at.desc(), models.DocumentChunk.chunk_index)
            .limit(top_k)
            .all()
        )
        ranked = [
            (self._keyword_score(question, terms, chunk), chunk)
            for chunk in candidates
        ]
        ranked = [(score, chunk) for score, chunk in ranked if score > 0]
        ranked.sort(
            key=lambda item: (
                item[0],
                item[1].document.uploaded_at,
                -item[1].chunk_index,
            ),
            reverse=True,
        )
        max_score = max((score for score, _ in ranked), default=1)
        return [
            RetrievalMatch(chunk=chunk, score=score / max_score, signal="keyword")
            for score, chunk in ranked[:top_k]
        ]

    def _apply_filters(
        self,
        query: Query,
        project_id: UUID | None,
        document_filename: str | None,
        content_type: str | None,
    ) -> Query:
        if project_id:
            query = query.filter(models.Document.project_id == project_id)
        if document_filename:
            query = query.filter(models.Document.filename.ilike(f"%{document_filename}%"))
        if content_type:
            query = query.filter(models.Document.content_type == content_type)
        return query

    def _latest_chunks(
        self,
        top_k: int,
        project_id: UUID | None,
        document_filename: str | None,
        content_type: str | None,
    ) -> List[RetrievalMatch]:
        query = self.db.query(models.DocumentChunk).join(models.DocumentChunk.document)
        query = self._apply_filters(query, project_id, document_filename, content_type)
        chunks = query.order_by(models.Document.uploaded_at.desc()).limit(top_k).all()
        return [RetrievalMatch(chunk=chunk, score=0.0, signal="latest") for chunk in chunks]

    def _merge_results(
        self,
        vector_results: List[RetrievalMatch],
        keyword_results: List[RetrievalMatch],
    ) -> List[RetrievalMatch]:
        merged: dict[UUID, tuple[models.DocumentChunk, float, float]] = {}
        for match in vector_results:
            merged[match.chunk.id] = (match.chunk, match.score, 0.0)
        for match in keyword_results:
            current = merged.get(match.chunk.id, (match.chunk, 0.0, 0.0))
            merged[match.chunk.id] = (match.chunk, current[1], match.score)
        return [
            RetrievalMatch(
                chunk=chunk,
                score=(vector_score * 0.65) + (keyword_score * 0.35),
                signal=self._retrieval_signal(vector_score, keyword_score),
            )
            for chunk, vector_score, keyword_score in merged.values()
        ]

    def _retrieval_signal(self, vector_score: float, keyword_score: float) -> str:
        if vector_score > 0 and keyword_score > 0:
            return "hybrid"
        if vector_score > 0:
            return "vector"
        return "keyword"

    def _rerank(
        self,
        question: str,
        results: List[RetrievalMatch],
        top_k: int,
    ) -> List[RetrievalMatch]:
        terms = self._question_terms(question)
        ranked = [
            (match, match.score + (self._keyword_score(question, terms, match.chunk) / 20.0))
            for match in results
        ]
        ranked.sort(
            key=lambda item: (
                item[1],
                item[0].chunk.document.uploaded_at,
                -item[0].chunk.chunk_index,
            ),
            reverse=True,
        )
        return [
            RetrievalMatch(chunk=match.chunk, score=min(score, 1.0), signal=match.signal)
            for match, score in ranked[:top_k]
        ]

    def _question_terms(self, question: str) -> list[str]:
        stop_words = {
            "about",
            "archpilot",
            "choose",
            "does",
            "that",
            "this",
            "what",
            "when",
            "where",
            "which",
            "why",
        }
        return [
            term
            for term in re.findall(r"[a-z0-9]+", question.lower())
            if len(term) > 3 and term not in stop_words
        ]

    def _keyword_score(
        self,
        question: str,
        terms: list[str],
        chunk: models.DocumentChunk,
    ) -> int:
        content = chunk.content.lower()
        filename = chunk.document.filename.lower()
        score = sum(2 for term in terms if term in content)
        score += sum(1 for term in terms if term in filename)

        phrases = self._question_phrases(question)
        score += sum(6 for phrase in phrases if phrase in content)
        score += sum(3 for phrase in phrases if phrase in filename)

        if question.lower().lstrip().startswith("why"):
            reason_terms = {"because", "debugging", "easier", "faster", "overhead", "simple", "simpler"}
            score += sum(1 for term in reason_terms if term in content)
        return score

    def _question_phrases(self, question: str) -> list[str]:
        terms = self._question_terms(question)
        return [
            f"{terms[index]} {terms[index + 1]}"
            for index in range(len(terms) - 1)
        ]
