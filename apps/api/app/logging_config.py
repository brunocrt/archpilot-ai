"""
Logging configuration for the application.

Configure the root logger and set log levels for third party libraries.
"""
import logging
import sys

from .config import settings
from .observability import JsonFormatter


def configure_logging() -> None:
    """Configure basic logging for the app."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=log_level, handlers=[handler], force=True)

    # Reduce noise from third-party libraries
    for noisy in ["uvicorn", "sqlalchemy.engine", "httpx"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)
