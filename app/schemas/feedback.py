"""Validate private feedback submission and administrator review contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


FeedbackCategory = Literal["problem", "suggestion", "other"]
FeedbackStatus = Literal["new", "reviewing", "resolved", "closed"]


class FeedbackReceipt(BaseModel):
    reference: str
    status: FeedbackStatus
    submitted_at: datetime


class FeedbackSubmitterRead(BaseModel):
    display_name: str
    email: str
    workspace_name: str


class FeedbackAdminEventRead(BaseModel):
    actor_display_name: str
    actor_email: str
    previous_status: FeedbackStatus
    new_status: FeedbackStatus
    notes_changed: bool
    created_at: datetime


class FeedbackAdminRead(BaseModel):
    reference: str
    category: FeedbackCategory
    description: str
    status: FeedbackStatus
    route: str
    app_version: str
    viewport_width: int | None
    viewport_height: int | None
    browser_context: str
    submitter: FeedbackSubmitterRead
    has_screenshot: bool
    screenshot_filename: str | None
    screenshot_content_type: str | None
    screenshot_size_bytes: int | None
    admin_notes: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    events: list[FeedbackAdminEventRead] = Field(default_factory=list)


class FeedbackAdminSummary(BaseModel):
    reference: str
    category: FeedbackCategory
    status: FeedbackStatus
    description_preview: str
    submitter: FeedbackSubmitterRead
    has_screenshot: bool
    created_at: datetime


class FeedbackAdminPage(BaseModel):
    items: list[FeedbackAdminSummary]
    total: int
    page: int
    pages: int


class FeedbackAdminUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: FeedbackStatus
    admin_notes: str | None = Field(default=None, max_length=5000)
