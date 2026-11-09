"""Persist append-only ticket status transitions and their required context."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime


class TicketStatusEvent(Base):
    __tablename__ = "ticket_status_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id"),
        index=True,
        nullable=False,
    )
    from_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    to_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
    )

    ticket: Mapped["Ticket"] = relationship(
        "Ticket",
        back_populates="status_events",
    )
    actor: Mapped["User | None"] = relationship("User")
