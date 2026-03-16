"""
Repository layer for document and document chunk persistence.

This module encapsulates database operations related to Document and
DocumentChunk entities.  It provides methods for creating documents,
adding chunks, retrieving documents and listing all documents.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..domain import models


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_document(self, filename: str, content_type: Optional[str] = None) -> models.Document:
        document = models.Document(filename=filename, content_type=content_type, status="processing")
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def update_document_status(self, document_id: UUID, status: str) -> None:
        document = self.db.query(models.Document).get(document_id)
        if document:
            document.status = status
            self.db.commit()

    def add_chunk(self, document_id: UUID, chunk_index: int, content: str, embedding: Optional[list] = None, metadata: Optional[dict] = None) -> models.DocumentChunk:
        chunk = models.DocumentChunk(
            document_id=document_id,
            chunk_index=chunk_index,
            content=content,
            embedding=embedding,
            metadata=metadata,
        )
        self.db.add(chunk)
        self.db.commit()
        self.db.refresh(chunk)
        return chunk

    def list_documents(self) -> List[models.Document]:
        return self.db.query(models.Document).order_by(models.Document.uploaded_at.desc()).all()

    def get_document(self, document_id: UUID) -> Optional[models.Document]:
        return self.db.query(models.Document).filter(models.Document.id == document_id).first()

    def list_chunks_by_document(self, document_id: UUID) -> List[models.DocumentChunk]:
        return (
            self.db.query(models.DocumentChunk)
            .filter(models.DocumentChunk.document_id == document_id)
            .order_by(models.DocumentChunk.chunk_index)
            .all()
        )