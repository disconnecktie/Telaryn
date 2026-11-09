"""Define the bounded, provider-neutral Project Review snapshot contract."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.my_work_preference import FocusAvailabilityMode
from app.models.subtask import SubtaskStatus
from app.models.ticket import TicketPriority, TicketStatus, TicketType
from app.schemas.project import ProjectWorkOverviewRead


class ProjectReviewProjectContext(BaseModel):
    id: int
    name: str
    description: str | None = None
    purpose: str | None = None
    why_it_matters: str | None = None
    target_date: date | None = None
    updated_at: datetime


class ProjectReviewCriterionContext(BaseModel):
    id: int
    text: str
    completed: bool
    deferred: bool
    deferred_reason: str | None = None
    sort_order: int
    updated_at: datetime


class ProjectReviewSubtaskContext(BaseModel):
    id: int
    title: str
    description: str | None = None
    status: SubtaskStatus
    deferred_reason: str | None = None
    sort_order: int
    updated_at: datetime


class ProjectReviewUpdateContext(BaseModel):
    id: int
    content: str
    created_at: datetime


class ProjectReviewAvailabilityContext(BaseModel):
    mode: FocusAvailabilityMode
    available_on: date | None = None
    is_current_focus: bool = False


class ProjectReviewTicketContext(BaseModel):
    id: int
    title: str
    description: str | None = None
    status: TicketStatus
    priority: TicketPriority
    ticket_type: TicketType
    updated_at: datetime
    detail_included: bool
    acceptance_criteria: list[ProjectReviewCriterionContext] = Field(default_factory=list)
    subtasks: list[ProjectReviewSubtaskContext] = Field(default_factory=list)
    latest_update: ProjectReviewUpdateContext | None = None
    availability: ProjectReviewAvailabilityContext


class ProjectReviewActivityContext(BaseModel):
    ticket_id: int
    ticket_title: str
    source_type: str
    source_id: int
    summary: str
    occurred_at: datetime


class ProjectReviewContextPolicy(BaseModel):
    recent_activity_limit: int
    latest_updates_per_active_ticket: int = 1
    terminal_ticket_detail: str = "summary_only"


class ProjectReviewSnapshotRead(BaseModel):
    project: ProjectReviewProjectContext
    snapshot_version: str
    generated_at: datetime
    work_overview: ProjectWorkOverviewRead
    current_focus_ticket_id: int | None = None
    tickets: list[ProjectReviewTicketContext] = Field(default_factory=list)
    recent_activity: list[ProjectReviewActivityContext] = Field(default_factory=list)
    context_policy: ProjectReviewContextPolicy
