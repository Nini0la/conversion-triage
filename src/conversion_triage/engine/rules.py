from __future__ import annotations

import calendar
import re
from collections.abc import Iterable

from conversion_triage.engine.schemas import Flag, FlagCategory, Severity, SourceType


def run_rule_checks(text: str, source_type: SourceType) -> list[Flag]:
    flags: list[Flag] = []
    flags.extend(_formatting_checks(text))
    flags.extend(_number_and_date_checks(text))
    flags.extend(_semantic_and_phrase_checks(text, source_type))
    if source_type == SourceType.OCR:
        flags.extend(_ocr_checks(text))
    if source_type == SourceType.ASR:
        flags.extend(_asr_checks(text))
    return flags


def _make_flag(
    text: str,
    start: int,
    end: int,
    *,
    severity: Severity,
    category: FlagCategory,
    reason: str,
    suggestion: str | None,
    confidence: float,
) -> Flag:
    return Flag(
        start=start,
        end=end,
        text=text[start:end],
        severity=severity,
        category=category,
        reason=reason,
        suggestion=suggestion,
        confidence=confidence,
    )


def _formatting_checks(text: str) -> Iterable[Flag]:
    patterns = [
        (
            re.compile(r" {2,}"),
            Severity.MINOR,
            "Repeated spaces may indicate conversion artifacts.",
            "Normalize spacing.",
            0.72,
        ),
        (
            re.compile(r"\b\w+-\s*\n\s*\w+\b"),
            Severity.MAJOR,
            "Hyphenated line break may be an OCR layout artifact.",
            "Join the split word if it should be continuous.",
            0.86,
        ),
    ]
    for pattern, severity, reason, suggestion, confidence in patterns:
        for match in pattern.finditer(text):
            yield _make_flag(
                text,
                match.start(),
                match.end(),
                severity=severity,
                category=FlagCategory.FORMATTING_ISSUE,
                reason=reason,
                suggestion=suggestion,
                confidence=confidence,
            )


def _number_and_date_checks(text: str) -> Iterable[Flag]:
    for match in re.finditer(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", text):
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))

        if year < 100:
            year += 2000

        is_invalid = not (1 <= month <= 12)
        if not is_invalid:
            _, max_day = calendar.monthrange(year, month)
            is_invalid = not (1 <= day <= max_day)

        if is_invalid:
            yield _make_flag(
                text,
                match.start(),
                match.end(),
                severity=Severity.CRITICAL,
                category=FlagCategory.NUMBER_OR_DATE_ISSUE,
                reason="Date appears invalid for calendar constraints.",
                suggestion="Verify day/month order and correct invalid date values.",
                confidence=0.97,
            )

    for match in re.finditer(r"\b([01]?\d|2[0-4]):([0-5]\d)\b", text):
        hour = int(match.group(1))
        minute = int(match.group(2))
        if hour == 24 and minute > 0:
            yield _make_flag(
                text,
                match.start(),
                match.end(),
                severity=Severity.MAJOR,
                category=FlagCategory.NUMBER_OR_DATE_ISSUE,
                reason="Time value is outside valid 24-hour format.",
                suggestion="Use hour values from 00 to 23.",
                confidence=0.9,
            )


def _semantic_and_phrase_checks(text: str, source_type: SourceType) -> Iterable[Flag]:
    phrase_rules: list[tuple[str, str, str | None, FlagCategory, Severity, float]] = [
        (
            r"\bfor all intensive purposes\b",
            "Common ASR confusion for 'for all intents and purposes'.",
            "for all intents and purposes",
            FlagCategory.ASR_CONFUSION,
            Severity.MAJOR,
            0.95,
        ),
        (
            r"\bcould of\b",
            "Likely transcription confusion with 'could have'.",
            "could have",
            FlagCategory.ASR_CONFUSION,
            Severity.MAJOR,
            0.93,
        ),
        (
            r"\bdefiantly\b",
            "Potential word substitution error for 'definitely'.",
            "definitely",
            FlagCategory.SEMANTIC_INCONSISTENCY,
            Severity.MINOR,
            0.79,
        ),
    ]

    if source_type == SourceType.OCR:
        phrase_rules.append(
            (
                r"\bmodem\b",
                "Contextually suspicious: OCR sometimes confuses 'modern' and 'modem'.",
                "modern",
                FlagCategory.SEMANTIC_INCONSISTENCY,
                Severity.MINOR,
                0.6,
            )
        )

    for pattern, reason, suggestion, category, severity, confidence in phrase_rules:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            yield _make_flag(
                text,
                match.start(),
                match.end(),
                severity=severity,
                category=category,
                reason=reason,
                suggestion=suggestion,
                confidence=confidence,
            )


def _ocr_checks(text: str) -> Iterable[Flag]:
    patterns = [
        (
            re.compile(r"\b\w*[0-9][A-Za-z]+\w*\b"),
            "Mixed digits inside a word can indicate OCR character confusion.",
            Severity.MAJOR,
            0.88,
        ),
        (
            re.compile(r"\brn\w{2,}\b", flags=re.IGNORECASE),
            "OCR can confuse 'm' as 'rn' in words.",
            Severity.MINOR,
            0.64,
        ),
        (
            re.compile(r"\b[I1l]{3,}\b"),
            "Repeated visually similar characters can indicate OCR noise.",
            Severity.MAJOR,
            0.85,
        ),
    ]
    for pattern, reason, severity, confidence in patterns:
        for match in pattern.finditer(text):
            yield _make_flag(
                text,
                match.start(),
                match.end(),
                severity=severity,
                category=FlagCategory.OCR_NOISE,
                reason=reason,
                suggestion=None,
                confidence=confidence,
            )


def _asr_checks(text: str) -> Iterable[Flag]:
    pattern = re.compile(r"\b(uh+|um+|erm+)\b", flags=re.IGNORECASE)
    for match in pattern.finditer(text):
        yield _make_flag(
            text,
            match.start(),
            match.end(),
            severity=Severity.MINOR,
            category=FlagCategory.ASR_CONFUSION,
            reason="Disfluency token may be a transcription artifact rather than intended wording.",
            suggestion="Confirm whether filler speech should remain.",
            confidence=0.55,
        )
