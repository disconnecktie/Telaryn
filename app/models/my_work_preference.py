"""Persist user-specific focus and availability choices without changing ticket state."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from sqlalchemy import Boolean, Date, Enum as SQLEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime


class FocusAvailabilityMode(str, Enum):
    AVAILABLE = "available"
    DATE = "date"
    CONTEXT_CHANGE = "context_change"
    MANUAL = "manual"


class MyWorkPreference(Base):
    __tablename__ = "my_work_preferences"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "workspace_id",
            "ticket_id",
            name="uq_my_work_preference_owner_ticket",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id"), index=True, nullable=False
    )
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    is_current_focus: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    availability_mode: Mapped[FocusAvailabilityMode] = mapped_column(
        SQLEnum(FocusAvailabilityMode),
        default=FocusAvailabilityMode.AVAILABLE,
        nullable=False,
    )
    available_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    context_ticket_updated_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now, nullable=False
    )
