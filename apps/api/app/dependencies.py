"""
Shared dependency providers for FastAPI routes.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from .db import get_db


def get_db_session() -> Session:
    """Provide a database session dependency for FastAPI routes."""
    with get_db() as db:
        yield db