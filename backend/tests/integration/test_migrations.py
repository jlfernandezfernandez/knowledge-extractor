"""Integration coverage for fresh, legacy, and repeatable schema upgrades."""

from importlib import resources
from datetime import UTC, datetime, timedelta
from hashlib import md5
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg_pool import ConnectionPool

from knowli import config
from knowli.infrastructure.postgres.migrations import run_migrations


@pytest.fixture
def database():
    schema = f"migration_test_{uuid4().hex}"
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    pool = ConnectionPool(
        make_conninfo(config.DATABASE_URL, options=f"-c search_path={schema},public"),
        open=True,
    )
    try:
        yield pool
    finally:
        pool.close()
        with psycopg.connect(config.DATABASE_URL, autocommit=True) as connection:
            for table in ("claim", "contribution", "interview", "login_session", "schema_migration",
                          "audit_event", "team_member", "legacy_interview", "review_session",
                          "knowledge", "app_session", "team", "knowledge_base", "workspace",
                          "organisation", "app_user", "legacy_app_user"):
                connection.execute(
                    sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
                        sql.Identifier(schema), sql.Identifier(table)
                    )
                )
            connection.execute(sql.SQL("DROP SCHEMA {}").format(sql.Identifier(schema)))


def _versions(pool: ConnectionPool) -> list[int]:
    with pool.connection() as connection:
        return [row[0] for row in connection.execute(
            "SELECT version FROM schema_migration ORDER BY version"
        )]


def test_fresh_database_reaches_version_4(database: ConnectionPool):
    run_migrations(database)

    assert _versions(database) == [1, 2, 3, 4]
    with database.connection() as connection:
        tables = {row[0] for row in connection.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = current_schema()"
        )}
    assert {"app_user", "login_session", "interview", "contribution", "claim"} <= tables


def test_legacy_database_preserves_every_row(database: ConnectionPool):
    legacy_schema = resources.files("tests.fixtures").joinpath("legacy_schema.sql").read_text()
    with database.connection() as connection:
        connection.execute(legacy_schema)
        requester_id, assignee_id, organisation_id, workspace_id, base_id, team_id = (
            uuid4() for _ in range(6)
        )
        review_id, interview_id, predecessor_id, claim_id = (uuid4() for _ in range(4))
        requester_created = datetime(2023, 1, 2, 3, 4, 5, tzinfo=UTC)
        assignee_created = requester_created + timedelta(days=1)
        session_created = requester_created + timedelta(days=2)
        session_expires = session_created + timedelta(days=14)
        review_created = requester_created + timedelta(days=3)
        review_updated = review_created + timedelta(hours=5)
        interview_created = requester_created + timedelta(days=4)
        interview_started = interview_created + timedelta(hours=2)
        interview_completed = interview_started + timedelta(hours=3)
        predecessor_created = requester_created + timedelta(days=5)
        claim_created = predecessor_created + timedelta(hours=1)
        embedding = "[" + ",".join(["0.125", "-0.25"] + ["0"] * 382) + "]"
        connection.execute(
            """INSERT INTO app_user (id, email, display_name, password_hash, created_at)
               VALUES (%s, %s, %s, %s, %s), (%s, %s, %s, %s, %s)""",
            (
                requester_id, "requester@example.com", "Legacy Requester", "requester-password",
                requester_created, assignee_id, "assignee@example.com", "Legacy Assignee",
                "assignee-password", assignee_created,
            ),
        )
        connection.execute("INSERT INTO organisation (id, name) VALUES (%s, 'Legacy')", (organisation_id,))
        connection.execute(
            "INSERT INTO workspace (id, slug, name) VALUES (%s, 'legacy', 'Legacy')", (workspace_id,)
        )
        connection.execute(
            "INSERT INTO knowledge_base (id, workspace_id, slug, name) VALUES (%s, %s, 'legacy', 'Legacy')",
            (base_id, workspace_id),
        )
        connection.execute(
            "INSERT INTO team (id, organisation_id, name, knowledge_base_id) VALUES (%s, %s, 'Legacy', %s)",
            (team_id, organisation_id, base_id),
        )
        connection.execute("INSERT INTO team_member (team_id, user_id) VALUES (%s, %s)", (team_id, assignee_id))
        connection.execute(
            """INSERT INTO app_session (token_hash, user_id, expires_at, created_at)
               VALUES (%s, %s, %s, %s)""",
            ("a" * 64, assignee_id, session_expires, session_created),
        )
        connection.execute(
            """INSERT INTO review_session
               (id, knowledge_base_id, author, stage, summary, created_at, updated_at,
                contributor_id, contribution_kind)
               VALUES (%s, %s, 'Legacy Assignee', 'done', 'Distinct review summary', %s, %s,
                       %s, 'interview')""",
            (review_id, base_id, review_created, review_updated, assignee_id),
        )
        connection.execute(
            """INSERT INTO interview
               (id, team_id, requester_id, assignee_id, title, brief, session_id, status,
                created_at, started_at, completed_at)
               VALUES (%s, %s, %s, %s, 'Distinct legacy interview', 'Distinct legacy brief', %s,
                       'done', %s, %s, %s)""",
            (interview_id, team_id, requester_id, assignee_id, review_id,
             interview_created, interview_started, interview_completed),
        )
        connection.execute(
            """INSERT INTO knowledge
               (id, knowledge_base_id, title, statement, tags, author, source, embedding, created_at)
               VALUES (%s, %s, 'Predecessor claim', 'Old preserved statement.', ARRAY['old'],
                       'Another synthetic author', 'old-source', %s::vector, %s)""",
            (predecessor_id, base_id, embedding, predecessor_created),
        )
        connection.execute(
            """INSERT INTO knowledge
               (id, knowledge_base_id, title, statement, tags, author, source, embedding,
                superseded_by, created_at)
               VALUES (%s, %s, 'Legacy claim', 'Preserve this distinctive statement.',
                       ARRAY['legacy', 'preserved'], 'Synthetic legacy author', 'legacy-source',
                       %s::vector, %s, %s)""",
            (claim_id, base_id, embedding, predecessor_id, claim_created),
        )

    run_migrations(database)

    with database.connection() as connection:
        users = connection.execute(
            """SELECT id, email, display_name, password_hash, created_at FROM app_user
               WHERE id IN (%s, %s) ORDER BY email""",
            (requester_id, assignee_id),
        ).fetchall()
        session = connection.execute(
            "SELECT user_id, expires_at, created_at FROM login_session WHERE token_hash = %s", ("a" * 64,)
        ).fetchone()
        interview = connection.execute(
            """SELECT requester_id, assignee_id, title, brief, status, created_at, started_at, completed_at
               FROM interview WHERE id = %s""",
            (interview_id,),
        ).fetchone()
        review = connection.execute(
            """SELECT author_id, kind, interview_id, source, raw_text, stage, summary,
                      created_at, updated_at, committed_at
               FROM contribution WHERE id = %s""",
            (review_id,),
        ).fetchone()
        claim = connection.execute(
            """SELECT claim.id, claim.title, claim.statement, claim.tags, claim.embedding::text,
                      claim.superseded_by, claim.created_at, contribution.source, contribution.stage,
                      contribution.created_at, contribution.updated_at, contribution.committed_at,
                      author.email
               FROM claim JOIN contribution ON contribution.id = claim.contribution_id
               JOIN app_user author ON author.id = contribution.author_id
               WHERE claim.id = %s""",
            (claim_id,),
        ).fetchone()

    assert users == [
        (assignee_id, "assignee@example.com", "Legacy Assignee", "assignee-password", assignee_created),
        (requester_id, "requester@example.com", "Legacy Requester", "requester-password", requester_created),
    ]
    assert session == (assignee_id, session_expires, session_created)
    assert interview == (
        requester_id, assignee_id, "Distinct legacy interview", "Distinct legacy brief", "completed",
        interview_created, interview_started, interview_completed,
    )
    assert review == (
        assignee_id, "interview", interview_id, "text", "", "committed", "Distinct review summary",
        review_created, review_updated, review_updated,
    )
    assert claim == (
        claim_id, "Legacy claim", "Preserve this distinctive statement.", ["legacy", "preserved"],
        embedding, predecessor_id, claim_created, "legacy-source", "committed", claim_created,
        claim_created, claim_created, f"legacy-{md5('Synthetic legacy author'.encode()).hexdigest()}@local.invalid",
    )


def test_migration_runner_is_idempotent(database: ConnectionPool):
    run_migrations(database)
    run_migrations(database)

    assert _versions(database) == [1, 2, 3, 4]


def test_knowledge_only_legacy_imports_without_review_tables(database: ConnectionPool):
    claim_id = uuid4()
    with database.connection() as connection:
        connection.execute(
            """CREATE TABLE knowledge (
                 id uuid PRIMARY KEY, title text NOT NULL, statement text NOT NULL,
                 tags text[] NOT NULL, author text, source text, embedding vector(384) NOT NULL,
                 superseded_by uuid, created_at timestamptz NOT NULL
               )"""
        )
        connection.execute(
            """INSERT INTO knowledge VALUES
               (%s, 'Only knowledge', 'The review table is absent.', ARRAY['partial'],
                'Knowledge only author', 'partial-source', %s::vector, NULL, %s)""",
            (claim_id, "[" + ",".join(["0"] * 384) + "]", datetime(2024, 1, 1, tzinfo=UTC)),
        )

    run_migrations(database)

    with database.connection() as connection:
        row = connection.execute(
            """SELECT claim.id, contribution.stage, contribution.source, author.email
               FROM claim
               JOIN contribution ON contribution.id = claim.contribution_id
               JOIN app_user author ON author.id = contribution.author_id"""
        ).fetchone()
    assert row == (
        claim_id, "committed", "partial-source",
        f"legacy-{md5('Knowledge only author'.encode()).hexdigest()}@local.invalid",
    )


def test_review_only_legacy_imports_without_interview_table(database: ConnectionPool):
    review_id = uuid4()
    created = datetime(2024, 2, 1, tzinfo=UTC)
    with database.connection() as connection:
        connection.execute(
            """CREATE TABLE review_session (
                 id uuid PRIMARY KEY, author text, stage text NOT NULL, summary text NOT NULL,
                 created_at timestamptz NOT NULL, updated_at timestamptz NOT NULL,
                 contributor_id uuid, contribution_kind text NOT NULL
               )"""
        )
        connection.execute(
            """INSERT INTO review_session VALUES
               (%s, 'Review only author', 'resolve', 'No interview table', %s, %s, NULL, 'voluntary')""",
            (review_id, created, created + timedelta(minutes=1)),
        )

    run_migrations(database)

    with database.connection() as connection:
        row = connection.execute(
            "SELECT id, interview_id, stage, summary FROM contribution"
        ).fetchone()
    assert row == (review_id, None, "conflicts", "No interview table")


def test_duplicate_legacy_display_names_receive_a_synthetic_author(database: ConnectionPool):
    first_id, second_id, review_id = uuid4(), uuid4(), uuid4()
    with database.connection() as connection:
        connection.execute(
            """CREATE TABLE app_user (
                 id uuid PRIMARY KEY, email text UNIQUE NOT NULL, display_name text NOT NULL,
                 password_hash text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
               )"""
        )
        connection.execute(
            """CREATE TABLE review_session (
                 id uuid PRIMARY KEY, author text, stage text NOT NULL, summary text NOT NULL,
                 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
                 contributor_id uuid, contribution_kind text NOT NULL DEFAULT 'voluntary'
               )"""
        )
        connection.execute(
            """INSERT INTO app_user (id, email, display_name, password_hash) VALUES
               (%s, 'first@example.com', 'Duplicate Name', 'first'),
               (%s, 'second@example.com', 'Duplicate Name', 'second')""",
            (first_id, second_id),
        )
        connection.execute(
            """INSERT INTO review_session (id, author, stage, summary, contribution_kind)
               VALUES (%s, 'Duplicate Name', 'confirm', 'Ambiguous author', 'voluntary')""",
            (review_id,),
        )

    run_migrations(database)

    with database.connection() as connection:
        author = connection.execute(
            """SELECT user_account.email FROM contribution
               JOIN app_user user_account ON user_account.id = contribution.author_id
               WHERE contribution.id = %s""",
            (review_id,),
        ).fetchone()[0]
    assert author == f"legacy-{md5('Duplicate Name'.encode()).hexdigest()}@local.invalid"


def test_partial_legacy_interview_shape_fails_before_rename(database: ConnectionPool):
    with database.connection() as connection:
        connection.execute("CREATE TABLE interview (id uuid PRIMARY KEY, team_id uuid)")

    with pytest.raises(psycopg.Error, match="legacy interview has an unsupported shape"):
        run_migrations(database)

    with database.connection() as connection:
        assert connection.execute("SELECT version FROM schema_migration").fetchall() == []
