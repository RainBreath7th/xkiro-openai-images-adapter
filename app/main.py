from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile

from app.config import Settings
from app.dependencies import require_api_key
from app.exceptions import ApiError, error_response
from app.services.param_policy import EDIT_FIELDS, GENERATION_FIELDS, select_parameters
from app.services.poller import wait_for_job
from app.services.response_builder import build_response
from app.services.image_format import detect_image_type
from app.services.xkiro_client import XkiroClient


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.http = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))
        app.state.xkiro = XkiroClient(app.state.http, str(settings.xkiro_base_url).rstrip("/"), settings.xkiro_api_key)
        yield
        await app.state.http.aclose()

    app = FastAPI(title="Xkiro Image API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings

    @app.middleware("http")
    async def limit_body(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                too_large = int(content_length) > settings.max_body_bytes
            except ValueError:
                return error_response(ApiError("Invalid Content-Length", 400, "invalid_request_error"))
            if too_large:
                return error_response(ApiError("Request body is too large", 413, "invalid_request_error", code="body_too_large"))
        return await call_next(request)

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError):
        return error_response(exc)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError):
        return error_response(ApiError("Invalid request", 400, "invalid_request_error"))

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/v1/images/generations", dependencies=[Depends(require_api_key)])
    async def generations(request: Request):
        try:
            payload = await request.json()
        except ValueError as exc:
            raise ApiError("Request body must be valid JSON", 400, "invalid_request_error") from exc
        if not isinstance(payload, dict):
            raise ApiError("Request body must be a JSON object", 400, "invalid_request_error")
        upstream, response_format = select_parameters(payload, GENERATION_FIELDS, settings.strict_parameters)
        client: XkiroClient = request.app.state.xkiro
        created = await client.create_generation(upstream)
        job_id = created.get("id")
        if not job_id:
            raise ApiError("Xkiro returned no job id", 502, "api_error", code="invalid_upstream_response")
        job = await wait_for_job(client.get_job, job_id, settings.upstream_timeout_seconds)
        return await build_response(job, response_format, client.download)

    @app.post("/v1/images/edits", dependencies=[Depends(require_api_key)])
    async def edits(request: Request):
        form = await request.form()
        images = form.getlist("image")
        if not images or any(not isinstance(image, UploadFile) for image in images):
            raise ApiError("At least one image file is required", 400, "invalid_request_error", "image")
        allowed = {"prompt", "model", "size", "n", "response_format"}
        fields = {key: form[key] for key in form if key != "image" and key in allowed}
        unknown = {key for key in form if key not in allowed and key != "image"}
        if settings.strict_parameters and unknown:
            name = sorted(unknown)[0]
            raise ApiError(f"Unsupported parameter: {name}", 400, "invalid_request_error", name, "unsupported_parameter")
        upstream, selected_format = select_parameters(fields, EDIT_FIELDS, settings.strict_parameters)
        files = []
        for image in images:
            content = await image.read()
            if not content:
                raise ApiError("Image file is empty", 400, "invalid_request_error", "image")
            detected_type = detect_image_type(content)
            if detected_type is None:
                raise ApiError("Image must be JPEG, PNG, GIF, or WebP", 400, "invalid_request_error", "image")
            files.append((image.filename or "image", content, detected_type))
        client: XkiroClient = request.app.state.xkiro
        created = await client.create_edit(files, upstream)
        job_id = created.get("id")
        if not job_id:
            raise ApiError("Xkiro returned no job id", 502, "api_error", code="invalid_upstream_response")
        job = await wait_for_job(client.get_job, job_id, settings.upstream_timeout_seconds)
        return await build_response(job, selected_format, client.download)

    @app.get("/v1/models", dependencies=[Depends(require_api_key)])
    async def models(request: Request):
        return await request.app.state.xkiro.list_models()

    return app


app = create_app()
