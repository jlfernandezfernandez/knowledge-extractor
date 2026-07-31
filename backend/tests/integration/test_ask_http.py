"""Public Ask HTTP errors stay useful when a model cannot be used."""

import httpx
import pytest
from fastapi import FastAPI
from openai import OpenAIError

from knowli.domain.user import User
from knowli.interfaces.http import ask, auth
from knowli.interfaces.http.errors import register_error_handlers


class UnavailableAskService:
    def ask(self, _: str) -> dict:
        raise OpenAIError("Missing credentials")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_ask_reports_an_unconfigured_model_without_an_internal_error():
    """Leaking the provider error makes a missing local setting look like an app bug."""
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(ask.router)
    app.dependency_overrides[ask.get_ask_service] = UnavailableAskService
    app.dependency_overrides[auth.require_user] = lambda: User(
        id="user-1", email="demo@knowli.local", display_name="Demo"
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
    ) as client:
        response = await client.post("/api/ask", json={"question": "What is the rule?"})

    assert response.status_code == 503
    assert response.json() == {
        "code": "model_unavailable",
        "message": "configure a model to use Ask",
    }
