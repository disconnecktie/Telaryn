"""Validate one atomic drawer commit across ticket fields and work structure."""

from pydantic import BaseModel, Field, field_validator

from app.models.subtask import SubtaskStatus
from app.models.ticket import TicketPriority, TicketStatus, TicketType
from app.schemas.acceptance_criterion import AcceptanceCriterionRead
from app.schemas.subtask import SubtaskRead
from app.schemas.ticket import TicketRead


class DrawerTicketDraft(BaseModel):
    title: str = Field(max_length=200)
    description: str | None = None
    priority: TicketPriority
    ticket_type: TicketType
    status: TicketStatus
    project_id: int | None = None
    ai_context_enabled: bool = True

    @field_validator("title")
    @classmethod
    def require_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A ticket title is required.")
        return value


class DrawerCriterionDraft(BaseModel):
    id: int | None = None
    text: str
    completed: bool = False
    deferred: bool = False

    @field_validator("text")
    @classmethod
    def require_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Every acceptance criterion needs text.")
        return value


class DrawerSubtaskDraft(BaseModel):
    id: int | None = None
    title: str = Field(max_length=200)
    description: str | None = None
    status: SubtaskStatus = SubtaskStatus.TODO

    @field_validator("title")
    @classmethod
    def require_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Every subtask needs a title.")
        return value


class DrawerSessionCommit(BaseModel):
    ticket: DrawerTicketDraft
    acceptance_criteria: list[DrawerCriterionDraft]
    subtasks: list[DrawerSubtaskDraft]
    note: str | None = Field(default=None, max_length=2000)
    update_content: str | None = Field(default=None, max_length=2000)

    @field_validator("note", "update_content")
    @classmethod
    def clean_note(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class DrawerSessionResult(BaseModel):
    ticket: TicketRead
    acceptance_criteria: list[AcceptanceCriterionRead]
    subtasks: list[SubtaskRead]
