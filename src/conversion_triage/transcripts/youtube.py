from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import (
    CouldNotRetrieveTranscript,
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)

from conversion_triage.transcripts.base import TranscriptProvider, TranscriptProviderError

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_video_id(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        raise TranscriptProviderError("YouTube URL is empty.")

    if _VIDEO_ID_RE.fullmatch(raw):
        return raw

    parsed = urlparse(raw)
    host = parsed.netloc.lower()
    path = parsed.path.strip("/")

    if host in {"youtu.be", "www.youtu.be"}:
        candidate = path.split("/")[0] if path else ""
        if _VIDEO_ID_RE.fullmatch(candidate):
            return candidate

    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if path == "watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
            if _VIDEO_ID_RE.fullmatch(video_id):
                return video_id

        for prefix in ("shorts/", "live/", "embed/"):
            if path.startswith(prefix):
                candidate = path.split("/")[1] if len(path.split("/")) > 1 else ""
                if _VIDEO_ID_RE.fullmatch(candidate):
                    return candidate

    raise TranscriptProviderError("Could not extract a valid YouTube video ID from URL.")


def _normalize_segments(segments: object) -> str:
    text_parts: list[str] = []
    if not isinstance(segments, Iterable):
        return ""

    for segment in segments:
        if isinstance(segment, dict):
            value = segment.get("text", "")
        else:
            value = getattr(segment, "text", "")
        snippet = str(value).strip()
        if snippet:
            text_parts.append(snippet)

    return re.sub(r"\s+", " ", " ".join(text_parts)).strip()


class YouTubeTranscriptProvider(TranscriptProvider):
    """Fetches subtitle transcript text from a YouTube URL."""

    def __init__(self, *, languages: list[str] | None = None) -> None:
        self.languages = languages or ["en"]
        self.client = YouTubeTranscriptApi()

    def fetch_text(self, *, url: str) -> str:
        video_id = extract_video_id(url)
        try:
            segments = self.client.fetch(video_id, languages=self.languages)
        except (TranscriptsDisabled, NoTranscriptFound):
            raise TranscriptProviderError(
                "No YouTube subtitles found for this video. We only import existing subtitles; "
                "we do not transcribe audio."
            ) from None
        except CouldNotRetrieveTranscript as exc:
            raise TranscriptProviderError(
                f"Failed to fetch YouTube subtitles: {exc}. We only import existing subtitles."
            ) from exc
        except Exception as exc:  # pragma: no cover - external errors vary by environment
            raise TranscriptProviderError(f"Failed to fetch YouTube transcript: {exc}") from exc

        text = _normalize_segments(segments)
        if not text:
            raise TranscriptProviderError(
                "YouTube subtitles were fetched but empty. We only import existing subtitles."
            )
        return text
