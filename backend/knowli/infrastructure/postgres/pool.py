"""Connection pools and the database migration bootstrap."""

import psycopg
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from ... import config
from .migrations import run_migrations

_pool: ConnectionPool | None = None
_checkpoint_pool: ConnectionPool | None = None


def create_pool() -> ConnectionPool:
    """Create the web application's main pool without making it module state."""
    return ConnectionPool(config.DATABASE_URL, configure=register_vector, open=True)


def create_checkpoint_pool() -> ConnectionPool:
    """Create the separate autocommit pool required by LangGraph."""
    return ConnectionPool(
        config.DATABASE_URL,
        kwargs={"autocommit": True, "prepare_threshold": 0},
        open=True,
    )


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = create_pool()
    return _pool


def checkpoint_pool() -> ConnectionPool:
    """A separate pool for LangGraph's checkpointer.

    It needs autocommit: its migrations use CREATE INDEX CONCURRENTLY, which
    Postgres refuses to run inside a transaction block. `prepare_threshold=0`
    is what LangGraph's own docs recommend alongside it.
    """
    global _checkpoint_pool
    if _checkpoint_pool is None:
        _checkpoint_pool = create_checkpoint_pool()
    return _checkpoint_pool


def init() -> None:
    """Prepare pgvector before the configured pool, then run migrations once."""
    # register_vector() looks up PostgreSQL's vector type. Bootstrap it through
    # a bare connection first so a fresh install can construct the normal pool.
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    run_migrations(pool())
