"""
LLM Gateway abstraction.

This module defines a simple interface for sending prompts to a language
model provider.  Currently only the OpenAI chat API is supported.  If no API
key is configured, the gateway will return a fallback response.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class LLMGateway:
    """Gateway for invoking language models."""

    async def ask(self, prompt: str) -> str:
        """Send a prompt to an LLM provider and return the generated answer.

        :param prompt: Prompt text to send
        :return: Assistant response
        """
        # Prefer Anthropic if configured (future extension)
        if settings.OPENAI_API_KEY:
            return await self._ask_openai(prompt)
        else:
            logger.warning("No LLM API key configured; returning fallback answer")
            return "I'm sorry, but I cannot answer that question because no LLM provider is configured."

    async def _ask_openai(self, prompt: str) -> str:
        """Call OpenAI's Chat API."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 512,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]  # type: ignore[index]
            except Exception as exc:  # broad catch OK for logging
                logger.exception("LLM request failed: %s", exc)
                return "There was an error contacting the language model service."