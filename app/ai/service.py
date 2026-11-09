"""Coordinate advisory AI reviews and explicit, auditable human acceptance."""

from sqlalchemy.orm import Session

from app.ai.base import AIProvider, AIReviewResult
from app.core.time import utc_now
from app.ai.context import (
    AcceptanceCriterionContext,
    SubtaskContext,
    WorkContext,
)
from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.ai_review import AIReview, AIReviewStatus
from app.models.ticket import Ticket, TicketPriority, TicketType
from app.models.subtask import Subtask, SubtaskStatus
from app.schemas.ai_review import AIReviewAccept
from app.services.ticket_activity import apply_audited_ticket_field
from app.services.ticket_activity import (
    acceptance_criterion_activity_snapshot,
    add_ticket_activity_event,
    subtask_activity_snapshot,
)


class AIReviewService:
    """Coordinate AI proposals while keeping the user in control of persistence."""

    def __init__(self, provider: AIProvider):
        self.provider = provider

    def review_ticket(
        self,
        ticket: Ticket,
        db: Session,
    ) -> AIReview:
        """Record an existing-ticket review and populate its provider proposals."""
        # Persist PENDING first so both successful reviews and provider failures
        # leave an auditable record of the request.
        review = AIReview(
            ticket_id=ticket.id,
            status=AIReviewStatus.PENDING,
            provider=self.provider.name,
            model=self.provider.model_name,
        )

        db.add(review)
        db.commit()
        db.refresh(review)

        try:
            context = WorkContext(
                title=ticket.title,
                description=ticket.description,
                project_name=ticket.project.name if ticket.project else None,
                status=ticket.status.value,
                priority=ticket.priority.value,
                ticket_type=ticket.ticket_type.value,
                subtasks=[
                    SubtaskContext(
                        title=subtask.title,
                        description=subtask.description,
                        status=subtask.status.value,
                        completed=subtask.status == SubtaskStatus.DONE,
                    )
                    for subtask in ticket.subtasks
                ],
                acceptance_criteria=[
                    AcceptanceCriterionContext(
                        text=criterion.text,
                        completed=criterion.completed,
                    )
                    for criterion in ticket.acceptance_criteria
                ],
            )

            result = self.provider.review_ticket(context)

            # Avoid proposing criteria the ticket already records.
            existing_criteria = {
                criterion.text.strip().lower()
                for criterion in context.acceptance_criteria
            }
            result.acceptance_criteria = [
                criterion
                for criterion in result.acceptance_criteria
                if criterion.text.strip().lower() not in existing_criteria
            ]

            review.suggested_title = result.suggested_title
            review.suggested_description = result.suggested_description
            review.suggested_priority = result.suggested_priority
            review.suggested_ticket_type = result.suggested_ticket_type

            review.reasoning_summary = result.reasoning_summary
            review.missing_information = result.missing_information
            review.recommendations = [
                {
                    "text": recommendation.text,
                    "rationale": recommendation.rationale,
                    "basis": recommendation.basis.value,
                }
                for recommendation in result.recommendations
            ]
            review.acceptance_criteria = [
                {"text": criterion.text, "basis": criterion.basis.value}
                for criterion in result.acceptance_criteria
            ]
            review.suggested_subtasks = [
                {
                    "title": subtask.title,
                    "description": subtask.description,
                    "basis": subtask.basis.value,
                }
                for subtask in result.suggested_subtasks
            ]
            review.status = AIReviewStatus.COMPLETED
            review.completed_at = utc_now()

        except Exception:
            review.status = AIReviewStatus.FAILED
            review.completed_at = utc_now()
            db.commit()
            raise

        db.commit()
        db.refresh(review)

        return review

    def review_draft(self, context: WorkContext) -> AIReviewResult:
        """Review unsaved input without creating a ticket or review record."""
        result = self.provider.review_ticket(context)

        result.subtask_revisions = [
            revision
            for revision in result.subtask_revisions
            if 0 <= revision.source_index < len(context.subtasks)
            and revision.suggested_title.strip()
        ]
        result.acceptance_criteria_revisions = [
            revision
            for revision in result.acceptance_criteria_revisions
            if 0 <= revision.source_index < len(context.acceptance_criteria)
            and revision.suggested_text.strip()
        ]

        # A draft can already contain human-authored structure, so only return
        # additions that do not duplicate it.
        existing_subtasks = {
            subtask.title.strip().lower() for subtask in context.subtasks
        }
        result.suggested_subtasks = [
            subtask
            for subtask in result.suggested_subtasks
            if subtask.title.strip().lower()
            not in existing_subtasks
        ]

        existing_criteria = {
            criterion.text.strip().lower()
            for criterion in context.acceptance_criteria
        }
        result.acceptance_criteria = [
            criterion
            for criterion in result.acceptance_criteria
            if criterion.text.strip().lower() not in existing_criteria
        ]

        return result

    def accept_review(
        self,
        review: AIReview,
        ticket: Ticket,
        options: AIReviewAccept,
        db: Session,
        actor_type: str = "local_user",
        actor_id: str | None = None,
    ) -> AIReview:
        """Apply selected proposals and present the atomic acceptance as one update."""
        if review.status != AIReviewStatus.COMPLETED:
            raise ValueError("Only completed AI reviews can be accepted.")

        review_note = f"Accepted from Telaryn AI review #{review.id}."
        grouped_events = []
        ticket_changes = []
        added_subtasks = []
        added_criteria = []

        def apply_reviewed_field(field_name, new_value):
            previous_value = getattr(ticket, field_name)
            event = apply_audited_ticket_field(
                db,
                ticket=ticket,
                field_name=field_name,
                new_value=new_value,
                note=review_note,
                actor_type=actor_type,
                actor_id=actor_id,
            )
            if event is not None:
                grouped_events.append(event)
                ticket_changes.append({
                    "field_name": field_name,
                    "previous_value": previous_value,
                    "new_value": new_value,
                })

        # Nothing from a completed review changes authoritative work by default.
        if options.apply_title and review.suggested_title:
            apply_reviewed_field("title", review.suggested_title)

        if options.apply_description and review.suggested_description:
            apply_reviewed_field("description", review.suggested_description)

        if options.apply_priority and review.suggested_priority:
            apply_reviewed_field(
                "priority", TicketPriority(review.suggested_priority)
            )

        if options.apply_ticket_type and review.suggested_ticket_type:
            apply_reviewed_field(
                "ticket_type", TicketType(review.suggested_ticket_type)
            )

        if options.create_subtasks and review.suggested_subtasks:
            existing_titles = {
                subtask.title.strip().lower() for subtask in ticket.subtasks
            }

            next_sort_order = len(ticket.subtasks) + 1

            for suggestion in review.suggested_subtasks:
                title = suggestion["title"].strip()

                if title.lower() in existing_titles:
                    continue

                subtask = Subtask(
                    ticket_id=ticket.id,
                    title=title,
                    description=suggestion.get("description"),
                    sort_order=next_sort_order,
                )

                db.add(subtask)
                db.flush()
                event = add_ticket_activity_event(
                    db,
                    ticket_id=ticket.id,
                    event_type="subtask_added",
                    new_value=subtask_activity_snapshot(subtask),
                    note=review_note,
                    actor_type=actor_type,
                    actor_id=actor_id,
                )
                grouped_events.append(event)
                added_subtasks.append(subtask_activity_snapshot(subtask))

                existing_titles.add(title.lower())
                next_sort_order += 1

        if options.acceptance_criteria_indices and review.acceptance_criteria:
            existing_criteria = {
                criterion.text.strip().lower()
                for criterion in ticket.acceptance_criteria
            }
            next_criterion_sort_order = len(ticket.acceptance_criteria) + 1

            for index in sorted(set(options.acceptance_criteria_indices)):
                if index < 0 or index >= len(review.acceptance_criteria):
                    continue

                suggestion = review.acceptance_criteria[index]
                text = (
                    suggestion.get("text", "")
                    if isinstance(suggestion, dict)
                    else suggestion
                ).strip()

                if not text or text.lower() in existing_criteria:
                    continue

                criterion = AcceptanceCriterion(
                    ticket_id=ticket.id,
                    text=text,
                    sort_order=next_criterion_sort_order,
                )
                db.add(criterion)
                db.flush()
                event = add_ticket_activity_event(
                    db,
                    ticket_id=ticket.id,
                    event_type="acceptance_criterion_added",
                    new_value=acceptance_criterion_activity_snapshot(criterion),
                    note=review_note,
                    actor_type=actor_type,
                    actor_id=actor_id,
                )
                grouped_events.append(event)
                added_criteria.append(
                    acceptance_criterion_activity_snapshot(criterion)
                )
                existing_criteria.add(text.lower())
                next_criterion_sort_order += 1

        # Retain granular immutable audit events, but group them into one readable
        # timeline entry because the user accepted the review in one operation.
        if grouped_events:
            db.flush()
            add_ticket_activity_event(
                db,
                ticket_id=ticket.id,
                event_type="ai_review_applied",
                new_value={
                    "review_id": review.id,
                    "activity_event_ids": [event.id for event in grouped_events],
                    "ticket_changes": ticket_changes,
                    "acceptance_criteria": added_criteria,
                    "subtasks": added_subtasks,
                },
                note=review_note,
                actor_type=actor_type,
                actor_id=actor_id,
            )

        review.status = AIReviewStatus.ACCEPTED

        db.commit()
        db.refresh(review)
        db.refresh(ticket)

        return review

