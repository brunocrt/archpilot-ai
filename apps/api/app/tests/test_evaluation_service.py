import unittest

from app.services.evaluation_service import EvaluationService


class EvaluationServiceTests(unittest.TestCase):
    def test_retrieval_metrics_score_expected_chunk_overlap(self) -> None:
        service = EvaluationService(db=None)  # type: ignore[arg-type]

        metrics = service.retrieval_metrics(
            retrieved_chunk_ids=["a", "b", "c"],
            expected_chunk_ids=["b", "d"],
            retrieval_latency_ms=12.345,
        )

        self.assertEqual(0.3333, metrics["context_precision"])
        self.assertEqual(0.5, metrics["context_recall"])
        self.assertEqual(12.35, metrics["retrieval_latency_ms"])

    def test_answer_metrics_score_facts_and_citations(self) -> None:
        service = EvaluationService(db=None)  # type: ignore[arg-type]

        metrics = service.answer_metrics(
            "Use a modular monolith for faster development. [chunk-1]",
            retrieved_chunk_ids=["chunk-1", "chunk-2"],
            expected_facts=["modular monolith", "easier debugging"],
        )

        self.assertEqual(0.5, metrics["answer_completeness"])
        self.assertEqual(0.5, metrics["citation_coverage"])
        self.assertEqual(["modular monolith"], metrics["matched_expected_facts"])


if __name__ == "__main__":
    unittest.main()
