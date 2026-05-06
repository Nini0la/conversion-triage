from __future__ import annotations

import pytest

from conversion_triage.transcripts import (
    TranscriptProviderError,
    YouTubeTranscriptProvider,
    extract_video_id,
)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ],
)
def test_extract_video_id_supported_shapes(url: str, expected: str) -> None:
    assert extract_video_id(url) == expected


def test_extract_video_id_rejects_invalid_url() -> None:
    with pytest.raises(TranscriptProviderError):
        extract_video_id("https://example.com/not-youtube")


def test_youtube_provider_uses_client_fetch() -> None:
    class FakeClient:
        def fetch(self, video_id: str, languages):
            assert video_id == "dQw4w9WgXcQ"
            assert list(languages) == ["en"]
            return [{"text": "hello"}, {"text": "world"}]

    provider = YouTubeTranscriptProvider(languages=["en"])
    provider.client = FakeClient()

    text = provider.fetch_text(url="https://youtu.be/dQw4w9WgXcQ")
    assert text == "hello world"
