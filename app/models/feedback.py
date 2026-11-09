"""Persist private user feedback and administrator review history."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime
from app.models.identifiers import generate_public_id


def generate_feedback_public_id() -> str:
    return generate_public_id("FBK")


class FeedbackSubmission(Base):
    """A user-authored report whose content is visible only to deployment administrators."""

    __tablename__ = "feedback_submissions"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_feedback_submissions_public_id"),
        CheckConstraint("category IN ('problem', 'suggestion', 'other')", name="ck_feedback_category"),
        CheckConstraint("status IN ('new', 'reviewing', 'resolved', 'closed')", name="ck_feedback_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(18), default=generate_feedback_public_id, nullable=False)
    submitted_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    route: Mapped[str] = mapped_column(String(500), nullable=False)
    app_version: Mapped[str] = mapped_column(String(50), nullable=False)
    viewport_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    viewport_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    browser_context: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="new", server_default="new", nullable=False)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    # Closure anchors retention independently from later review-note activity.
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), index=True, nullable=True)
    screenshot_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    screenshot_content_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    screenshot_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    screenshot_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now, nullable=False)

    submitter: Mapped["User"] = relationship("User", foreign_keys=[submitted_by_user_id])
    workspace: Mapped["Workspace"] = relationship("Workspace")
    reviewer: Mapped["User | None"] = relationship("User", foreign_keys=[reviewed_by_user_id])
    admin_events: Mapped[list["FeedbackAdminEvent"]] = relationship(
        "FeedbackAdminEvent", back_populates="feedback", cascade="all, delete-orphan"
    )


class FeedbackAdminEvent(Base):
    """Append-only status history for deployment-administrator review."""

    __tablename__ = "feedback_admin_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    feedback_id: Mapped[int] = mapped_column(ForeignKey("feedback_submissions.id"), index=True, nullable=False)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    previous_status: Mapped[str] = mapped_column(String(20), nullable=False)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    notes_changed: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)

    feedback: Mapped[FeedbackSubmission] = relationship("FeedbackSubmission", back_populates="admin_events")
    actor: Mapped["User"] = relationship("User", foreign_keys=[actor_id])


@event.listens_for(FeedbackAdminEvent, "before_update")
@event.listens_for(FeedbackAdminEvent, "before_delete")
def protect_feedback_admin_event(_mapper, _connection, _target) -> None:
    """Keep feedback review history append-only after it is recorded."""
    raise ValueError("Feedback administrator events are append-only and immutable.")
