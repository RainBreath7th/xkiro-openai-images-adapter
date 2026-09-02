from __future__ import annotations

from typing import Any

from fastapi import status
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, message: str, status_code: int = 500, error_type: str = "api_error", param: str | None = None, code: str | None = None):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.param = param
        self.code = code


def error_response(error: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"error": {"message": error.message, "type": error.error_type, "param": error.param, "code": error.code}},
    )


def upstream_error(response_status: int, message: str) -> ApiError:
    if response_status in (401, 403):
        return ApiError(message, response_status, "authentication_error", code="upstream_authentication_error")
    if response_status == 429:
        return ApiError(message, 429, "rate_limit_error", code="rate_limit_exceeded")
    if 400 <= response_status < 500:
        return ApiError(message, response_status, "invalid_request_error")
    return ApiError(message, status.HTTP_502_BAD_GATEWAY, "api_error", code="upstream_error")
