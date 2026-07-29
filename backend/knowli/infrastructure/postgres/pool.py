"""Connection pools, and creating the schema.

Two pools, because LangGraph's checkpointer needs different connection settings
from ours and mixing them breaks one or the other.
"""

from importlib import resources

import psycopg
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from ... import config
from ...domain.knowledge_base import slugify

_pool: ConnectionPool | None = None
_checkpoint_pool: ConnectionPool | None = None


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(config.DATABASE_URL, configure=register_vector, open=True)
    return _pool


def checkpoint_pool() -> ConnectionPool:
    """A separate pool for LangGraph's checkpointer.

    It needs autocommit: its migrations use CREATE INDEX CONCURRENTLY, which
    Postgres refuses to run inside a transaction block. `prepare_threshold=0`
    is what LangGraph's own docs recommend alongside it.
    """
    global _checkpoint_pool
    if _checkpoint_pool is None:
        _checkpoint_pool = ConnectionPool(
            config.DATABASE_URL,
            kwargs={"autocommit": True, "prepare_threshold": 0},
            open=True,
        )
    return _checkpoint_pool


def init() -> None:
    """Create the schema, migrate an existing one, and seed the default
    workspace and knowledge base. Idempotent — it runs on every startup."""
    # Runs on a standalone connection, not the pool: the pool's `configure` calls
    # register_vector(), which needs the extension to already exist. Chicken and egg.
    schema = resources.files(__package__).joinpath("schema.sql").read_text()

    # The two slugs are interpolated rather than bound, because psycopg refuses
    # parameters on a multi-statement script and this file is one. That is only
    # safe because `slugify` has already reduced them to [a-z0-9-], which cannot
    # carry a quote — so the same function that keeps two knowledge bases from
    # colliding is also what keeps this line from being an injection. The names
    # are derived from the slugs for the same reason, and because "Personal" is
    # a better thing to show in a sidebar than "personal".
    workspace = slugify(config.DEFAULT_WORKSPACE)
    knowledge_base = slugify(config.DEFAULT_KNOWLEDGE_BASE)
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
        conn.execute(
            schema.format(
                dim=config.EMBED_DIM,
                workspace=workspace,
                workspace_name=workspace.replace("-", " ").title(),
                knowledge_base=knowledge_base,
                knowledge_base_name=knowledge_base.replace("-", " ").title(),
            )
        )
