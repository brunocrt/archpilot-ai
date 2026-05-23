"""
Application configuration module.

Uses pydantic BaseSettings to load values from environment variables. See
.env.example for available variables.
"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration for the FastAPI application."""

    APP_NAME: str = Field("ArchPilotAI", description="Name of the application")
    LOG_LEVEL: str = Field("info", description="Logging level")
    DATABASE_URL: str = Field(..., description="SQLAlchemy database URI")
    OPENAI_API_KEY: str | None = Field(None, description="API key for OpenAI embeddings and chat")
    ANTHROPIC_API_KEY: str | None = Field(None, description="API key for Anthropic models")
    ALLOW_ORIGINS: str = Field("*", description="Comma separated list of allowed CORS origins")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of settings."""
    return Settings()  # type: ignore


# Instantiate at module load
settings = get_settings()