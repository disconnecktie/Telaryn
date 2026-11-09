"""Observe safe ASGI response lifecycle events for ticket history and exports.

Only a few read-only, high-value endpoints are instrumented. No request or
response content, raw path IDs, URL queries, cookies or header values are logged.
A response-body completion event means ASGI handed the last chunk to the server;
it does not prove the upstream proxy received all bytes.
"""

import asyncio
import logging
import re
from time import perf_counter
from typing import Any

from app.core.diagnostics import log_diagnostic_event, new_support_reference


_ACTIVITY = re.compile(r"/tickets/[1-9][0-9]*/activity\Z")
_EXPORT = re.compile(r"/tickets/[1-9][0-9]*/export\.(?:json|pdf)\Z")


def _safe_route(path: str) -> str | None:
    if _ACTIVITY.fullmatch(path):
        return "/tickets/{ticket_id}/activity"
    if _EXPORT.fullmatch(path):
        return "/tickets/{ticket_id}/export.{format}"
    return None


class TicketResponseTransmissionMiddleware:
    """Log when selected responses begin, finish, or abort at the ASGI boundary."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope.get("type") != "http" or scope.get("method") != "GET":
            await self.app(scope, receive, send)
            return

        route = _safe_route(scope.get("path", ""))
        if route is None:
            await self.app(scope, receive, send)
            return

        reference = new_support_reference()
        started_at = perf_counter()
        status: int | None = None
        body_bytes = 0
        body_chunks = 0
        completed = False

        async def observed_send(message: dict) -> None:
            nonlocal status, body_bytes, body_chunks, completed
            message_type = message.get("type")
            if message_type == "http.response.start":
                status = message["status"]
                # A random opaque reference is safe for support correlation
                # without exposing ticket/user IDs or altering payload bytes.
                headers = list(message.get("headers", []))
                headers.append(
                    (b"x-telaryn-response-reference", reference.encode("ascii"))
                )
                await send({**message, "headers": headers})
                log_diagnostic_event(
                    "response_started",
                    response_reference=reference,
                    method="GET",
                    route=route,
                    status=status,
                )
                return

            if message_type == "http.response.body":
                await send(message)
                body_bytes += len(message.get("body") or b"")
                body_chunks += 1
                if not message.get("more_body", False):
                    completed = True
                    log_diagnostic_event(
                        "response_body_completed",
                        response_reference=reference,
                        method="GET",
                        route=route,
                        status=status,
                        response_bytes=body_bytes,
                        response_chunks=body_chunks,
                        duration_ms=round((perf_counter() - started_at) * 1000),
                    )
                return

            await send(message)

        try:
            await self.app(scope, receive, observed_send)
        except BaseException as error:
            if not completed:
                log_diagnostic_event(
                    "response_stream_failed",
                    level=logging.ERROR,
                    response_reference=reference,
                    method="GET",
                    route=route,
                    status=status,
                    response_bytes=body_bytes,
                    response_chunks=body_chunks,
                    duration_ms=round((perf_counter() - started_at) * 1000),
                    safe_category=(
                        "cancelled" if isinstance(error, asyncio.CancelledError)
                        else "send_or_application_failure"
                    ),
                    exception_type=type(error).__name__,
                )
            raise

        if not completed:
            # An ASGI app can return without emitting a terminating body frame.
            log_diagnostic_event(
                "response_stream_incomplete",
                level=logging.WARNING,
                response_reference=reference,
                method="GET",
                route=route,
                status=status,
                response_bytes=body_bytes,
                response_chunks=body_chunks,
                duration_ms=round((perf_counter() - started_at) * 1000),
            )
