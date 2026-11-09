"""Persist append-only human progress updates associated with a ticket."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime


class TicketUpdateEntry(Base):
    __tablename__ = "ticket_update_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id"),
        index=True,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
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
        back_populates="update_entries",
    )
    attachments: Mapped[list["TicketUpdateAttachment"]] = relationship(
        "TicketUpdateAttachment",
        back_populates="update_entry",
        cascade="all, delete-orphan",
    )
    actor: Mapped["User | None"] = relationship("User")
