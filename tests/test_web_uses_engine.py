from __future__ import annotations

from fastapi.testclient import TestClient

from conversion_triage.engine import Flag, FlagCategory, Severity, TriageResult
from conversion_triage.web.app import create_app


def test_web_route_calls_engine(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)
    called: dict[str, str | None] = {}

    def fake_triage_text(*, text: str, source_type: str, context: str | None, llm_adapter=None):
        _ = llm_adapter
        called["text"] = text
        called["source_type"] = source_type
        called["context"] = context
        return TriageResult(
            flags=[
                Flag(
                    start=0,
                    end=4,
                    text=text[0:4],
                    severity=Severity.MINOR,
                    category=FlagCategory.FORMATTING_ISSUE,
                    reason="stub reason",
                    suggestion=None,
                    confidence=0.42,
                )
            ]
        )

    monkeypatch.setattr("conversion_triage.web.routes.triage_text", fake_triage_text)

    response = client.post(
        "/triage",
        data={
            "text": "test payload",
            "youtube_url": "",
            "source_type": "ocr",
            "context": "invoice",
        },
    )

    assert response.status_code == 200
    assert called == {
        "text": "test payload",
        "source_type": "ocr",
        "context": "invoice",
    }
    assert "stub reason" in response.text


def test_web_route_can_use_youtube_transcript_source(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)
    called: dict[str, str | None] = {}

    def fake_fetch_youtube_text(*, url: str) -> str:
        called["url"] = url
        return "for all intensive purposes"

    def fake_triage_text(*, text: str, source_type: str, context: str | None, llm_adapter=None):
        _ = llm_adapter
        called["text"] = text
        called["source_type"] = source_type
        called["context"] = context
        return TriageResult(
            flags=[
                Flag(
                    start=0,
                    end=3,
                    text="for",
                    severity=Severity.MINOR,
                    category=FlagCategory.ASR_CONFUSION,
                    reason="stub",
                    suggestion=None,
                    confidence=0.5,
                )
            ]
        )

    monkeypatch.setattr("conversion_triage.web.routes.fetch_youtube_text", fake_fetch_youtube_text)
    monkeypatch.setattr("conversion_triage.web.routes.triage_text", fake_triage_text)

    response = client.post(
        "/triage",
        data={
            "text": "",
            "youtube_url": "https://youtu.be/dQw4w9WgXcQ",
            "source_type": "asr",
            "context": "youtube video",
            "action": "triage",
        },
    )

    assert response.status_code == 200
    assert called == {
        "url": "https://youtu.be/dQw4w9WgXcQ",
        "text": "for all intensive purposes",
        "source_type": "asr",
        "context": "youtube video",
    }
    assert "for all intensive purposes" in response.text


def test_web_import_button_fetches_without_running_triage(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)

    def fake_fetch_youtube_text(*, url: str) -> str:
        assert url == "https://youtu.be/dQw4w9WgXcQ"
        return "imported subtitle text"

    def fail_triage_text(*, text: str, source_type: str, context: str | None, llm_adapter=None):
        _ = (text, source_type, context, llm_adapter)
        raise AssertionError("triage_text should not be called during import action")

    monkeypatch.setattr("conversion_triage.web.routes.fetch_youtube_text", fake_fetch_youtube_text)
    monkeypatch.setattr("conversion_triage.web.routes.triage_text", fail_triage_text)

    response = client.post(
        "/triage",
        data={
            "text": "",
            "youtube_url": "https://youtu.be/dQw4w9WgXcQ",
            "source_type": "asr",
            "context": "youtube video",
            "action": "import_youtube",
        },
    )

    assert response.status_code == 200
    assert "imported subtitle text" in response.text
    assert 'readonly class="locked"' in response.text
