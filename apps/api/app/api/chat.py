"""
Chat API endpoints.

Provides an endpoint to ask questions against the knowledge base.  It
creates or reuses a conversation, logs user and assistant messages, and
returns an answer with citations.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..dependencies import get_db_session
from ..domain import schemas
from ..repositories.conversation_repository import ConversationRepository
from ..services.retrieval_service import RetrievalService
from ..services.llm_gateway import LLMGateway


router = APIRouter()


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "answer_with_citations.txt"


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


def conversation_title(question: str) -> str:
    """Create a compact title from the first user question."""
    title = " ".join(question.strip().split())
    return title[:80]


def get_or_create_conversation(
    payload: schemas.ChatQuery,
    conv_repo: ConversationRepository,
):
    if payload.conversation_id:
        try:
            conv_uuid = uuid.UUID(payload.conversation_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid conversation_id")
        conversation = conv_repo.get_conversation(conv_uuid)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation
    return conv_repo.create_conversation(title=conversation_title(payload.question))


def parse_project_id(project_id: str | None) -> uuid.UUID | None:
    if not project_id:
        return None
    try:
        return uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id")


async def retrieve_chunks(
    question: str,
    top_k: int,
    db,
    project_id: uuid.UUID | None,
    document_filename: str | None = None,
    content_type: str | None = None,
) -> List[schemas.RetrievedChunk]:
    retriever = RetrievalService(db)
    retrieved = await retriever.retrieve(
        question,
        top_k=top_k,
        project_id=project_id,
        document_filename=document_filename,
        content_type=content_type,
    )
    return [
        schemas.RetrievedChunk(
            chunk_id=str(match.chunk.id),
            document_id=str(match.chunk.document_id),
            document_filename=match.chunk.document.filename,
            document_project_name=match.chunk.document.project_name,
            document_content_type=match.chunk.document.content_type,
            chunk_index=match.chunk.chunk_index,
            score=match.score,
            retrieval_signal=match.signal,
            content=match.chunk.content,
        )
        for match in retrieved
    ]


def retrieval_diagnostics(
    payload: schemas.ChatQuery,
    project_id: uuid.UUID | None,
    retrieved_chunks: List[schemas.RetrievedChunk],
) -> schemas.RetrievalDiagnostics:
    signals = {chunk.retrieval_signal for chunk in retrieved_chunks if chunk.retrieval_signal}
    mode = "hybrid" if "hybrid" in signals else next(iter(signals), "none")
    return schemas.RetrievalDiagnostics(
        mode=mode,
        project_id=str(project_id) if project_id else None,
        document_filename=payload.document_filename,
        content_type=payload.content_type,
        top_k=payload.top_k,
    )


def sse_event(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/query", response_model=schemas.AnswerResponse)
async def query_chat(payload: schemas.ChatQuery, db=Depends(get_db_session)) -> schemas.AnswerResponse:
    """Ask a question and get an answer with citations."""
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    conv_repo = ConversationRepository(db)
    conversation = get_or_create_conversation(payload, conv_repo)
    project_uuid = parse_project_id(payload.project_id)

    # Persist user message
    conv_repo.add_message(conversation.id, role="user", content=payload.question)

    # Retrieve relevant chunks
    retrieved_chunks = await retrieve_chunks(
        payload.question,
        payload.top_k,
        db,
        project_uuid,
        payload.document_filename,
        payload.content_type,
    )
    diagnostics = retrieval_diagnostics(payload, project_uuid, retrieved_chunks)

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
        retrieval=diagnostics,
    )


@router.post("/query/stream")
async def stream_chat(payload: schemas.ChatQuery, db=Depends(get_db_session)) -> StreamingResponse:
    """Ask a question and stream answer deltas as server-sent events."""
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    conv_repo = ConversationRepository(db)
    conversation = get_or_create_conversation(payload, conv_repo)
    project_uuid = parse_project_id(payload.project_id)
    conv_repo.add_message(conversation.id, role="user", content=payload.question)

    retrieved_chunks = await retrieve_chunks(
        payload.question,
        payload.top_k,
        db,
        project_uuid,
        payload.document_filename,
        payload.content_type,
    )
    diagnostics = retrieval_diagnostics(payload, project_uuid, retrieved_chunks)
    prompt = build_prompt(payload.question, retrieved_chunks)

    async def events():
        yield sse_event("conversation", {"conversation_id": str(conversation.id)})
        yield sse_event(
            "sources",
            [chunk.model_dump(mode="json") for chunk in retrieved_chunks],
        )
        yield sse_event("retrieval", diagnostics.model_dump(mode="json"))

        llm = LLMGateway()
        answer_parts: list[str] = []
        async for delta in llm.ask_stream(prompt):
            answer_parts.append(delta)
            yield sse_event("delta", {"text": delta})

        answer_text = "".join(answer_parts)
        conv_repo.add_message(conversation.id, role="assistant", content=answer_text)
        yield sse_event(
            "done",
            {
                "conversation_id": str(conversation.id),
                "answer": answer_text,
                "retrieval": diagnostics.model_dump(mode="json"),
            },
        )

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/conversations", response_model=List[schemas.ConversationSummary])
def list_conversations(db=Depends(get_db_session)) -> List[schemas.ConversationSummary]:
    """List persisted conversations for the history UI."""
    conv_repo = ConversationRepository(db)
    summaries: list[schemas.ConversationSummary] = []
    for conversation in conv_repo.list_conversations():
        messages = conv_repo.list_messages(conversation.id)
        summaries.append(
            schemas.ConversationSummary(
                id=conversation.id,
                title=conversation.title,
                created_at=conversation.created_at,
                message_count=len(messages),
                last_message_at=messages[-1].created_at if messages else None,
            )
        )
    return summaries


@router.get("/conversations/{conversation_id}", response_model=schemas.ConversationDetail)
def get_conversation(conversation_id: str, db=Depends(get_db_session)) -> schemas.ConversationDetail:
    """Return a conversation and its persisted messages."""
    conv_repo = ConversationRepository(db)
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation_id")
    conversation = conv_repo.get_conversation(conv_uuid)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return schemas.ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        messages=conv_repo.list_messages(conversation.id),
    )
