"""
Embedding utilities.

Provides a helper function to generate embeddings for a piece of text using
OpenAI's embeddings API.  If no API key is configured or the request
fails, the function returns None.  You may extend this module to support
other providers or local embedding models.
"""
from __future__ import annotations

import logging
from typing import List, Optional

import httpx

from ..config import settings


logger = logging.getLogger(__name__)


async def get_embedding(text: str, model: str = "text-embedding-ada-002") -> Optional[List[float]]:
    """Generate an embedding for the given text.

    :param text: Text to embed
    :param model: Name of the OpenAI embedding model
    :return: List of floats representing the embedding, or None on failure
    """
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        logger.warning("OPENAI_API_KEY not configured; returning None for embedding")
        return None

    url = "https://api.openai.com/v1/embeddings"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "input": text,
        "model": model,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]  # type: ignore[index]
        except Exception as exc:  # broad catch OK for logging
            logger.exception("Failed to fetch embedding: %s", exc)
            return None