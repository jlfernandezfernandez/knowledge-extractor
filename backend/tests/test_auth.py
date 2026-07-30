"""Authentication behaviours independent from HTTP and PostgreSQL."""

from datetime import UTC, datetime, timedelta

import pytest

from knowli.application.auth import AuthService, InvalidCredentials, SessionExpired
from knowli.domain.user import DuplicateEmail, User, UserCredentials


class MemorySessionStore:
    """A complete, in-memory implementation of the auth storage boundary."""

    def __init__(self) -> None:
        self.users: dict[str, UserCredentials] = {}
        self.sessions: dict[str, tuple[str, datetime]] = {}

    def create_user(self, email: str, display_name: str, password_hash: str) -> User:
        if email in self.users:
            raise DuplicateEmail(email)
        user = User(id=str(len(self.users) + 1), email=email, display_name=display_name)
        self.users[email] = UserCredentials(user=user, password_hash=password_hash)
        return user

    def get_user_credentials(self, email: str) -> UserCredentials | None:
        return self.users.get(email)

    def create_session(self, user_id: str, token_hash: str, expires_at: datetime) -> None:
        self.sessions[token_hash] = (user_id, expires_at)

    def get_user_by_session(self, token_hash: str, now: datetime) -> User | None:
        session = self.sessions.get(token_hash)
        if session is None or session[1] <= now:
            return None
        return next(
            credentials.user
            for credentials in self.users.values()
            if credentials.user.id == session[0]
        )

    def delete_session(self, token_hash: str) -> None:
        self.sessions.pop(token_hash, None)


def test_register_hashes_password_and_creates_an_opaque_session():
    """Plaintext password persistence would make this registration unsafe."""
    store = MemorySessionStore()
    service = AuthService(store, session_days=14)

    result = service.register("  ADA@Example.Test ", "correct horse battery staple", " Ada ")

    credentials = store.users["ada@example.test"]
    assert result.user == User(id="1", email="ada@example.test", display_name="Ada")
    assert credentials.password_hash != "correct horse battery staple"
    assert result.token not in store.sessions
    assert service.authenticate(result.token) == result.user


def test_login_rejects_a_wrong_password():
    """Removing password verification must prevent login with a wrong secret."""
    service = AuthService(MemorySessionStore(), session_days=14)
    service.register("ada@example.test", "correct horse battery staple", "Ada")

    with pytest.raises(InvalidCredentials):
        service.login("ada@example.test", "wrong password")


def test_authenticate_rejects_an_expired_session():
    """Ignoring expiry would allow an old cookie to regain access."""
    now = datetime(2030, 1, 1, tzinfo=UTC)
    store = MemorySessionStore()
    service = AuthService(store, session_days=14, clock=lambda: now)
    result = service.register("ada@example.test", "correct horse battery staple", "Ada")
    store.sessions = {
        token_hash: (user_id, now - timedelta(seconds=1))
        for token_hash, (user_id, _) in store.sessions.items()
    }

    with pytest.raises(SessionExpired):
        service.authenticate(result.token)


def test_login_rotates_the_session_token():
    """Reusing a login token would leave a stolen cookie valid indefinitely."""
    service = AuthService(MemorySessionStore(), session_days=14)
    registered = service.register("ada@example.test", "correct horse battery staple", "Ada")

    logged_in = service.login("ada@example.test", "correct horse battery staple")

    assert logged_in.user == registered.user
    assert logged_in.token != registered.token
    assert service.authenticate(logged_in.token) == registered.user


def test_logout_invalidates_the_session():
    """A deleted session must no longer authenticate the browser cookie."""
    service = AuthService(MemorySessionStore(), session_days=14)
    result = service.register("ada@example.test", "correct horse battery staple", "Ada")

    service.logout(result.token)

    with pytest.raises(SessionExpired):
        service.authenticate(result.token)
