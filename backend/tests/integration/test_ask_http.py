"""Public Ask HTTP errors stay useful when a model cannot be used."""

import json
from datetime import UTC, datetime

import httpx
import pytest
from fastapi import FastAPI
from openai import OpenAIError

from knowli.domain.user import User
from knowli.interfaces.http import ask, auth
from knowli.interfaces.http.errors import register_error_handlers


class UnavailableAskService:
    def stream_ask(self, question: str, user_id: str, thread_id: str):
        raise OpenAIError("Missing credentials")
        yield  # pragma: no cover - keeps this a generator


class CitingAskService:
    """Streams what the real service streams: claims carry a datetime."""

    def stream_ask(self, question: str, user_id: str, thread_id: str):
        yield {
            "type": "claims",
            "items": [
                {
                    "id": "claim-1",
                    "statement": "Deploy on Tuesdays.",
                    "contribution_created_at": datetime(2026, 7, 30, tzinfo=UTC),
                }
            ],
        }
        yield {"type": "token", "content": "Tuesdays."}
        yield {"type": "done"}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_ask_stream_reports_an_unconfigured_model_as_a_stable_code():
    """A started stream cannot change status, and provider text is not for the reader."""
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
        response = await client.get(
            "/api/ask/stream", params={"question": "What is the rule?", "thread_id": "t-1"}
        )

    assert response.status_code == 200
    assert response.text.strip() == 'data: {"type": "error", "code": "model_unavailable"}'
    assert "Missing credentials" not in response.text


@pytest.mark.anyio
async def test_every_streamed_event_reaches_the_client_as_parseable_sse():
    """A claim's datetime is not JSON by itself: unserializable, the first event raises
    and the reader gets one error instead of the answer."""
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(ask.router)
    app.dependency_overrides[ask.get_ask_service] = CitingAskService
    app.dependency_overrides[auth.require_user] = lambda: User(
        id="user-1", email="demo@knowli.local", display_name="Demo"
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/api/ask/stream", params={"question": "When do we deploy?", "thread_id": "t-1"}
        )

    payloads = [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]

    assert [payload["type"] for payload in payloads] == ["claims", "token", "done"]
    assert payloads[0]["items"][0]["contribution_created_at"].startswith("2026-07-30")
