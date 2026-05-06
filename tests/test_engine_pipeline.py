from __future__ import annotations

from conversion_triage.engine import Flag, FlagCategory, Severity, triage_text, triage_youtube_url
from conversion_triage.engine.llm import LLMAdapter
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
