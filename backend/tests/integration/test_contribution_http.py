"""Public contribution HTTP and SSE contracts."""

from datetime import UTC, datetime

import httpx
import pytest
from fastapi import FastAPI
from fastapi.sse import ServerSentEvent

from knowli.domain.contribution import StaleRevision
from knowli.domain.user import User
from knowli.interfaces.http import auth, review
from knowli.interfaces.http.errors import register_error_handlers
from knowli.interfaces.http.sse import review_events


class FakeContributionService:
    def __init__(self):
        self.state = {
            "id": "00000000-0000-0000-0000-000000000001",
            "author_id": "author-1",
            "author": "Ada",
            "kind": "voluntary",
            "source": "text",
            "raw_text": "Deploy on Tuesdays.",
            "stage": "claims",
            "revision": 1,
            "summary": "A deployment rule.",
            "created_at": datetime(2026, 7, 30, tzinfo=UTC),
            "committed_at": None,
            "claim_count": 0,
            "claims": [],
            "conflicts": [],
        }

    def capture(self, user_id, raw_text, source, interview_id=None):
        self.state = {**self.state, "author_id": user_id, "raw_text": raw_text, "source": source}
        return self.state

    def _check(self, user_id, contribution_id):
        from knowli.application.review import ContributionUnavailable

        if user_id != self.state["author_id"] or contribution_id != self.state["id"]:
            raise ContributionUnavailable(contribution_id)

    def get(self, user_id, contribution_id):
        self._check(user_id, contribution_id)
        return self.state

    def confirm_claims(self, user_id, contribution_id, revision, claims):
        self._check(user_id, contribution_id)
        if revision != self.state["revision"]:
            raise StaleRevision(contribution_id)
        self.state = {**self.state, "stage": "conflicts", "revision": revision + 1, "claims": claims}
        return self.state

    def resolve_conflicts(self, user_id, contribution_id, revision, resolutions):
        self._check(user_id, contribution_id)
        self.state = {**self.state, "stage": "commit", "revision": revision + 1}
        return self.state

    def commit(self, user_id, contribution_id, revision):
        self._check(user_id, contribution_id)
        self.state = {**self.state, "stage": "committed", "revision": revision + 1}
        return self.state

    def back(self, user_id, contribution_id, revision):
        self._check(user_id, contribution_id)
        self.state = {**self.state, "stage": "claims", "revision": revision + 1}
        return self.state


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def service():
    return FakeContributionService()


def _client(service, user_id="author-1"):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(review.router)
    app.dependency_overrides[review.get_contribution_service] = lambda: service
    app.dependency_overrides[auth.require_user] = lambda: User(
        id=user_id, email=f"{user_id}@example.test", display_name=user_id
    )
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
    )


@pytest.mark.anyio
async def test_all_contribution_mutations_require_the_author(service):
    async with _client(service, "author-2") as client:
        read = await client.get("/api/contributions/00000000-0000-0000-0000-000000000001")
        confirm = await client.post(
            "/api/contributions/00000000-0000-0000-0000-000000000001/confirm",
            json={"revision": 1, "claims": []},
        )

    assert read.status_code == 404
    assert confirm.status_code == 404


@pytest.mark.anyio
async def test_create_and_edit_use_public_contribution_contracts(service):
    async with _client(service) as client:
        created = await client.post(
            "/api/contributions",
            json={"raw_text": "Deploy on Tuesdays.", "source": "text"},
        )
        confirmed = await client.post(
            f"/api/contributions/{service.state['id']}/confirm",
            json={"revision": 1, "claims": []},
        )

    assert created.status_code == 201
    assert created.json()["revision"] == 1
    assert confirmed.status_code == 200
    assert confirmed.json()["stage"] == "conflicts"


@pytest.mark.anyio
async def test_capture_source_is_owned_by_the_server(service):
    async with _client(service) as client:
        response = await client.post(
            "/api/contributions",
            json={"raw_text": "A dictated rule.", "source": "speech"},
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_generic_capture_rejects_an_interview_id(service):
    """Accepting an interview id here would bypass assignee and started-status checks."""
    async with _client(service) as client:
        response = await client.post(
            "/api/contributions",
            json={
                "raw_text": "An unauthorized interview answer.",
                "source": "text",
                "interview_id": "00000000-0000-0000-0000-000000000001",
            },
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_stale_revision_has_stable_http_conflict(service):
    async with _client(service) as client:
        response = await client.post(
            f"/api/contributions/{service.state['id']}/confirm",
            json={"revision": 0, "claims": []},
        )

    assert response.status_code == 409
    assert response.json() == {
        "code": "stale_revision",
        "message": "contribution changed; refresh and try again",
    }


@pytest.mark.anyio
async def test_sse_reconnect_sends_only_a_newer_revision(service):
    newer = review_events(service, "author-1", service.state["id"], last_event_id="0")
    current = review_events(
        service,
        "author-1",
        service.state["id"],
        last_event_id="1",
        heartbeat_seconds=0,
    )

    event = await anext(newer)
    heartbeat = await anext(current)
    await newer.aclose()
    await current.aclose()

    assert isinstance(event, ServerSentEvent)
    assert (event.id, event.event, event.data["revision"]) == ("1", "review", 1)
    assert heartbeat.comment == "heartbeat"


@pytest.mark.anyio
async def test_sse_checks_ownership_before_starting_the_stream(service):
    async with _client(service, "author-2") as client:
        unauthorized = await client.get(
            f"/api/contributions/{service.state['id']}/events"
        )
    async with _client(service) as client:
        missing = await client.get(
            "/api/contributions/00000000-0000-0000-0000-000000000099/events"
        )

    assert unauthorized.status_code == 404
    assert missing.status_code == 404
