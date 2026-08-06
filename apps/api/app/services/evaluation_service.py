"""Deterministic evaluation service for retrieval and grounded answers."""
from __future__ import annotations

import time
from statistics import mean

from sqlalchemy.orm import Session

from ..domain import models, schemas
from ..repositories.evaluation_repository import EvaluationRepository
from ..services.llm_gateway import LLMGateway
from ..services.llm_settings import llm_settings_store
from ..services.prompt_service import build_prompt
from ..services.retrieval_service import RetrievalService


class EvaluationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EvaluationRepository(db)

    async def run_dataset(self, dataset: models.EvaluationDataset, top_k: int) -> models.EvaluationRun:
        runtime_settings = llm_settings_store.get()
        run = self.repo.create_run(dataset.id, runtime_settings.provider, runtime_settings.model)
        cases = self.repo.list_cases(dataset.id)
        for case in cases:
            await self._run_case(run, case, top_k, runtime_settings.provider, runtime_settings.model)
        return self.repo.complete_run(run, self._aggregate_metrics(self.repo.list_results(run.id)))

    async def _run_case(
        self,
        run: models.EvaluationRun,
        case: models.EvaluationCase,
        top_k: int,
        provider: str | None,
        model: str | None,
    ) -> None:
        started = time.perf_counter()
        matches = await RetrievalService(self.db).retrieve(case.question, top_k=top_k)
        retrieval_latency_ms = (time.perf_counter() - started) * 1000
        retrieved_chunks = [
            schemas.RetrievedChunk(
                chunk_id=str(match.chunk.id),
                document_id=str(match.chunk.document_id),
                document_filename=match.chunk.document.filename,
                document_project_name=match.chunk.document.project_name,
                document_content_type=match.chunk.document.content_type,
                chunk_index=match.chunk.chunk_index,
                score=match.score,
                retrieval_signal=match.signal,
                content=match.chunk.content,
            )
            for match in matches
        ]
        answer = await LLMGateway().ask(build_prompt(case.question, retrieved_chunks))
        retrieval_metrics = self.retrieval_metrics(
            [chunk.chunk_id for chunk in retrieved_chunks],
            case.expected_chunk_ids or [],
            retrieval_latency_ms,
        )
        answer_metrics = self.answer_metrics(
            answer,
            [chunk.chunk_id for chunk in retrieved_chunks],
            case.expected_facts or [],
        )
        status = "passed" if answer_metrics["answer_completeness"] >= 0.6 and retrieval_metrics["context_recall"] >= 0.6 else "failed"
        if not case.expected_facts and not case.expected_chunk_ids:
            status = "completed"
        self.repo.add_result(
            run.id,
            case.id,
            generated_answer=answer,
            retrieved_chunks=[chunk.model_dump(mode="json") for chunk in retrieved_chunks],
            retrieval_metrics=retrieval_metrics,
            answer_metrics=answer_metrics,
            provider=provider,
            model=model,
            status=status,
        )

    def retrieval_metrics(
        self,
        retrieved_chunk_ids: list[str],
        expected_chunk_ids: list[str],
        retrieval_latency_ms: float,
    ) -> dict:
        expected = set(expected_chunk_ids)
        retrieved = set(retrieved_chunk_ids)
        overlap = expected & retrieved
        precision = len(overlap) / len(retrieved) if retrieved and expected else 1.0
        recall = len(overlap) / len(expected) if expected else 1.0
        return {
            "context_precision": round(precision, 4),
            "context_recall": round(recall, 4),
            "retrieval_latency_ms": round(retrieval_latency_ms, 2),
        }

    def answer_metrics(self, answer: str, retrieved_chunk_ids: list[str], expected_facts: list[str]) -> dict:
        normalized_answer = answer.lower()
        expected = [fact.strip().lower() for fact in expected_facts if fact.strip()]
        found_facts = [fact for fact in expected if fact in normalized_answer]
        citation_hits = [chunk_id for chunk_id in retrieved_chunk_ids if f"[{chunk_id}]" in answer]
        citation_coverage = len(citation_hits) / len(retrieved_chunk_ids) if retrieved_chunk_ids else 1.0
        completeness = len(found_facts) / len(expected) if expected else 1.0
        unsupported_claim_score = 1.0 if citation_hits or not retrieved_chunk_ids else 0.5
        return {
            "citation_coverage": round(citation_coverage, 4),
            "unsupported_claim_score": unsupported_claim_score,
            "answer_completeness": round(completeness, 4),
            "matched_expected_facts": found_facts,
        }

    def _aggregate_metrics(self, results: list[models.EvaluationResult]) -> dict:
        if not results:
            return {"case_count": 0, "pass_rate": 0.0}
        passed = [result for result in results if result.status == "passed"]
        return {
            "case_count": len(results),
            "pass_rate": round(len(passed) / len(results), 4),
            "average_context_precision": self._average_metric(results, "retrieval_metrics", "context_precision"),
            "average_context_recall": self._average_metric(results, "retrieval_metrics", "context_recall"),
            "average_citation_coverage": self._average_metric(results, "answer_metrics", "citation_coverage"),
            "average_answer_completeness": self._average_metric(results, "answer_metrics", "answer_completeness"),
            "average_retrieval_latency_ms": self._average_metric(results, "retrieval_metrics", "retrieval_latency_ms"),
        }

    def _average_metric(self, results: list[models.EvaluationResult], group: str, metric: str) -> float:
        values = [
            (getattr(result, group) or {}).get(metric)
            for result in results
            if (getattr(result, group) or {}).get(metric) is not None
        ]
        return round(mean(values), 4) if values else 0.0
