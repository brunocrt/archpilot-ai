import unittest
from datetime import datetime
from uuid import uuid4

from app.domain import models
from app.services.retrieval_service import RetrievalMatch, RetrievalService


def make_chunk(content: str, filename: str, chunk_index: int = 0) -> models.DocumentChunk:
    document = models.Document(
        id=uuid4(),
        filename=filename,
        content_type="text/markdown",
        uploaded_at=datetime.utcnow(),
    )
    return models.DocumentChunk(
        id=uuid4(),
        document=document,
        document_id=document.id,
        chunk_index=chunk_index,
        content=content,
    )


class RetrievalPhase3Tests(unittest.TestCase):
    def test_rerank_boosts_exact_phrase_match(self) -> None:
        service = RetrievalService(db=None)  # type: ignore[arg-type]
        broad = make_chunk("Architecture overview and implementation notes.", "overview.md")
        focused = make_chunk("Use a modular monolith for the MVP.", "0001-modular-monolith.md")

        ranked = service._rerank(
            "Why choose a modular monolith?",
            [
                RetrievalMatch(chunk=broad, score=0.9, signal="vector"),
                RetrievalMatch(chunk=focused, score=0.5, signal="keyword"),
            ],
            top_k=2,
        )

        self.assertEqual(focused.id, ranked[0].chunk.id)

    def test_merge_combines_vector_and_keyword_scores(self) -> None:
        service = RetrievalService(db=None)  # type: ignore[arg-type]
        chunk = make_chunk("Use pgvector with keyword retrieval.", "retrieval.md")

        merged = service._merge_results(
            [RetrievalMatch(chunk=chunk, score=0.6, signal="vector")],
            [RetrievalMatch(chunk=chunk, score=1.0, signal="keyword")],
        )

        self.assertEqual(1, len(merged))
        self.assertAlmostEqual(0.74, merged[0].score)
        self.assertEqual("hybrid", merged[0].signal)


if __name__ == "__main__":
    unittest.main()
