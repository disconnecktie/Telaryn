"""Verify shared diagnostics correlate failures without exposing private content."""

import json
import logging
import re
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.diagnostics import (
    AtlasDiagnosticFormatter,
    log_diagnostic_event,
    new_support_reference,
)


SENSITIVE_VALUES = (
    "Install backyard fence for dog containment",
    "Boo will be upset",
    "sk-proj-secret",
    "session-cookie-secret",
    '{"raw_provider_output":"private"}',
)


def test_support_reference_is_short_random_and_non_credential_shaped():
    first = new_support_reference()
    second = new_support_reference()

    assert re.fullmatch(r"ATL-[0-9A-F]{6}", first)
    assert first != second
    assert not re.search(r"sk-|bearer|session", first, re.IGNORECASE)


def test_closed_diagnostic_helper_emits_only_allowlisted_metadata():
    with patch("app.core.diagnostics.logger.log") as log:
        log_diagnostic_event(
            "request_completed",
            support_reference="ATL-A1B2C3",
            method="GET",
            route="/tickets/{ticket_id}",
            status=500,
            duration_ms=14,
            user_id=7,
            workspace_id=3,
            exception_type="RuntimeError",
            failure_location="read_ticket:42",
        )

    log.assert_called_once()
    _, _, kwargs = log.mock_calls[0]
    fields = kwargs["extra"]
    assert fields["atlas_support_reference"] == "ATL-A1B2C3"
    assert fields["atlas_route"] == "/tickets/{ticket_id}"
    assert fields["atlas_duration_ms"] == 14
    rendered = repr(fields)
    for sensitive in SENSITIVE_VALUES:
        assert sensitive not in rendered


def test_json_formatter_uses_utc_dtg_and_documented_duration_unit():
    formatter = AtlasDiagnosticFormatter(output="json")
    record = logging.LogRecord(
        name="atlas.diagnostics",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="atlas_diagnostic",
        args=(),
        exc_info=None,
    )
    record.atlas_event = "unexpected_api_failure"
    record.atlas_support_reference = "ATL-A1B2C3"
    record.atlas_duration_ms = 9

    payload = json.loads(formatter.format(record))

    assert payload["dtg"].endswith("Z")
    assert payload["severity"] == "ERROR"
    assert payload["event"] == "unexpected_api_failure"
    assert payload["support_reference"] == "ATL-A1B2C3"
    assert payload["duration_ms"] == 9


def test_unhandled_failure_returns_safe_json_with_correlated_reference():
    local_app = FastAPI()

    @local_app.middleware("http")
    async def boundary(request, call_next):
        try:
            return await call_next(request)
        except Exception as error:
            from fastapi.responses import JSONResponse

            reference = new_support_reference()
            log_diagnostic_event(
                "unexpected_api_failure",
                level=logging.ERROR,
                support_reference=reference,
                method=request.method,
                route="/explode",
                status=500,
                exception_type=type(error).__name__,
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Telaryn encountered an unexpected error.", "reference": reference},
            )

    @local_app.get("/explode")
    def explode():
        raise RuntimeError(" ".join(SENSITIVE_VALUES))

    with patch("app.core.diagnostics.logger.log") as log:
        response = TestClient(local_app).get("/explode")

    assert response.status_code == 500
    payload = response.json()
    assert re.fullmatch(r"ATL-[0-9A-F]{6}", payload["reference"])
    assert payload["detail"] == "Telaryn encountered an unexpected error."
    assert log.call_args.kwargs["extra"]["atlas_support_reference"] == payload["reference"]
    rendered = response.text + repr(log.call_args.kwargs)
    for sensitive in SENSITIVE_VALUES:
        assert sensitive not in rendered

