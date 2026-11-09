"""Shape My Work focus, availability, and deterministic recommendation data."""

from datetime import date, datetime, timezone

from pydantic import BaseModel, Field, model_validator, field_validator

from app.models.my_work_preference import FocusAvailabilityMode
from app.models.subtask import SubtaskStatus
from app.models.ticket import TicketPriority, TicketStatus


class MyWorkProgress(BaseModel):
    completed: int = 0
    total: int = 0


class MyWorkNextAction(BaseModel):
    subtask_id: int
    title: str
    status: SubtaskStatus


class MyWorkItem(BaseModel):
    id: int
    workspace_ticket_number: int
    title: str
    description: str | None = None
    project_id: int | None = None
    project_name: str | None = None
    project_purpose: str | None = None
    project_why_it_matters: str | None = None
    project_target_date: date | None = None
    focus_rationale: str
    status: TicketStatus
    priority: TicketPriority
    updated_at: datetime
    reasons: list[str] = Field(default_factory=list)
    acceptance_criteria: MyWorkProgress = Field(default_factory=MyWorkProgress)
    subtasks: MyWorkProgress = Field(default_factory=MyWorkProgress)
    next_action: MyWorkNextAction | None = None
    availability_mode: FocusAvailabilityMode = FocusAvailabilityMode.AVAILABLE
    available_on: date | None = None

    @field_validator("updated_at", mode="before")
    @classmethod
    def mark_updated_at_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class MyWorkRead(BaseModel):
    generated_at: datetime
    current_focus: MyWorkItem | None = None
    suggestions: list[MyWorkItem] = Field(default_factory=list)
    upcoming: list[MyWorkItem] = Field(default_factory=list)
    focus_now: list[MyWorkItem] = Field(default_factory=list)
    needs_attention: list[MyWorkItem] = Field(default_factory=list)
    up_next: list[MyWorkItem] = Field(default_factory=list)
    ready_later_count: int = 0
    in_review: list[MyWorkItem] = Field(default_factory=list)
    recently_completed: list[MyWorkItem] = Field(default_factory=list)

    @field_validator("generated_at", mode="before")
    @classmethod
    def mark_generated_at_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class MyWorkPreferenceUpdate(BaseModel):
    current_focus: bool | None = None
    make_available_and_focus: bool = False
    availability_mode: FocusAvailabilityMode | None = None
    available_on: date | None = None

    @model_validator(mode="after")
    def validate_availability(self):
        if self.make_available_and_focus and self.current_focus is not True:
            raise ValueError(
                "make_available_and_focus requires current_focus=true"
            )
        if self.current_focus is True and self.availability_mode is not None:
            raise ValueError(
                "Focus and availability changes must be requested separately"
            )
        if (
            self.availability_mode == FocusAvailabilityMode.DATE
            and self.available_on is None
        ):
            raise ValueError("available_on is required for date-based availability")
        return self
