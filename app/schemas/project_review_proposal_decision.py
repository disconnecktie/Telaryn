"""API contracts for human decisions on Project Review proposals."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.ai.project_review import ProjectReviewProposedChanges


class ProjectReviewProposalDecisionWrite(BaseModel):
    decision: Literal["pending", "approved", "rejected", "deferred"]
    edited_changes: ProjectReviewProposedChanges | None = None
    note: str | None = Field(default=None, max_length=1000)


class ProjectReviewProposalDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    proposal_index: int
    decision: Literal["pending", "approved", "rejected", "deferred"]
    edited_changes: ProjectReviewProposedChanges | None
    note: str | None
    application_id: int | None = None
    focus_applied_at: datetime | None = None
    focus_previous_ticket_id: int | None = None
    created_at: datetime | None
    updated_at: datetime | None
