import os

os.environ.setdefault("API_KEY", "client-key")
os.environ.setdefault("XKIRO_API_KEY", "upstream-key")

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings():
    return Settings(api_key="client-key", xkiro_api_key="upstream-key", upstream_timeout_seconds=0.01)


@pytest.fixture
async def client(settings):
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
            yield value
