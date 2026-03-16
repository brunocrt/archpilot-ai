"""
Document management API.

Endpoints for uploading documents, listing documents, and retrieving a document
with its chunks.  Uploads are processed asynchronously by the ingestion
service (although in this MVP it runs synchronously).
"""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..dependencies import get_db_session
from ..repositories.document_repository import DocumentRepository
from ..services.ingestion_service import IngestionService
from ..domain import schemas


router = APIRouter()


@router.post("/upload", response_model=schemas.DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db=Depends(get_db_session),
) -> schemas.DocumentUploadResponse:
    """Upload a file and ingest it into the knowledge base."""
    repo = DocumentRepository(db)
    service = IngestionService(repo)
    doc_id = await service.ingest_upload(file)
    return schemas.DocumentUploadResponse(document_id=doc_id, filename=file.filename, status="processed")


@router.get("/", response_model=List[schemas.DocumentBase])
def list_documents(db=Depends(get_db_session)) -> List[schemas.DocumentBase]:
    """Return all documents sorted by most recent first."""
    repo = DocumentRepository(db)
    return repo.list_documents()


@router.get("/{document_id}", response_model=schemas.DocumentWithChunks)
def get_document(document_id: str, db=Depends(get_db_session)) -> schemas.DocumentWithChunks:
    """Get a single document with its chunks."""
    repo = DocumentRepository(db)
    doc = repo.get_document(uuid.UUID(document_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    chunks = repo.list_chunks_by_document(doc.id)
    return schemas.DocumentWithChunks(
        id=str(doc.id),
        filename=doc.filename,
        content_type=doc.content_type,
        status=doc.status,
        uploaded_at=doc.uploaded_at,
        chunks=[
            schemas.DocumentChunkBase(
                id=str(chunk.id),
                document_id=str(chunk.document_id),
                chunk_index=chunk.chunk_index,
                content=chunk.content,
            )
            for chunk in chunks
        ],
    )