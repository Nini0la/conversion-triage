from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class SourceType(StrEnum):
    ASR = "asr"
    OCR = "ocr"


class Severity(StrEnum):
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class FlagCategory(StrEnum):
    OCR_NOISE = "ocr_noise"
    ASR_CONFUSION = "asr_confusion"
    SEMANTIC_INCONSISTENCY = "semantic_inconsistency"
    NUMBER_OR_DATE_ISSUE = "number_or_date_issue"
    FORMATTING_ISSUE = "formatting_issue"


class Flag(BaseModel):
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str
    severity: Severity
    category: FlagCategory
    reason: str
    suggestion: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_span(self) -> Flag:
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        return self


class TriageResult(BaseModel):
    flags: list[Flag] = Field(default_factory=list)
