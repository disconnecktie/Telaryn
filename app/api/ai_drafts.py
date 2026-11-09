"""Review unsaved ticket drafts without making them authoritative Telaryn records."""

import logging
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.context import (
    AcceptanceCriterionContext,
    SubtaskContext,
    WorkContext,
)
from app.ai.base import AIProviderError, AIProviderTimeoutError
from app.ai.factory import get_ai_provider
from app.ai.service import AIReviewService
from app.db.session import get_db
from app.core.diagnostics import log_diagnostic_event
from app.models.project import Project
from app.schemas.ai_review import AIDraftReviewRead, AIDraftReviewRequest
from app.services.ai_context_policy import (
    require_project_ai_context,
    require_ticket_ai_context_enabled,
)
from app.services.auth import AuthContext, require_auth_context
from app.services.workspaces import request_workspace, require_workspace_project


# Transient draft analysis: proposals return to the client without persistence.
router = APIRouter(
    prefix="/ai-reviews",
    tags=["AI Reviews"],
)


@router.post("/draft", response_model=AIDraftReviewRead)
def review_ticket_draft(
    draft: AIDraftReviewRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Analyze user-supplied draft context without persisting a ticket or review."""
    require_ticket_ai_context_enabled(draft.ai_context_enabled)

    project_name = None
    workspace_id = None

    if draft.project_id is not None:
        workspace = request_workspace(db, auth)
        workspace_id = workspace.id
        project = require_workspace_project(
            db, workspace_id=workspace_id, project_id=draft.project_id
        )
        require_project_ai_context(project)

        project_name = project.name

    provider = get_ai_provider()
    service = AIReviewService(provider)
    started = perf_counter()
    log_diagnostic_event(
        "ai_operation",
        operation="draft_ticket_review",
        outcome="requested",
        provider=provider.name,
        model=provider.model_name,
        user_id=getattr(getattr(auth, "user", None), "id", None),
        workspace_id=workspace_id,
    )
    try:
        result = service.review_draft(
            WorkContext(
                title=draft.title.strip(),
                description=(draft.description or "").strip() or None,
                project_name=project_name,
                status="ready",
                priority=draft.priority.value,
                ticket_type=draft.ticket_type.value,
                subtasks=[
                    SubtaskContext(
                        title=subtask.title.strip(),
                        description=(subtask.description or "").strip() or None,
                        status="todo",
                        completed=False,
                    )
                    for subtask in draft.subtasks
                    if subtask.title.strip()
                ],
                acceptance_criteria=[
                    AcceptanceCriterionContext(
                        text=criterion.strip(),
                        completed=False,
                    )
                    for criterion in draft.acceptance_criteria
                    if criterion.strip()
                ],
            )
        )
    except AIProviderTimeoutError as error:
        log_diagnostic_event(
            "ai_operation",
            level=logging.WARNING,
            operation="draft_ticket_review",
            outcome="timeout",
            provider=provider.name,
            model=provider.model_name,
            user_id=getattr(getattr(auth, "user", None), "id", None),
            workspace_id=workspace_id,
            duration_ms=round((perf_counter() - started) * 1000),
        )
        raise HTTPException(
            status_code=504,
            detail=(
                "Telaryn AI did not respond in time. Your draft was not changed; "
                "please retry when ready."
            ),
        ) from error
    except AIProviderError as error:
        log_diagnostic_event(
            "ai_operation",
            level=logging.WARNING,
            operation="draft_ticket_review",
            outcome="provider_failure",
            provider=provider.name,
            model=provider.model_name,
            user_id=getattr(getattr(auth, "user", None), "id", None),
            workspace_id=workspace_id,
            duration_ms=round((perf_counter() - started) * 1000),
        )
        raise HTTPException(
            status_code=502,
            detail=(
                "Telaryn AI is temporarily unavailable. Your draft was not "
                "changed; please retry when ready."
            ),
        ) from error

    log_diagnostic_event(
        "ai_operation",
        operation="draft_ticket_review",
        outcome="completed",
        provider=provider.name,
        model=provider.model_name,
        user_id=getattr(getattr(auth, "user", None), "id", None),
        workspace_id=workspace_id,
        duration_ms=round((perf_counter() - started) * 1000),
    )

    return AIDraftReviewRead(
        provider=provider.name,
        model=provider.model_name,
        suggested_title=result.suggested_title,
        suggested_description=result.suggested_description,
        suggested_priority=result.suggested_priority,
        suggested_ticket_type=result.suggested_ticket_type,
        reasoning_summary=result.reasoning_summary,
        missing_information=result.missing_information,
        recommendations=[
            {
                "text": recommendation.text,
                "rationale": recommendation.rationale,
                "basis": recommendation.basis.value,
            }
            for recommendation in result.recommendations
        ],
        acceptance_criteria=[
            {"text": criterion.text, "basis": criterion.basis.value}
            for criterion in result.acceptance_criteria
        ],
        suggested_subtasks=[
            {
                "title": subtask.title,
                "description": subtask.description,
                "basis": subtask.basis.value,
            }
            for subtask in result.suggested_subtasks
        ],
        subtask_revisions=[
            {
                "source_index": revision.source_index,
                "suggested_title": revision.suggested_title,
                "suggested_description": revision.suggested_description,
                "rationale": revision.rationale,
                "basis": revision.basis.value,
            }
            for revision in result.subtask_revisions
        ],
        acceptance_criteria_revisions=[
            {
                "source_index": revision.source_index,
                "suggested_text": revision.suggested_text,
                "rationale": revision.rationale,
                "basis": revision.basis.value,
            }
            for revision in result.acceptance_criteria_revisions
        ],
    )

