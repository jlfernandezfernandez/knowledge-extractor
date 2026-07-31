"""The global contribution store against an isolated PostgreSQL schema.

Each test would fail if the store reintroduced a knowledge-base filter, lost
provenance, accepted a stale write, or treated a retry as a second commit.
"""

from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg_pool import ConnectionPool

from knowli import config
from knowli.domain.claim import ClaimToCommit
from knowli.domain.contribution import StaleRevision
from knowli.infrastructure.postgres.migrations import run_migrations
from knowli.infrastructure.postgres.repository import PostgresStore


@pytest.fixture
def database():
    schema = f"store_test_{uuid4().hex}"
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    pool = ConnectionPool(
        make_conninfo(config.DATABASE_URL, options=f"-c search_path={schema},public"),
        open=True,
    )
    run_migrations(pool)
    try:
        yield pool
    finally:
        pool.close()
        # The random schema contains only this test's tables; no user database
        # or user data is ever selected or dropped.
        with psycopg.connect(config.DATABASE_URL, autocommit=True) as connection:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def _user(database: ConnectionPool, name: str) -> str:
    with database.connection() as connection:
        return str(connection.execute(
            """INSERT INTO app_user (email, display_name, password_hash)
               VALUES (%s, %s, 'test-password') RETURNING id""",
            (f"{name.lower()}@example.test", name),
        ).fetchone()[0])


def _claim(key: str, title: str, statement: str) -> ClaimToCommit:
    return ClaimToCommit(key, title, statement, ("test",), (0.0,) * 384)


def test_global_search_returns_claims_from_two_authors(database: ConnectionPool):
    store = PostgresStore(database)
    ana, bruno = _user(database, "Ana"), _user(database, "Bruno")
    first = store.create_contribution(ana, "Ana contribution")
    second = store.create_contribution(bruno, "Bruno contribution")
    store.commit_claims(first.id, 0, [_claim("ana", "Ana result", "Global retrieval signal")])
    store.commit_claims(second.id, 0, [_claim("bruno", "Bruno result", "Global retrieval signal")])

    results = store.search_claims("Global retrieval signal", [0.0] * 384, 10)

    assert {(result.author, result.contribution_id) for result in results} == {
        ("Ana", first.id), ("Bruno", second.id)
    }


def test_history_includes_author_source_and_claim_count(database: ConnectionPool):
    store = PostgresStore(database)
    author = _user(database, "Ada")
    contribution = store.create_contribution(author, "An imported note")
    store.commit_claims(contribution.id, 0, [_claim("one", "One", "First statement")])

    items, next_cursor = store.list_history(None, 10)

    assert len(items) == 1
    assert items[0].contribution_id == contribution.id
    assert items[0].author == "Ada"
    assert items[0].claim_count == 1
    assert next_cursor is None


def test_review_rejects_a_stale_revision(database: ConnectionPool):
    store = PostgresStore(database)
    contribution = store.create_contribution(_user(database, "Rita"), "Text")
    updated = store.save_review(contribution.id, 0, "conflicts", "Found a conflict")

    with pytest.raises(StaleRevision):
        store.save_review(contribution.id, 0, "conflicts", "A stale overwrite")

    assert updated.revision == 1


def test_commit_retry_is_idempotent(database: ConnectionPool):
    store = PostgresStore(database)
    contribution = store.create_contribution(_user(database, "Iris"), "Text")
    claims = [_claim("stable-key", "Stable", "A retry must not duplicate this claim")]

    committed = store.commit_claims(contribution.id, 0, claims)
    retried = store.commit_claims(contribution.id, 0, claims)

    assert (committed.stage, committed.revision, committed.claim_count) == ("committed", 1, 1)
    assert retried == committed
    with database.connection() as connection:
        assert connection.execute("SELECT count(*) FROM claim").fetchone()[0] == 1


def test_commit_retry_requires_the_original_revision_and_full_payload(database: ConnectionPool):
    store = PostgresStore(database)
    contribution = store.create_contribution(_user(database, "Nora"), "Text")
    claims = [_claim("stable-key", "Stable", "The original statement")]
    store.commit_claims(contribution.id, 0, claims)

    with pytest.raises(StaleRevision):
        store.commit_claims(contribution.id, 1, claims)
    with pytest.raises(StaleRevision):
        store.commit_claims(
            contribution.id, 0, [_claim("stable-key", "Changed", "The original statement")]
        )


def test_commit_retry_rejects_duplicate_keys_when_another_claim_is_omitted(
    database: ConnectionPool,
):
    store = PostgresStore(database)
    contribution = store.create_contribution(_user(database, "Quinn"), "Text")
    first = _claim("first", "First", "First stored statement")
    second = _claim("second", "Second", "Second stored statement")
    store.commit_claims(contribution.id, 0, [first, second])

    with pytest.raises(StaleRevision):
        store.commit_claims(contribution.id, 0, [first, first])


def test_commit_returns_the_result_of_its_locked_transaction(
    database: ConnectionPool, monkeypatch: pytest.MonkeyPatch
):
    store = PostgresStore(database)
    contribution = store.create_contribution(_user(database, "Mina"), "Text")
    original_get = store.get_contribution

    def read_after_a_concurrent_write(contribution_id: str):
        with database.connection() as connection:
            connection.execute(
                """UPDATE contribution
                   SET summary = 'Later writer', revision = revision + 1
                   WHERE id = %s""",
                (contribution_id,),
            )
        return original_get(contribution_id)

    monkeypatch.setattr(store, "get_contribution", read_after_a_concurrent_write)

    committed = store.commit_claims(contribution.id, 0, [_claim("one", "One", "Statement")])

    assert (committed.revision, committed.summary) == (1, "")


def test_review_returns_the_revision_it_wrote(
    database: ConnectionPool, monkeypatch: pytest.MonkeyPatch
):
    store = PostgresStore(database)
    contribution = store.create_contribution(_user(database, "Omar"), "Text")
    original_get = store.get_contribution

    def read_after_a_concurrent_write(contribution_id: str):
        with database.connection() as connection:
            connection.execute(
                """UPDATE contribution
                   SET summary = 'Later writer', revision = revision + 1
                   WHERE id = %s""",
                (contribution_id,),
            )
        return original_get(contribution_id)

    monkeypatch.setattr(store, "get_contribution", read_after_a_concurrent_write)

    updated = store.save_review(contribution.id, 0, "conflicts", "Reviewed now")

    assert (updated.revision, updated.summary) == (1, "Reviewed now")


def test_history_cursor_pages_without_skipping_or_repeating_items(database: ConnectionPool):
    store = PostgresStore(database)
    author = _user(database, "Pia")
    contribution_ids = []
    for key in ("first", "second", "third"):
        contribution = store.create_contribution(author, key)
        store.commit_claims(contribution.id, 0, [_claim(key, key, f"{key} statement")])
        contribution_ids.append(contribution.id)

    first_page, cursor = store.list_history(None, 2)
    second_page, final_cursor = store.list_history(cursor, 2)

    assert len(first_page) == 2
    assert len(second_page) == 1
    assert {item.contribution_id for item in first_page + second_page} == set(contribution_ids)
    assert final_cursor is None


def test_started_interview_reuses_one_contribution_and_completes_on_commit(
    database: ConnectionPool,
):
    """A retry or commit that loses the interview link breaks the interview lifecycle."""
    store = PostgresStore(database)
    requester, assignee = _user(database, "Requestor"), _user(database, "Answerer")
    interview = store.create_interview(requester, assignee, "Release process", "Context only")

    first = store.start_interview(interview.id, assignee)
    retried = store.start_interview(interview.id, assignee)
    assert first is not None
    assert retried is not None
    assert first.contribution_id == retried.contribution_id

    store.commit_claims(first.contribution_id, 0, [_claim("answer", "Release", "Ship Tuesday")])

    completed = store.get_interview(interview.id)
    assert completed is not None
    assert completed.status == "completed"
    assert completed.completed_at is not None
