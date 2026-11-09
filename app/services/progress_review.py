"""Persist, revalidate, and selectively apply advisory progress suggestions."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.progress_review import ProgressCandidate, ProgressReviewContext
from app.core.time import utc_now
from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.ai_review import AIReview, AIReviewStatus
from app.models.subtask import Subtask, SubtaskStatus
from app.models.ticket import Ticket
from app.schemas.progress_review import ProgressReviewRequest
from app.services.ticket_activity import add_ticket_activity_event


def _candidate(kind, item, text):
    return ProgressCandidate(kind, item.id, item.reference_number, text, item.updated_at.isoformat())


def serialize_progress_review(review: AIReview) -> dict:
    return {
        "id": review.id, "ticket_id": review.ticket_id, "status": review.status,
        "provider": review.provider, "model": review.model,
        "summary": review.reasoning_summary, "source_evidence": review.source_evidence,
        "suggestions": review.progress_suggestions or [],
        "applied_progress": review.applied_progress,
        "created_at": review.created_at, "completed_at": review.completed_at,
    }


class ProgressReviewService:
    def __init__(self, provider: AIProvider): self.provider = provider

    def create(self, *, ticket: Ticket, request: ProgressReviewRequest, db: Session) -> AIReview:
        criteria = db.scalars(select(AcceptanceCriterion).where(
            AcceptanceCriterion.ticket_id == ticket.id,
            AcceptanceCriterion.completed.is_(False),
            AcceptanceCriterion.deferred.is_(False),
        )).all()
        subtasks = db.scalars(select(Subtask).where(
            Subtask.ticket_id == ticket.id,
            Subtask.status.in_([SubtaskStatus.TODO, SubtaskStatus.IN_PROGRESS]),
        )).all()
        candidates = [_candidate("acceptance_criterion", x, x.text) for x in criteria]
        candidates += [_candidate("subtask", x, x.title) for x in subtasks]
        review = AIReview(
            ticket_id=ticket.id, status=AIReviewStatus.PENDING,
            provider=self.provider.name, model=self.provider.model_name,
            review_kind="progress_review",
            source_evidence=request.model_dump(),
        )
        db.add(review); db.flush()
        try:
            result = self.provider.review_ticket_progress(ProgressReviewContext(
                evidence=request.evidence, evidence_type=request.evidence_type,
                evidence_id=request.evidence_id, candidates=candidates,
            ))
            by_key = {(x.kind, x.item_id): x for x in candidates}
            suggestions = []
            for suggestion in result.suggestions[:5]:
                candidate = by_key.get((suggestion.kind, suggestion.item_id))
                if not candidate: continue
                suggestions.append({
                    "key": f"{candidate.kind}:{candidate.item_id}",
                    "kind": candidate.kind, "item_id": candidate.item_id,
                    "reference_number": candidate.reference_number, "text": candidate.text,
                    "rationale": suggestion.rationale,
                    "updated_at": candidate.updated_at, "state": "available",
                })
            review.reasoning_summary = result.summary
            review.progress_suggestions = suggestions
            review.status = AIReviewStatus.COMPLETED
            review.completed_at = utc_now()
            db.commit(); db.refresh(review); return review
        except Exception:
            review.status = AIReviewStatus.FAILED; review.completed_at = utc_now()
            db.commit(); raise

    def accept(self, *, review: AIReview, ticket: Ticket, keys: list[str], db: Session,
               actor_type: str, actor_id: str | None) -> AIReview:
        if review.review_kind != "progress_review" or review.status != AIReviewStatus.COMPLETED:
            raise ValueError("This progress review is no longer available.")
        selected = set(keys)
        known = {x["key"] for x in review.progress_suggestions or []}
        if not selected <= known: raise ValueError("An unknown progress suggestion was selected.")
        applied, stale = [], []
        for suggestion in review.progress_suggestions or []:
            if suggestion["key"] not in selected: continue
            model = AcceptanceCriterion if suggestion["kind"] == "acceptance_criterion" else Subtask
            item = db.get(model, suggestion["item_id"])
            valid = item is not None and item.ticket_id == ticket.id and item.updated_at.isoformat() == suggestion["updated_at"]
            if valid and suggestion["kind"] == "acceptance_criterion":
                valid = not item.completed and not item.deferred
            elif valid:
                valid = item.status in {SubtaskStatus.TODO, SubtaskStatus.IN_PROGRESS}
            if not valid:
                suggestion["state"] = "stale"; stale.append(suggestion["key"]); continue
            if suggestion["kind"] == "acceptance_criterion": item.completed = True
            else: item.status = SubtaskStatus.DONE
            item.completed_at = utc_now(); suggestion["state"] = "applied"; applied.append(suggestion["key"])
        review.progress_suggestions = list(review.progress_suggestions or [])
        review.applied_progress = {"applied": applied, "stale": stale, "not_selected": sorted(known-selected)}
        review.status = AIReviewStatus.ACCEPTED
        add_ticket_activity_event(db, ticket_id=ticket.id, event_type="ai_progress_review_applied",
            new_value={"review_id": review.id, **review.applied_progress},
            actor_type=actor_type, actor_id=actor_id)
        db.commit(); db.refresh(review); return review

    def reject(self, *, review: AIReview, db: Session) -> AIReview:
        if review.review_kind != "progress_review" or review.status != AIReviewStatus.COMPLETED:
            raise ValueError("This progress review is no longer available.")
        review.status = AIReviewStatus.REJECTED; db.commit(); db.refresh(review); return review
