"""Preview and atomically apply approved Project Review candidates."""

from collections import defaultdict
from datetime import date
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.project_review import ProjectReviewProposalType, ProjectReviewResult
from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.project_review_application import ProjectReviewApplication
from app.models.project_review_proposal_decision import ProjectReviewProposalDecision, ProjectReviewProposalDecisionValue
from app.models.subtask import Subtask
from app.models.ticket import Ticket, TicketPriority, TicketType
from app.schemas.project_review_application import ProjectReviewApplicationItem, ProjectReviewApplicationPreview, ProjectReviewApplicationRead
from app.services.project_review_proposal_decisions import _validate_candidate
from app.services.ticket_activity import add_ticket_activity_event


def _json_value(value):
    return value.isoformat() if isinstance(value, date) else value


def _approved_items(db, attempt):
    result = ProjectReviewResult.model_validate(attempt.result)
    rows = db.scalars(select(ProjectReviewProposalDecision).where(
        ProjectReviewProposalDecision.review_attempt_id == attempt.id,
        ProjectReviewProposalDecision.decision == ProjectReviewProposalDecisionValue.APPROVED,
        ProjectReviewProposalDecision.application_id.is_(None),
    )).all()
    by_index = {row.proposal_index: row for row in rows}
    items, applicable_rows = [], []
    for index, proposal in enumerate(result.proposals):
        row = by_index.get(index)
        if row is None or proposal.proposal_type == ProjectReviewProposalType.RECOMMEND_CURRENT_FOCUS:
            continue
        candidate = proposal.proposed_changes.model_validate(
            row.edited_changes or proposal.proposed_changes.model_dump(mode="json")
        )
        _validate_candidate(proposal, candidate)
        items.append(ProjectReviewApplicationItem(
            proposal_index=index, proposal_type=proposal.proposal_type.value,
            summary=proposal.summary, target_project_id=proposal.target_project_id,
            target_ticket_id=proposal.target_ticket_id,
            candidate_changes=candidate.model_dump(mode="json"),
        ))
        applicable_rows.append(row)
    return items, applicable_rows


def _conflicts(items):
    owners, conflicts = {}, []
    scalar = {"title", "description", "priority", "ticket_type", "project_description",
              "project_purpose", "project_why_it_matters", "project_target_date"}
    for item in items:
        kind = "ticket" if item.target_ticket_id is not None else "project"
        target = item.target_ticket_id or item.target_project_id
        for field, value in item.candidate_changes.items():
            if field not in scalar or value is None:
                continue
            key = (kind, target, field)
            if key in owners:
                conflicts.append(
                    f"Proposals {owners[key] + 1} and {item.proposal_index + 1} both change "
                    f"{kind} {target} field {field.replace('_', ' ')}."
                )
            else:
                owners[key] = item.proposal_index
    return conflicts


def preview_application(db, *, attempt):
    items, _ = _approved_items(db, attempt)
    conflicts = _conflicts(items)
    return ProjectReviewApplicationPreview(
        review_id=attempt.id, items=items, conflicts=conflicts,
        can_apply=bool(items) and not conflicts,
    )


def _ticket(db, ticket_id, workspace_id, project_id):
    ticket = db.scalar(select(Ticket).where(
        Ticket.id == ticket_id, Ticket.workspace_id == workspace_id,
        Ticket.project_id == project_id,
    ))
    if ticket is None:
        raise HTTPException(status_code=409, detail="Target Ticket is no longer available.")
    return ticket


def _reject_duplicates(ticket, field, values):
    existing = ({item.text.strip().casefold() for item in ticket.acceptance_criteria}
                if field == "acceptance_criteria"
                else {item.title.strip().casefold() for item in ticket.subtasks})
    normalized = [value.strip().casefold() for value in values]
    if len(normalized) != len(set(normalized)) or existing.intersection(normalized):
        label = "Acceptance Criterion" if field == "acceptance_criteria" else "Subtask"
        raise HTTPException(status_code=409, detail=f"An approved proposal would create a duplicate {label}.")


def apply_approved_proposals(db: Session, *, attempt, project, workspace_id, user_id, actor_type, actor_id):
    items, rows = _approved_items(db, attempt)
    if not items:
        raise HTTPException(status_code=409, detail="No approved, unapplied proposals are ready.")
    if _conflicts(items):
        raise HTTPException(status_code=409, detail="Resolve conflicting approved proposals before applying.")

    tickets = {}
    for item in items:
        if item.target_ticket_id is not None:
            tickets[item.target_ticket_id] = _ticket(db, item.target_ticket_id, workspace_id, project.id)
        if item.proposal_type in {"add_acceptance_criteria", "add_subtasks"}:
            field = "acceptance_criteria" if item.proposal_type == "add_acceptance_criteria" else "subtasks"
            _reject_duplicates(tickets[item.target_ticket_id], field, item.candidate_changes[field])

    application = ProjectReviewApplication(
        review_attempt_id=attempt.id, workspace_id=workspace_id, project_id=project.id,
        applied_by_user_id=user_id, proposal_indexes=[item.proposal_index for item in items],
        resulting_changes=[],
    )
    db.add(application)
    db.flush()
    resulting, ticket_changes = [], defaultdict(list)

    for item in items:
        changes, kind = item.candidate_changes, item.proposal_type
        result = {"proposal_index": item.proposal_index, "proposal_type": kind}
        if kind == "create_ticket":
            ticket = Ticket(
                workspace_id=workspace_id, project_id=project.id, title=changes["title"],
                description=changes.get("description"),
                priority=TicketPriority(changes.get("priority") or "medium"),
                ticket_type=TicketType(changes.get("ticket_type") or "task"),
            )
            db.add(ticket)
            db.flush()
            criteria = [AcceptanceCriterion(ticket_id=ticket.id, text=text, sort_order=i)
                        for i, text in enumerate(changes.get("acceptance_criteria", []), 1)]
            subtasks = [Subtask(ticket_id=ticket.id, title=title, sort_order=i)
                        for i, title in enumerate(changes.get("subtasks", []), 1)]
            db.add_all([*criteria, *subtasks])
            db.flush()
            result.update(ticket_id=ticket.id, created=changes)
            ticket_changes[ticket.id].append(result)
        elif kind == "update_project_context":
            mapping = {"project_description": "description", "project_purpose": "purpose",
                       "project_why_it_matters": "why_it_matters", "project_target_date": "target_date"}
            applied = {}
            for source, target in mapping.items():
                if changes.get(source) is not None:
                    value = (
                        date.fromisoformat(changes[source])
                        if source == "project_target_date" and isinstance(changes[source], str)
                        else changes[source]
                    )
                    applied[target] = {
                        "before": _json_value(getattr(project, target)),
                        "after": _json_value(value),
                    }
                    setattr(project, target, value)
            result["fields"] = applied
        else:
            ticket, applied = tickets[item.target_ticket_id], {}
            if kind == "edit_ticket":
                for field in ("title", "description"):
                    if changes.get(field) is not None:
                        applied[field] = {"before": getattr(ticket, field), "after": changes[field]}
                        setattr(ticket, field, changes[field])
            elif kind == "change_ticket_priority":
                applied["priority"] = {"before": ticket.priority.value, "after": changes["priority"]}
                ticket.priority = TicketPriority(changes["priority"])
            elif kind == "add_acceptance_criteria":
                added = [AcceptanceCriterion(ticket_id=ticket.id, text=text,
                         sort_order=len(ticket.acceptance_criteria) + i)
                         for i, text in enumerate(changes["acceptance_criteria"], 1)]
                db.add_all(added); db.flush()
                applied["acceptance_criteria"] = [{"id": x.id, "text": x.text} for x in added]
            elif kind == "add_subtasks":
                added = [Subtask(ticket_id=ticket.id, title=title,
                         sort_order=len(ticket.subtasks) + i)
                         for i, title in enumerate(changes["subtasks"], 1)]
                db.add_all(added); db.flush()
                applied["subtasks"] = [{"id": x.id, "title": x.title} for x in added]
            result.update(ticket_id=ticket.id, fields=applied)
            ticket_changes[ticket.id].append(result)
        resulting.append(result)

    for ticket_id, changes in ticket_changes.items():
        add_ticket_activity_event(
            db, ticket_id=ticket_id, event_type="project_review_applied",
            field_name="project_review",
            new_value={"review_id": attempt.id, "application_id": application.id, "changes": changes},
            note="Applied approved Telaryn Project Review proposals.",
            actor_type=actor_type, actor_id=actor_id,
        )
    application.resulting_changes = resulting
    for row in rows:
        row.application_id = application.id
    db.commit()
    db.refresh(application)
    return ProjectReviewApplicationRead(
        id=application.id, review_id=attempt.id,
        proposal_indexes=application.proposal_indexes,
        resulting_changes=application.resulting_changes, applied_at=application.applied_at,
    )

