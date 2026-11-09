"""Build one authorized Ticket snapshot and render its human-readable PDF."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.time import utc_now
from app.models.ticket import Ticket
from app.models.ticket_activity_event import TicketActivityEvent
from app.models.ticket_status_event import TicketStatusEvent
from app.models.ticket_update_entry import TicketUpdateEntry


SCHEMA_VERSION = "1.0"


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _safe_history_value(value: Any) -> Any:
    """Retain authored history while excluding internal relational identifiers."""
    if isinstance(value, dict):
        return {
            key: _safe_history_value(item)
            for key, item in value.items()
            if key != "id" and not key.endswith("_id") and key != "activity_event_ids"
        }
    if isinstance(value, list):
        return [_safe_history_value(item) for item in value]
    return _enum_value(value)


def _actor_name(record: Any) -> str | None:
    actor = getattr(record, "actor", None)
    return getattr(actor, "display_name", None) if actor is not None else None


def build_ticket_export_snapshot(
    db: Session,
    *,
    ticket_id: int,
    workspace_id: int | None = None,
    project_id: int | None = None,
) -> dict[str, Any]:
    """Return the canonical snapshot, optionally constrained by its owning scope.

    Normal Ticket routes authorize before calling. Composite Project exports
    pass both identifiers to prevent a cross-workspace or reassigned child
    from entering the downloaded snapshot.
    """
    statement = select(Ticket).where(Ticket.id == ticket_id)
    if workspace_id is not None:
        statement = statement.where(Ticket.workspace_id == workspace_id)
    if project_id is not None:
        statement = statement.where(Ticket.project_id == project_id)
    ticket = db.scalar(
        statement.options(
            selectinload(Ticket.project),
            selectinload(Ticket.acceptance_criteria),
            selectinload(Ticket.subtasks),
            selectinload(Ticket.update_entries).selectinload(TicketUpdateEntry.actor),
            selectinload(Ticket.status_events).selectinload(TicketStatusEvent.actor),
            selectinload(Ticket.activity_events),
        )
    )
    if ticket is None:
        raise LookupError("Ticket not found")

    local_reference = f"TKT-{ticket.workspace_ticket_number:03d}"
    project = ticket.project
    project_snapshot = None
    if project is not None:
        project_snapshot = {
            "local_reference": f"PRJ-{project.workspace_project_number:03d}",
            "public_reference": project.public_id,
            "name": project.name,
            "archived": project.archived_at is not None,
        }

    criteria = sorted(ticket.acceptance_criteria, key=lambda item: (item.sort_order, item.id))
    subtasks = sorted(ticket.subtasks, key=lambda item: (item.sort_order, item.id))
    updates = sorted(ticket.update_entries, key=lambda item: (item.created_at, item.id))
    status_events = sorted(ticket.status_events, key=lambda item: (item.created_at, item.id))
    activity_events = sorted(ticket.activity_events, key=lambda item: (item.created_at, item.id))

    return {
        "schema": "atlas.ticket-export",
        "schema_version": SCHEMA_VERSION,
        "exported_at": _iso(utc_now()),
        "ticket": {
            "local_reference": local_reference,
            "public_reference": ticket.public_id,
            "title": ticket.title,
            "description": ticket.description,
            "status": _enum_value(ticket.status),
            "priority": _enum_value(ticket.priority),
            "type": _enum_value(ticket.ticket_type),
            "private": not ticket.ai_context_enabled,
            "created_at": _iso(ticket.created_at),
            "updated_at": _iso(ticket.updated_at),
        },
        "project": project_snapshot,
        "acceptance_criteria": [
            {
                "reference": f"AC-{item.reference_number:03d}",
                "public_reference": f"{ticket.public_id}-AC-{item.reference_number:03d}",
                "text": item.text,
                "completed": item.completed,
                "deferred": item.deferred,
                "deferred_reason": item.deferred_reason,
                "created_at": _iso(item.created_at),
                "updated_at": _iso(item.updated_at),
                "completed_at": _iso(item.completed_at),
                "deferred_at": _iso(item.deferred_at),
            }
            for item in criteria
        ],
        "subtasks": [
            {
                "reference": f"ST-{item.reference_number:03d}",
                "public_reference": f"{ticket.public_id}-ST-{item.reference_number:03d}",
                "title": item.title,
                "description": item.description,
                "status": _enum_value(item.status),
                "deferred_reason": item.deferred_reason,
                "created_at": _iso(item.created_at),
                "updated_at": _iso(item.updated_at),
                "completed_at": _iso(item.completed_at),
                "deferred_at": _iso(item.deferred_at),
            }
            for item in subtasks
        ],
        "updates": [
            {
                "content": item.content,
                "author": _actor_name(item),
                "created_at": _iso(item.created_at),
                "attachment_count": len(item.attachments),
            }
            for item in updates
        ],
        "status_history": [
            {
                "from": _enum_value(item.from_status),
                "to": _enum_value(item.to_status),
                "note": item.note,
                "author": _actor_name(item),
                "created_at": _iso(item.created_at),
            }
            for item in status_events
        ],
        "activity_history": [
            {
                "event_type": item.event_type,
                "field": item.field_name,
                "previous_value": _safe_history_value(item.previous_value),
                "new_value": _safe_history_value(item.new_value),
                "note": item.note,
                "actor_type": item.actor_type,
                "created_at": _iso(item.created_at),
            }
            for item in activity_events
        ],
    }


def ticket_export_filename(snapshot: dict[str, Any], extension: str) -> str:
    reference = snapshot["ticket"]["local_reference"].lower()
    return f"{reference}-export.{extension}"


def _pdf_text(value: Any) -> str:
    if value is None or value == "":
        return "—"
    return escape(str(value)).replace("\n", "<br/>")


def render_ticket_export_pdf(snapshot: dict[str, Any]) -> bytes:
    """Render the canonical snapshot without interpreting authored text as HTML."""
    output = BytesIO()
    ticket = snapshot["ticket"]
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="AtlasTitle", parent=styles["Title"], textColor=colors.HexColor("#17263A"), spaceAfter=5 * mm))
    styles.add(ParagraphStyle(name="AtlasHeading", parent=styles["Heading2"], textColor=colors.HexColor("#264A73"), spaceBefore=5 * mm, spaceAfter=2 * mm))
    styles.add(ParagraphStyle(name="AtlasBody", parent=styles["BodyText"], leading=15, spaceAfter=2 * mm))
    styles.add(ParagraphStyle(name="AtlasSmall", parent=styles["BodyText"], fontSize=8, leading=10, textColor=colors.HexColor("#657286")))
    styles.add(ParagraphStyle(name="AtlasFooter", parent=styles["BodyText"], fontSize=8, alignment=TA_CENTER, textColor=colors.HexColor("#657286")))

    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title=f"{ticket['local_reference']} — {ticket['title']}",
        author="Telaryn",
    )
    story = [
        Paragraph("TELARYN", styles["AtlasSmall"]),
        Paragraph(_pdf_text(ticket["title"]), styles["AtlasTitle"]),
    ]

    metadata = [
        ["Ticket", ticket["local_reference"]],
        ["Public reference", ticket["public_reference"]],
        ["Project", snapshot["project"]["name"] if snapshot["project"] else "Unassigned"],
        ["Status", ticket["status"].replace("_", " ").title()],
        ["Priority", ticket["priority"].title()],
        ["Type", ticket["type"].title()],
        ["Privacy", "Private" if ticket["private"] else "Standard workspace access"],
        ["Exported", snapshot["exported_at"]],
    ]
    table = Table(metadata, colWidths=[38 * mm, 120 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#526174")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#D3DBE5")),
    ]))
    story.extend([table, Paragraph("Description", styles["AtlasHeading"]), Paragraph(_pdf_text(ticket["description"]), styles["AtlasBody"])])

    def add_collection(title: str, items: list[dict[str, Any]], render_item) -> None:
        story.append(Paragraph(title, styles["AtlasHeading"]))
        if not items:
            story.append(Paragraph("None", styles["AtlasBody"]))
            return
        for item in items:
            story.append(KeepTogether(render_item(item)))

    add_collection(
        "Acceptance Criteria",
        snapshot["acceptance_criteria"],
        lambda item: [
            Paragraph(f"<b>{_pdf_text(item['reference'])}</b> — {'Deferred' if item['deferred'] else ('Complete' if item['completed'] else 'Open')}", styles["AtlasSmall"]),
            Paragraph(_pdf_text(item["text"]), styles["AtlasBody"]),
        ],
    )
    add_collection(
        "Subtasks",
        snapshot["subtasks"],
        lambda item: [
            Paragraph(f"<b>{_pdf_text(item['reference'])}</b> — {_pdf_text(item['status'].replace('_', ' ').title())}", styles["AtlasSmall"]),
            Paragraph(f"<b>{_pdf_text(item['title'])}</b>", styles["AtlasBody"]),
            Paragraph(_pdf_text(item["description"]), styles["AtlasBody"]),
        ],
    )
    add_collection(
        "Updates",
        snapshot["updates"],
        lambda item: [
            Paragraph(f"{_pdf_text(item['created_at'])} · {_pdf_text(item['author'] or 'Telaryn user')}", styles["AtlasSmall"]),
            Paragraph(_pdf_text(item["content"]), styles["AtlasBody"]),
        ],
    )
    add_collection(
        "Status History",
        snapshot["status_history"],
        lambda item: [
            Paragraph(f"{_pdf_text(item['created_at'])} · {_pdf_text(item['from'])} → {_pdf_text(item['to'])}", styles["AtlasSmall"]),
            Paragraph(_pdf_text(item["note"]), styles["AtlasBody"]),
        ],
    )

    def page_footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#657286"))
        canvas.drawCentredString(A4[0] / 2, 9 * mm, f"Telaryn · {ticket['local_reference']} · Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    return output.getvalue()

