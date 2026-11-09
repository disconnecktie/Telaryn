"""Shape final summaries and results for atomic Project Review application."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ProjectReviewApplicationItem(BaseModel):
    proposal_index: int
    proposal_type: str
    summary: str
    target_project_id: int | None
    target_ticket_id: int | None
    candidate_changes: dict[str, Any]


class ProjectReviewApplicationPreview(BaseModel):
    review_id: int
    items: list[ProjectReviewApplicationItem]
    conflicts: list[str]
    can_apply: bool


class ProjectReviewApplicationRead(BaseModel):
    id: int
    review_id: int
    proposal_indexes: list[int]
    resulting_changes: list[dict[str, Any]]
    applied_at: datetime
