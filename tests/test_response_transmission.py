"""Verify safe ASGI response-byte diagnostics without exposing ticket contents."""

import asyncio
from unittest.mock import patch

import pytest

from app.core.response_transmission import TicketResponseTransmissionMiddleware


def scope(path="/tickets/3/activity", method="GET"):
    return {"type": "http", "method": method, "path": path}


def events(mock_logger):
    return [
        {"event": call.args[0], **call.kwargs}
        for call in mock_logger.call_args_list
    ]


def test_activity_response_reports_start_and_final_bytes_with_opaque_reference():
    sent = []
    private_content = b"User-authored progress note with secret title"
    async def application(_scope, _receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": private_content, "more_body": True})
        await send({"type": "http.response.body", "body": b"-end", "more_body": False})

    async def send(message):
        sent.append(message)

    with patch("app.core.response_transmission.log_diagnostic_event") as logger:
        asyncio.run(TicketResponseTransmissionMiddleware(application)(
            scope(), lambda: None, send
        ))

    emitted = events(logger)
    assert [record["event"] for record in emitted] == [
        "response_started", "response_body_completed"
    ]
    ref = dict(sent[0]["headers"])[b"x-telaryn-response-reference"].decode()
    assert ref.startswith("ATL-")
    assert emitted[0]["response_reference"] == emitted[1]["response_reference"] == ref
    assert emitted[1]["response_bytes"] == len(private_content) + 4
    assert emitted[1]["response_chunks"] == 2
    assert emitted[1]["status"] == 200
    assert emitted[1]["route"] == "/tickets/{ticket_id}/activity"
    assert emitted[1]["duration_ms"] >= 0
    assert private_content in sent[1]["body"]
    assert "secret title" not in repr(emitted)
    assert "/tickets/3/activity" not in repr(emitted)


def test_send_failure_is_reported_without_claiming_completion():
    async def application(_scope, _receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"partial", "more_body": True})
        await send({"type": "http.response.body", "body": b"second", "more_body": False})

    async def send(message):
        if message.get("type") == "http.response.body" and message.get("body") == b"second":
            raise ConnectionResetError("private upstream or socket address")

    with patch("app.core.response_transmission.log_diagnostic_event") as logger:
        with pytest.raises(ConnectionResetError):
            asyncio.run(TicketResponseTransmissionMiddleware(application)(
                scope(), lambda: None, send
            ))

    emitted = events(logger)
    assert [record["event"] for record in emitted] == [
        "response_started", "response_stream_failed"
    ]
    assert emitted[-1]["response_bytes"] == len(b"partial")
    assert emitted[-1]["exception_type"] == "ConnectionResetError"
    assert emitted[-1]["safe_category"] == "send_or_application_failure"
    assert "private upstream" not in repr(emitted)


def test_cancellation_during_body_is_reported_without_swallowing_it():
    async def application(_scope, _receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        raise asyncio.CancelledError()

    async def send(_message):
        pass

    with patch("app.core.response_transmission.log_diagnostic_event") as logger:
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(TicketResponseTransmissionMiddleware(application)(
                scope(), lambda: None, send
            ))
    emitted = events(logger)
    assert [record["event"] for record in emitted] == [
        "response_started", "response_stream_failed"
    ]
    assert emitted[-1]["safe_category"] == "cancelled"


def test_incomplete_body_is_not_mistaken_for_success():
    async def application(_scope, _receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"unfinished", "more_body": True})

    async def send(_message):
        pass

    with patch("app.core.response_transmission.log_diagnostic_event") as logger:
        asyncio.run(TicketResponseTransmissionMiddleware(application)(
            scope(), lambda: None, send
        ))
    assert [record["event"] for record in events(logger)] == [
        "response_started", "response_stream_incomplete"
    ]


@pytest.mark.parametrize("request_scope", [
    scope(path="/tickets/3/subtasks/"),
    scope(path="/tickets/3/activity-events"),
    scope(path="/tickets/3/activity", method="POST"),
    scope(path="/tickets/not-an-id/activity"),
    {"type": "lifespan"},
])
def test_unrelated_requests_and_lifespan_are_unmodified(request_scope):
    async def application(_scope, _receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok", "more_body": False})

    sent = []
    async def send(message):
        sent.append(message)

    with patch("app.core.response_transmission.log_diagnostic_event") as logger:
        asyncio.run(TicketResponseTransmissionMiddleware(application)(
            request_scope, lambda: None, send
        ))

    assert sent[0]["headers"] == []
    assert not logger.called


@pytest.mark.parametrize("path", [
    "/tickets/18/export.json",
    "/tickets/18/export.pdf",
])
def test_export_endpoints_have_safe_normalized_route(path):
    async def application(_scope, _receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"data", "more_body": False})

    async def send(_message):
        pass

    with patch("app.core.response_transmission.log_diagnostic_event") as logger:
        asyncio.run(TicketResponseTransmissionMiddleware(application)(
            scope(path=path), lambda: None, send
        ))
    emitted = events(logger)
    assert emitted[-1]["route"] == "/tickets/{ticket_id}/export.{format}"
    assert emitted[-1]["response_bytes"] == 4


def test_failure_before_headers_records_safe_metadata():
    async def application(_scope, _receive, _send):
        raise RuntimeError("sensitive source details")

    async def send(_message):
        pass

    with patch("app.core.response_transmission.log_diagnostic_event") as logger:
        with pytest.raises(RuntimeError):
            asyncio.run(TicketResponseTransmissionMiddleware(application)(
                scope(), lambda: None, send
            ))
    emitted = events(logger)
    assert len(emitted) == 1
    assert emitted[0]["event"] == "response_stream_failed"
    assert emitted[0]["status"] is None
    assert emitted[0]["exception_type"] == "RuntimeError"
    assert "sensitive source" not in repr(emitted)
