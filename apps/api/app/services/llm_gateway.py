"""
LLM Gateway abstraction.

This module defines a simple interface for sending prompts to a language
model provider.  Currently only the OpenAI chat API is supported.  If no API
key is configured, the gateway will return a fallback response.
"""
from __future__ import annotations

import logging
import json
import re
from typing import AsyncIterator

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
        question = self._extract_question(prompt)
        context = prompt.split("Context:", maxsplit=1)[-1].strip()
        chunks = self._parse_context_chunks(context)
        if not chunks:
            return "I do not have enough retrieved context to answer that question."

        terms = self._question_terms(question)
        matches: list[tuple[int, str, str]] = []
        for chunk_id, content in chunks:
            for excerpt in self._decision_reason_excerpts(content):
                score = self._sentence_score(excerpt, terms, question)
                if score > 0:
                    matches.append((score + self._content_score(excerpt, terms, question), chunk_id, excerpt))
            cleaned_content = self._clean_context(content)
            chunk_score = self._content_score(cleaned_content, terms, question)
            for sentence in self._sentences(cleaned_content):
                score = self._sentence_score(sentence, terms, question)
                if score > 0:
                    matches.append((score + chunk_score, chunk_id, sentence))

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

    def _extract_question(self, prompt: str) -> str:
        for marker in ("User question:", "Question:"):
            question = self._extract_section(prompt, marker, "Context:")
            if question:
                return question
        return ""

    def _parse_context_chunks(self, context: str) -> list[tuple[str, str]]:
        pattern = re.compile(r"^\[(?P<id>[^\]]+)\]\s*(?P<content>.*?)(?=^\[[^\]]+\]|\Z)", re.M | re.S)
        return [
            (match.group("id").strip(), match.group("content").strip())
            for match in pattern.finditer(context)
            if match.group("content").strip()
        ]

    def _decision_reason_excerpts(self, content: str) -> list[str]:
        lines = [line.strip().lstrip("-* ").strip() for line in content.splitlines()]
        excerpts: list[str] = []
        index = 0
        while index < len(lines):
            line = lines[index]
            if line.lower().startswith("decision:"):
                decision = line.split(":", maxsplit=1)[1].strip()
                if not decision and index + 1 < len(lines):
                    decision = lines[index + 1]
                reason = self._nearby_labeled_value(lines, index + 1, "reason")
                if decision and reason:
                    excerpts.append(f"{decision} Reason: {reason}")
            index += 1
        return excerpts

    def _nearby_labeled_value(self, lines: list[str], start_index: int, label: str) -> str:
        for index in range(start_index, min(start_index + 5, len(lines))):
            line = lines[index]
            if line.lower().startswith(f"{label}:"):
                value = line.split(":", maxsplit=1)[1].strip()
                if value:
                    return value
                if index + 1 < len(lines):
                    return lines[index + 1]
        return ""

    def _question_terms(self, question: str) -> set[str]:
        stop_words = {"about", "archpilot", "choose", "could", "does", "that", "the", "this", "what", "when", "where", "which", "why"}
        return {
            term
            for term in re.findall(r"[a-z0-9]+", question.lower())
            if len(term) > 3 and term not in stop_words
        }

    def _sentences(self, content: str) -> list[str]:
        sentences: list[str] = []
        for sentence in re.split(r"(?<=[.!?])\s+", content):
            sentence = sentence.strip()
            if sentence and not self._looks_like_mixed_decision_list(sentence):
                sentences.append(sentence)
        return sentences

    def _sentence_score(self, sentence: str, terms: set[str], question: str) -> int:
        if len(sentence.split()) < 5:
            return 0
        lower_sentence = sentence.lower()
        direct_hits = sum(1 for term in terms if term in lower_sentence)
        score = direct_hits
        for phrase in self._question_phrases(question):
            if phrase in lower_sentence:
                score += 5
        if question.lower().startswith("why"):
            reason_terms = {"allow", "because", "easier", "goal", "however", "overhead", "simple", "slow"}
            score += sum(1 for term in reason_terms if term in lower_sentence)
            if direct_hits == 0 and score < 2:
                return 0
        return score

    def _content_score(self, content: str, terms: set[str], question: str) -> int:
        lower_content = content.lower()
        score = sum(1 for term in terms if term in lower_content)
        score += sum(4 for phrase in self._question_phrases(question) if phrase in lower_content)
        return score

    def _question_phrases(self, question: str) -> list[str]:
        terms = [
            term
            for term in re.findall(r"[a-z0-9]+", question.lower())
            if term in self._question_terms(question)
        ]
        return [
            f"{terms[index]} {terms[index + 1]}"
            for index in range(len(terms) - 1)
        ]

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
            bullet = stripped.lstrip("-* ").strip()
            if not self._looks_like_heading_label(bullet):
                lines.append(bullet)
        return " ".join(lines)

    def _looks_like_heading_label(self, text: str) -> bool:
        words = text.split()
        return len(words) <= 3 and not text.endswith((".", "?", "!"))

    def _looks_like_mixed_decision_list(self, sentence: str) -> bool:
        lower_sentence = sentence.lower()
        decision_markers = {
            "use embeddings",
            "keyword search",
            "use fastapi",
            "modular monolith",
            "pdf parsing",
            "pgvector",
        }
        return sum(1 for marker in decision_markers if marker in lower_sentence) >= 3

    def _deduplicate_matches(self, matches: list[tuple[int, str, str]]) -> list[tuple[int, str, str]]:
        seen: set[str] = set()
        unique_matches = []
        for score, chunk_id, sentence in matches:
            key = re.sub(r"[^a-z0-9]+", " ", sentence.lower()).strip()[:120]
            if any(key in seen_key or seen_key in key for seen_key in seen):
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

    async def ask_stream(self, prompt: str) -> AsyncIterator[str]:
        """Stream response text from the configured provider when supported."""
        runtime_settings = llm_settings_store.get()
        if runtime_settings.provider == "openai" and runtime_settings.api_key:
            async for delta in self._ask_openai_stream(
                prompt,
                api_key=runtime_settings.api_key,
                model=runtime_settings.model,
            ):
                yield delta
            return

        answer = self._fallback_answer(prompt)
        for chunk in self._chunk_text(answer):
            yield chunk

    def _chunk_text(self, text: str, size: int = 24) -> list[str]:
        words = text.split(" ")
        chunks: list[str] = []
        for index in range(0, len(words), size):
            chunk = " ".join(words[index:index + size])
            if index + size < len(words):
                chunk += " "
            chunks.append(chunk)
        return chunks

    async def _ask_openai_stream(self, prompt: str, api_key: str, model: str) -> AsyncIterator[str]:
        """Stream text deltas from OpenAI's Chat API."""
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
            "stream": True,
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line.removeprefix("data: ").strip()
                        if data == "[DONE]":
                            break
                        payload = json.loads(data)
                        delta = payload["choices"][0].get("delta", {}).get("content")
                        if delta:
                            yield delta
        except Exception as exc:  # broad catch OK for logging
            logger.exception("Streaming LLM request failed: %s", exc)
            yield "There was an error contacting the language model service."
