"""Validate project CRUD and the read-only project work overview."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.models.ticket import TicketPriority, TicketStatus

ProjectLifeContext = Literal["work", "volunteer", "personal", "unclassified"]

class ProjectFields(BaseModel):
    name: str
    description: str | None = None
    purpose: str | None = None
    why_it_matters: str | None = None
    target_date: date | None = None
    life_context: ProjectLifeContext = "unclassified"
    ai_context_enabled: bool = True
    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value: raise ValueError("Project name is required.")
        if len(value) > 200: raise ValueError("Project name must be 200 characters or fewer.")
        return value
    @field_validator("description", "purpose", "why_it_matters")
    @classmethod
    def clean_context(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

class ProjectCreate(ProjectFields): pass
class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    purpose: str | None = None
    why_it_matters: str | None = None
    target_date: date | None = None
    life_context: ProjectLifeContext | None = None
    @field_validator("name")
    @classmethod
    def clean_optional_name(cls, value: str | None) -> str:
        if value is None: raise ValueError("Project name cannot be null.")
        return ProjectFields.clean_name(value)
    @field_validator("description", "purpose", "why_it_matters")
    @classmethod
    def clean_optional_context(cls, value: str | None) -> str | None:
        return ProjectFields.clean_context(value)
    @field_validator("life_context")
    @classmethod
    def require_life_context(cls, value: ProjectLifeContext | None) -> ProjectLifeContext:
        if value is None:
            raise ValueError("Project life context cannot be null.")
        return value

ArchiveReason = Literal["completed", "superseded", "cancelled", "test_development", "other"]


class ProjectArchiveRequest(BaseModel):
    archive_reason: ArchiveReason
    archive_reason_note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_reason_note(self):
        if self.archive_reason_note is not None:
            self.archive_reason_note = self.archive_reason_note.strip() or None
        if self.archive_reason == "other" and not self.archive_reason_note:
            raise ValueError("Explain why this Project is being archived as Other.")
        return self


class ProjectAIPolicyUpdate(BaseModel):
    ai_context_enabled: bool

class ProjectLifecycleEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    actor_user_id: int
    action: str
    archive_reason: str | None
    archive_reason_note: str | None
    previous_life_context: ProjectLifeContext | None
    new_life_context: ProjectLifeContext | None
    created_at: datetime

class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; public_id: str; workspace_project_number: int
    name: str; description: str | None; purpose: str | None; why_it_matters: str | None
    target_date: date | None; life_context: ProjectLifeContext; ai_context_enabled: bool
    archived_at: datetime | None; archived_by_user_id: int | None
    archive_reason: str | None; archive_reason_note: str | None
    archive_report_eligible_by_default: bool
    created_at: datetime; updated_at: datetime

class ProjectTicketCounts(BaseModel):
    total: int = 0; active: int = 0; ready: int = 0; in_progress: int = 0; blocked: int = 0; review: int = 0; done: int = 0; cancelled: int = 0
class ProjectProgressCounts(BaseModel):
    completed: int = 0; total: int = 0; deferred: int = 0
class ProjectAttentionTicket(BaseModel):
    id: int; workspace_ticket_number: int; title: str; status: TicketStatus; priority: TicketPriority; updated_at: datetime
    reasons: list[str] = Field(default_factory=list)
class ProjectHistoryEntry(BaseModel):
    ticket_id: int; workspace_ticket_number: int; ticket_title: str; ticket_status: TicketStatus
    occurred_at: datetime; event_type: str; summary: str; actor: str | None = None
class ProjectWorkOverviewRead(BaseModel):
    project_id: int; generated_at: datetime; tickets: ProjectTicketCounts
    acceptance_criteria: ProjectProgressCounts; subtasks: ProjectProgressCounts
    attention: list[ProjectAttentionTicket] = Field(default_factory=list)
    recent_history: list[ProjectHistoryEntry] = Field(default_factory=list)
