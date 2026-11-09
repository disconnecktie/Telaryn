"""Expose authorized, human-configured Activity Report generation."""

import logging
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.base import AIProvider, AIProviderError, AIProviderTimeoutError
from app.ai.factory import get_ai_provider
from app.core.diagnostics import log_diagnostic_event
from app.core.time import utc_now
from app.db.session import get_db
from app.schemas.activity_report import (
    ActivityReportProjectOption,
    ActivityReportRead,
    ActivityReportRequest,
)
from app.services.activity_reports import build_report_snapshot, list_report_projects
from app.services.auth import AuthContext, require_auth_context
from app.services.workspaces import request_workspace

router = APIRouter(prefix="/activity-reports", tags=["Activity Reports"])


@router.get("/projects", response_model=list[ActivityReportProjectOption])
def report_project_options(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    return list_report_projects(db, workspace.id)


@router.post("/generate", response_model=ActivityReportRead)
def generate_activity_report(
    request: ActivityReportRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
    provider: AIProvider = Depends(get_ai_provider),
):
    workspace = request_workspace(db, auth)
    subject_first_name = auth.user.display_name.strip().split(maxsplit=1)[0]
    snapshot = build_report_snapshot(
        request,
        workspace_id=workspace.id,
        subject_first_name=subject_first_name,
        db=db,
    )
    started = perf_counter()
    log_diagnostic_event(
        "ai_operation",
        user_id=auth.user.id,
        workspace_id=workspace.id,
        provider=provider.name,
        model=provider.model_name,
        operation="activity_report",
        outcome="requested",
    )
    try:
        result = provider.generate_activity_report(snapshot)
    except AIProviderTimeoutError as error:
        log_diagnostic_event(
            "ai_operation", level=logging.WARNING,
            duration_ms=round((perf_counter() - started) * 1000),
            user_id=auth.user.id, workspace_id=workspace.id,
            provider=provider.name, model=provider.model_name,
            operation="activity_report", outcome="timeout",
        )
        raise HTTPException(status_code=504, detail=str(error)) from error
    except AIProviderError as error:
        log_diagnostic_event(
            "ai_operation", level=logging.WARNING,
            duration_ms=round((perf_counter() - started) * 1000),
            user_id=auth.user.id, workspace_id=workspace.id,
            provider=provider.name, model=provider.model_name,
            operation="activity_report", outcome="provider_failure",
        )
        raise HTTPException(status_code=502, detail=str(error)) from error
    log_diagnostic_event(
        "ai_operation",
        duration_ms=round((perf_counter() - started) * 1000),
        user_id=auth.user.id, workspace_id=workspace.id,
        provider=provider.name, model=provider.model_name,
        operation="activity_report", outcome="completed",
    )
    return ActivityReportRead(
        **result.model_dump(),
        period=snapshot.period,
        output_format=snapshot.output_format,
        period_start=snapshot.period_start,
        period_end=snapshot.period_end,
        generated_at=utc_now(),
        included_project_ids=[project.id for project in snapshot.projects],
    )
