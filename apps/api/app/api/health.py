"""
Health check endpoint.
"""
from fastapi import APIRouter


router = APIRouter()


@router.get("/")
def read_health() -> dict[str, str]:
    """Return a simple health status."""
    return {"status": "ok"}