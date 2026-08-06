"""
SQLAlchemy models representing the core database entities.

These definitions use a UUID primary key for all tables.  The Document and
DocumentChunk tables capture uploaded files and their embedded chunks.  The
Conversation and Message tables record chat history, retrieval logs capture
metadata about which chunks were used to answer a question, and the Feedback
table stores user feedback on answers.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector


Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)
    filename = Column(String, nullable=False, index=True)
    content_type = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="processed")
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    project = relationship("Project", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    @property
    def project_name(self) -> str | None:
        return self.project.name if self.project else None


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    documents = relationship("Document", back_populates="project")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)
    chunk_metadata = Column("metadata", JSONB, nullable=True)

    document = relationship("Document", back_populates="chunks")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
    retrieval_logs = relationship("RetrievalLog", back_populates="message", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="message", cascade="all, delete-orphan", uselist=False)


class RetrievalLog(Base):
    __tablename__ = "retrieval_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False, index=True)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("document_chunks.id"), nullable=False, index=True)
    similarity_score = Column(Float, nullable=True)
    retrieval_signal = Column(String, nullable=True)
    rank = Column(Integer, nullable=True)
    retrieval_latency_ms = Column(Float, nullable=True)
    applied_filters = Column(JSONB, nullable=True)
    retrieval_mode = Column(String, nullable=True)
    embedding_model = Column(String, nullable=True)
    llm_provider = Column(String, nullable=True)
    llm_model = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    message = relationship("Message", back_populates="retrieval_logs")
    chunk = relationship("DocumentChunk")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), unique=True, nullable=False)
    rating = Column(String, nullable=False)  # e.g. 'up' or 'down'
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    message = relationship("Message", back_populates="feedback")


class EvaluationDataset(Base):
    __tablename__ = "evaluation_datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    cases = relationship("EvaluationCase", back_populates="dataset", cascade="all, delete-orphan")
    runs = relationship("EvaluationRun", back_populates="dataset", cascade="all, delete-orphan")


class EvaluationCase(Base):
    __tablename__ = "evaluation_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_datasets.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=True)
    expected_facts = Column(JSONB, nullable=True)
    expected_chunk_ids = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    dataset = relationship("EvaluationDataset", back_populates="cases")
    results = relationship("EvaluationResult", back_populates="case", cascade="all, delete-orphan")


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_datasets.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="completed")
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    aggregate_metrics = Column(JSONB, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    dataset = relationship("EvaluationDataset", back_populates="runs")
    results = relationship("EvaluationResult", back_populates="run", cascade="all, delete-orphan")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_runs.id"), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_cases.id"), nullable=False, index=True)
    generated_answer = Column(Text, nullable=False)
    retrieved_chunks = Column(JSONB, nullable=True)
    retrieval_metrics = Column(JSONB, nullable=True)
    answer_metrics = Column(JSONB, nullable=True)
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    run = relationship("EvaluationRun", back_populates="results")
    case = relationship("EvaluationCase", back_populates="results")
