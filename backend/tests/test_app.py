"""The assembled web application exposes only the authenticated product API."""

import importlib.util

import httpx
import pytest

from knowli.interfaces.http import create_app


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
    assert "/api/transcribe/live" not in paths
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
        ("GET", "/api/users", None),
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
