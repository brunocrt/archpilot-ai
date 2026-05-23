"""Architecture project API."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError

from ..dependencies import get_db_session
from ..domain import schemas
from ..repositories.project_repository import ProjectRepository


router = APIRouter()


@router.get("/", response_model=List[schemas.ProjectBase])
def list_projects(db=Depends(get_db_session)) -> List[schemas.ProjectBase]:
    """Return architecture projects sorted by name."""
    return ProjectRepository(db).list_projects()


@router.post("/", response_model=schemas.ProjectBase)
def create_project(payload: schemas.ProjectCreate, db=Depends(get_db_session)) -> schemas.ProjectBase:
    """Create a new architecture project."""
    try:
        return ProjectRepository(db).create_project(
            name=payload.name,
            description=payload.description,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Project name already exists")
