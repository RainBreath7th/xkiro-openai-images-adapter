from __future__ import annotations

import base64
from urllib.parse import urlparse

from app.exceptions import ApiError


async def build_response(job: dict, response_format: str, download) -> dict:
    items = job.get("data")
    if not isinstance(items, list) or not items:
        raise ApiError("Xkiro returned no image data", 502, "api_error", code="invalid_upstream_response")
    result = []
    for item in items:
        url = item.get("url") if isinstance(item, dict) else None
        if not isinstance(url, str):
            raise ApiError("Xkiro returned an invalid image URL", 502, "api_error", code="invalid_upstream_response")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ApiError("Xkiro returned an invalid image URL", 502, "api_error", code="invalid_upstream_response")
        if response_format == "url":
            result.append({"url": url})
        else:
            content = await download(url)
            result.append({"b64_json": base64.b64encode(content).decode("ascii")})
    return {"created": job.get("created", 0), "data": result}
