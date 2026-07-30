"""The one PostgreSQL-backed global contribution store."""

from psycopg_pool import ConnectionPool

from ...domain.claim import ClaimSearchResult, ClaimToCommit
from ...domain.contribution import (
    ContributionNotFound,
    HistoryItem,
    StaleRevision,
    StoredContribution,
)
from .pool import pool as configured_pool


class PostgresStore:
    def __init__(self, connection_pool: ConnectionPool | None = None):
        self._pool = connection_pool or configured_pool()

    @staticmethod
    def _stored(row: tuple) -> StoredContribution:
        return StoredContribution(
            id=row[0], author_id=row[1], author=row[2], kind=row[3], source=row[4],
            raw_text=row[5], stage=row[6], revision=row[7], summary=row[8],
            created_at=row[9], committed_at=row[10], claim_count=row[11],
        )

    def create_contribution(
        self, author_id: str, raw_text: str, source: str, interview_id: str | None = None
    ) -> StoredContribution:
        kind = "interview" if interview_id else "voluntary"
        with self._pool.connection() as connection:
            contribution_id = str(connection.execute(
                """INSERT INTO contribution
                   (author_id, kind, interview_id, source, raw_text, stage)
                   VALUES (%s, %s, %s, %s, %s, 'claims')
                   RETURNING id""",
                (author_id, kind, interview_id, source, raw_text),
            ).fetchone()[0])
        contribution = self.get_contribution(contribution_id)
        assert contribution is not None
        return contribution

    def get_contribution(self, contribution_id: str) -> StoredContribution | None:
        with self._pool.connection() as connection:
            row = connection.execute(
                """SELECT c.id::text, c.author_id::text, u.display_name, c.kind, c.source,
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
            updated = connection.execute(
                """UPDATE contribution
                   SET stage = %s, summary = %s, revision = revision + 1, updated_at = now()
                   WHERE id = %s AND revision = %s AND stage <> 'committed'
                   RETURNING id""",
                (stage, summary, contribution_id, expected_revision),
            ).fetchone()
        if updated is None:
            if self.get_contribution(contribution_id) is None:
                raise ContributionNotFound(contribution_id)
            raise StaleRevision(contribution_id)
        contribution = self.get_contribution(contribution_id)
        assert contribution is not None
        return contribution

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
                pass
            elif contribution[1] != expected_revision:
                raise StaleRevision(contribution_id)
            else:
                for claim in claims:
                    claim_id = str(connection.execute(
                        """INSERT INTO claim
                           (contribution_id, draft_key, title, statement, tags, embedding)
                           VALUES (%s, %s, %s, %s, %s, %s::vector)
                           ON CONFLICT (contribution_id, draft_key) DO UPDATE
                           SET title = EXCLUDED.title, statement = EXCLUDED.statement,
                               tags = EXCLUDED.tags, embedding = EXCLUDED.embedding
                           RETURNING id""",
                        (
                            contribution_id, claim.draft_key, claim.title, claim.statement,
                            list(claim.tags), list(claim.embedding),
                        ),
                    ).fetchone()[0])
                    if claim.supersedes:
                        connection.execute(
                            "UPDATE claim SET superseded_by = %s WHERE id = ANY(%s::uuid[])",
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
        stored = self.get_contribution(contribution_id)
        assert stored is not None
        return stored

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
                          author.display_name, contribution.id::text, contribution.created_at,
                          COALESCE(1.0 / (60 + semantic.rank), 0)
                        + COALESCE(1.0 / (60 + lexical.rank), 0) AS score
                   FROM claim
                   JOIN contribution ON contribution.id = claim.contribution_id
                   JOIN app_user author ON author.id = contribution.author_id
                   LEFT JOIN semantic ON semantic.id = claim.id
                   LEFT JOIN lexical ON lexical.id = claim.id
                   WHERE semantic.id IS NOT NULL OR lexical.id IS NOT NULL
                   ORDER BY score DESC, claim.id
                   LIMIT %s""",
                (query_embedding, query_embedding, candidate_limit, query_text, candidate_limit, limit),
            ).fetchall()
        return [
            ClaimSearchResult(
                id=row[0], title=row[1], statement=row[2], tags=tuple(row[3]), author=row[4],
                contribution_id=row[5], contribution_created_at=row[6], score=float(row[7]),
            )
            for row in rows
        ]

    def list_history(self, cursor: str | None, limit: int) -> tuple[list[HistoryItem], str | None]:
        with self._pool.connection() as connection:
            rows = connection.execute(
                """SELECT contribution.id::text, author.display_name, contribution.source,
                          contribution.summary, count(claim.id), contribution.created_at
                   FROM contribution
                   JOIN app_user author ON author.id = contribution.author_id
                   LEFT JOIN claim ON claim.contribution_id = contribution.id
                   WHERE contribution.stage = 'committed'
                     AND (%s::uuid IS NULL OR (contribution.created_at, contribution.id) <
                         (SELECT created_at, id FROM contribution WHERE id = %s::uuid))
                   GROUP BY contribution.id, author.display_name
                   ORDER BY contribution.created_at DESC, contribution.id DESC
                   LIMIT %s""",
                (cursor, cursor, limit + 1),
            ).fetchall()
        items = [
            HistoryItem(
                contribution_id=row[0], author=row[1], source=row[2], summary=row[3],
                claim_count=row[4], created_at=row[5],
            )
            for row in rows[:limit]
        ]
        return items, rows[limit][0] if len(rows) > limit else None
