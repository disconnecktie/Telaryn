"""API contracts for durable Work Intake operations."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.work_intake_attempt import WorkIntakeAttemptStatus
from app.schemas.work_intake import WorkIntakeRead


class WorkIntakeAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_text: str
    status: WorkIntakeAttemptStatus
    provider: str
    model: str
    result: WorkIntakeRead | None
    safe_error_category: str | None
    duration_ms: int | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    dismissed_at: datetime | None
    clarification_answers: list[str] = Field(default_factory=list)
    refinement_count: int = 0
