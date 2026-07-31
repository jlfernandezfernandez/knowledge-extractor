"""Local email/password authentication with opaque server-side sessions."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import secrets
from typing import Callable

from pwdlib import PasswordHash

from ..domain.ports import SessionStore
from ..domain.user import DuplicateEmail, User

DEMO_EMAIL = "demo@knowli.local"
DEMO_PASSWORD = "demo"
DEMO_DISPLAY_NAME = "Demo"


class InvalidCredentials(Exception):
    """Raised when an email/password pair cannot authenticate."""


class SessionExpired(Exception):
    """Raised when a session cookie is missing, unknown, or expired."""


class InvalidRegistration(Exception):
    """Raised when a submitted registration does not meet product rules."""

    def __init__(self, fields: dict[str, str]):
        self.fields = fields


@dataclass(frozen=True)
class AuthResult:
    user: User
    token: str


def ensure_demo_account(store: SessionStore) -> None:
    """Create the documented local demo account once, without changing it."""
    if store.get_user_credentials(DEMO_EMAIL) is not None:
        return
    try:
        store.create_user(
            DEMO_EMAIL,
            DEMO_DISPLAY_NAME,
            PasswordHash.recommended().hash(DEMO_PASSWORD),
        )
    except DuplicateEmail:
        pass


class AuthService:
    def __init__(
        self,
        store: SessionStore,
        session_days: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._session_days = session_days
        self._clock = clock or (lambda: datetime.now(UTC))
        self._passwords = PasswordHash.recommended()

    def register(self, email: str, password: str, display_name: str) -> AuthResult:
        email, display_name = self._validated_registration(email, password, display_name)
        user = self._store.create_user(email, display_name, self._passwords.hash(password))
        return self._session_for(user)

    def login(self, email: str, password: str) -> AuthResult:
        credentials = self._store.get_user_credentials(email.strip().lower())
        if credentials is None or not self._passwords.verify(password, credentials.password_hash):
            raise InvalidCredentials()
        self._store.delete_user_sessions(credentials.user.id)
        return self._session_for(credentials.user)

    def authenticate(self, raw_token: str) -> User:
        user = self._store.get_user_by_session(self._token_hash(raw_token), self._clock())
        if user is None:
            raise SessionExpired()
        return user

    def list_users(self, exclude_user_id: str) -> list[User]:
        return self._store.list_users(exclude_user_id)

    def logout(self, raw_token: str) -> None:
        self._store.delete_session(self._token_hash(raw_token))

    def _session_for(self, user: User) -> AuthResult:
        token = secrets.token_urlsafe(32)
        self._store.create_session(
            user.id,
            self._token_hash(token),
            self._clock() + timedelta(days=self._session_days),
        )
        return AuthResult(user=user, token=token)

    @staticmethod
    def _token_hash(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode()).hexdigest()

    @staticmethod
    def _validated_registration(email: str, password: str, display_name: str) -> tuple[str, str]:
        normalized_email = email.strip().lower()
        normalized_name = display_name.strip()
        fields = {}
        if not normalized_email:
            fields["email"] = "email is required"
        if len(password) < 8:
            fields["password"] = "password must contain at least 8 characters"
        if not normalized_name:
            fields["display_name"] = "display name is required"
        if fields:
            raise InvalidRegistration(fields)
        return normalized_email, normalized_name
