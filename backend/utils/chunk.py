from typing import List


def chunk_text(text: str, chunk_size: int = 180, overlap: int = 30) -> List[str]:
    """Split text into overlapping word-based chunks for embedding/retrieval."""
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        if end >= len(words):
            break
        start = end - overlap
    return chunks
