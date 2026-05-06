from __future__ import annotations

from conversion_triage.engine.schemas import Flag


def merge_flags(flags: list[Flag]) -> list[Flag]:
    """Sort and deduplicate exact duplicates while preserving distinct categories."""
    deduped: dict[tuple[int, int, str, str], Flag] = {}
    for flag in flags:
        key = (flag.start, flag.end, flag.category.value, flag.reason)
        existing = deduped.get(key)
        if existing is None or flag.confidence > existing.confidence:
            deduped[key] = flag

    return sorted(deduped.values(), key=lambda f: (f.start, f.end, f.category.value))
