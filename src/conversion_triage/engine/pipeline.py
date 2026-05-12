from __future__ import annotations

from collections.abc import Sequence

from conversion_triage.engine.chunking import sentence_chunks
from conversion_triage.engine.llm import LLMAdapterLike
from conversion_triage.engine.merge import merge_flags
from conversion_triage.engine.rules import run_rule_checks
from conversion_triage.engine.schemas import Flag, SourceType, TriageResult
from conversion_triage.transcripts import TranscriptProvider, YouTubeTranscriptProvider


def triage_text(
    *,
    text: str,
    source_type: str,
    context: str | None = None,
    llm_adapter: LLMAdapterLike | None = None,
) -> TriageResult:
    """Run deterministic checks plus optional multi-pass LLM checks."""
    parsed_source = SourceType(source_type)
    chunks = sentence_chunks(text)

    flags = run_rule_checks(text=text, source_type=parsed_source)
    flags.extend(
        _run_llm_checks(
            text=text,
            chunks=chunks,
            source_type=parsed_source,
            context=context,
            llm_adapter=llm_adapter,
        )
    )

    return TriageResult(flags=merge_flags(flags))


def _run_llm_checks(
    *,
    text: str,
    chunks: Sequence,
    source_type: SourceType,
    context: str | None,
    llm_adapter: LLMAdapterLike | None,
) -> list[Flag]:
    if llm_adapter is None:
        return []

    # Preferred multi-pass path: document summary -> per-chunk review -> cross-chunk review.
    if (
        hasattr(llm_adapter, "summarize_document")
        and hasattr(llm_adapter, "triage_chunk")
        and hasattr(llm_adapter, "triage_cross_chunk")
    ):
        context_map = llm_adapter.summarize_document(
            text=text,
            source_type=source_type,
            context=context,
            chunks=chunks,
        )
        llm_flags: list[Flag] = []
        total_chunks = len(chunks)
        for chunk_index, chunk in enumerate(chunks):
            llm_flags.extend(
                llm_adapter.triage_chunk(
                    chunk=chunk,
                    chunk_index=chunk_index,
                    total_chunks=total_chunks,
                    source_type=source_type,
                    context=context,
                    context_map=context_map,
                )
            )
        llm_flags.extend(
            llm_adapter.triage_cross_chunk(
                text=text,
                chunks=chunks,
                source_type=source_type,
                context=context,
                context_map=context_map,
            )
        )
        return llm_flags

    # Backward-compatible one-shot fallback adapter path.
    return list(llm_adapter.triage(text=text, source_type=source_type, context=context))


def fetch_youtube_text(
    *,
    url: str,
    transcript_provider: TranscriptProvider | None = None,
) -> str:
    """Fetch subtitle transcript text from a YouTube URL."""
    provider = transcript_provider or YouTubeTranscriptProvider()
    return provider.fetch_text(url=url)


def triage_youtube_url(
    *,
    url: str,
    source_type: str = "asr",
    context: str | None = None,
    transcript_provider: TranscriptProvider | None = None,
    llm_adapter: LLMAdapterLike | None = None,
) -> TriageResult:
    """Fetch subtitles from YouTube and triage the transcript text."""
    transcript_text = fetch_youtube_text(url=url, transcript_provider=transcript_provider)
    return triage_text(
        text=transcript_text,
        source_type=source_type,
        context=context,
        llm_adapter=llm_adapter,
    )
