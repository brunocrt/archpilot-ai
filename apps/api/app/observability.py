"""Lightweight observability helpers for local development."""
from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict
from threading import Lock
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


logger = logging.getLogger("app.requests")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, self.datefmt),
        }
        for key in ("request_id", "method", "path", "status_code", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload)


class MetricsStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[str, float] = defaultdict(float)
        self._durations: dict[str, list[float]] = defaultdict(list)

    def increment(self, name: str, value: float = 1.0) -> None:
        with self._lock:
            self._counters[name] += value

    def observe_duration(self, name: str, duration_ms: float) -> None:
        with self._lock:
            self._durations[name].append(duration_ms)

    def render_prometheus(self) -> str:
        with self._lock:
            counters = dict(self._counters)
            durations = {name: list(values) for name, values in self._durations.items()}
        lines: list[str] = []
        for name, value in sorted(counters.items()):
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value:g}")
        for name, values in sorted(durations.items()):
            count = len(values)
            total = sum(values)
            lines.append(f"# TYPE {name}_milliseconds summary")
            lines.append(f"{name}_milliseconds_count {count}")
            lines.append(f"{name}_milliseconds_sum {total:.4f}")
        return "\n".join(lines) + "\n"


metrics = MetricsStore()


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            metrics.increment("archpilot_http_requests_total")
            if status_code >= 500:
                metrics.increment("archpilot_http_errors_total")
            metrics.observe_duration("archpilot_http_request_duration", duration_ms)
            logger.info(
                "request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            if "response" in locals():
                response.headers["x-request-id"] = request_id
