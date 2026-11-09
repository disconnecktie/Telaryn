"""Persist advisory AI review requests and their structured proposals."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Enum as SQLEnum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime


class AIReviewStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FAILED = "failed"


class AIReview(Base):
    __tablename__ = "ai_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)

    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id"),
        nullable=False,
    )

    status: Mapped[AIReviewStatus] = mapped_column(
        SQLEnum(AIReviewStatus),
        default=AIReviewStatus.PENDING,
        nullable=False,
    )

    provider: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    suggested_title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    suggested_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    suggested_priority: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    suggested_ticket_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    missing_information: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    suggested_subtasks: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(),
        nullable=True,
    )

    ticket: Mapped["Ticket"] = relationship(
        "Ticket",
        back_populates="ai_reviews",
    )

    reasoning_summary: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
    )

    acceptance_criteria: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    recommendations: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    review_kind: Mapped[str] = mapped_column(
        String(50), default="ticket_review", nullable=False
    )
    source_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    progress_suggestions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    applied_progress: Mapped[dict | None] = mapped_column(JSON, nullable=True)
