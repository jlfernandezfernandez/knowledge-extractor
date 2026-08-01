"""PostgreSQL implementation of the Interview store (InterviewStore port)."""

import psycopg
from psycopg_pool import ConnectionPool

from ...domain.interview import Interview, InterviewStart, InterviewView
from ...domain.user import User
from .pool import pool as configured_pool


class PostgresInterviewStore:
    """Handles interview requests, assignments, and status transitions."""

    def __init__(self, connection_pool: ConnectionPool | None = None):
        self._pool = connection_pool or configured_pool()

    @staticmethod
    def _interview(row: tuple) -> Interview:
        return Interview(
            id=row[0], requester_id=row[1], assignee_id=row[2], title=row[3],
            brief=row[4] or "", status=row[5], created_at=row[6], started_at=row[7],
            completed_at=row[8],
        )

    def get_user_by_id(self, user_id: str) -> User | None:
        try:
            with self._pool.connection() as connection:
                row = connection.execute(
                    "SELECT id::text, email, display_name FROM app_user WHERE id = %s", (user_id,)
                ).fetchone()
            return User(id=row[0], email=row[1], display_name=row[2]) if row else None
        except psycopg.DataError:
            return None

    def create_interview(
        self, requester_id: str, assignee_id: str, title: str, brief: str
    ) -> Interview:
        with self._pool.connection() as connection:
            row = connection.execute(
                """INSERT INTO interview (requester_id, assignee_id, title, brief)
                   VALUES (%s, %s, %s, %s)
                   RETURNING id::text, requester_id::text, assignee_id::text, title, brief,
                             status, created_at, started_at, completed_at""",
                (requester_id, assignee_id, title, brief),
            ).fetchone()
        assert row is not None
        return self._interview(row)

    def get_interview(self, interview_id: str) -> Interview | None:
        try:
            with self._pool.connection() as connection:
                row = connection.execute(
                    """SELECT id::text, requester_id::text, assignee_id::text, title, brief,
                              status, created_at, started_at, completed_at
                       FROM interview WHERE id = %s""",
                    (interview_id,),
                ).fetchone()
            return self._interview(row) if row else None
        except psycopg.DataError:
            return None

    def get_interview_by_contribution(self, contribution_id: str) -> Interview | None:
        try:
            with self._pool.connection() as connection:
                row = connection.execute(
                    """SELECT interview.id::text, interview.requester_id::text,
                              interview.assignee_id::text, interview.title, interview.brief,
                              interview.status, interview.created_at, interview.started_at,
                              interview.completed_at
                       FROM interview
                       JOIN contribution ON contribution.interview_id = interview.id
                       WHERE contribution.id = %s""",
                    (contribution_id,),
                ).fetchone()
            return self._interview(row) if row else None
        except psycopg.DataError:
            return None

    def list_interviews(self, user_id: str, view: InterviewView) -> list[Interview]:
        condition = "assignee_id = %s AND status IN ('pending', 'started')"
        if view == "sent":
            condition = "requester_id = %s AND status IN ('pending', 'started')"
        elif view == "completed":
            condition = "(requester_id = %s OR assignee_id = %s) AND status = 'completed'"

        params = (user_id, user_id) if view == "completed" else (user_id,)
        with self._pool.connection() as connection:
            rows = connection.execute(
                f"""SELECT id::text, requester_id::text, assignee_id::text, title, brief,
                           status, created_at, started_at, completed_at
                    FROM interview WHERE {condition}
                    ORDER BY created_at DESC""",
                params,
            ).fetchall()
        return [self._interview(row) for row in rows]

    def start_interview(self, interview_id: str, assignee_id: str) -> InterviewStart | None:
        with self._pool.connection() as connection:
            row = connection.execute(
                """SELECT id::text, requester_id::text, assignee_id::text, title, brief,
                          status, created_at, started_at, completed_at
                   FROM interview WHERE id = %s AND assignee_id = %s FOR UPDATE""",
                (interview_id, assignee_id),
            ).fetchone()
            if row is None:
                return None
            interview = self._interview(row)
            if interview.status == "pending":
                row = connection.execute(
                    """UPDATE interview SET status = 'started', started_at = now()
                       WHERE id = %s
                       RETURNING id::text, requester_id::text, assignee_id::text, title, brief,
                                 status, created_at, started_at, completed_at""",
                    (interview_id,),
                ).fetchone()
                assert row is not None
                interview = self._interview(row)
            contribution_row = connection.execute(
                """INSERT INTO contribution
                   (author_id, interview_id, raw_text, stage)
                   VALUES (%s, %s, '', 'claims')
                   ON CONFLICT (interview_id) DO UPDATE SET interview_id = EXCLUDED.interview_id
                   RETURNING id::text""",
                (assignee_id, interview_id),
            ).fetchone()
            assert contribution_row is not None
            return InterviewStart(interview, contribution_row[0])
