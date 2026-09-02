from __future__ import annotations

from typing import Annotated

from fastapi import Header, Request

from app.exceptions import ApiError


def require_api_key(request: Request, authorization: Annotated[str | None, Header()] = None) -> None:
    expected = request.app.state.settings.api_key
    if not authorization or not authorization.startswith("Bearer ") or authorization[7:] != expected:
        raise ApiError("Invalid API key", 401, "authentication_error", code="invalid_api_key")
