"""Persist durable, user-scoped Work Intake operations."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime


class WorkIntakeAttemptStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    INVALID = "invalid"
    CANCELLED = "cancelled"


class WorkIntakeAttempt(Base):
    __tablename__ = "work_intake_attempts"
    __table_args__ = (
        Index(
            "ix_work_intake_owner_current",
            "workspace_id",
            "requested_by_user_id",
            "dismissed_at",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id"), index=True, nullable=False
    )
    requested_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[WorkIntakeAttemptStatus] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    safe_error_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    @property
    def clarification_answers(self) -> list[str]:
        return (self.snapshot or {}).get("clarification_answers", [])

    @property
    def refinement_count(self) -> int:
        return (self.snapshot or {}).get("refinement_count", 0)
