"""
File parsing utilities.

The ingestion service uses these helpers to turn uploaded files into plain
text.  At the moment only simple text and markdown files are supported.  PDF
parsing could be added using `pypdf` or similar libraries.
"""
from __future__ import annotations

import io
from typing import Optional

from fastapi import UploadFile


def parse_upload_file(file: UploadFile) -> str:
    """Parse an uploaded file into plain text.

    Currently supports text/plain and text/markdown.  Other content types will
    be read as bytes and decoded as UTF‑8 if possible.

    :param file: UploadFile object from FastAPI
    :return: The extracted text
    """
    content_type = file.content_type
    data = file.file.read()

    # Basic handling based on content type
    if content_type in ("text/plain", "text/markdown", "application/json"):
        return data.decode("utf-8", errors="ignore")

    # Attempt naive UTF‑8 decode for unknown text types
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        # Fallback: return empty string for unsupported types
        return ""