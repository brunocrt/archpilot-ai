"""Evaluation API for local retrieval and answer-quality checks."""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError

from ..dependencies import get_db_session
from ..domain import models, schemas
from ..repositories.evaluation_repository import EvaluationRepository
from ..services.evaluation_service import EvaluationService


router = APIRouter()


def _parse_uuid(value: str, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}")


def _dataset_response(dataset: models.EvaluationDataset) -> schemas.EvaluationDatasetResponse:
    return schemas.EvaluationDatasetResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        created_at=dataset.created_at,
        case_count=len(dataset.cases),
    )


def _case_response(case: models.EvaluationCase) -> schemas.EvaluationCaseResponse:
    return schemas.EvaluationCaseResponse(
        id=case.id,
        dataset_id=case.dataset_id,
        question=case.question,
        expected_answer=case.expected_answer,
        expected_facts=case.expected_facts or [],
        expected_chunk_ids=case.expected_chunk_ids or [],
        created_at=case.created_at,
    )


def _run_summary(run: models.EvaluationRun) -> schemas.EvaluationRunSummary:
    return schemas.EvaluationRunSummary(
        id=run.id,
        dataset_id=run.dataset_id,
        dataset_name=run.dataset.name,
        status=run.status,
        provider=run.provider,
        model=run.model,
        aggregate_metrics=run.aggregate_metrics or {},
        started_at=run.started_at,
        completed_at=run.completed_at,
        result_count=len(run.results),
    )


def _result_response(result: models.EvaluationResult) -> schemas.EvaluationResultResponse:
    return schemas.EvaluationResultResponse(
        id=result.id,
        case_id=result.case_id,
        question=result.case.question,
        generated_answer=result.generated_answer,
        retrieved_chunks=result.retrieved_chunks or [],
        retrieval_metrics=result.retrieval_metrics or {},
        answer_metrics=result.answer_metrics or {},
        provider=result.provider,
        model=result.model,
        status=result.status,
        created_at=result.created_at,
    )


@router.post("/datasets", response_model=schemas.EvaluationDatasetResponse)
def create_dataset(
    payload: schemas.EvaluationDatasetCreate,
    db=Depends(get_db_session),
) -> schemas.EvaluationDatasetResponse:
    repo = EvaluationRepository(db)
    try:
        return _dataset_response(repo.create_dataset(payload.name, payload.description))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Evaluation dataset name already exists")


@router.get("/datasets", response_model=List[schemas.EvaluationDatasetResponse])
def list_datasets(db=Depends(get_db_session)) -> List[schemas.EvaluationDatasetResponse]:
    return [_dataset_response(dataset) for dataset in EvaluationRepository(db).list_datasets()]


@router.post("/datasets/{dataset_id}/cases", response_model=schemas.EvaluationCaseResponse)
def create_case(
    dataset_id: str,
    payload: schemas.EvaluationCaseCreate,
    db=Depends(get_db_session),
) -> schemas.EvaluationCaseResponse:
    repo = EvaluationRepository(db)
    dataset_uuid = _parse_uuid(dataset_id, "dataset_id")
    if repo.get_dataset(dataset_uuid) is None:
        raise HTTPException(status_code=404, detail="Evaluation dataset not found")
    return _case_response(
        repo.create_case(
            dataset_uuid,
            payload.question,
            payload.expected_answer,
            payload.expected_facts,
            payload.expected_chunk_ids,
        )
    )


@router.get("/datasets/{dataset_id}/cases", response_model=List[schemas.EvaluationCaseResponse])
def list_cases(dataset_id: str, db=Depends(get_db_session)) -> List[schemas.EvaluationCaseResponse]:
    repo = EvaluationRepository(db)
    dataset_uuid = _parse_uuid(dataset_id, "dataset_id")
    if repo.get_dataset(dataset_uuid) is None:
        raise HTTPException(status_code=404, detail="Evaluation dataset not found")
    return [_case_response(case) for case in repo.list_cases(dataset_uuid)]


@router.post("/runs", response_model=schemas.EvaluationRunDetail)
async def create_run(
    payload: schemas.EvaluationRunCreate,
    db=Depends(get_db_session),
) -> schemas.EvaluationRunDetail:
    repo = EvaluationRepository(db)
    dataset_uuid = _parse_uuid(payload.dataset_id, "dataset_id")
    dataset = repo.get_dataset(dataset_uuid)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Evaluation dataset not found")
    run = await EvaluationService(db).run_dataset(dataset, payload.top_k)
    return get_run(str(run.id), db)


@router.get("/runs", response_model=List[schemas.EvaluationRunSummary])
def list_runs(db=Depends(get_db_session)) -> List[schemas.EvaluationRunSummary]:
    return [_run_summary(run) for run in EvaluationRepository(db).list_runs()]


@router.get("/runs/{run_id}", response_model=schemas.EvaluationRunDetail)
def get_run(run_id: str, db=Depends(get_db_session)) -> schemas.EvaluationRunDetail:
    repo = EvaluationRepository(db)
    run_uuid = _parse_uuid(run_id, "run_id")
    run = repo.get_run(run_uuid)
    if run is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    summary = _run_summary(run)
    return schemas.EvaluationRunDetail(
        **summary.model_dump(),
        results=[_result_response(result) for result in repo.list_results(run.id)],
    )
