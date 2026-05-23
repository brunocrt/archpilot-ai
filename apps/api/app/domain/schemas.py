"""
Pydantic schemas for the API.

Defines request and response models for each entity.  Response models use
`orm_mode=True` to allow conversion from SQLAlchemy objects.
"""
from datetime import datetime
from typing import List, Optional
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
    question: str = Field(..., description="The user's question")
    top_k: int = Field(5, description="Number of top chunks to retrieve")


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_filename: str
    chunk_index: int
    score: Optional[float] = None
    content: str


class AnswerResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: List[RetrievedChunk]
    retrieved_chunks: List[RetrievedChunk]


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
