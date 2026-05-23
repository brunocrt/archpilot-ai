"""
Database setup for ArchPilot AI.

Creates a SQLAlchemy engine and a session factory using the database URL from
configuration.  Includes a dependency provider for FastAPI routes.
"""
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .config import settings
from .domain.models import Base


# SQLAlchemy engine and session factory
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create database tables for the application if they do not exist."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db() -> Iterator[Session]:
    """Yield a database session and ensure it is closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
