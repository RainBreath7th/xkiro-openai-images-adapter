from __future__ import annotations

from typing import Any

from app.exceptions import ApiError

GENERATION_FIELDS = {"model", "prompt", "n", "size", "style", "source_job_id"}
EDIT_FIELDS = {"prompt", "model", "size", "n"}
LOCAL_FIELDS = {"response_format"}


def select_parameters(payload: dict[str, Any], allowed: set[str], strict: bool) -> tuple[dict[str, Any], str]:
    unknown = set(payload) - allowed - LOCAL_FIELDS
    if strict and unknown:
        name = sorted(unknown)[0]
        raise ApiError(f"Unsupported parameter: {name}", 400, "invalid_request_error", name, "unsupported_parameter")
    selected = {key: payload[key] for key in allowed if key in payload}
    response_format = payload.get("response_format", "url")
    if response_format not in {"url", "b64_json"}:
        raise ApiError("Invalid response_format", 400, "invalid_request_error", "response_format", "invalid_value")
    return selected, response_format
