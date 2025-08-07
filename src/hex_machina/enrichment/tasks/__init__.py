"""Enrichment task implementations."""

from .base import LLMTask
from .content_completeness import ContentCompletenessTask

__all__ = [
    "LLMTask",
    "ContentCompletenessTask",
]
