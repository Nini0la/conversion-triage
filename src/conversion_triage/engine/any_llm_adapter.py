from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from conversion_triage.engine.chunking import TextChunk
from conversion_triage.engine.llm import LLMContextMap
from conversion_triage.engine.schemas import Flag, FlagCategory, Severity, SourceType

try:
    from any_llm import completion as any_llm_completion
except ImportError:  # pragma: no cover - handled at runtime in adapter init
    any_llm_completion = None


@dataclass(slots=True)
class AnyLLMSettings:
    provider: str
    model: str
    temperature: float = 0.0
    reasoning_effort: str | None = "auto"
    max_tokens_summary: int = 500
    max_tokens_chunk: int = 500
    max_tokens_cross: int = 600
    client_args: dict[str, Any] | None = None


class _SummaryPayload(BaseModel):
    summary: str = ""
    entities: list[str] = Field(default_factory=list)
    timeline: list[str] = Field(default_factory=list)
    domain_cues: list[str] = Field(default_factory=list)


class _IssuePayload(BaseModel):
    span_text: str = Field(min_length=1)
    severity: Severity
    category: FlagCategory
    reason: str
    suggestion: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class _IssueListPayload(BaseModel):
    issues: list[_IssuePayload] = Field(default_factory=list)


class AnyLLMMultiPassAdapter:
    """Multi-pass LLM adapter backed by Mozilla's any-llm router."""

    def __init__(self, settings: AnyLLMSettings) -> None:
        if any_llm_completion is None:
            raise RuntimeError(
                "any-llm-sdk is not installed. Install dependencies and retry."
            )
        self.settings = settings

    def summarize_document(
        self,
        *,
        text: str,
        source_type: SourceType,
        context: str | None,
        chunks: list[TextChunk],
    ) -> LLMContextMap:
        messages = [
            {
                "role": "system",
                "content": (
                    "You analyze converted transcripts. Produce concise context mapping for "
                    "downstream consistency checks."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Source type: {source_type.value}\n"
                    f"External context: {context or 'none'}\n"
                    f"Chunk count: {len(chunks)}\n"
                    "Summarize the document and extract entities, timeline points, "
                    "and domain cues.\n\n"
                    f"Text:\n{text}"
                ),
            },
        ]

        payload = self._call_structured(
            messages=messages,
            response_model=_SummaryPayload,
            max_tokens=self.settings.max_tokens_summary,
        )
        return LLMContextMap(
            summary=payload.summary,
            entities=payload.entities,
            timeline=payload.timeline,
            domain_cues=payload.domain_cues,
        )

    def triage_chunk(
        self,
        *,
        chunk: TextChunk,
        chunk_index: int,
        total_chunks: int,
        source_type: SourceType,
        context: str | None,
        context_map: LLMContextMap,
    ) -> list[Flag]:
        messages = [
            {
                "role": "system",
                "content": (
                    "Find likely OCR/ASR conversion mistakes in one chunk. "
                    "Only emit issues where confidence is justified."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Source type: {source_type.value}\n"
                    f"External context: {context or 'none'}\n"
                    f"Document summary: {context_map.summary}\n"
                    f"Known entities: {', '.join(context_map.entities) or 'none'}\n"
                    f"Timeline cues: {', '.join(context_map.timeline) or 'none'}\n"
                    f"Chunk {chunk_index + 1}/{total_chunks}:\n{chunk.text}\n\n"
                    "Return only issues in this chunk. Use exact span_text from the chunk."
                ),
            },
        ]
        payload = self._call_structured(
            messages=messages,
            response_model=_IssueListPayload,
            max_tokens=self.settings.max_tokens_chunk,
        )
        return self._map_chunk_issues(chunk=chunk, issues=payload.issues)

    def triage_cross_chunk(
        self,
        *,
        text: str,
        chunks: list[TextChunk],
        source_type: SourceType,
        context: str | None,
        context_map: LLMContextMap,
    ) -> list[Flag]:
        _ = chunks
        messages = [
            {
                "role": "system",
                "content": (
                    "Find cross-sentence inconsistencies, contradictions, or suspicious wording "
                    "that depends on full-document context."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Source type: {source_type.value}\n"
                    f"External context: {context or 'none'}\n"
                    f"Document summary: {context_map.summary}\n"
                    f"Known entities: {', '.join(context_map.entities) or 'none'}\n"
                    f"Timeline cues: {', '.join(context_map.timeline) or 'none'}\n"
                    f"Domain cues: {', '.join(context_map.domain_cues) or 'none'}\n\n"
                    "Return issues only when they clearly require cross-chunk context. "
                    "Use exact span_text from the full text.\n\n"
                    f"Full text:\n{text}"
                ),
            },
        ]
        payload = self._call_structured(
            messages=messages,
            response_model=_IssueListPayload,
            max_tokens=self.settings.max_tokens_cross,
        )
        return self._map_document_issues(text=text, issues=payload.issues)

    def _call_structured(
        self,
        *,
        messages: list[dict[str, str]],
        response_model: type[BaseModel],
        max_tokens: int,
    ) -> Any:
        try:
            response = any_llm_completion(
                model=self.settings.model,
                provider=self.settings.provider,
                messages=messages,
                response_format=response_model,
                temperature=self.settings.temperature,
                reasoning_effort=self.settings.reasoning_effort,
                max_tokens=max_tokens,
                client_args=self.settings.client_args,
            )
        except Exception as exc:  # pragma: no cover - depends on provider/runtime config
            raise RuntimeError(
                f"any-llm request failed for provider={self.settings.provider} "
                f"model={self.settings.model}: {exc}"
            ) from exc

        parsed = self._extract_parsed(response=response, response_model=response_model)
        return response_model.model_validate(parsed)

    @staticmethod
    def _extract_parsed(*, response: Any, response_model: type[BaseModel]) -> Any:
        choices = getattr(response, "choices", None)
        if not choices:
            raise RuntimeError("LLM response did not contain choices.")

        message = getattr(choices[0], "message", None)
        if message is None:
            raise RuntimeError("LLM response did not contain a message.")

        parsed = getattr(message, "parsed", None)
        if parsed is not None:
            if isinstance(parsed, BaseModel):
                return parsed.model_dump()
            if isinstance(parsed, dict):
                return parsed
            return response_model.model_validate(parsed).model_dump()

        content = getattr(message, "content", None)
        if isinstance(content, str):
            return json.loads(content)

        raise RuntimeError("LLM response missing parsed structured content.")

    @staticmethod
    def _map_chunk_issues(*, chunk: TextChunk, issues: list[_IssuePayload]) -> list[Flag]:
        flags: list[Flag] = []
        for issue in issues:
            relative_start = _find_span(chunk.text, issue.span_text)
            if relative_start is None:
                continue
            start = chunk.start + relative_start
            end = start + len(issue.span_text)
            flags.append(
                Flag(
                    start=start,
                    end=end,
                    text=issue.span_text,
                    severity=issue.severity,
                    category=issue.category,
                    reason=issue.reason,
                    suggestion=issue.suggestion,
                    confidence=issue.confidence,
                )
            )
        return flags

    @staticmethod
    def _map_document_issues(*, text: str, issues: list[_IssuePayload]) -> list[Flag]:
        flags: list[Flag] = []
        for issue in issues:
            start = _find_span(text, issue.span_text)
            if start is None:
                continue
            end = start + len(issue.span_text)
            flags.append(
                Flag(
                    start=start,
                    end=end,
                    text=issue.span_text,
                    severity=issue.severity,
                    category=issue.category,
                    reason=issue.reason,
                    suggestion=issue.suggestion,
                    confidence=issue.confidence,
                )
            )
        return flags


def _find_span(text: str, span_text: str) -> int | None:
    needle = span_text.strip()
    if not needle:
        return None

    direct = text.find(needle)
    if direct >= 0:
        return direct

    lowered = text.lower()
    lowered_needle = needle.lower()
    lowered_match = lowered.find(lowered_needle)
    if lowered_match >= 0:
        return lowered_match
    return None
