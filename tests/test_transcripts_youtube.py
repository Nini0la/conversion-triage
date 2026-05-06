from __future__ import annotations

import pytest

from conversion_triage.transcripts import TranscriptProviderError, extract_video_id


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
