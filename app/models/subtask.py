"""Persist executable ticket steps, workflow state, and deferral context."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Enum as SQLEnum, ForeignKey, Integer, String, Text, UniqueConstraint, event, update
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime


class SubtaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"
    DEFERRED = "deferred"


class Subtask(Base):
    __tablename__ = "subtasks"
    __table_args__ = (
        UniqueConstraint("ticket_id", "reference_number", name="uq_subtasks_ticket_reference_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False)
    # Immutable per-Ticket component of TKT-…-ST-001.
    reference_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SubtaskStatus] = mapped_column(SQLEnum(SubtaskStatus), default=SubtaskStatus.TODO, nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    deferred_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    deferred_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="subtasks")


@event.listens_for(Subtask, "before_insert")
def assign_subtask_reference(_mapper, connection, subtask: Subtask) -> None:
    if subtask.reference_number is not None:
        return

    from app.models.ticket import Ticket

    next_number = connection.execute(
        update(Ticket.__table__)
        .where(Ticket.id == subtask.ticket_id)
        .values(next_subtask_number=Ticket.next_subtask_number + 1)
        .returning(Ticket.next_subtask_number)
    ).scalar_one()
    subtask.reference_number = next_number - 1
