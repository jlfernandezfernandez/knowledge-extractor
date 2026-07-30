"""Authenticated public routes delegate interview, ask, and history behaviour."""

from datetime import UTC, datetime

import httpx
import pytest
from fastapi import FastAPI

from knowli.domain.interview import Interview, InterviewStart
from knowli.domain.user import User
from knowli.interfaces.http import ask, auth, history, interviews
from knowli.interfaces.http.errors import register_error_handlers


class FakeInterviewService:
    def __init__(self) -> None:
        self.interview = Interview(
            id="interview-1",
            requester_id="requester",
            assignee_id="assignee",
            title="Release process",
            brief="Describe the release process.",
            status="pending",
            created_at=datetime(2026, 7, 30, tzinfo=UTC),
            started_at=None,
            completed_at=None,
        )
        self.answer_calls = []

    def list(self, user_id, view):
        return [self.interview]

    def create(self, requester_id, assignee_id, title, brief):
        return self.interview

    def start(self, user_id, interview_id):
        return InterviewStart(self.interview, "contribution-1")

    def by_contribution(self, user_id, contribution_id):
        if user_id not in {self.interview.requester_id, self.interview.assignee_id}:
            from knowli.application.interviews import InterviewUnavailable
            raise InterviewUnavailable(contribution_id)
        return self.interview

    def answer(self, user_id, interview_id, raw_text, contribution_service):
        self.answer_calls.append((user_id, interview_id, raw_text, contribution_service))
        return {"id": "contribution-1", "raw_text": raw_text}


class FakeAskService:
    def ask(self, question):
        return {"answer": "Answer", "citations": [], "sufficient_evidence": True}

    def history(self, cursor, limit):
        return {"items": [], "next_cursor": None}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client(interview_service, ask_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(interviews.router)
    app.include_router(ask.router)
    app.include_router(history.router)
    app.dependency_overrides[interviews.get_interview_service] = lambda: interview_service
    app.dependency_overrides[interviews.get_contribution_service] = lambda: object()
    app.dependency_overrides[ask.get_ask_service] = lambda: ask_service
    app.dependency_overrides[history.get_ask_service] = lambda: ask_service
    app.dependency_overrides[auth.require_user] = lambda: User(
        id="assignee", email="assignee@example.test", display_name="Assignee"
    )
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
    )


class InvalidCursorStore:
    def list_history(self, cursor, limit):
        raise ValueError("invalid history cursor")


def _invalid_cursor_client():
    from knowli.application.ask import HistoryService

    app = FastAPI()
    register_error_handlers(app)
    app.include_router(history.router)
    app.dependency_overrides[history.get_ask_service] = lambda: HistoryService(InvalidCursorStore())
    app.dependency_overrides[auth.require_user] = lambda: User(
        id="assignee", email="assignee@example.test", display_name="Assignee"
    )
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
    )


@pytest.mark.anyio
async def test_global_routes_require_auth_and_use_the_global_contract():
    """Reintroducing the old team router would reject this authenticated global request."""
    interview_service = FakeInterviewService()
    async with _client(interview_service, FakeAskService()) as client:
        listed = await client.get("/api/interviews?view=pending")
        context = await client.get("/api/interviews/by-contribution/contribution-1")
        started = await client.post("/api/interviews/interview-1/start")
        answered = await client.post(
            "/api/interviews/interview-1/answer", json={"raw_text": "We deploy on Tuesdays."}
        )
        asked = await client.post("/api/ask", json={"question": "When do we deploy?"})
        listed_history = await client.get("/api/history?limit=20")

    assert listed.json()["items"][0]["assignee_id"] == "assignee"
    assert context.json()["title"] == "Release process"
    assert started.json()["contribution_id"] == "contribution-1"
    assert answered.json() == {"id": "contribution-1", "raw_text": "We deploy on Tuesdays."}
    assert interview_service.answer_calls[0][:3] == (
        "assignee", "interview-1", "We deploy on Tuesdays."
    )
    assert asked.json()["sufficient_evidence"] is True
    assert listed_history.json() == {"items": [], "next_cursor": None}


@pytest.mark.anyio
async def test_malformed_history_cursor_has_a_stable_client_error():
    """An opaque cursor belongs to the client contract and must not produce a server error."""
    async with _invalid_cursor_client() as client:
        response = await client.get("/api/history?cursor=not-a-cursor")

    assert response.status_code == 400
    assert response.json() == {
        "code": "invalid_history_cursor",
        "message": "invalid history cursor",
    }
