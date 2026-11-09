"""Validate ticket writes and shape ticket, status, and activity API responses."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def assume_utc(value: datetime) -> datetime:
    """Mark legacy SQLite timestamps as UTC before JSON serialization."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value

from app.models.ticket import TicketPriority, TicketStatus, TicketType


class TicketCreateCriterion(BaseModel):
    text: str
    sort_order: int = 0

    @field_validator("text")
    @classmethod
    def require_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Every acceptance criterion needs text.")
        return value


class TicketCreateSubtask(BaseModel):
    title: str = Field(max_length=200)
    description: str | None = None
    sort_order: int = 0

    @field_validator("title")
    @classmethod
    def require_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Every subtask needs a title.")
        return value


class TicketCreate(BaseModel):
    title: str
    description: str | None = None
    priority: TicketPriority = TicketPriority.MEDIUM
    ticket_type: TicketType = TicketType.TASK
    project_id: int | None = None
    ai_context_enabled: bool = True
    acceptance_criteria: list[TicketCreateCriterion] = Field(default_factory=list)
    subtasks: list[TicketCreateSubtask] = Field(default_factory=list)


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    workspace_ticket_number: int
    title: str
    description: str | None
    status: TicketStatus
    priority: TicketPriority
    ticket_type: TicketType
    created_at: datetime
    updated_at: datetime
    project_id: int | None
    ai_context_enabled: bool


class TicketUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    ticket_type: TicketType | None = None
    project_id: int | None = None
    ai_context_enabled: bool | None = None
    status_note: str | None = None

    @field_validator("status")
    @classmethod
    def reject_null_status(cls, value: TicketStatus | None) -> TicketStatus:
        if value is None:
            raise ValueError("Ticket status cannot be null.")

        return value

    @field_validator("status_note")
    @classmethod
    def clean_status_note(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if len(value) > 2000:
            raise ValueError("Status note must be 2,000 characters or fewer.")

        return value or None


class TicketStatusEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    from_status: TicketStatus
    to_status: TicketStatus
    note: str | None
    created_at: datetime

    @field_validator("created_at", mode="before")
    @classmethod
    def mark_created_at_utc(cls, value: datetime) -> datetime:
        return assume_utc(value)


class TicketActivityEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    event_type: str
    actor_type: str
    actor_id: str | None
    actor_name: str | None = None
    field_name: str | None
    previous_value: Any | None
    new_value: Any | None
    note: str | None
    created_at: datetime

    @field_validator("created_at", mode="before")
    @classmethod
    def mark_created_at_utc(cls, value: datetime) -> datetime:
        return assume_utc(value)


class TicketActivityItemRead(BaseModel):
    """A normalized timeline item backed by one authoritative source record."""

    source_type: str
    source_id: int
    event_type: str
    actor_type: str
    actor_id: str | None
    actor_name: str | None = None
    field_name: str | None = None
    previous_value: Any | None = None
    new_value: Any | None = None
    note: str | None = None
    content: str | None = None
    attachment_count: int = 0
    created_at: datetime

    @field_validator("created_at", mode="before")
    @classmethod
    def mark_created_at_utc(cls, value: datetime) -> datetime:
        return assume_utc(value)
