"""Repository layer for architecture projects."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..domain import models


class ProjectRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_project(self, name: str, description: Optional[str] = None) -> models.Project:
        project = models.Project(name=name.strip(), description=description)
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_project(self, project_id: UUID) -> Optional[models.Project]:
        return self.db.query(models.Project).filter(models.Project.id == project_id).first()

    def get_project_by_name(self, name: str) -> Optional[models.Project]:
        return self.db.query(models.Project).filter(models.Project.name == name.strip()).first()

    def list_projects(self) -> List[models.Project]:
        return self.db.query(models.Project).order_by(models.Project.name).all()
