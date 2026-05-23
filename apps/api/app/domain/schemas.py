"""
Pydantic schemas for the API.

Defines request and response models for each entity.  Response models use
`orm_mode=True` to allow conversion from SQLAlchemy objects.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentChunkBase(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    content: str
    # Note: embedding and metadata fields are omitted from API responses by default

    class Config:
        orm_mode = True


class DocumentBase(BaseModel):
    id: str
    filename: str
    content_type: Optional[str] = None
    status: str
    uploaded_at: datetime

    class Config:
        orm_mode = True


class DocumentWithChunks(DocumentBase):
    chunks: List[DocumentChunkBase] = []


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str


class ChatQuery(BaseModel):
    conversation_id: Optional[str] = Field(None, description="ID of an existing conversation to continue")
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


class FeedbackCreate(BaseModel):
    message_id: str
    rating: str  # 'up' or 'down'
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    message_id: str
    rating: str
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True
