"""The PostgreSQL-backed global contribution, interview, and session store."""

import base64
import json
from datetime import datetime

from psycopg.errors import UniqueViolation
from psycopg_pool import ConnectionPool

from ...domain.claim import ClaimSearchResult, ClaimToCommit
from ...domain.contribution import (
    ContributionNotFound,
    HistoryItem,
    StaleRevision,
    StoredContribution,
)
from ...domain.interview import Interview, InterviewStart, InterviewView
from ...domain.user import DuplicateEmail, User, UserCredentials
from .pool import pool as configured_pool


class PostgresStore:
    """The PostgreSQL-backed implementation of all domain store ports."""

    def __init__(self, connection_pool: ConnectionPool | None = None):
        self._pool = connection_pool or configured_pool()

    @staticmethod
    def _stored(row: tuple) -> StoredContribution:
        return StoredContribution(
            id=row[0], author_id=row[1], author=row[2], raw_text=row[3],
            stage=row[4], revision=row[5], summary=row[6], created_at=row[7],
            committed_at=row[8], claim_count=row[9],
        )

    @staticmethod
    def _interview(row: tuple) -> Interview:
        return Interview(
            id=row[0], requester_id=row[1], assignee_id=row[2], title=row[3],
            brief=row[4] or "", status=row[5], created_at=row[6], started_at=row[7],
            completed_at=row[8],
        )

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

    def get_user_by_id(self, user_id: str) -> User | None:
        with self._pool.connection() as connection:
            row = connection.execute(
                "SELECT id::text, email, display_name FROM app_user WHERE id = %s", (user_id,)
            ).fetchone()
        return User(id=row[0], email=row[1], display_name=row[2]) if row else None

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
        with self._pool.connection() as connection:
            row = connection.execute(
                """SELECT id::text, requester_id::text, assignee_id::text, title, brief,
                          status, created_at, started_at, completed_at
                   FROM interview WHERE id = %s""",
                (interview_id,),
            ).fetchone()
        return self._interview(row) if row else None

    def get_interview_by_contribution(self, contribution_id: str) -> Interview | None:
        with self._pool.connection() as connection:
            row = connection.execute(
                """SELECT interview.id::text, interview.requester_id::text,
                          interview.assignee_id::text, interview.title, interview.brief,
                          interview.status, interview.created_at, interview.started_at,
                          interview.completed_at
                   FROM contribution
                   JOIN interview ON interview.id = contribution.interview_id
                   WHERE contribution.id = %s""",
                (contribution_id,),
            ).fetchone()
        return self._interview(row) if row else None

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

    def create_contribution(
        self, author_id: str, raw_text: str, interview_id: str | None = None
    ) -> StoredContribution:
        with self._pool.connection() as connection:
            if interview_id is None:
                contribution_id = str(connection.execute(
                    """INSERT INTO contribution
                       (author_id, interview_id, raw_text, stage)
                       VALUES (%s, %s, %s, 'claims')
                       RETURNING id""",
                    (author_id, interview_id, raw_text),
                ).fetchone()[0])
            else:
                row = connection.execute(
                    """INSERT INTO contribution
                       (author_id, interview_id, raw_text, stage)
                       VALUES (%s, %s, %s, 'claims')
                       ON CONFLICT (interview_id) DO UPDATE
                       SET raw_text = EXCLUDED.raw_text, updated_at = now()
                       WHERE contribution.author_id = EXCLUDED.author_id
                         AND contribution.raw_text = ''
                         AND contribution.stage = 'claims'
                       RETURNING id""",
                    (author_id, interview_id, raw_text),
                ).fetchone()
                if row is None:
                    raise ContributionNotFound(interview_id)
                contribution_id = str(row[0])

            stored = connection.execute(
                """SELECT c.id::text, c.author_id::text, author.display_name,
                          c.raw_text, c.stage, c.revision, c.summary, c.created_at,
                          c.committed_at, count(claim.id)
                   FROM contribution c
                   JOIN app_user author ON author.id = c.author_id
                   LEFT JOIN claim ON claim.contribution_id = c.id
                   WHERE c.id = %s::uuid
                   GROUP BY c.id, author.display_name""",
                (contribution_id,),
            ).fetchone()
        assert stored is not None
        return self._stored(stored)

    def get_contribution(self, contribution_id: str) -> StoredContribution | None:
        with self._pool.connection() as connection:
            row = connection.execute(
                """SELECT c.id::text, c.author_id::text, u.display_name,
                          c.raw_text, c.stage, c.revision, c.summary, c.created_at,
                          c.committed_at, count(claim.id)
                   FROM contribution c
                   JOIN app_user u ON u.id = c.author_id
                   LEFT JOIN claim ON claim.contribution_id = c.id
                   WHERE c.id = %s
                   GROUP BY c.id, u.display_name""",
                (contribution_id,),
            ).fetchone()
        return self._stored(row) if row else None

    def save_review(
        self, contribution_id: str, expected_revision: int, stage: str, summary: str
    ) -> StoredContribution:
        with self._pool.connection() as connection:
            row = connection.execute(
                """WITH updated AS (
                       UPDATE contribution
                       SET stage = %s, summary = %s, revision = revision + 1, updated_at = now()
                       WHERE id = %s AND revision = %s AND stage <> 'committed'
                       RETURNING id, author_id, raw_text, stage, revision,
                                 summary, created_at, committed_at
                   )
                   SELECT updated.id::text, updated.author_id::text, author.display_name,
                          updated.raw_text, updated.stage, updated.revision,
                          updated.summary, updated.created_at, updated.committed_at, count(claim.id)
                   FROM updated
                   JOIN app_user author ON author.id = updated.author_id
                   LEFT JOIN claim ON claim.contribution_id = updated.id
                   GROUP BY updated.id, updated.author_id, author.display_name,
                            updated.raw_text, updated.stage, updated.revision,
                            updated.summary, updated.created_at, updated.committed_at""",
                (stage, summary, contribution_id, expected_revision),
            ).fetchone()
            if row is None:
                if connection.execute(
                    "SELECT 1 FROM contribution WHERE id = %s", (contribution_id,)
                ).fetchone() is None:
                    raise ContributionNotFound(contribution_id)
                raise StaleRevision(contribution_id)
            return self._stored(row)

    def commit_claims(
        self, contribution_id: str, expected_revision: int, claims: list[ClaimToCommit]
    ) -> StoredContribution:
        with self._pool.connection() as connection:
            contribution = connection.execute(
                "SELECT stage, revision FROM contribution WHERE id = %s FOR UPDATE",
                (contribution_id,),
            ).fetchone()
            if contribution is None:
                raise ContributionNotFound(contribution_id)
            if contribution[0] == "committed":
                if contribution[1] != expected_revision + 1:
                    raise StaleRevision(contribution_id)
                draft_keys = {claim.draft_key for claim in claims}
                if len(draft_keys) != len(claims):
                    raise StaleRevision(contribution_id)
                if len(draft_keys) != connection.execute(
                    "SELECT count(*) FROM claim WHERE contribution_id = %s", (contribution_id,)
                ).fetchone()[0]:
                    raise StaleRevision(contribution_id)
                for claim in claims:
                    if connection.execute(
                        """SELECT 1 FROM claim
                           WHERE contribution_id = %s AND draft_key = %s
                             AND title = %s AND statement = %s""",
                        (contribution_id, claim.draft_key, claim.title, claim.statement),
                    ).fetchone() is None:
                        raise StaleRevision(contribution_id)
                row = connection.execute(
                    """SELECT c.id::text, c.author_id::text, author.display_name,
                              c.raw_text, c.stage, c.revision, c.summary, c.created_at,
                              c.committed_at, count(claim.id)
                       FROM contribution c
                       JOIN app_user author ON author.id = c.author_id
                       LEFT JOIN claim ON claim.contribution_id = c.id
                       WHERE c.id = %s
                       GROUP BY c.id, author.display_name""",
                    (contribution_id,),
                ).fetchone()
                assert row is not None
                return self._stored(row)

            if contribution[1] != expected_revision:
                raise StaleRevision(contribution_id)

            with connection.transaction():
                connection.execute(
                    "DELETE FROM claim WHERE contribution_id = %s", (contribution_id,)
                )
                for claim in claims:
                    claim_id = str(connection.execute(
                        """INSERT INTO claim (
                             contribution_id, draft_key, title, statement, tags, embedding
                           ) VALUES (%s, %s, %s, %s, %s, %s::vector)
                           RETURNING id""",
                        (
                            contribution_id, claim.draft_key, claim.title, claim.statement,
                            list(claim.tags), list(claim.embedding),
                        ),
                    ).fetchone()[0])
                    if claim.supersedes:
                        connection.execute(
                            """UPDATE claim SET superseded_by = %s
                               WHERE id = ANY(%s::uuid[]) AND superseded_by IS NULL""",
                            (claim_id, list(claim.supersedes)),
                        )
                connection.execute(
                    """UPDATE contribution
                       SET stage = 'committed', revision = revision + 1,
                           committed_at = now(), updated_at = now()
                       WHERE id = %s""",
                    (contribution_id,),
                )
                connection.execute(
                    """UPDATE interview SET status = 'completed', completed_at = now()
                       WHERE id = (SELECT interview_id FROM contribution WHERE id = %s)""",
                    (contribution_id,),
                )
            row = connection.execute(
                """SELECT c.id::text, c.author_id::text, author.display_name,
                          c.raw_text, c.stage, c.revision, c.summary, c.created_at,
                          c.committed_at, count(claim.id)
                   FROM contribution c
                   JOIN app_user author ON author.id = c.author_id
                   LEFT JOIN claim ON claim.contribution_id = c.id
                   WHERE c.id = %s
                   GROUP BY c.id, author.display_name""",
                (contribution_id,),
            ).fetchone()
            assert row is not None
            return self._stored(row)

    def search_claims(
        self, query_text: str, query_embedding: list[float], limit: int
    ) -> list[ClaimSearchResult]:
        candidate_limit = max(limit * 4, 20)
        with self._pool.connection() as connection:
            rows = connection.execute(
                """WITH semantic AS (
                       SELECT id, row_number() OVER (ORDER BY embedding <=> %s::vector) AS rank
                       FROM claim
                       WHERE superseded_by IS NULL
                       ORDER BY embedding <=> %s::vector
                       LIMIT %s
                   ), lexical AS (
                       SELECT claim.id,
                              row_number() OVER (ORDER BY ts_rank_cd(search_vector, query) DESC) AS rank
                       FROM claim, websearch_to_tsquery('simple', %s) query
                       WHERE superseded_by IS NULL AND search_vector @@ query
                       ORDER BY ts_rank_cd(search_vector, query) DESC
                       LIMIT %s
                   )
                   SELECT claim.id::text, claim.title, claim.statement, claim.tags,
                          author.display_name, contribution.id::text, contribution.created_at
                   FROM claim
                   JOIN contribution ON contribution.id = claim.contribution_id
                   JOIN app_user author ON author.id = contribution.author_id
                   LEFT JOIN semantic ON semantic.id = claim.id
                   LEFT JOIN lexical ON lexical.id = claim.id
                   WHERE semantic.id IS NOT NULL OR lexical.id IS NOT NULL
                   ORDER BY COALESCE(1.0 / (60 + semantic.rank), 0) + COALESCE(1.0 / (60 + lexical.rank), 0) DESC, claim.id
                   LIMIT %s""",
                (query_embedding, query_embedding, candidate_limit, query_text, candidate_limit, limit),
            ).fetchall()
        return [
            ClaimSearchResult(
                id=row[0], title=row[1], statement=row[2], tags=tuple(row[3]), author=row[4],
                contribution_id=row[5], contribution_created_at=row[6],
            )
            for row in rows
        ]

    @staticmethod
    def _decode_history_cursor(cursor: str | None) -> tuple[datetime | None, str | None]:
        if cursor is None:
            return None, None
        try:
            encoded = cursor + "=" * (-len(cursor) % 4)
            value = json.loads(base64.urlsafe_b64decode(encoded).decode())
            return datetime.fromisoformat(value["created_at"]), value["id"]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError("invalid history cursor") from error

    @staticmethod
    def _history_cursor(item: HistoryItem) -> str:
        payload = json.dumps(
            {"created_at": item.created_at.isoformat(), "id": item.contribution_id},
            separators=(",", ":"),
        )
        return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")

    def list_history(self, cursor: str | None, limit: int) -> tuple[list[HistoryItem], str | None]:
        created_at, contribution_id = self._decode_history_cursor(cursor)
        with self._pool.connection() as connection:
            rows = connection.execute(
                """SELECT contribution.id::text, author.display_name,
                          contribution.summary, count(claim.id), contribution.created_at
                   FROM contribution
                   JOIN app_user author ON author.id = contribution.author_id
                   LEFT JOIN claim ON claim.contribution_id = contribution.id
                   WHERE contribution.stage = 'committed'
                     AND (%s::timestamptz IS NULL OR (contribution.created_at, contribution.id) <
                         (%s::timestamptz, %s::uuid))
                   GROUP BY contribution.id, author.display_name
                   ORDER BY contribution.created_at DESC, contribution.id DESC
                   LIMIT %s""",
                (created_at, created_at, contribution_id, limit + 1),
            ).fetchall()
        items = [
            HistoryItem(
                contribution_id=row[0], author=row[1], summary=row[2],
                claim_count=row[3], created_at=row[4],
            )
            for row in rows[:limit]
        ]
        return items, self._history_cursor(items[-1]) if len(rows) > limit else None
