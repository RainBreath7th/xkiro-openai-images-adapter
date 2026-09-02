from __future__ import annotations

import asyncio
import logging
import time
from typing import Awaitable, Callable

from app.exceptions import ApiError

logger = logging.getLogger(__name__)


async def wait_for_job(get_job: Callable[[str], Awaitable[dict]], job_id: str, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    delay = 2.0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ApiError("Image generation timed out", 504, "api_error", code="timeout")
        await asyncio.sleep(min(delay, remaining))
        job = await get_job(job_id)
        status = job.get("status")
        if status == "succeeded":
            return job
        if status == "failed":
            message = job.get("error", {}).get("message", "Image generation failed")
            raise ApiError(message, 502, "api_error", code="generation_failed")
        if status == "blocked":
            message = job.get("error", {}).get("message", "Image generation was blocked")
            raise ApiError(message, 400, "invalid_request_error", code="content_policy_violation")
        delay = min(delay * 1.5, 10.0)
