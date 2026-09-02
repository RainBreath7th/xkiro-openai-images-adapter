from __future__ import annotations

from collections.abc import Sequence

import httpx

from app.exceptions import ApiError, upstream_error


ImagePart = tuple[str, bytes, str]


class XkiroClient:
    def __init__(self, client: httpx.AsyncClient, base_url: str, api_key: str):
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"}

    async def _json(self, response: httpx.Response) -> dict:
        if response.status_code >= 400:
            try:
                body = response.json()
                message = body.get("error", {}).get("message", str(body))
            except ValueError:
                message = "Xkiro returned an invalid error response"
            raise upstream_error(response.status_code, message)
        try:
            return response.json()
        except ValueError as exc:
            raise ApiError("Xkiro returned invalid JSON", 502, "api_error", code="invalid_upstream_response") from exc

    async def create_generation(self, payload: dict) -> dict:
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/images/generations", headers=self.headers, json=payload
            )
        except httpx.HTTPError as exc:
            raise ApiError("Unable to reach Xkiro", 502, "api_error", code="upstream_connection_error") from exc
        return await self._json(response)

    async def create_edit(self, images: Sequence[ImagePart], data: dict) -> dict:
        files = [("image", image) for image in images]
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/images/edits", headers=self.headers, files=files, data=data
            )
        except httpx.HTTPError as exc:
            raise ApiError("Unable to reach Xkiro", 502, "api_error", code="upstream_connection_error") from exc
        return await self._json(response)

    async def get_job(self, job_id: str) -> dict:
        try:
            response = await self.client.get(
                f"{self.base_url}/v1/images/generations/{job_id}", headers=self.headers
            )
        except httpx.HTTPError as exc:
            raise ApiError("Unable to reach Xkiro", 502, "api_error", code="upstream_connection_error") from exc
        return await self._json(response)

    async def list_models(self) -> dict:
        try:
            response = await self.client.get(
                f"{self.base_url}/v1/models", headers=self.headers, params={"modality": "image"}
            )
        except httpx.HTTPError as exc:
            raise ApiError("Unable to reach Xkiro", 502, "api_error", code="upstream_connection_error") from exc
        return await self._json(response)

    async def download(self, url: str) -> bytes:
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.content
        except httpx.HTTPError as exc:
            raise ApiError("Unable to download generated image", 502, "api_error", code="image_download_failed") from exc
