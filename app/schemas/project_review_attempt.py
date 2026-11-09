"""API contracts for persisted Project Review attempts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.ai.project_review import ProjectReviewResult
from app.models.project_review_attempt import ProjectReviewAttemptStatus


class ProjectReviewAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    snapshot_version: str
    review_reference: str | None
    status: ProjectReviewAttemptStatus
    provider: str
    model: str
    result: ProjectReviewResult | None
    safe_error_category: str | None
    duration_ms: int | None
    excluded_private_tickets: list[dict] | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
