"""Validate Subtask CRUD and atomic section-save payloads."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.subtask import SubtaskStatus


class SubtaskCreate(BaseModel):
    title: str = Field(max_length=200)
    description: str | None = None
    sort_order: int = 0

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Subtask title is required")
        return title


class SubtaskUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None
    status: SubtaskStatus | None = None
    sort_order: int | None = None
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        title = value.strip()
        if not title:
            raise ValueError("Subtask title is required")
        return title


class SubtaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    reference_number: int
    title: str
    description: str | None
    status: SubtaskStatus
    sort_order: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    deferred_at: datetime | None
    deferred_reason: str | None


class SubtaskSaveItem(BaseModel):
    id: int | None = None
    title: str = Field(max_length=200)
    description: str | None = None
    status: SubtaskStatus = SubtaskStatus.TODO

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Subtask title is required")
        return value


class SubtasksSave(BaseModel):
    subtasks: list[SubtaskSaveItem]
    reason: str | None = Field(default=None, max_length=2000)
