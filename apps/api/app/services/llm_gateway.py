"""
LLM Gateway abstraction.

This module defines a simple interface for sending prompts to a language
model provider.  Currently only the OpenAI chat API is supported.  If no API
key is configured, the gateway will return a fallback response.
"""
from __future__ import annotations

import logging
import re

import httpx

from .llm_settings import llm_settings_store

logger = logging.getLogger(__name__)


class LLMGateway:
    """Gateway for invoking language models."""

    async def ask(self, prompt: str) -> str:
        """Send a prompt to an LLM provider and return the generated answer.

        :param prompt: Prompt text to send
        :return: Assistant response
        """
        runtime_settings = llm_settings_store.get()
        if runtime_settings.provider == "openai" and runtime_settings.api_key:
            return await self._ask_openai(prompt, api_key=runtime_settings.api_key, model=runtime_settings.model)
        else:
            logger.warning("No LLM API key configured; returning extractive fallback answer")
            return self._fallback_answer(prompt)

    def _fallback_answer(self, prompt: str) -> str:
        """Return a cited extractive answer when no LLM provider is configured."""
        question = self._extract_section(prompt, "User question:", "Context:")
        context = prompt.split("Context:", maxsplit=1)[-1].strip()
        chunks = self._parse_context_chunks(context)
        if not chunks:
            return "I do not have enough retrieved context to answer that question."

        terms = self._question_terms(question)
        matches: list[tuple[int, str, str]] = []
        for chunk_id, content in chunks:
            for sentence in self._sentences(self._clean_context(content)):
                score = self._sentence_score(sentence, terms, question)
                if score > 0:
                    matches.append((score, chunk_id, sentence))

        if not matches:
            matches = [
                (0, chunk_id, self._first_excerpt(self._clean_context(content)))
                for chunk_id, content in chunks[:3]
            ]

        matches.sort(key=lambda item: item[0], reverse=True)
        matches = self._deduplicate_matches(matches)
        evidence = " ".join(
            f"{self._first_excerpt(sentence, max_length=220)} [{chunk_id}]"
            for _, chunk_id, sentence in matches[:3]
        )
        return f"Based on the retrieved architecture context: {evidence}"

    def _extract_section(self, text: str, start_marker: str, end_marker: str) -> str:
        if start_marker not in text:
            return ""
        section = text.split(start_marker, maxsplit=1)[1]
        if end_marker in section:
            section = section.split(end_marker, maxsplit=1)[0]
        return section.strip()

    def _parse_context_chunks(self, context: str) -> list[tuple[str, str]]:
        pattern = re.compile(r"^\[(?P<id>[^\]]+)\]\s*(?P<content>.*?)(?=^\[[^\]]+\]|\Z)", re.M | re.S)
        return [
            (match.group("id").strip(), match.group("content").strip())
            for match in pattern.finditer(context)
            if match.group("content").strip()
        ]

    def _question_terms(self, question: str) -> set[str]:
        stop_words = {"about", "archpilot", "choose", "could", "does", "that", "the", "this", "what", "when", "where", "which", "why"}
        return {
            term
            for term in re.findall(r"[a-z0-9]+", question.lower())
            if len(term) > 3 and term not in stop_words
        }

    def _sentences(self, content: str) -> list[str]:
        return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", content) if sentence.strip()]

    def _sentence_score(self, sentence: str, terms: set[str], question: str) -> int:
        if len(sentence.split()) < 5:
            return 0
        lower_sentence = sentence.lower()
        score = sum(1 for term in terms if term in lower_sentence)
        if question.lower().startswith("why"):
            reason_terms = {"allow", "because", "easier", "goal", "however", "overhead", "simple", "slow"}
            score += sum(1 for term in reason_terms if term in lower_sentence)
        return score

    def _clean_context(self, content: str) -> str:
        lines = []
        in_code_block = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            if not stripped or stripped.startswith("#") or stripped in {"Accepted", "Context", "Decision", "Status"}:
                continue
            if stripped.startswith("Date:"):
                continue
            if stripped.endswith(":") and len(stripped.split()) <= 4:
                continue
            if stripped.startswith("|") or set(stripped) <= {"|", "-", "+", " "}:
                continue
            lines.append(stripped.lstrip("-* "))
        return " ".join(lines)

    def _deduplicate_matches(self, matches: list[tuple[int, str, str]]) -> list[tuple[int, str, str]]:
        seen: set[str] = set()
        unique_matches = []
        for score, chunk_id, sentence in matches:
            key = re.sub(r"[^a-z0-9]+", " ", sentence.lower()).strip()[:120]
            if key in seen:
                continue
            seen.add(key)
            unique_matches.append((score, chunk_id, sentence))
        return unique_matches

    def _first_excerpt(self, content: str, max_length: int = 280) -> str:
        excerpt = " ".join(content.split())
        if len(excerpt) <= max_length:
            return excerpt
        return f"{excerpt[:max_length].rstrip()}..."

    async def _ask_openai(self, prompt: str, api_key: str, model: str) -> str:
        """Call OpenAI's Chat API."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
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
