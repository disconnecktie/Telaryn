"""Provider-neutral contracts for configurable Activity Reports."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.project import ProjectLifeContext

ReportPeriod = Literal["weekly", "monthly", "quarterly", "annual"]
ReportFormat = Literal["narrative", "action_result_impact"]
ReportScope = Literal["work", "volunteer", "personal", "all"]


class ActivityReportRequest(BaseModel):
    period: ReportPeriod
    output_format: ReportFormat
    scope: ReportScope = "work"
    project_ids: list[int] = Field(default_factory=list, max_length=50)
    style_example: str | None = Field(default=None, max_length=4000)
    period_start: date | None = None
    period_end: date | None = None

    @field_validator("project_ids")
    @classmethod
    def unique_project_ids(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))

    @field_validator("style_example")
    @classmethod
    def clean_style_example(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.period_start and self.period_end and self.period_start > self.period_end:
            raise ValueError("period_start must be on or before period_end")
        return self


class ActivityReportProjectOption(BaseModel):
    id: int
    name: str
    life_context: ProjectLifeContext
    archived: bool
    archive_reason: str | None = None
    included_by_default: bool


class ActivityReportTicketEvidence(BaseModel):
    reference: str
    title: str
    status: str
    updates: list[str] = Field(default_factory=list)
    status_notes: list[str] = Field(default_factory=list)


class ActivityReportProjectEvidence(BaseModel):
    id: int
    name: str
    life_context: ProjectLifeContext
    purpose: str | None = None
    why_it_matters: str | None = None
    tickets: list[ActivityReportTicketEvidence] = Field(default_factory=list)


class ActivityReportSnapshot(BaseModel):
    subject_first_name: str
    period: ReportPeriod
    output_format: ReportFormat
    period_start: date
    period_end: date
    style_example: str | None = None
    projects: list[ActivityReportProjectEvidence]


class ActivityReportResult(BaseModel):
    # OpenAI strict structured outputs require additionalProperties=false.
    model_config = ConfigDict(extra="forbid")

    title: str
    items: list[str] = Field(min_length=1, max_length=20)


class ActivityReportRead(ActivityReportResult):
    period: ReportPeriod
    output_format: ReportFormat
    period_start: date
    period_end: date
    generated_at: datetime
    included_project_ids: list[int]
