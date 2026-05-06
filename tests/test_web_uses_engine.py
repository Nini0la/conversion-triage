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
