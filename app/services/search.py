"""Search authorized workspace work without invoking an AI provider."""

from __future__ import annotations

import re
from collections.abc import Iterable

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.project import Project
from app.models.subtask import Subtask, SubtaskStatus
from app.models.ticket import Ticket, TicketStatus
from app.schemas.search import SearchRead, SearchResourceType, SearchResult


RESOURCE_ORDER = {
    SearchResourceType.PROJECT: 0,
    SearchResourceType.TICKET: 1,
    SearchResourceType.ACCEPTANCE_CRITERION: 2,
    SearchResourceType.SUBTASK: 3,
}

def _project_reference(project: Project) -> str:
    return f"PRJ-{project.workspace_project_number:03d}"


def _ticket_reference(ticket: Ticket) -> str:
    return f"TKT-{ticket.workspace_ticket_number:03d}"


def _criterion_reference(item: AcceptanceCriterion) -> str:
    return f"{_ticket_reference(item.ticket)}-AC-{item.reference_number:03d}"


def _subtask_reference(item: Subtask) -> str:
    return f"{_ticket_reference(item.ticket)}-ST-{item.reference_number:03d}"


def _contains(column, query: str):
    return column.icontains(query, autoescape=True)


def _first_match(
    query: str,
    fields: Iterable[tuple[str, str | None]],
) -> tuple[int, str, str]:
    normalized = query.casefold()
    matches: list[tuple[int, int, str, str]] = []
    for position, (label, value) in enumerate(fields):
        if value is None:
            continue
        folded = value.casefold()
        index = folded.find(normalized)
        if index < 0:
            continue
        if folded == normalized:
            score = 0
        elif folded.startswith(normalized):
            score = 1
        else:
            score = 2
        matches.append((score, position, label, _excerpt(value, index, len(query))))
    if not matches:
        raise ValueError("Search candidate did not contain the query")
    score, _position, label, excerpt = min(matches)
    return score, label, excerpt


def _excerpt(value: str, index: int, query_length: int, limit: int = 180) -> str:
    compact = " ".join(value.split())
    compact_index = compact.casefold().find(value[index:index + query_length].casefold())
    if compact_index < 0:
        compact_index = compact.casefold().find(value[index:index + query_length].strip().casefold())
    if len(compact) <= limit:
        return compact
    start = max(0, compact_index - 65)
    end = min(len(compact), start + limit)
    if end == len(compact):
        start = max(0, end - limit)
    excerpt = compact[start:end].strip()
    return f"{'…' if start else ''}{excerpt}{'…' if end < len(compact) else ''}"


def _ticket_allowed(
    ticket: Ticket,
    *,
    include_completed: bool,
    include_cancelled: bool,
    include_archived: bool,
    statuses: set[TicketStatus] | None,
) -> bool:
    if statuses is not None and ticket.status not in statuses:
        return False
    if ticket.status == TicketStatus.DONE and not include_completed:
        return False
    if ticket.status == TicketStatus.CANCELLED and not include_cancelled:
        return False
    if ticket.project is not None and ticket.project.archived_at is not None and not include_archived:
        return False
    return True


def _ticket_private(ticket: Ticket) -> bool:
    return (
        not ticket.ai_context_enabled
        or (ticket.project is not None and not ticket.project.ai_context_enabled)
    )


def _project_result(project: Project, query: str) -> tuple[int, SearchResult]:
    reference = _project_reference(project)
    score, field, excerpt = _first_match(query, (
        ("Project reference", reference),
        ("Project public reference", project.public_id),
        ("Project name", project.name),
        ("Project description", project.description),
        ("Project purpose", project.purpose),
        ("Why it matters", project.why_it_matters),
    ))
    return score, SearchResult(
        resource_type=SearchResourceType.PROJECT,
        id=project.id,
        reference=reference,
        public_id=project.public_id,
        title=project.name,
        matched_field=field,
        excerpt=excerpt,
        project_id=project.id,
        project_reference=reference,
        project_name=project.name,
        archived=project.archived_at is not None,
        private=not project.ai_context_enabled,
    )


def _ticket_result(ticket: Ticket, query: str) -> tuple[int, SearchResult]:
    reference = _ticket_reference(ticket)
    score, field, excerpt = _first_match(query, (
        ("Ticket reference", reference),
        ("Ticket public reference", ticket.public_id),
        ("Ticket title", ticket.title),
        ("Ticket description", ticket.description),
    ))
    project_reference = _project_reference(ticket.project) if ticket.project else None
    return score, SearchResult(
        resource_type=SearchResourceType.TICKET,
        id=ticket.id,
        reference=reference,
        public_id=ticket.public_id,
        title=ticket.title,
        matched_field=field,
        excerpt=excerpt,
        project_id=ticket.project_id,
        project_reference=project_reference,
        project_name=ticket.project.name if ticket.project else None,
        ticket_id=ticket.id,
        ticket_reference=reference,
        ticket_title=ticket.title,
        status=ticket.status.value,
        archived=bool(ticket.project and ticket.project.archived_at),
        private=_ticket_private(ticket),
    )


def _criterion_result(item: AcceptanceCriterion, query: str) -> tuple[int, SearchResult]:
    ticket = item.ticket
    reference = _criterion_reference(item)
    public_id = f"{ticket.public_id}-AC-{item.reference_number:03d}"
    score, field, excerpt = _first_match(query, (
        ("Acceptance Criterion reference", reference),
        ("Acceptance Criterion public reference", public_id),
        ("Acceptance Criterion", item.text),
    ))
    project_reference = _project_reference(ticket.project) if ticket.project else None
    return score, SearchResult(
        resource_type=SearchResourceType.ACCEPTANCE_CRITERION,
        id=item.id,
        reference=reference,
        public_id=public_id,
        title=item.text,
        matched_field=field,
        excerpt=excerpt,
        project_id=ticket.project_id,
        project_reference=project_reference,
        project_name=ticket.project.name if ticket.project else None,
        ticket_id=ticket.id,
        ticket_reference=_ticket_reference(ticket),
        ticket_title=ticket.title,
        status="completed" if item.completed else "open",
        archived=bool(ticket.project and ticket.project.archived_at),
        private=_ticket_private(ticket),
        deferred=item.deferred,
    )


def _subtask_result(item: Subtask, query: str) -> tuple[int, SearchResult]:
    ticket = item.ticket
    reference = _subtask_reference(item)
    public_id = f"{ticket.public_id}-ST-{item.reference_number:03d}"
    score, field, excerpt = _first_match(query, (
        ("Subtask reference", reference),
        ("Subtask public reference", public_id),
        ("Subtask title", item.title),
        ("Subtask description", item.description),
    ))
    project_reference = _project_reference(ticket.project) if ticket.project else None
    return score, SearchResult(
        resource_type=SearchResourceType.SUBTASK,
        id=item.id,
        reference=reference,
        public_id=public_id,
        title=item.title,
        matched_field=field,
        excerpt=excerpt,
        project_id=ticket.project_id,
        project_reference=project_reference,
        project_name=ticket.project.name if ticket.project else None,
        ticket_id=ticket.id,
        ticket_reference=_ticket_reference(ticket),
        ticket_title=ticket.title,
        status=item.status.value,
        archived=bool(ticket.project and ticket.project.archived_at),
        private=_ticket_private(ticket),
        deferred=item.status == SubtaskStatus.DEFERRED,
    )


def _exact_reference_result(db: Session, workspace_id: int, query: str):
    """Resolve a complete work key before lifecycle filtering or result limits."""
    match = re.fullmatch(
        r"(PRJ|TKT)-(\d{3,}|[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4})"
        r"(?:-(AC|ST)-(\d{3,}))?",
        query.upper(),
    )
    if match is None:
        return None
    kind, identity, child_kind, child_number = match.groups()
    if kind == "PRJ":
        if child_kind:
            return None
        predicate = (
            Project.workspace_project_number == int(identity)
            if identity.isdigit() else Project.public_id == query.upper()
        )
        project = db.scalar(select(Project).where(
            Project.workspace_id == workspace_id, predicate,
        ))
        if project is None:
            return None
        canonical = _project_reference(project) if identity.isdigit() else project.public_id
        return "projects", _project_result(project, canonical)[1]

    predicate = (
        Ticket.workspace_ticket_number == int(identity)
        if identity.isdigit() else Ticket.public_id == f"TKT-{identity}"
    )
    ticket = db.scalar(select(Ticket).where(
        Ticket.workspace_id == workspace_id, predicate,
    ).options(selectinload(Ticket.project)))
    if ticket is None:
        return None
    canonical = _ticket_reference(ticket) if identity.isdigit() else ticket.public_id
    if not child_kind:
        return "tickets", _ticket_result(ticket, canonical)[1]
    model = AcceptanceCriterion if child_kind == "AC" else Subtask
    child = db.scalar(select(model).where(
        model.ticket_id == ticket.id,
        model.reference_number == int(child_number),
    ))
    if child is None:
        return None
    canonical = f"{canonical}-{child_kind}-{child.reference_number:03d}"
    if child_kind == "AC":
        return "acceptance_criteria", _criterion_result(child, canonical)[1]
    return "subtasks", _subtask_result(child, canonical)[1]


def search_workspace(
    db: Session,
    *,
    workspace_id: int,
    query: str,
    include_completed: bool = False,
    include_cancelled: bool = False,
    include_deferred: bool = False,
    include_archived: bool = False,
    statuses: set[TicketStatus] | None = None,
    limit: int = 40,
) -> SearchRead:
    """Return deterministic, bounded matches from one authorized workspace."""
    query = query.strip()
    exact = _exact_reference_result(db, workspace_id, query)
    if exact is not None:
        group, result = exact
        return SearchRead(query=query, total=1, **{group: [result]})
    project_number = re.fullmatch(r"PRJ-0*(\d+)", query, re.IGNORECASE)
    ticket_number = re.fullmatch(r"TKT-0*(\d+)", query, re.IGNORECASE)
    criterion_number = re.fullmatch(r"TKT-0*(\d+)-AC-0*(\d+)", query, re.IGNORECASE)
    subtask_number = re.fullmatch(r"TKT-0*(\d+)-ST-0*(\d+)", query, re.IGNORECASE)
    derived_public = re.fullmatch(r"(TKT-[A-Z0-9-]+)-(AC|ST)-0*(\d+)", query, re.IGNORECASE)

    project_predicates = [
        _contains(Project.public_id, query),
        _contains(Project.name, query),
        _contains(Project.description, query),
        _contains(Project.purpose, query),
        _contains(Project.why_it_matters, query),
    ]
    if project_number:
        project_predicates.append(
            Project.workspace_project_number == int(project_number.group(1))
        )
    project_statement = select(Project).where(
        Project.workspace_id == workspace_id,
        or_(*project_predicates),
    )
    if not include_archived:
        project_statement = project_statement.where(Project.archived_at.is_(None))
    projects = list(db.scalars(project_statement.limit(limit + 1)).all())

    ticket_predicates = [
        _contains(Ticket.public_id, query),
        _contains(Ticket.title, query),
        _contains(Ticket.description, query),
    ]
    if ticket_number:
        ticket_predicates.append(
            Ticket.workspace_ticket_number == int(ticket_number.group(1))
        )
    tickets = list(db.scalars(
        select(Ticket)
        .where(Ticket.workspace_id == workspace_id, or_(*ticket_predicates))
        .options(selectinload(Ticket.project))
        .limit(limit + 1)
    ).all())

    criterion_predicates = [_contains(AcceptanceCriterion.text, query)]
    if criterion_number:
        criterion_predicates.append(and_(
            AcceptanceCriterion.reference_number == int(criterion_number.group(2)),
            Ticket.workspace_ticket_number == int(criterion_number.group(1)),
        ))
    if derived_public and derived_public.group(2).upper() == "AC":
        criterion_predicates.append(and_(
            AcceptanceCriterion.reference_number == int(derived_public.group(3)),
            Ticket.public_id == derived_public.group(1).upper(),
        ))
    criteria = list(db.scalars(
        select(AcceptanceCriterion)
        .join(AcceptanceCriterion.ticket)
        .where(
            Ticket.workspace_id == workspace_id,
            or_(*criterion_predicates),
        )
        .options(
            selectinload(AcceptanceCriterion.ticket).selectinload(Ticket.project)
        )
        .limit(limit + 1)
    ).all())

    subtask_predicates = [
        _contains(Subtask.title, query),
        _contains(Subtask.description, query),
    ]
    if subtask_number:
        subtask_predicates.append(and_(
            Subtask.reference_number == int(subtask_number.group(2)),
            Ticket.workspace_ticket_number == int(subtask_number.group(1)),
        ))
    if derived_public and derived_public.group(2).upper() == "ST":
        subtask_predicates.append(and_(
            Subtask.reference_number == int(derived_public.group(3)),
            Ticket.public_id == derived_public.group(1).upper(),
        ))
    subtasks = list(db.scalars(
        select(Subtask)
        .join(Subtask.ticket)
        .where(Ticket.workspace_id == workspace_id, or_(*subtask_predicates))
        .options(selectinload(Subtask.ticket).selectinload(Ticket.project))
        .limit(limit + 1)
    ).all())

    ranked: list[tuple[int, int, str, int, SearchResult]] = []
    for project in projects:
        score, result = _project_result(project, query)
        ranked.append((score, RESOURCE_ORDER[result.resource_type], result.title.casefold(), result.id, result))
    for ticket in tickets:
        if _ticket_allowed(
            ticket,
            include_completed=include_completed,
            include_cancelled=include_cancelled,
            include_archived=include_archived,
            statuses=statuses,
        ):
            score, result = _ticket_result(ticket, query)
            ranked.append((score, RESOURCE_ORDER[result.resource_type], result.title.casefold(), result.id, result))
    for item in criteria:
        ticket = item.ticket
        if (
            _ticket_allowed(
                ticket,
                include_completed=include_completed,
                include_cancelled=include_cancelled,
                include_archived=include_archived,
                statuses=statuses,
            )
            and (include_completed or not item.completed)
            and (include_deferred or not item.deferred)
        ):
            score, result = _criterion_result(item, query)
            ranked.append((score, RESOURCE_ORDER[result.resource_type], result.title.casefold(), result.id, result))
    for item in subtasks:
        ticket = item.ticket
        if (
            _ticket_allowed(
                ticket,
                include_completed=include_completed,
                include_cancelled=include_cancelled,
                include_archived=include_archived,
                statuses=statuses,
            )
            and (include_completed or item.status != SubtaskStatus.DONE)
            and (include_cancelled or item.status != SubtaskStatus.CANCELLED)
            and (include_deferred or item.status != SubtaskStatus.DEFERRED)
        ):
            score, result = _subtask_result(item, query)
            ranked.append((score, RESOURCE_ORDER[result.resource_type], result.title.casefold(), result.id, result))

    ranked.sort(key=lambda item: item[:4])
    truncated = (
        len(projects) > limit
        or len(tickets) > limit
        or len(criteria) > limit
        or len(subtasks) > limit
        or len(ranked) > limit
    )
    selected = [item[4] for item in ranked[:limit]]
    return SearchRead(
        query=query,
        projects=[item for item in selected if item.resource_type == SearchResourceType.PROJECT],
        tickets=[item for item in selected if item.resource_type == SearchResourceType.TICKET],
        acceptance_criteria=[
            item for item in selected
            if item.resource_type == SearchResourceType.ACCEPTANCE_CRITERION
        ],
        subtasks=[item for item in selected if item.resource_type == SearchResourceType.SUBTASK],
        total=len(selected),
        truncated=truncated,
    )
