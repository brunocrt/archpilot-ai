"""Prometheus-compatible metrics endpoint."""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from ..observability import metrics


router = APIRouter()


@router.get("/", response_class=PlainTextResponse)
def read_metrics() -> str:
    return metrics.render_prometheus()
