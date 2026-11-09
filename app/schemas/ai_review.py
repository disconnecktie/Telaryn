"""Define draft-review, persisted-review, and explicit-acceptance contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.ai_review import AIReviewStatus
from app.models.ticket import TicketPriority, TicketType
from app.ai.provenance import SuggestionBasis


class AIDraftSubtask(BaseModel):
    title: str
    description: str | None = None


class AIRecommendationRead(BaseModel):
    text: str
    rationale: str | None = None
    basis: SuggestionBasis | None = None


class AISuggestedCriterionRead(BaseModel):
    text: str
    basis: SuggestionBasis | None = None


class AISuggestedSubtaskRead(BaseModel):
    title: str
    description: str | None = None
    basis: SuggestionBasis | None = None


class AISubtaskRevisionRead(BaseModel):
    source_index: int
    suggested_title: str
    suggested_description: str | None = None
    rationale: str | None = None
    basis: SuggestionBasis | None = None


class AICriterionRevisionRead(BaseModel):
    source_index: int
    suggested_text: str
    rationale: str | None = None
    basis: SuggestionBasis | None = None


class AIDraftReviewRequest(BaseModel):
    title: str = ""
    description: str | None = None
    priority: TicketPriority = TicketPriority.MEDIUM
    ticket_type: TicketType = TicketType.TASK
    project_id: int | None = None
    ai_context_enabled: bool = True
    subtasks: list[AIDraftSubtask] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_draft_content(self):
        if not self.title.strip() and not (self.description or "").strip():
            raise ValueError("Add a title or description before reviewing the draft.")

        return self


class AIDraftReviewRead(BaseModel):
    provider: str
    model: str
    suggested_title: str | None
    suggested_description: str | None
    suggested_priority: str | None
    suggested_ticket_type: str | None
    reasoning_summary: str | None
    missing_information: list[str]
    recommendations: list[AIRecommendationRead]
    acceptance_criteria: list[AISuggestedCriterionRead]
    suggested_subtasks: list[AISuggestedSubtaskRead]
    subtask_revisions: list[AISubtaskRevisionRead]
    acceptance_criteria_revisions: list[AICriterionRevisionRead]


class AIReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    status: AIReviewStatus
    provider: str | None
    model: str | None
    suggested_title: str | None
    suggested_description: str | None
    suggested_priority: str | None
    suggested_ticket_type: str | None
    missing_information: list | None
    suggested_subtasks: list[AISuggestedSubtaskRead] | None
    created_at: datetime
    completed_at: datetime | None
    reasoning_summary: str | None
    acceptance_criteria: list[AISuggestedCriterionRead | str] | None
    recommendations: list[AIRecommendationRead] | None

class AIReviewAccept(BaseModel):
    apply_title: bool = True
    apply_description: bool = True
    apply_priority: bool = True
    apply_ticket_type: bool = True
    create_subtasks: bool = True
    acceptance_criteria_indices: list[int] = Field(default_factory=list)
