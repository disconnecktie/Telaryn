"""Persist privacy-safe Project Review attempt history and snapshot reuse metadata."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime


class ProjectReviewAttemptStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    INVALID = "invalid"


class ProjectReviewAttempt(Base):
    __tablename__ = "project_review_attempts"
    __table_args__ = (
        Index(
            "ix_project_review_success_lookup",
            "workspace_id",
            "project_id",
            "requested_by_user_id",
            "snapshot_version",
            "status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    requested_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    snapshot_version: Mapped[str] = mapped_column(String(64), nullable=False)
    review_reference: Mapped[str | None] = mapped_column(String(16), nullable=True)
    snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Local-only metadata: never included in the provider snapshot or prompt.
    excluded_private_tickets: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    successful_snapshot_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[ProjectReviewAttemptStatus] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    context_window_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_safety_margin: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_encoding: Mapped[str | None] = mapped_column(String(100), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    safe_error_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
