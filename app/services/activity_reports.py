"""Select authorized report evidence and keep privacy boundaries server-owned."""

from datetime import date, datetime, time, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.ticket import Ticket
from app.models.ticket_status_event import TicketStatusEvent
from app.models.ticket_update_entry import TicketUpdateEntry
from app.schemas.activity_report import (
    ActivityReportProjectEvidence,
    ActivityReportProjectOption,
    ActivityReportRequest,
    ActivityReportSnapshot,
    ActivityReportTicketEvidence,
)


def report_dates(
    period: str,
    period_start: date | None,
    period_end: date | None,
) -> tuple[date, date]:
    end = period_end or date.today()
    if period_start is not None:
        return period_start, end
    if period == "weekly":
        return end - timedelta(days=6), end
    if period == "monthly":
        return end.replace(day=1), end
    if period == "quarterly":
        quarter_month = ((end.month - 1) // 3) * 3 + 1
        return end.replace(month=quarter_month, day=1), end
    # One inclusive rolling year, ending on the selected Through date. Moving
    # forward one day before changing the year also handles February 29 safely.
    return (end + timedelta(days=1)).replace(year=end.year - 1), end


def list_report_projects(db: Session, workspace_id: int) -> list[ActivityReportProjectOption]:
    projects = db.scalars(
        select(Project)
        .where(Project.workspace_id == workspace_id, Project.ai_context_enabled.is_(True))
        .order_by(Project.archived_at.is_not(None), Project.name)
    ).all()
    return [
        ActivityReportProjectOption(
            id=project.id,
            name=project.name,
            life_context=project.life_context,
            archived=project.archived_at is not None,
            archive_reason=project.archive_reason,
            included_by_default=(
                project.archived_at is None
                or project.archive_report_eligible_by_default
            ),
        )
        for project in projects
    ]


def build_report_snapshot(
    request: ActivityReportRequest,
    *,
    workspace_id: int,
    subject_first_name: str,
    db: Session,
) -> ActivityReportSnapshot:
    period_start, period_end = report_dates(
        request.period,
        request.period_start,
        request.period_end,
    )
    start_instant = datetime.combine(period_start, time.min, tzinfo=timezone.utc)
    end_instant = datetime.combine(period_end + timedelta(days=1), time.min, tzinfo=timezone.utc)
    options = list_report_projects(db, workspace_id)
    option_by_id = {option.id: option for option in options}
    if request.project_ids:
        missing = set(request.project_ids) - option_by_id.keys()
        if missing:
            # Foreign, missing, or Private Projects share one non-disclosing response.
            raise HTTPException(status_code=404, detail="One or more Projects are unavailable for reporting.")
        selected_ids = request.project_ids
    else:
        selected_ids = [
            option.id
            for option in options
            if option.included_by_default
            and (request.scope == "all" or option.life_context == request.scope)
        ]
    if not selected_ids:
        raise HTTPException(status_code=422, detail="Choose at least one eligible Project with reportable activity.")

    projects = db.scalars(select(Project).where(Project.id.in_(selected_ids))).all()
    evidence: list[ActivityReportProjectEvidence] = []
    for project in projects:
        tickets = db.scalars(
            select(Ticket).where(
                Ticket.workspace_id == workspace_id,
                Ticket.project_id == project.id,
                Ticket.ai_context_enabled.is_(True),
            )
        ).all()
        ticket_evidence: list[ActivityReportTicketEvidence] = []
        for ticket in tickets:
            updates = db.scalars(
                select(TicketUpdateEntry.content).where(
                    TicketUpdateEntry.ticket_id == ticket.id,
                    TicketUpdateEntry.created_at >= start_instant,
                    TicketUpdateEntry.created_at < end_instant,
                ).order_by(TicketUpdateEntry.created_at)
            ).all()
            status_notes = db.scalars(
                select(TicketStatusEvent.note).where(
                    TicketStatusEvent.ticket_id == ticket.id,
                    TicketStatusEvent.created_at >= start_instant,
                    TicketStatusEvent.created_at < end_instant,
                    TicketStatusEvent.note.is_not(None),
                ).order_by(TicketStatusEvent.created_at)
            ).all()
            changed_in_period = period_start <= ticket.updated_at.date() <= period_end
            if not updates and not status_notes and not changed_in_period:
                continue
            ticket_evidence.append(ActivityReportTicketEvidence(
                reference=f"TKT-{ticket.workspace_ticket_number:03d}",
                title=ticket.title,
                status=ticket.status.value,
                updates=list(updates),
                status_notes=[note for note in status_notes if note],
            ))
        if ticket_evidence:
            evidence.append(ActivityReportProjectEvidence(
                id=project.id,
                name=project.name,
                life_context=project.life_context,
                purpose=project.purpose,
                why_it_matters=project.why_it_matters,
                tickets=ticket_evidence,
            ))
    if not evidence:
        raise HTTPException(status_code=422, detail="The selected Projects have no reportable activity in this period.")
    return ActivityReportSnapshot(
        subject_first_name=subject_first_name,
        period=request.period,
        output_format=request.output_format,
        period_start=period_start,
        period_end=period_end,
        style_example=request.style_example,
        projects=evidence,
    )
