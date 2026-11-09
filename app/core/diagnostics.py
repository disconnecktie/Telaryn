"""Privacy-safe application diagnostics and support-reference correlation.

This module is intentionally the only general-purpose operational logging
boundary. Callers choose from explicit parameters; arbitrary dictionaries,
request content, exception messages, and user-authored text are not accepted.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import secrets
import traceback
from typing import Literal

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine


_LOG_RECORD_FIELDS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "taskName",
}


def new_support_reference() -> str:
    """Return a random, non-sequential reference safe to show in the browser."""
    return f"ATL-{secrets.token_hex(3).upper()}"


def safe_failure_location(error: BaseException) -> str | None:
    """Return a bounded callable/line reference without message text or locals."""
    frames = traceback.extract_tb(error.__traceback__)
    if not frames:
        return None
    frame = frames[-1]
    return f"{frame.name}:{frame.lineno}"


class AtlasDiagnosticFormatter(logging.Formatter):
    """Render allowlisted diagnostic extras as JSON or readable development text."""

    def __init__(self, *, output: Literal["json", "human"]) -> None:
        super().__init__()
        self.output = output

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, timezone.utc)
        values = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _LOG_RECORD_FIELDS
            and key.startswith("atlas_")
            and value is not None
        }
        event = values.pop("atlas_event", "diagnostic")
        fields = {
            "dtg": timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "severity": record.levelname,
            "event": event,
            **{key.removeprefix("atlas_"): value for key, value in values.items()},
        }
        if self.output == "json":
            return json.dumps(fields, separators=(",", ":"), sort_keys=True)
        rendered = " ".join(f"{key}={value}" for key, value in fields.items())
        return f"TELARYN {rendered}"


def configure_diagnostics(*, level: str, output: str, environment: str) -> None:
    """Configure Telaryn-owned formatting and deliberately level-control noisy loggers."""
    resolved_output = output
    if output == "auto":
        resolved_output = "human" if environment == "development" else "json"

    handler = logging.StreamHandler()
    handler.setFormatter(AtlasDiagnosticFormatter(output=resolved_output))
    atlas_logger = logging.getLogger("atlas")
    atlas_logger.handlers.clear()
    atlas_logger.addHandler(handler)
    atlas_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    atlas_logger.propagate = False

    # Keep framework and persistence noise controlled; their content is not
    # automatically safe enough to adopt as Telaryn diagnostic fields.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


logger = logging.getLogger("atlas.diagnostics")


def log_diagnostic_event(
    event: str,
    *,
    level: int = logging.INFO,
    support_reference: str | None = None,
    response_reference: str | None = None,
    review_reference: str | None = None,
    method: str | None = None,
    route: str | None = None,
    status: int | None = None,
    duration_ms: int | None = None,
    response_bytes: int | None = None,
    response_chunks: int | None = None,
    user_id: int | None = None,
    workspace_id: int | None = None,
    requester_id: int | None = None,
    project_id: int | None = None,
    attempt_id: int | None = None,
    snapshot_prefix: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    operation: str | None = None,
    outcome: str | None = None,
    safe_category: str | None = None,
    selected_ticket_count: int | None = None,
    exception_type: str | None = None,
    failure_location: str | None = None,
    environment: str | None = None,
    app_version: str | None = None,
    migration_state: str | None = None,
) -> None:
    """Emit one event using a closed, privacy-reviewed field set."""
    logger.log(
        level,
        "atlas_diagnostic",
        extra={
            "atlas_event": event,
            "atlas_support_reference": support_reference,
            "atlas_response_reference": response_reference,
            "atlas_review_reference": review_reference,
            "atlas_method": method,
            "atlas_route": route,
            "atlas_status": status,
            "atlas_duration_ms": duration_ms,
            "atlas_response_bytes": response_bytes,
            "atlas_response_chunks": response_chunks,
            "atlas_user_id": user_id,
            "atlas_workspace_id": workspace_id,
            "atlas_requester_id": requester_id,
            "atlas_project_id": project_id,
            "atlas_attempt_id": attempt_id,
            "atlas_snapshot_prefix": snapshot_prefix,
            "atlas_provider": provider,
            "atlas_model": model,
            "atlas_operation": operation,
            "atlas_outcome": outcome,
            "atlas_safe_category": safe_category,
            "atlas_selected_ticket_count": selected_ticket_count,
            "atlas_exception_type": exception_type,
            "atlas_failure_location": failure_location,
            "atlas_environment": environment,
            "atlas_app_version": app_version,
            "atlas_migration_state": migration_state,
        },
    )


def database_migration_state(database_url: str) -> str:
    """Report revision alignment without logging credentials or mutating the database."""
    try:
        scripts = ScriptDirectory.from_config(Config("alembic.ini"))
        expected = set(scripts.get_heads())
        engine = create_engine(database_url)
        try:
            with engine.connect() as connection:
                current = set(MigrationContext.configure(connection).get_current_heads())
        finally:
            engine.dispose()
    except Exception:
        return "unavailable"

    if current == expected:
        return "current"
    if not current:
        return "unversioned"
    return "behind"

