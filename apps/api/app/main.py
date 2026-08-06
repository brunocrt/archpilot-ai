"""Main entrypoint for the ArchPilot AI FastAPI application."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import init_db
from .logging_config import configure_logging
from .observability import RequestObservabilityMiddleware
from .api import health, documents, chat, feedback, projects, settings as settings_api, evaluations, metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application resources before serving requests."""
    init_db()
    yield


def create_app() -> FastAPI:
    """Factory for the FastAPI app."""
    configure_logging()
    app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestObservabilityMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.ALLOW_ORIGINS.split(",") if origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(projects.router, prefix="/projects", tags=["projects"])
    app.include_router(documents.router, prefix="/documents", tags=["documents"])
    app.include_router(chat.router, prefix="/chat", tags=["chat"])
    app.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
    app.include_router(settings_api.router, prefix="/settings", tags=["settings"])
    app.include_router(evaluations.router, prefix="/evaluations", tags=["evaluations"])
    app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])

    return app


app = create_app()
