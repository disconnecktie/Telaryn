"""Compose the Telaryn FastAPI application, middleware, routes, and health endpoint."""

from contextlib import asynccontextmanager
import asyncio
import logging
from time import perf_counter

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.ai_reviews import router as ai_reviews_router
from app.api.auth import router as auth_router
from app.api.access_requests import router as access_requests_router
from app.api.ai_drafts import router as ai_drafts_router
from app.api.acceptance_criteria import router as acceptance_criteria_router
from app.api.ticket_updates import router as ticket_updates_router
from app.api.projects import router as projects_router
from app.api.project_reviews import router as project_reviews_router
from app.api.search import router as search_router
from app.api.my_work import router as my_work_router
from app.api.preferences import router as preferences_router
from app.api.onboarding import router as onboarding_router
from app.api.tickets import router as tickets_router
from app.api.subtasks import router as subtasks_router
from app.api.user_management import router as user_management_router
from app.api.work_intake import router as work_intake_router
from app.api.activity_reports import router as activity_reports_router
from app.api.feedback import router as feedback_router
from app.ai.factory import AIProviderUnavailableError
from app.core.config import settings
from app.core.diagnostics import (
    configure_diagnostics,
    database_migration_state,
    log_diagnostic_event,
    new_support_reference,
    safe_failure_location,
)
from app.core.response_transmission import TicketResponseTransmissionMiddleware
from app.services.auth import require_auth_context
from app.services.project_review_worker import run_project_review_worker
from app.services.work_intake_worker import run_work_intake_worker

# Application composition: CORS and all public API routers are registered here.
configure_diagnostics(
    level=settings.log_level,
    output=settings.log_format,
    environment=settings.environment,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Report safe startup state without mutating data or delaying shutdown."""
    log_diagnostic_event(
        "application_started",
        environment=settings.environment,
        app_version=settings.app_version,
        provider=settings.ai_provider,
        migration_state=database_migration_state(settings.database_url),
    )
    stop_workers = asyncio.Event()
    workers = [
        asyncio.create_task(run_project_review_worker(stop_workers)),
        asyncio.create_task(run_work_intake_worker(stop_workers)),
    ]
    try:
        yield
    finally:
        stop_workers.set()
        await asyncio.gather(*workers)


app = FastAPI(
    title=settings.app_name,
    description="AI-assisted personal and work management",
    version=settings.app_version,
    lifespan=lifespan,
)


@app.exception_handler(AIProviderUnavailableError)
async def ai_provider_unavailable(
    _request: Request, _error: AIProviderUnavailableError
) -> JSONResponse:
    """Return an actionable response for deployments where AI is unavailable."""
    return JSONResponse(
        status_code=503,
        content={"detail": "Telaryn AI is not configured for this deployment."},
    )


app.include_router(access_requests_router)

allowed_origins = [value.strip() for value in settings.frontend_origins.split(",") if value.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def validate_cookie_request_origin(request: Request, call_next):
    """Reject cross-origin browser mutations before cookie authentication runs."""
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        has_session = settings.session_cookie_name in request.cookies
        if (has_session or request.url.path == "/auth/login") and origin not in allowed_origins:
            return JSONResponse(status_code=403, content={"detail": "Request origin is not allowed."})
    return await call_next(request)


@app.middleware("http")
async def diagnostic_boundary(request: Request, call_next):
    """Correlate requests and convert unexpected failures into safe JSON."""
    started = perf_counter()
    support_reference = None
    try:
        response = await call_next(request)
    except Exception as error:
        support_reference = new_support_reference()
        response = JSONResponse(
            status_code=500,
            content={
                "detail": "Telaryn encountered an unexpected error. Your work may not have been changed.",
                "reference": support_reference,
            },
        )
        log_diagnostic_event(
            "unexpected_api_failure",
            level=logging.ERROR,
            support_reference=support_reference,
            method=request.method,
            route=getattr(request.scope.get("route"), "path", "unmatched"),
            status=500,
            safe_category="unexpected_failure",
            exception_type=type(error).__name__,
            failure_location=safe_failure_location(error),
        )

    duration_ms = round((perf_counter() - started) * 1000)
    log_diagnostic_event(
        "request_completed",
        support_reference=support_reference,
        method=request.method,
        route=getattr(request.scope.get("route"), "path", "unmatched"),
        status=response.status_code,
        duration_ms=duration_ms,
    )
    return response

# Pure ASGI observer wraps the existing HTTP middleware and records the final
# response-body send, not merely the route returning its Response object.
# It only instruments read-only ticket activity and export endpoints.
app.add_middleware(TicketResponseTransmissionMiddleware)

app.include_router(auth_router)
protected = [Depends(require_auth_context)]
app.include_router(tickets_router, dependencies=protected)
app.include_router(projects_router, dependencies=protected)
app.include_router(project_reviews_router, dependencies=protected)
app.include_router(search_router, dependencies=protected)
app.include_router(my_work_router, dependencies=protected)
app.include_router(preferences_router, dependencies=protected)
app.include_router(onboarding_router, dependencies=protected)
app.include_router(subtasks_router, dependencies=protected)
app.include_router(ai_reviews_router, dependencies=protected)
app.include_router(ai_drafts_router, dependencies=protected)
app.include_router(acceptance_criteria_router, dependencies=protected)
app.include_router(ticket_updates_router, dependencies=protected)
app.include_router(user_management_router, dependencies=protected)
app.include_router(work_intake_router, dependencies=protected)
app.include_router(activity_reports_router, dependencies=protected)
app.include_router(feedback_router, dependencies=protected)

@app.post("/dev/reload-settings")
def reload_settings(_=Depends(require_auth_context)):
    settings.__init__()

    return {
        "status": "reloaded",
        "ai_provider": settings.ai_provider,
        "openai_model": settings.openai_model,
    }

@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "workspace_mode": settings.workspace_mode,
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/ready")
def readiness_check():
    """Verify database reachability and migration alignment without exposing details."""
    if database_migration_state(settings.database_url) != "current":
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}
