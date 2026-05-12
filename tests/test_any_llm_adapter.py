from __future__ import annotations

from conversion_triage.engine.any_llm_adapter import AnyLLMMultiPassAdapter, AnyLLMSettings
from conversion_triage.engine.chunking import TextChunk
from conversion_triage.engine.schemas import SourceType


class _FakeMessage:
    def __init__(self, parsed):
        self.parsed = parsed


class _FakeChoice:
    def __init__(self, parsed):
        self.message = _FakeMessage(parsed)


class _FakeResponse:
    def __init__(self, parsed):
        self.choices = [_FakeChoice(parsed)]


def test_any_llm_adapter_routes_multi_pass_calls(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_completion(*, model: str, provider: str, messages, response_format, **kwargs):
        _ = (messages, kwargs)
        calls.append((provider, model))

        if len(calls) == 1:
            return _FakeResponse(
                {
                    "summary": "Meeting notes about release date.",
                    "entities": ["release team"],
                    "timeline": ["yesterday"],
                    "domain_cues": ["standup"],
                }
            )
        if len(calls) == 2:
            return _FakeResponse(
                {
                    "issues": [
                        {
                            "span_text": "intensive purposes",
                            "severity": "major",
                            "category": "asr_confusion",
                            "reason": "Likely phrase confusion.",
                            "suggestion": "intents and purposes",
                            "confidence": 0.91,
                        }
                    ]
                }
            )
        return _FakeResponse({"issues": []})

    monkeypatch.setattr(
        "conversion_triage.engine.any_llm_adapter.any_llm_completion",
        fake_completion,
    )

    adapter = AnyLLMMultiPassAdapter(
        AnyLLMSettings(provider="openai", model="gpt-4o-mini")
    )
    chunk = TextChunk(
        start=4,
        end=40,
        text="for all intensive purposes we shipped.",
    )
    context_map = adapter.summarize_document(
        text="abc " + chunk.text,
        source_type=SourceType.ASR,
        context="meeting transcript",
        chunks=[chunk],
    )
    chunk_flags = adapter.triage_chunk(
        chunk=chunk,
        chunk_index=0,
        total_chunks=1,
        source_type=SourceType.ASR,
        context="meeting transcript",
        context_map=context_map,
    )
    cross_flags = adapter.triage_cross_chunk(
        text="abc " + chunk.text,
        chunks=[chunk],
        source_type=SourceType.ASR,
        context="meeting transcript",
        context_map=context_map,
    )

    assert calls == [("openai", "gpt-4o-mini")] * 3
    assert context_map.summary.startswith("Meeting notes")
    assert len(chunk_flags) == 1
    assert chunk_flags[0].text == "intensive purposes"
    assert chunk_flags[0].start == 12
    assert cross_flags == []
