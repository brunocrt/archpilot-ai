"""Runtime LLM provider settings."""
from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from ..config import settings


@dataclass
class RuntimeLLMSettings:
    provider: str
    model: str
    api_key: str | None


class RuntimeLLMSettingsStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._settings = RuntimeLLMSettings(
            provider="openai" if settings.OPENAI_API_KEY else "none",
            model="gpt-3.5-turbo",
            api_key=settings.OPENAI_API_KEY,
        )

    def get(self) -> RuntimeLLMSettings:
        with self._lock:
            return RuntimeLLMSettings(
                provider=self._settings.provider,
                model=self._settings.model,
                api_key=self._settings.api_key,
            )

    def update(self, provider: str, model: str, api_key: str | None) -> RuntimeLLMSettings:
        with self._lock:
            next_key = api_key.strip() if api_key and api_key.strip() else self._settings.api_key
            if provider == "none":
                next_key = None
            self._settings = RuntimeLLMSettings(
                provider=provider,
                model=model.strip() or "gpt-3.5-turbo",
                api_key=next_key,
            )
            return RuntimeLLMSettings(
                provider=self._settings.provider,
                model=self._settings.model,
                api_key=self._settings.api_key,
            )


llm_settings_store = RuntimeLLMSettingsStore()
