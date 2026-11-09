"""Verify accepted AI suggestions appear as one grouped, auditable activity item."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - registers every model with Base metadata
from app.ai.base import (
    AIProvider,
    AIRecommendation,
    AIReviewResult,
    AISuggestedAcceptanceCriterion,
    AISuggestedSubtask,
)
from app.ai.context import WorkContext
from app.ai.provenance import SuggestionBasis
from app.ai.service import AIReviewService
from app.api.tickets import create_ticket
from app.db.base import Base
from app.models.ai_review import AIReview, AIReviewStatus
from app.models.ticket_activity_event import TicketActivityEvent
from app.schemas.ai_review import AIReviewAccept
from app.schemas.ticket import TicketCreate
from app.services.ticket_activity import list_ticket_activity


class _UnusedProvider(AIProvider):
    @property
    def name(self) -> str:
        return "unused"

    @property
    def model_name(self) -> str:
        return "unused"

    def review_ticket(self, context: WorkContext) -> AIReviewResult:
        raise AssertionError("The acceptance test should not request another review.")


class _ProvenanceProvider(_UnusedProvider):
    def review_ticket(self, context: WorkContext) -> AIReviewResult:
        return AIReviewResult(
            recommendations=[
                AIRecommendation(
                    text="Consider a rollback note.",
                    rationale="It may improve recovery guidance.",
                    basis=SuggestionBasis.RECOMMENDED,
                )
            ],
            acceptance_criteria=[
                AISuggestedAcceptanceCriterion(
                    text="The recorded outcome is verified.",
                    basis=SuggestionBasis.INFERRED,
                )
            ],
            suggested_subtasks=[
                AISuggestedSubtask(
                    title="Verify the recorded outcome",
                    description=None,
                    basis=SuggestionBasis.SUPPORTED,
                )
            ],
        )


def test_review_persists_provider_neutral_suggestion_basis():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        ticket = create_ticket(TicketCreate(title="Review provenance"), db)
        review = AIReviewService(_ProvenanceProvider()).review_ticket(ticket, db)

        assert review.recommendations[0]["basis"] == "recommended"
        assert review.acceptance_criteria[0] == {
            "text": "The recorded outcome is verified.",
            "basis": "inferred",
        }
        assert review.suggested_subtasks[0]["basis"] == "supported"

    engine.dispose()


def test_accepting_multiple_ai_suggestions_creates_one_timeline_item():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        ticket = create_ticket(TicketCreate(title="Review activity"), db)
        review = AIReview(
            ticket_id=ticket.id,
            status=AIReviewStatus.COMPLETED,
            provider="test",
            model="test",
            acceptance_criteria=["First outcome", "Second outcome"],
            suggested_subtasks=[],
        )
        db.add(review)
        db.commit()
        db.refresh(review)

        AIReviewService(_UnusedProvider()).accept_review(
            review=review,
            ticket=ticket,
            options=AIReviewAccept(
                apply_title=False,
                apply_description=False,
                apply_priority=False,
                apply_ticket_type=False,
                create_subtasks=False,
                acceptance_criteria_indices=[0, 1],
            ),
            db=db,
        )

        timeline = list_ticket_activity(db, ticket_id=ticket.id)
        review_items = [
            item for item in timeline if item.event_type == "ai_review_applied"
        ]
        criterion_items = [
            item
            for item in timeline
            if item.event_type == "acceptance_criterion_added"
        ]

        assert len(review_items) == 1
        assert criterion_items == []
        assert [
            value["text"]
            for value in review_items[0].new_value["acceptance_criteria"]
        ] == ["First outcome", "Second outcome"]
        assert review_items[0].note == f"Accepted from Telaryn AI review #{review.id}."

        # Granular records remain stored for audit integrity even though the
        # user-facing timeline presents the atomic acceptance once.
        stored_criterion_events = db.scalars(
            select(TicketActivityEvent).where(
                TicketActivityEvent.ticket_id == ticket.id,
                TicketActivityEvent.event_type == "acceptance_criterion_added",
            )
        ).all()
        assert len(stored_criterion_events) == 2

    engine.dispose()

