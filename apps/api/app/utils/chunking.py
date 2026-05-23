"""
Text chunking utilities.

The `split_text` function splits a long string into smaller overlapping
chunks.  The chunk size and overlap are configurable.  Overlap helps
retain context between adjacent chunks.
"""
from typing import List


def split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks of roughly `chunk_size` characters.

    :param text: Raw text to split
    :param chunk_size: Number of characters per chunk
    :param overlap: Number of characters to overlap between chunks
    :return: List of text chunks
    """
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")
    chunks: List[str] = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == text_length:
            break
        start = end - overlap
        if start < 0:
            start = 0
    return chunks
