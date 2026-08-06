"""
Pydantic schemas for the API.

Defines request and response models for each entity.  Response models use
`orm_mode=True` to allow conversion from SQLAlchemy objects.
"""
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentChunkBase(BaseModel):
    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    # Note: embedding and metadata fields are omitted from API responses by default

    model_config = ConfigDict(from_attributes=True)


class DocumentBase(BaseModel):
    id: UUID
    project_id: Optional[UUID] = None
    project_name: Optional[str] = None
    filename: str
    content_type: Optional[str] = None
    status: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentWithChunks(DocumentBase):
    chunks: List[DocumentChunkBase] = Field(default_factory=list)


class DocumentUploadResponse(BaseModel):
    document_id: str
    project_id: Optional[str] = None
    filename: str
    status: str


class ProjectBase(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None


class ChatQuery(BaseModel):
    conversation_id: Optional[str] = Field(None, description="ID of an existing conversation to continue")
    project_id: Optional[str] = Field(None, description="Optional project scope for retrieval")
    document_filename: Optional[str] = Field(None, description="Optional filename contains filter")
    content_type: Optional[str] = Field(None, description="Optional document content type filter")
    question: str = Field(..., description="The user's question")
    top_k: int = Field(5, description="Number of top chunks to retrieve")


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_filename: str
    document_project_name: Optional[str] = None
    document_content_type: Optional[str] = None
    chunk_index: int
    score: Optional[float] = None
    retrieval_signal: Optional[str] = None
    content: str


class RetrievalDiagnostics(BaseModel):
    mode: str
    project_id: Optional[str] = None
    document_filename: Optional[str] = None
    content_type: Optional[str] = None
    top_k: int
    retrieval_latency_ms: Optional[float] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None


class AnswerResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: List[RetrievedChunk]
    retrieved_chunks: List[RetrievedChunk]
    retrieval: Optional[RetrievalDiagnostics] = None


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationSummary(BaseModel):
    id: UUID
    title: Optional[str] = None
    created_at: datetime
    message_count: int
    last_message_at: Optional[datetime] = None


class ConversationDetail(BaseModel):
    id: UUID
    title: Optional[str] = None
    created_at: datetime
    messages: List[MessageResponse]


class RetrievalDiagnosticsChunk(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_filename: str
    document_project_name: Optional[str] = None
    document_content_type: Optional[str] = None
    chunk_index: int
    content: str
    score: Optional[float] = None
    retrieval_signal: Optional[str] = None
    rank: Optional[int] = None


class MessageDiagnosticsResponse(BaseModel):
    question: Optional[MessageResponse] = None
    answer: MessageResponse
    selected_chunks: List[RetrievalDiagnosticsChunk]
    filters: dict[str, Any] = Field(default_factory=dict)
    retrieval_mode: Optional[str] = None
    retrieval_latency_ms: Optional[float] = None
    embedding_model: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None


class LLMSettingsResponse(BaseModel):
    provider: str
    model: str
    has_api_key: bool


class LLMSettingsUpdate(BaseModel):
    provider: str = Field(..., description="LLM provider: none or openai")
    model: str = Field("gpt-3.5-turbo", description="Provider model name")
    api_key: Optional[str] = Field(None, description="Provider API key")


class FeedbackCreate(BaseModel):
    message_id: str
    rating: str  # 'up' or 'down'
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: UUID
    message_id: UUID
    rating: str
    comment: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationDatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    description: Optional[str] = None


class EvaluationDatasetResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    case_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class EvaluationCaseCreate(BaseModel):
    question: str = Field(..., min_length=1)
    expected_answer: Optional[str] = None
    expected_facts: List[str] = Field(default_factory=list)
    expected_chunk_ids: List[str] = Field(default_factory=list)


class EvaluationCaseResponse(BaseModel):
    id: UUID
    dataset_id: UUID
    question: str
    expected_answer: Optional[str] = None
    expected_facts: List[str] = Field(default_factory=list)
    expected_chunk_ids: List[str] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationRunCreate(BaseModel):
    dataset_id: str
    top_k: int = Field(5, ge=1, le=20)


class EvaluationResultResponse(BaseModel):
    id: UUID
    case_id: UUID
    question: str
    generated_answer: str
    retrieved_chunks: List[dict[str, Any]] = Field(default_factory=list)
    retrieval_metrics: dict[str, Any] = Field(default_factory=dict)
    answer_metrics: dict[str, Any] = Field(default_factory=dict)
    provider: Optional[str] = None
    model: Optional[str] = None
    status: str
    created_at: datetime


class EvaluationRunSummary(BaseModel):
    id: UUID
    dataset_id: UUID
    dataset_name: str
    status: str
    provider: Optional[str] = None
    model: Optional[str] = None
    aggregate_metrics: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    completed_at: Optional[datetime] = None
    result_count: int = 0


class EvaluationRunDetail(EvaluationRunSummary):
    results: List[EvaluationResultResponse]
