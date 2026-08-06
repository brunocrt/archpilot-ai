"""Prompt construction helpers shared by chat and evaluation flows."""
from pathlib import Path
from typing import List

from ..domain import schemas


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "answer_with_citations.txt"


def build_prompt(question: str, context_chunks: List[schemas.RetrievedChunk]) -> str:
    """Fill the answer prompt template with the user's question and retrieved context."""
    try:
        template = PROMPT_PATH.read_text()
    except FileNotFoundError:
        template = (
            "Answer the user's question using only the provided context.\n"
            "If the context is insufficient, say that you don't know.\n\n"
            "Question: {question}\n"
            "Context:\n{context}"
        )
    context = "\n\n".join(
        f"[{chunk.chunk_id}] {chunk.content}" for chunk in context_chunks
    )
    return template.format(question=question, context=context)
