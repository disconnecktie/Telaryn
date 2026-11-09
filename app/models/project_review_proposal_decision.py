"""Persist user decisions separately from immutable Project Review output."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime


class ProjectReviewProposalDecisionValue(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class ProjectReviewProposalDecision(Base):
    __tablename__ = "project_review_proposal_decisions"
    __table_args__ = (
        UniqueConstraint(
            "review_attempt_id",
            "proposal_index",
            name="uq_project_review_proposal_decision",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    review_attempt_id: Mapped[int] = mapped_column(
        ForeignKey("project_review_attempts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    decided_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    proposal_index: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[ProjectReviewProposalDecisionValue] = mapped_column(String(20), nullable=False)
    edited_changes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    focus_applied_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    focus_previous_ticket_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    application_id: Mapped[int | None] = mapped_column(
        ForeignKey("project_review_applications.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now, nullable=False
    )
