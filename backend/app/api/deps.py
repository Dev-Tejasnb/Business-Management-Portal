"""Shared FastAPI dependencies."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Header, Request

X_REQUEST_ID = "X-Request-ID"


def request_id_header(
    x_request_id: Annotated[str | None, Header(alias=X_REQUEST_ID)] = None,
) -> str:
    """Return the incoming request id, or generate one for correlation logs."""
    return x_request_id or str(uuid.uuid4())


def attach_request_id(request: Request) -> None:
    """Attach the request id onto request.state for error correlation."""
    if not hasattr(request.state, "request_id"):
        request.state.request_id = request_id_header(
            request.headers.get(X_REQUEST_ID)
        )