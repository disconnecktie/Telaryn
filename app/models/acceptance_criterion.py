"""Persist ticket definitions of done, including completion and deferral context."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, Text, UniqueConstraint, event, update
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime


class AcceptanceCriterion(Base):
    __tablename__ = "acceptance_criteria"
    __table_args__ = (
        UniqueConstraint("ticket_id", "reference_number", name="uq_acceptance_criteria_ticket_reference_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False)
    # Immutable per-Ticket component of TKT-…-AC-001.
    reference_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    deferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deferred_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    deferred_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="acceptance_criteria")


@event.listens_for(AcceptanceCriterion, "before_insert")
def assign_acceptance_criterion_reference(_mapper, connection, criterion: AcceptanceCriterion) -> None:
    if criterion.reference_number is not None:
        return

    from app.models.ticket import Ticket

    next_number = connection.execute(
        update(Ticket.__table__)
        .where(Ticket.id == criterion.ticket_id)
        .values(next_acceptance_criterion_number=Ticket.next_acceptance_criterion_number + 1)
        .returning(Ticket.next_acceptance_criterion_number)
    ).scalar_one()
    criterion.reference_number = next_number - 1
