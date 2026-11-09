"""Provider-neutral contracts for advisory ticket-progress review."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProgressCandidate:
    kind: str
    item_id: int
    reference_number: int
    text: str
    updated_at: str


@dataclass(frozen=True)
class ProgressReviewContext:
    evidence: str
    evidence_type: str
    evidence_id: int | None
    candidates: list[ProgressCandidate]


@dataclass(frozen=True)
class ProgressSuggestion:
    kind: str
    item_id: int
    rationale: str


@dataclass(frozen=True)
class ProgressReviewResult:
    summary: str
    suggestions: list[ProgressSuggestion] = field(default_factory=list)
