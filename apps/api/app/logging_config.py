"""
Logging configuration for the application.

Configure the root logger and set log levels for third party libraries.
"""
import logging
import sys

from .config import settings


def configure_logging() -> None:
    """Configure basic logging for the app."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Reduce noise from third-party libraries
    for noisy in ["uvicorn", "sqlalchemy.engine", "httpx"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)