from __future__ import annotations

from conversion_triage.engine.chunking import sentence_chunks
from conversion_triage.engine.llm import LLMAdapter
from conversion_triage.engine.merge import merge_flags
from conversion_triage.engine.rules import run_rule_checks
from conversion_triage.engine.schemas import SourceType, TriageResult


def triage_text(
    *,
    text: str,
    source_type: str,
    context: str | None = None,
    llm_adapter: LLMAdapter | None = None,
) -> TriageResult:
    """Run deterministic checks, then optional LLM checks, and return merged flags."""
    parsed_source = SourceType(source_type)

    # Chunking is available for future per-chunk pipelines while preserving full-text spans.
    _ = sentence_chunks(text)

    flags = run_rule_checks(text=text, source_type=parsed_source)

    if llm_adapter is not None:
        flags.extend(llm_adapter.triage(text=text, source_type=parsed_source, context=context))

    return TriageResult(flags=merge_flags(flags))
