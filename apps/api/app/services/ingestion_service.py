"""
Ingestion service for processing uploaded documents.

This service parses uploaded files into plain text, splits the text into
manageable chunks, generates embeddings for each chunk, and persists
documents and chunks to the database.
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

import anyio
from fastapi import UploadFile

from ..repositories.document_repository import DocumentRepository
from ..utils.parsing import parse_upload_file
from ..utils.chunking import split_text
from ..utils.embeddings import get_embedding

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, document_repo: DocumentRepository) -> None:
        self.document_repo = document_repo

    async def ingest_upload(self, file: UploadFile, project_id: Optional[UUID] = None) -> str:
        """Process an uploaded file and persist it to the database.

        :param file: FastAPI UploadFile
        :return: ID of the created document
        """
        # Create document entry
        document = self.document_repo.create_document(
            filename=file.filename,
            content_type=file.content_type,
            project_id=project_id,
        )
        doc_id = document.id

        # Parse file
        try:
            text = parse_upload_file(file)
        finally:
            # Ensure file handle is closed
            await file.close()

        chunks = split_text(text, chunk_size=512, overlap=50)

        async def process_chunk(chunk_index: int, chunk_text: str) -> None:
            embedding = await get_embedding(chunk_text)  # returns None if not available
            self.document_repo.add_chunk(document_id=doc_id, chunk_index=chunk_index, content=chunk_text, embedding=embedding)

        # Process chunks sequentially (could be parallelised later)
        for idx, chunk_text in enumerate(chunks):
            await process_chunk(idx, chunk_text)

        # Update document status
        self.document_repo.update_document_status(doc_id, status="processed")

        logger.info("Ingested document %s with %d chunks", doc_id, len(chunks))
        return str(doc_id)
