"""Validate Acceptance Criterion CRUD and atomic section-save payloads."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AcceptanceCriterionCreate(BaseModel):
    text: str
    sort_order: int = 0

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Acceptance criterion text is required.")
        return value


class AcceptanceCriterionUpdate(BaseModel):
    text: str | None = None
    completed: bool | None = None
    deferred: bool | None = None
    reason: str | None = Field(default=None, max_length=2000)
    sort_order: int | None = None

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Acceptance criterion text is required.")
        return value


class AcceptanceCriterionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    reference_number: int
    text: str
    completed: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    deferred: bool
    deferred_at: datetime | None
    deferred_reason: str | None


class AcceptanceCriterionSaveItem(BaseModel):
    id: int | None = None
    text: str
    completed: bool = False
    deferred: bool = False

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Acceptance criterion text is required.")
        return value


class AcceptanceCriteriaSave(BaseModel):
    criteria: list[AcceptanceCriterionSaveItem]
    reason: str | None = Field(default=None, max_length=2000)
