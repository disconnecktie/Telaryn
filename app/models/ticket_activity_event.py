"""Persist immutable, human-readable audit events for meaningful ticket changes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime


class TicketActivityEvent(Base):
    """An immutable, human-visible record of a meaningful ticket change."""

    __tablename__ = "ticket_activity_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id"),
        index=True,
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_type: Mapped[str] = mapped_column(
        String(30),
        default="local_user",
        nullable=False,
    )
    actor_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    field_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    previous_value: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
    )

    ticket: Mapped["Ticket"] = relationship(
        "Ticket",
        back_populates="activity_events",
    )


@event.listens_for(TicketActivityEvent, "before_update")
@event.listens_for(TicketActivityEvent, "before_delete")
def _prevent_activity_event_mutation(*_args: object) -> None:
    raise ValueError("Ticket activity events are append-only and immutable.")
