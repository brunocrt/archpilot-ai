"""File parsing utilities."""
from __future__ import annotations

import io

from fastapi import UploadFile
from pypdf import PdfReader


def parse_upload_file(file: UploadFile) -> str:
    """Parse an uploaded text, markdown, JSON, or PDF file into plain text."""
    return parse_file_bytes(
        file.file.read(),
        filename=file.filename,
        content_type=file.content_type,
    )


def parse_file_bytes(data: bytes, filename: str | None, content_type: str | None) -> str:
    """Parse text, markdown, JSON, or PDF bytes into plain text."""

    if content_type in ("text/plain", "text/markdown", "application/json"):
        return data.decode("utf-8", errors="ignore")

    if content_type == "application/pdf" or (filename or "").lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return ""
