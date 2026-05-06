from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TextChunk:
    start: int
    end: int
    text: str


def sentence_chunks(text: str) -> list[TextChunk]:
    """Split text into lightweight sentence-like chunks with char spans."""
    if not text:
        return []

    chunks: list[TextChunk] = []
    start = 0
    for idx, char in enumerate(text):
        if char in ".!?\n":
            end = idx + 1
            if end > start:
                snippet = text[start:end]
                if snippet.strip():
                    chunks.append(TextChunk(start=start, end=end, text=snippet))
            start = end

    if start < len(text):
        snippet = text[start:]
        if snippet.strip():
            chunks.append(TextChunk(start=start, end=len(text), text=snippet))
    return chunks
