"""API contracts for explicit, advisory progress review."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.ai_review import AIReviewStatus


class ProgressReviewRequest(BaseModel):
    evidence_type: Literal["ticket_update", "drawer_session"]
    evidence_id: int | None = None
    evidence: str = Field(min_length=1, max_length=20000)


class ProgressSuggestionRead(BaseModel):
    key: str
    kind: Literal["acceptance_criterion", "subtask"]
    item_id: int
    reference_number: int
    text: str
    rationale: str
    updated_at: str
    state: Literal["available", "applied", "stale"] = "available"


class ProgressReviewRead(BaseModel):
    id: int
    ticket_id: int
    status: AIReviewStatus
    provider: str | None
    model: str | None
    summary: str | None
    source_evidence: dict | None
    suggestions: list[ProgressSuggestionRead]
    applied_progress: dict | None
    created_at: datetime
    completed_at: datetime | None


class ProgressReviewAccept(BaseModel):
    suggestion_keys: list[str] = Field(default_factory=list, max_length=10)
