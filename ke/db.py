"""Postgres + pgvector. One store for the vectors, the history and the review sessions."""

import json
from contextlib import contextmanager

import psycopg
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from . import config

_pool: ConnectionPool | None = None

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS knowledge (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title         text NOT NULL,
    statement     text NOT NULL,
    tags          text[] NOT NULL DEFAULT '{{}}',
    author        text,
    source        text,
    embedding     vector({dim}) NOT NULL,
    -- Nothing is ever deleted: a replaced claim points at the claim that won.
    superseded_by uuid REFERENCES knowledge(id),
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS knowledge_embedding_idx
    ON knowledge USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS knowledge_live_idx
    ON knowledge (created_at) WHERE superseded_by IS NULL;

CREATE TABLE IF NOT EXISTS sessions (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    stage      text NOT NULL DEFAULT 'drafted',
    payload    jsonb NOT NULL DEFAULT '{{}}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
"""


def _configure(conn: psycopg.Connection) -> None:
    register_vector(conn)


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(config.DATABASE_URL, configure=_configure, open=True)
    return _pool


@contextmanager
def cursor():
    with pool().connection() as conn, conn.cursor() as cur:
        yield cur


def init() -> None:
    # Runs on a standalone connection, not the pool: the pool's `configure` calls
    # register_vector(), which needs the extension to already exist. Chicken and egg.
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
        conn.execute(SCHEMA.format(dim=config.EMBED_DIM))


# --- knowledge ----------------------------------------------------------


def neighbours(embedding, k: int, max_distance: float) -> list[dict]:
    """Live claims closest to `embedding`, nearest first, within `max_distance`."""
    with cursor() as cur:
        cur.execute(
            """
            -- The ::vector casts are needed: a plain list parameter would be
            -- inferred as double precision[], which has no <=> operator.
            SELECT id, title, statement, tags, author, source, created_at,
                   embedding <=> %s::vector AS distance
            FROM knowledge
            WHERE superseded_by IS NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (embedding, embedding, k),
        )
        rows = _dicts(cur)
    return [r for r in rows if r["distance"] <= max_distance]


def insert(atom: dict, embedding, author: str | None, source: str | None) -> str:
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO knowledge (title, statement, tags, author, source, embedding)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (
                atom["title"],
                atom["statement"],
                atom.get("tags") or [],
                author,
                source,
                embedding,
            ),
        )
        return str(cur.fetchone()[0])


def supersede(old_id: str, new_id: str) -> None:
    with cursor() as cur:
        cur.execute(
            "UPDATE knowledge SET superseded_by = %s WHERE id = %s", (new_id, old_id)
        )


def live(limit: int = 200) -> list[dict]:
    with cursor() as cur:
        cur.execute(
            """
            SELECT id, title, statement, tags, author, source, created_at
            FROM knowledge WHERE superseded_by IS NULL
            ORDER BY created_at DESC LIMIT %s
            """,
            (limit,),
        )
        return _dicts(cur)


# --- review sessions ----------------------------------------------------


def create_session(payload: dict) -> str:
    with cursor() as cur:
        cur.execute(
            "INSERT INTO sessions (payload) VALUES (%s) RETURNING id",
            (json.dumps(payload),),
        )
        return str(cur.fetchone()[0])


def get_session(session_id: str) -> dict | None:
    with cursor() as cur:
        cur.execute(
            "SELECT id, stage, payload, created_at FROM sessions WHERE id = %s",
            (session_id,),
        )
        rows = _dicts(cur)
    return rows[0] if rows else None


def update_session(session_id: str, stage: str, payload: dict) -> None:
    with cursor() as cur:
        cur.execute(
            "UPDATE sessions SET stage = %s, payload = %s WHERE id = %s",
            (stage, json.dumps(payload), session_id),
        )


def _dicts(cur) -> list[dict]:
    columns = [c.name for c in cur.description]
    return [
        {k: (str(v) if k == "id" else v) for k, v in zip(columns, row)}
        for row in cur.fetchall()
    ]
