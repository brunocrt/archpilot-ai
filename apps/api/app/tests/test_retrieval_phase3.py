import unittest
from datetime import datetime
from uuid import uuid4

from app.domain import models
from app.services.retrieval_service import RetrievalService


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
            [(broad, 0.9), (focused, 0.5)],
            top_k=2,
        )

        self.assertEqual(focused.id, ranked[0][0].id)

    def test_merge_combines_vector_and_keyword_scores(self) -> None:
        service = RetrievalService(db=None)  # type: ignore[arg-type]
        chunk = make_chunk("Use pgvector with keyword retrieval.", "retrieval.md")

        merged = service._merge_results([(chunk, 0.6)], [(chunk, 1.0)])

        self.assertEqual(1, len(merged))
        self.assertAlmostEqual(0.74, merged[0][1])


if __name__ == "__main__":
    unittest.main()
