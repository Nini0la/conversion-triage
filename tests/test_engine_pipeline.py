from __future__ import annotations

from conversion_triage.engine import Flag, FlagCategory, Severity, triage_text, triage_youtube_url
from conversion_triage.engine.chunking import TextChunk
from conversion_triage.engine.llm import LLMAdapter, LLMContextMap
from conversion_triage.engine.schemas import SourceType


class DummyAdapter:
    def triage(self, *, text: str, source_type: SourceType, context: str | None) -> list[Flag]:
        _ = (source_type, context)
        phrase = "shipped"
        start = text.index(phrase)
        return [
            Flag(
                start=start,
                end=start + len(phrase),
                text=phrase,
                severity=Severity.MINOR,
                category=FlagCategory.SEMANTIC_INCONSISTENCY,
                reason="Model suspects wording mismatch for context.",
                suggestion="delivered",
                confidence=0.51,
            )
        ]


class DummyTranscriptProvider:
    def __init__(self) -> None:
        self.seen_url: str | None = None

    def fetch_text(self, *, url: str) -> str:
        self.seen_url = url
        return "for all intensive purposes we shipped on 32/13/2026"


class MultiPassDummyAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def summarize_document(
        self,
        *,
        text: str,
        source_type: SourceType,
        context: str | None,
        chunks: list[TextChunk],
    ) -> LLMContextMap:
        _ = (source_type, context, chunks)
        self.calls.append("summarize")
        return LLMContextMap(summary=f"summary:{len(text)}")

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
        _ = (chunk_index, total_chunks, source_type, context, context_map)
        self.calls.append(f"chunk:{chunk.text.strip()}")
        if "intensive purposes" not in chunk.text:
            return []
        start = chunk.start + chunk.text.lower().index("intensive")
        end = start + len("intensive")
        return [
            Flag(
                start=start,
                end=end,
                text="intensive",
                severity=Severity.MAJOR,
                category=FlagCategory.ASR_CONFUSION,
                reason="Likely wrong word in phrase.",
                suggestion="intents",
                confidence=0.9,
            )
        ]

    def triage_cross_chunk(
        self,
        *,
        text: str,
        chunks: list[TextChunk],
        source_type: SourceType,
        context: str | None,
        context_map: LLMContextMap,
    ) -> list[Flag]:
        _ = (text, chunks, source_type, context, context_map)
        self.calls.append("cross")
        return []


def test_engine_flags_rule_issues_without_web_app() -> None:
    text = "for all intensive purposes we shipped on 32/13/2026 with  two spaces"
    result = triage_text(text=text, source_type="asr", context="meeting transcript")

    assert len(result.flags) >= 3
    categories = {flag.category.value for flag in result.flags}
    assert "asr_confusion" in categories
    assert "number_or_date_issue" in categories
    assert "formatting_issue" in categories

    for flag in result.flags:
        assert 0 <= flag.start < flag.end <= len(text)
        assert flag.text == text[flag.start : flag.end]


def test_engine_supports_optional_llm_adapter() -> None:
    text = "for all intensive purposes we shipped on 01/12/2026"
    adapter: LLMAdapter = DummyAdapter()

    result = triage_text(text=text, source_type="asr", context="weekly update", llm_adapter=adapter)

    assert any(flag.reason.startswith("Model suspects") for flag in result.flags)


def test_engine_can_triage_from_youtube_provider() -> None:
    provider = DummyTranscriptProvider()

    result = triage_youtube_url(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        source_type="asr",
        context="video transcript",
        transcript_provider=provider,
    )

    assert provider.seen_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert any(flag.category.value == "asr_confusion" for flag in result.flags)


def test_engine_runs_multi_pass_llm_flow_when_supported() -> None:
    text = "for all intensive purposes we shipped."
    adapter = MultiPassDummyAdapter()

    result = triage_text(
        text=text,
        source_type="asr",
        context="meeting transcript",
        llm_adapter=adapter,
    )

    assert adapter.calls[0] == "summarize"
    assert adapter.calls[-1] == "cross"
    assert any(call.startswith("chunk:") for call in adapter.calls)
    assert any(flag.reason == "Likely wrong word in phrase." for flag in result.flags)
