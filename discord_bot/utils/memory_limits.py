from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


ABSOLUTE_MAX_FACT_LENGTH = 5000
ABSOLUTE_MAX_ATTRIBUTE_LENGTH = 5000
ABSOLUTE_MAX_SAMPLE_DIALOGUE_LENGTH = 5000
ABSOLUTE_MAX_DOCUMENT_TEXT_LENGTH = 500_000
ABSOLUTE_MAX_DOCUMENT_CHUNKS = 2_000


@dataclass(frozen=True)
class MemoryLimits:
    max_fact_length: int
    max_attribute_length: int
    max_sample_dialogue_length: int
    max_document_text_length: int
    max_document_chunks: int


@dataclass(frozen=True)
class MemoryValidationResult:
    is_valid: bool
    error: Optional[str] = None
    max_allowed: Optional[int] = None
    current_count: Optional[int] = None


def _parse_limit(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    try:
        value = int(raw) if raw is not None else default
    except ValueError:
        return default
    if value < minimum or value > maximum:
        return default
    return value


def get_memory_limits() -> MemoryLimits:
    return MemoryLimits(
        max_fact_length=_parse_limit(
            "MAX_MEMORY_LENGTH",
            1000,
            1,
            ABSOLUTE_MAX_FACT_LENGTH,
        ),
        max_attribute_length=_parse_limit(
            "MAX_ATTRIBUTE_LENGTH",
            2000,
            1,
            ABSOLUTE_MAX_ATTRIBUTE_LENGTH,
        ),
        max_sample_dialogue_length=_parse_limit(
            "MAX_SAMPLE_DIALOGUE_LENGTH",
            2000,
            1,
            ABSOLUTE_MAX_SAMPLE_DIALOGUE_LENGTH,
        ),
        max_document_text_length=_parse_limit(
            "MAX_DOCUMENT_TEXT_LENGTH",
            120_000,
            1,
            ABSOLUTE_MAX_DOCUMENT_TEXT_LENGTH,
        ),
        max_document_chunks=_parse_limit(
            "MAX_DOCUMENT_CHUNKS",
            150,
            1,
            ABSOLUTE_MAX_DOCUMENT_CHUNKS,
        ),
    )


def _validate_non_empty(content: str) -> MemoryValidationResult:
    if not content or not content.strip():
        return MemoryValidationResult(is_valid=False, error="CONTENT_EMPTY")
    return MemoryValidationResult(is_valid=True)


def validate_fact_content(content: str) -> MemoryValidationResult:
    base = _validate_non_empty(content)
    if not base.is_valid:
        return base
    limits = get_memory_limits()
    if len(content) > limits.max_fact_length:
        return MemoryValidationResult(
            is_valid=False,
            error="CONTENT_TOO_LONG",
            max_allowed=limits.max_fact_length,
        )
    return MemoryValidationResult(is_valid=True)


def validate_attribute_content(content: str) -> MemoryValidationResult:
    base = _validate_non_empty(content)
    if not base.is_valid:
        return base
    limits = get_memory_limits()
    if len(content) > limits.max_attribute_length:
        return MemoryValidationResult(
            is_valid=False,
            error="CONTENT_TOO_LONG",
            max_allowed=limits.max_attribute_length,
        )
    return MemoryValidationResult(is_valid=True)


def validate_sample_dialogue_content(content: str) -> MemoryValidationResult:
    base = _validate_non_empty(content)
    if not base.is_valid:
        return base
    limits = get_memory_limits()
    if len(content) > limits.max_sample_dialogue_length:
        return MemoryValidationResult(
            is_valid=False,
            error="CONTENT_TOO_LONG",
            max_allowed=limits.max_sample_dialogue_length,
        )
    return MemoryValidationResult(is_valid=True)


def validate_document_text(content: str) -> MemoryValidationResult:
    base = _validate_non_empty(content)
    if not base.is_valid:
        return base
    limits = get_memory_limits()
    if len(content) > limits.max_document_text_length:
        return MemoryValidationResult(
            is_valid=False,
            error="DOCUMENT_TEXT_TOO_LONG",
            max_allowed=limits.max_document_text_length,
        )
    return MemoryValidationResult(is_valid=True)


def validate_document_chunks(chunk_count: int) -> MemoryValidationResult:
    limits = get_memory_limits()
    if chunk_count > limits.max_document_chunks:
        return MemoryValidationResult(
            is_valid=False,
            error="DOCUMENT_CHUNK_LIMIT_EXCEEDED",
            max_allowed=limits.max_document_chunks,
            current_count=chunk_count,
        )
    return MemoryValidationResult(is_valid=True)


def get_memory_limit_error_message(result: MemoryValidationResult) -> str:
    if result.is_valid:
        return "ok"
    if result.error == "CONTENT_EMPTY":
        return "Memory content cannot be empty."
    if result.error == "CONTENT_TOO_LONG":
        return f"Content is too long (max {result.max_allowed} characters)."
    if result.error == "DOCUMENT_TEXT_TOO_LONG":
        return f"Document text is too long (max {result.max_allowed} characters)."
    if result.error == "DOCUMENT_CHUNK_LIMIT_EXCEEDED":
        return (
            f"Document produced too many chunks ({result.current_count}); "
            f"max allowed is {result.max_allowed}."
        )
    return "Memory validation failed."

