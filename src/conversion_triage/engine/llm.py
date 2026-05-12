from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from conversion_triage.engine.chunking import TextChunk
from conversion_triage.engine.schemas import Flag, SourceType


class LLMAdapter(Protocol):
    """Optional legacy adapter contract for one-shot model-assisted triage."""

    def triage(self, *, text: str, source_type: SourceType, context: str | None) -> Sequence[Flag]:
        """Return additional flags inferred from model reasoning."""


@dataclass(slots=True)
class LLMContextMap:
    """Document-level context summary used by downstream chunk checks."""

    summary: str
    entities: list[str] = field(default_factory=list)
    timeline: list[str] = field(default_factory=list)
    domain_cues: list[str] = field(default_factory=list)


class MultiPassLLMAdapter(Protocol):
    """Adapter contract for multi-pass document-aware LLM triage."""

    def summarize_document(
        self,
        *,
        text: str,
        source_type: SourceType,
        context: str | None,
        chunks: Sequence[TextChunk],
    ) -> LLMContextMap:
        """Create document context used by sentence/chunk checks."""

    def triage_chunk(
        self,
        *,
        chunk: TextChunk,
        chunk_index: int,
        total_chunks: int,
        source_type: SourceType,
        context: str | None,
        context_map: LLMContextMap,
    ) -> Sequence[Flag]:
        """Flag issues inside one chunk using full-document context."""

    def triage_cross_chunk(
        self,
        *,
        text: str,
        chunks: Sequence[TextChunk],
        source_type: SourceType,
        context: str | None,
        context_map: LLMContextMap,
    ) -> Sequence[Flag]:
        """Flag contradictions or inconsistencies across chunks."""


class NullLLMAdapter:
    """Default no-op adapter to keep engine deterministic by default."""

    def triage(self, *, text: str, source_type: SourceType, context: str | None) -> Sequence[Flag]:
        _ = (text, source_type, context)
        return []

    def summarize_document(
        self,
        *,
        text: str,
        source_type: SourceType,
        context: str | None,
        chunks: Sequence[TextChunk],
    ) -> LLMContextMap:
        _ = (text, source_type, chunks)
        summary = context or ""
        return LLMContextMap(summary=summary)

    def triage_chunk(
        self,
        *,
        chunk: TextChunk,
        chunk_index: int,
        total_chunks: int,
        source_type: SourceType,
        context: str | None,
        context_map: LLMContextMap,
    ) -> Sequence[Flag]:
        _ = (chunk, chunk_index, total_chunks, source_type, context, context_map)
        return []

    def triage_cross_chunk(
        self,
        *,
        text: str,
        chunks: Sequence[TextChunk],
        source_type: SourceType,
        context: str | None,
        context_map: LLMContextMap,
    ) -> Sequence[Flag]:
        _ = (text, chunks, source_type, context, context_map)
        return []


LLMAdapterLike = LLMAdapter | MultiPassLLMAdapter
