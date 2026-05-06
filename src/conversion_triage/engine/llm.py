from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from conversion_triage.engine.schemas import Flag, SourceType


class LLMAdapter(Protocol):
    """Optional adapter contract for model-assisted triage enrichment."""

    def triage(self, *, text: str, source_type: SourceType, context: str | None) -> Sequence[Flag]:
        """Return additional flags inferred from model reasoning."""


class NullLLMAdapter:
    """Default no-op adapter to keep engine deterministic by default."""

    def triage(self, *, text: str, source_type: SourceType, context: str | None) -> Sequence[Flag]:
        _ = (text, source_type, context)
        return []
