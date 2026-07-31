"""PostgreSQL implementation of the User & Session store (SessionStore port)."""

from datetime import datetime

from psycopg.errors import UniqueViolation
from psycopg_pool import ConnectionPool

from ...domain.user import DuplicateEmail, User, UserCredentials
from .pool import pool as configured_pool


class PostgresUserStore:
    """Handles user accounts, authentication credentials, and server-side sessions."""

    def __init__(self, connection_pool: ConnectionPool | None = None):
        self._pool = connection_pool or configured_pool()

    def create_user(self, email: str, display_name: str, password_hash: str) -> User:
        try:
            with self._pool.connection() as connection:
                row = connection.execute(
                    """INSERT INTO app_user (email, display_name, password_hash)
                       VALUES (%s, %s, %s)
                       RETURNING id::text, email, display_name""",
                    (email, display_name, password_hash),
                ).fetchone()
        except UniqueViolation as error:
            raise DuplicateEmail(email) from error
        assert row is not None
        return User(id=row[0], email=row[1], display_name=row[2])

    def get_user_credentials(self, email: str) -> UserCredentials | None:
        with self._pool.connection() as connection:
            row = connection.execute(
                """SELECT id::text, email, display_name, password_hash
                   FROM app_user WHERE lower(email) = lower(%s)""",
                (email,),
            ).fetchone()
        if row is None:
            return None
        return UserCredentials(
            user=User(id=row[0], email=row[1], display_name=row[2]), password_hash=row[3]
        )

    def list_users(self, exclude_user_id: str) -> list[User]:
        with self._pool.connection() as connection:
            rows = connection.execute(
                """SELECT id::text, email, display_name FROM app_user
                   WHERE id <> %s ORDER BY display_name, email""",
                (exclude_user_id,),
            ).fetchall()
        return [User(id=row[0], email=row[1], display_name=row[2]) for row in rows]

    def create_session(self, user_id: str, token_hash: str, expires_at: datetime) -> None:
        with self._pool.connection() as connection:
            connection.execute(
                """INSERT INTO login_session (token_hash, user_id, expires_at)
                   VALUES (%s, %s, %s)""",
                (token_hash, user_id, expires_at),
            )

    def get_user_by_session(self, token_hash: str, now: datetime) -> User | None:
        with self._pool.connection() as connection:
            row = connection.execute(
                """SELECT user_account.id::text, user_account.email, user_account.display_name
                   FROM login_session
                   JOIN app_user user_account ON user_account.id = login_session.user_id
                   WHERE login_session.token_hash = %s AND login_session.expires_at > %s""",
                (token_hash, now),
            ).fetchone()
        return User(id=row[0], email=row[1], display_name=row[2]) if row else None

    def delete_session(self, token_hash: str) -> None:
        with self._pool.connection() as connection:
            connection.execute("DELETE FROM login_session WHERE token_hash = %s", (token_hash,))

    def delete_user_sessions(self, user_id: str) -> None:
        with self._pool.connection() as connection:
            connection.execute("DELETE FROM login_session WHERE user_id = %s", (user_id,))
