"""
Chat API endpoints.

Provides an endpoint to ask questions against the knowledge base.  It
creates or reuses a conversation, logs user and assistant messages, and
returns an answer with citations.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..dependencies import get_db_session
from ..domain import schemas
from ..repositories.conversation_repository import ConversationRepository
from ..services.retrieval_service import RetrievalService
from ..services.llm_gateway import LLMGateway
from ..services.llm_settings import llm_settings_store
from ..services.prompt_service import build_prompt
from ..utils.embeddings import DEFAULT_EMBEDDING_MODEL


router = APIRouter()


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
    retrieval_latency_ms: float | None = None,
) -> schemas.RetrievalDiagnostics:
    signals = {chunk.retrieval_signal for chunk in retrieved_chunks if chunk.retrieval_signal}
    mode = "hybrid" if "hybrid" in signals else next(iter(signals), "none")
    runtime_settings = llm_settings_store.get()
    return schemas.RetrievalDiagnostics(
        mode=mode,
        project_id=str(project_id) if project_id else None,
        document_filename=payload.document_filename,
        content_type=payload.content_type,
        top_k=payload.top_k,
        retrieval_latency_ms=retrieval_latency_ms,
        llm_provider=runtime_settings.provider,
        llm_model=runtime_settings.model,
        embedding_model=DEFAULT_EMBEDDING_MODEL,
    )


def applied_filters(payload: schemas.ChatQuery, project_id: uuid.UUID | None) -> dict[str, str]:
    filters: dict[str, str] = {}
    if project_id:
        filters["project_id"] = str(project_id)
    if payload.document_filename:
        filters["document_filename"] = payload.document_filename
    if payload.content_type:
        filters["content_type"] = payload.content_type
    return filters


def persist_retrieval_diagnostics(
    conv_repo: ConversationRepository,
    assistant_message_id: uuid.UUID,
    payload: schemas.ChatQuery,
    project_id: uuid.UUID | None,
    retrieved_chunks: List[schemas.RetrievedChunk],
    diagnostics: schemas.RetrievalDiagnostics,
) -> None:
    filters = applied_filters(payload, project_id)
    entries = [
        {
            "chunk_id": uuid.UUID(chunk.chunk_id),
            "similarity_score": chunk.score,
            "retrieval_signal": chunk.retrieval_signal,
            "rank": rank,
            "retrieval_latency_ms": diagnostics.retrieval_latency_ms,
            "applied_filters": filters,
            "retrieval_mode": diagnostics.mode,
            "embedding_model": diagnostics.embedding_model,
            "llm_provider": diagnostics.llm_provider,
            "llm_model": diagnostics.llm_model,
        }
        for rank, chunk in enumerate(retrieved_chunks, start=1)
    ]
    if entries:
        conv_repo.add_retrieval_logs(assistant_message_id, entries)


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
    retrieval_started = time.perf_counter()
    retrieved_chunks = await retrieve_chunks(
        payload.question,
        payload.top_k,
        db,
        project_uuid,
        payload.document_filename,
        payload.content_type,
    )
    retrieval_latency_ms = (time.perf_counter() - retrieval_started) * 1000
    diagnostics = retrieval_diagnostics(payload, project_uuid, retrieved_chunks, retrieval_latency_ms)

    # Build prompt using template
    prompt = build_prompt(payload.question, retrieved_chunks)

    # Invoke LLM
    llm = LLMGateway()
    answer_text = await llm.ask(prompt)

    # Persist assistant message
    assistant_message = conv_repo.add_message(conversation.id, role="assistant", content=answer_text)
    persist_retrieval_diagnostics(
        conv_repo,
        assistant_message.id,
        payload,
        project_uuid,
        retrieved_chunks,
        diagnostics,
    )

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

    retrieval_started = time.perf_counter()
    retrieved_chunks = await retrieve_chunks(
        payload.question,
        payload.top_k,
        db,
        project_uuid,
        payload.document_filename,
        payload.content_type,
    )
    retrieval_latency_ms = (time.perf_counter() - retrieval_started) * 1000
    diagnostics = retrieval_diagnostics(payload, project_uuid, retrieved_chunks, retrieval_latency_ms)
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
        assistant_message = conv_repo.add_message(conversation.id, role="assistant", content=answer_text)
        persist_retrieval_diagnostics(
            conv_repo,
            assistant_message.id,
            payload,
            project_uuid,
            retrieved_chunks,
            diagnostics,
        )
        yield sse_event(
            "done",
            {
                "conversation_id": str(conversation.id),
                "answer": answer_text,
                "retrieval": diagnostics.model_dump(mode="json"),
            },
        )

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/messages/{message_id}/diagnostics", response_model=schemas.MessageDiagnosticsResponse)
def get_message_diagnostics(message_id: str, db=Depends(get_db_session)) -> schemas.MessageDiagnosticsResponse:
    """Return persisted retrieval diagnostics for an assistant answer."""
    conv_repo = ConversationRepository(db)
    try:
        message_uuid = uuid.UUID(message_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message_id")

    answer = conv_repo.get_message(message_uuid)
    if answer is None:
        raise HTTPException(status_code=404, detail="Message not found")
    if answer.role != "assistant":
        raise HTTPException(status_code=400, detail="Diagnostics are only available for assistant messages")

    logs = conv_repo.list_retrieval_logs(answer.id)
    first_log = logs[0] if logs else None
    question = conv_repo.get_previous_user_message(answer)
    return schemas.MessageDiagnosticsResponse(
        question=question,
        answer=answer,
        selected_chunks=[
            schemas.RetrievalDiagnosticsChunk(
                chunk_id=log.chunk.id,
                document_id=log.chunk.document_id,
                document_filename=log.chunk.document.filename,
                document_project_name=log.chunk.document.project_name,
                document_content_type=log.chunk.document.content_type,
                chunk_index=log.chunk.chunk_index,
                content=log.chunk.content,
                score=log.similarity_score,
                retrieval_signal=log.retrieval_signal,
                rank=log.rank,
            )
            for log in logs
        ],
        filters=first_log.applied_filters if first_log and first_log.applied_filters else {},
        retrieval_mode=first_log.retrieval_mode if first_log else None,
        retrieval_latency_ms=first_log.retrieval_latency_ms if first_log else None,
        embedding_model=first_log.embedding_model if first_log else None,
        llm_provider=first_log.llm_provider if first_log else None,
        llm_model=first_log.llm_model if first_log else None,
    )


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
