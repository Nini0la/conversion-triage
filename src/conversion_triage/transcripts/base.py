from __future__ import annotations

from typing import Protocol


class TranscriptProviderError(Exception):
    """Raised when transcript retrieval fails."""


class TranscriptProvider(Protocol):
    """Contract for URL-based transcript retrieval."""

    def fetch_text(self, *, url: str) -> str:
        """Return transcript text for a source URL."""
