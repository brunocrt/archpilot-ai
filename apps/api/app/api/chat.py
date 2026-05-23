"""
Chat API endpoints.

Provides an endpoint to ask questions against the knowledge base.  It
creates or reuses a conversation, logs user and assistant messages, and
returns an answer with citations.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_db_session
from ..domain import schemas
from ..repositories.conversation_repository import ConversationRepository
from ..services.retrieval_service import RetrievalService
from ..services.llm_gateway import LLMGateway


router = APIRouter()


PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "answer_with_citations.txt"


def build_prompt(question: str, context_chunks: List[schemas.RetrievedChunk]) -> str:
    """Fill the prompt template with the user's question and retrieved context."""
    try:
        template = PROMPT_PATH.read_text()
    except FileNotFoundError:
        # fallback template
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


@router.post("/query", response_model=schemas.AnswerResponse)
async def query_chat(payload: schemas.ChatQuery, db=Depends(get_db_session)) -> schemas.AnswerResponse:
    """Ask a question and get an answer with citations."""
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    conv_repo = ConversationRepository(db)

    # Create or load conversation
    if payload.conversation_id:
        try:
            conv_uuid = uuid.UUID(payload.conversation_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid conversation_id")
        conversation = conv_repo.get_conversation(conv_uuid)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = conv_repo.create_conversation()

    # Persist user message
    user_msg = conv_repo.add_message(conversation.id, role="user", content=payload.question)

    # Retrieve relevant chunks
    retriever = RetrievalService(db)
    retrieved = await retriever.retrieve(payload.question, top_k=payload.top_k)
    retrieved_chunks: List[schemas.RetrievedChunk] = []
    for chunk, score in retrieved:
        retrieved_chunks.append(
            schemas.RetrievedChunk(
                chunk_id=str(chunk.id),
                document_id=str(chunk.document_id),
                document_filename=chunk.document.filename,
                chunk_index=chunk.chunk_index,
                score=score,
                content=chunk.content,
            )
        )

    # Build prompt using template
    prompt = build_prompt(payload.question, retrieved_chunks)

    # Invoke LLM
    llm = LLMGateway()
    answer_text = await llm.ask(prompt)

    # Persist assistant message
    conv_repo.add_message(conversation.id, role="assistant", content=answer_text)

    # Build response
    return schemas.AnswerResponse(
        conversation_id=str(conversation.id),
        answer=answer_text,
        sources=retrieved_chunks,
        retrieved_chunks=retrieved_chunks,
    )
