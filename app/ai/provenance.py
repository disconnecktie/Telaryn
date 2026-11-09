"""Shared provenance vocabulary for human-reviewable AI suggestions."""

from enum import Enum


class SuggestionBasis(str, Enum):
    """Describe why Telaryn proposed an item without making it authoritative."""

    SUPPORTED = "supported"
    INFERRED = "inferred"
    RECOMMENDED = "recommended"

