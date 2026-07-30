"""The public cookie-session contract for the authentication router."""

import httpx
import pytest
from fastapi import FastAPI

from knowli.application.auth import AuthService
from knowli.interfaces.http import auth
from knowli.interfaces.http.errors import register_error_handlers
from tests.test_auth import MemorySessionStore


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _client() -> httpx.AsyncClient:
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(auth.router)
    service = AuthService(MemorySessionStore(), session_days=14)
    app.dependency_overrides[auth.get_auth_service] = lambda: service
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")


@pytest.mark.anyio
async def test_register_sets_a_safe_session_cookie_and_returns_a_public_user():
    """A register response must not expose a password and must establish a session."""
    async with _client() as client:
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "ada@example.test",
                "password": "correct horse battery staple",
                "display_name": "Ada",
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "user": {"id": "1", "email": "ada@example.test", "display_name": "Ada"}
    }
    cookie = response.headers["set-cookie"].lower()
    assert "knowli_session=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


@pytest.mark.anyio
async def test_login_me_and_logout_follow_the_session_contract():
    """Changing endpoint wiring must preserve the complete cookie lifecycle."""
    async with _client() as client:
        await client.post(
            "/api/auth/register",
            json={
                "email": "ada@example.test",
                "password": "correct horse battery staple",
                "display_name": "Ada",
            },
        )

        login = await client.post(
            "/api/auth/login",
            json={"email": "ada@example.test", "password": "correct horse battery staple"},
        )
        me = await client.get("/api/auth/me")
        logout = await client.post("/api/auth/logout")
        after_logout = await client.get("/api/auth/me")

    assert login.status_code == 200
    assert login.json() == {
        "user": {"id": "1", "email": "ada@example.test", "display_name": "Ada"}
    }
    assert me.status_code == 200
    assert me.json() == {
        "user": {"id": "1", "email": "ada@example.test", "display_name": "Ada"}
    }
    assert logout.status_code == 204
    assert after_logout.status_code == 401
    assert after_logout.json() == {
        "code": "unauthenticated", "message": "sign in required"
    }


@pytest.mark.anyio
async def test_register_rejects_a_duplicate_email_without_a_server_error():
    """A database uniqueness failure must remain a stable client conflict."""
    payload = {
        "email": "ada@example.test",
        "password": "correct horse battery staple",
        "display_name": "Ada",
    }
    async with _client() as client:
        await client.post("/api/auth/register", json=payload)
        response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 409
    assert response.json() == {"code": "duplicate_email", "message": "email is already registered"}
