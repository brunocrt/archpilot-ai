"""Runtime application settings API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..domain import schemas
from ..services.llm_settings import llm_settings_store


router = APIRouter()


@router.get("/llm", response_model=schemas.LLMSettingsResponse)
def get_llm_settings() -> schemas.LLMSettingsResponse:
    """Return public LLM provider settings without exposing secrets."""
    current = llm_settings_store.get()
    return schemas.LLMSettingsResponse(
        provider=current.provider,
        model=current.model,
        has_api_key=bool(current.api_key),
    )


@router.post("/llm", response_model=schemas.LLMSettingsResponse)
def update_llm_settings(payload: schemas.LLMSettingsUpdate) -> schemas.LLMSettingsResponse:
    """Update runtime LLM provider settings."""
    if payload.provider not in {"none", "openai"}:
        raise HTTPException(status_code=400, detail="Unsupported LLM provider")
    current = llm_settings_store.update(
        provider=payload.provider,
        model=payload.model,
        api_key=payload.api_key,
    )
    return schemas.LLMSettingsResponse(
        provider=current.provider,
        model=current.model,
        has_api_key=bool(current.api_key),
    )
