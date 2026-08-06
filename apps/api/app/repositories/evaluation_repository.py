"""Repository layer for persisted evaluation datasets, runs, and results."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..domain import models


class EvaluationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_dataset(self, name: str, description: Optional[str] = None) -> models.EvaluationDataset:
        dataset = models.EvaluationDataset(name=name.strip(), description=description)
        self.db.add(dataset)
        self.db.commit()
        self.db.refresh(dataset)
        return dataset

    def list_datasets(self) -> List[models.EvaluationDataset]:
        return self.db.query(models.EvaluationDataset).order_by(models.EvaluationDataset.created_at.desc()).all()

    def get_dataset(self, dataset_id: UUID) -> Optional[models.EvaluationDataset]:
        return self.db.query(models.EvaluationDataset).filter(models.EvaluationDataset.id == dataset_id).first()

    def create_case(
        self,
        dataset_id: UUID,
        question: str,
        expected_answer: Optional[str],
        expected_facts: list[str],
        expected_chunk_ids: list[str],
    ) -> models.EvaluationCase:
        case = models.EvaluationCase(
            dataset_id=dataset_id,
            question=question.strip(),
            expected_answer=expected_answer,
            expected_facts=expected_facts,
            expected_chunk_ids=expected_chunk_ids,
        )
        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)
        return case

    def list_cases(self, dataset_id: UUID) -> List[models.EvaluationCase]:
        return (
            self.db.query(models.EvaluationCase)
            .filter(models.EvaluationCase.dataset_id == dataset_id)
            .order_by(models.EvaluationCase.created_at)
            .all()
        )

    def create_run(
        self,
        dataset_id: UUID,
        provider: Optional[str],
        model: Optional[str],
    ) -> models.EvaluationRun:
        run = models.EvaluationRun(dataset_id=dataset_id, provider=provider, model=model, status="running")
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def complete_run(self, run: models.EvaluationRun, aggregate_metrics: dict) -> models.EvaluationRun:
        from datetime import datetime

        run.status = "completed"
        run.aggregate_metrics = aggregate_metrics
        run.completed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(run)
        return run

    def add_result(
        self,
        run_id: UUID,
        case_id: UUID,
        generated_answer: str,
        retrieved_chunks: list[dict],
        retrieval_metrics: dict,
        answer_metrics: dict,
        provider: Optional[str],
        model: Optional[str],
        status: str,
    ) -> models.EvaluationResult:
        result = models.EvaluationResult(
            run_id=run_id,
            case_id=case_id,
            generated_answer=generated_answer,
            retrieved_chunks=retrieved_chunks,
            retrieval_metrics=retrieval_metrics,
            answer_metrics=answer_metrics,
            provider=provider,
            model=model,
            status=status,
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    def list_runs(self) -> List[models.EvaluationRun]:
        return self.db.query(models.EvaluationRun).order_by(models.EvaluationRun.started_at.desc()).all()

    def get_run(self, run_id: UUID) -> Optional[models.EvaluationRun]:
        return self.db.query(models.EvaluationRun).filter(models.EvaluationRun.id == run_id).first()

    def list_results(self, run_id: UUID) -> List[models.EvaluationResult]:
        return (
            self.db.query(models.EvaluationResult)
            .filter(models.EvaluationResult.run_id == run_id)
            .order_by(models.EvaluationResult.created_at)
            .all()
        )
