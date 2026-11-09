"""Protect advisory, selective, and stale-safe Ticket Progress Reviews."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.ai.base import AIProvider, AIReviewResult
from app.ai.context import WorkContext
from app.ai.progress_review import ProgressReviewContext, ProgressReviewResult, ProgressSuggestion
from app.api.tickets import create_ticket
from app.db.base import Base
from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.subtask import Subtask, SubtaskStatus
from app.schemas.progress_review import ProgressReviewRequest
from app.schemas.ticket import TicketCreate
from app.services.progress_review import ProgressReviewService
from app.services.ticket_activity import list_ticket_activity


class _Provider(AIProvider):
    @property
    def name(self): return "test"
    @property
    def model_name(self): return "test-model"
    def review_ticket(self, context: WorkContext) -> AIReviewResult: raise AssertionError
    def review_ticket_progress(self, context: ProgressReviewContext) -> ProgressReviewResult:
        return ProgressReviewResult("Two items may be complete.", [
            ProgressSuggestion(item.kind, item.item_id, "The update directly supports this item.")
            for item in context.candidates
        ])


def _records(db):
    ticket = create_ticket(TicketCreate(title="Progress review"), db)
    criterion = AcceptanceCriterion(ticket_id=ticket.id, text="Document the result", sort_order=1)
    subtask = Subtask(ticket_id=ticket.id, title="Run validation", sort_order=1)
    db.add_all([criterion, subtask]); db.commit(); db.refresh(criterion); db.refresh(subtask)
    return ticket, criterion, subtask


def test_progress_review_is_advisory_and_selectively_applied():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        ticket, criterion, subtask = _records(db)
        service = ProgressReviewService(_Provider())
        review = service.create(ticket=ticket, request=ProgressReviewRequest(
            evidence_type="ticket_update", evidence_id=3,
            evidence="Documented the result and ran validation.",
        ), db=db)
        db.refresh(criterion); db.refresh(subtask)
        assert criterion.completed is False and subtask.status == SubtaskStatus.TODO
        service.accept(review=review, ticket=ticket,
            keys=[f"acceptance_criterion:{criterion.id}"], db=db,
            actor_type="user", actor_id="1")
        db.refresh(criterion); db.refresh(subtask)
        assert criterion.completed is True and subtask.status == SubtaskStatus.TODO
        events = [x for x in list_ticket_activity(db, ticket_id=ticket.id)
                  if x.event_type == "ai_progress_review_applied"]
        assert len(events) == 1
        assert events[0].new_value["not_selected"] == [f"subtask:{subtask.id}"]
    engine.dispose()


def test_progress_review_revalidates_changed_scope():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        ticket, criterion, _ = _records(db)
        service = ProgressReviewService(_Provider())
        review = service.create(ticket=ticket, request=ProgressReviewRequest(
            evidence_type="drawer_session", evidence="Documented the result."), db=db)
        criterion.deferred = True; db.commit()
        service.accept(review=review, ticket=ticket,
            keys=[f"acceptance_criterion:{criterion.id}"], db=db,
            actor_type="user", actor_id="1")
        db.refresh(criterion)
        assert criterion.completed is False
        assert review.applied_progress["stale"] == [f"acceptance_criterion:{criterion.id}"]
    engine.dispose()
