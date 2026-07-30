"""The assembled web application exposes only the authenticated product API."""

import importlib.util

import httpx
import pytest
from starlette.testclient import TestClient, WebSocketDenialResponse

from knowli.interfaces.http import create_app
from knowli.interfaces.http import auth


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _routes(app):
    """FastAPI 0.115 and 0.116 expose included routers differently."""
    for route in app.routes:
        router = getattr(route, "original_router", None)
        yield from router.routes if router is not None else (route,)


@pytest.mark.anyio
async def test_web_app_has_only_the_cookie_protected_product_surface():
    """Mounting a product route without auth would expose data or construct its services."""
    app = create_app()
    paths = {route.path for route in _routes(app) if hasattr(route, "path")}

    assert {"/api/health/live", "/api/health/ready"} <= paths
    assert all("a2a" not in path.lower() and "mcp" not in path.lower() for path in paths)
    assert importlib.util.find_spec("knowli.interfaces.a2a") is None
    assert importlib.util.find_spec("knowli.interfaces.mcp") is None

    requests = (
        ("GET", "/api/contributions/example", None),
        ("POST", "/api/contributions", {"raw_text": "A rule.", "source": "text"}),
        ("POST", "/api/contributions/example/confirm", {"revision": 1, "claims": []}),
        ("POST", "/api/contributions/example/resolve", {"revision": 1, "resolutions": []}),
        ("POST", "/api/contributions/example/commit", {"revision": 1}),
        ("POST", "/api/contributions/example/back", {"revision": 1}),
        ("GET", "/api/contributions/example/events", None),
        ("GET", "/api/interviews", None),
        (
            "POST",
            "/api/interviews",
            {"assignee_id": "example", "title": "Rule", "brief": "Explain it."},
        ),
        ("POST", "/api/interviews/example/start", None),
        ("POST", "/api/interviews/example/answer", {"raw_text": "A rule."}),
        ("POST", "/api/ask", {"question": "What is the rule?"}),
        ("GET", "/api/history", None),
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        for method, path, body in requests:
            response = await client.request(method, path, json=body)
            assert response.status_code == 401, f"{method} {path}: {response.text}"


def test_transcription_websocket_requires_a_session_cookie():
    """Checking speech before auth would reveal optional service state publicly."""
    with TestClient(create_app()) as client:
        with pytest.raises(WebSocketDenialResponse) as denied:
            with client.websocket_connect("/api/transcribe/live"):
                pass

    assert denied.value.status_code == 401


def test_transcription_websocket_reports_disabled_speech_to_authenticated_users(
    monkeypatch: pytest.MonkeyPatch,
):
    """An optional speech install must deny consistently instead of raising an import error."""
    class AuthenticatedSession:
        def authenticate(self, _: str) -> object:
            return object()

    app = create_app()
    app.dependency_overrides[auth.get_auth_service] = AuthenticatedSession
    monkeypatch.setattr(
        "knowli.interfaces.http.speech.wiring.speech_available", lambda: False
    )

    with TestClient(app) as client:
        client.cookies.set("knowli_session", "token")
        with pytest.raises(WebSocketDenialResponse) as denied:
            with client.websocket_connect("/api/transcribe/live"):
                pass

    assert denied.value.status_code == 501
    assert denied.value.json() == {
        "code": "speech_unavailable",
        "message": "speech is not available",
    }
