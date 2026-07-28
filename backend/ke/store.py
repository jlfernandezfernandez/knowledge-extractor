"""The knowledge store: Postgres + pgvector, with hybrid retrieval.

Two design points worth knowing about:

1. Nothing is deleted. A claim that loses a conflict keeps its row and gets a
   `superseded_by` pointer to the claim that replaced it. Retrieval only ever
   looks at rows where that column is NULL, so the live view stays clean while
   the history stays auditable.

2. Retrieval is hybrid. Dense vectors find paraphrases and cross-language
   matches; lexical full-text finds exact tokens (error codes, product names,
   acronyms) that embeddings routinely miss. The two rankings are fused with
   Reciprocal Rank Fusion, which needs no score calibration between the two
   very different scales — it only uses each result's *rank*.
"""

import psycopg
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from . import config
from .schemas import StoredClaim

_pool: ConnectionPool | None = None
_checkpoint_pool: ConnectionPool | None = None

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
    superseded_by uuid REFERENCES knowledge(id),
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- The lexical half of hybrid search, as a generated column so it can never
-- drift from the text. 'simple' rather than a language-specific config: this
-- project is used in mixed-language teams and 'simple' does not stem, so it
-- never mangles a language it was not configured for. Swap it if you are
-- single-language. Added via ALTER so existing databases migrate in place.
ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS search tsvector
    GENERATED ALWAYS AS (to_tsvector('simple', title || ' ' || statement)) STORED;

CREATE INDEX IF NOT EXISTS knowledge_embedding_idx
    ON knowledge USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS knowledge_search_idx
    ON knowledge USING gin (search);
CREATE INDEX IF NOT EXISTS knowledge_live_idx
    ON knowledge (created_at) WHERE superseded_by IS NULL;
"""


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
    # Runs on a standalone connection, not the pool: the pool's `configure` calls
    # register_vector(), which needs the extension to already exist. Chicken and egg.
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
        conn.execute(SCHEMA.format(dim=config.EMBED_DIM))


def _rows(cur) -> list[dict]:
    columns = [c.name for c in cur.description]
    return [
        {k: (str(v) if k == "id" else v) for k, v in zip(columns, row)}
        for row in cur.fetchall()
    ]


# --- retrieval ----------------------------------------------------------

_HYBRID_SQL = """
WITH semantic AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> %(vec)s::vector) AS rank
    FROM knowledge
    WHERE superseded_by IS NULL
    ORDER BY embedding <=> %(vec)s::vector
    LIMIT %(pool)s
),
lexical AS (
    SELECT k.id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(k.search, q) DESC) AS rank
    FROM knowledge k, websearch_to_tsquery('simple', %(q)s) q
    WHERE k.superseded_by IS NULL AND k.search @@ q
    ORDER BY ts_rank_cd(k.search, q) DESC
    LIMIT %(pool)s
)
SELECT k.id, k.title, k.statement, k.tags, k.author, k.source,
       COALESCE(1.0 / (%(rrf_k)s + s.rank), 0)
     + COALESCE(1.0 / (%(rrf_k)s + l.rank), 0) AS score
FROM knowledge k
LEFT JOIN semantic s ON s.id = k.id
LEFT JOIN lexical  l ON l.id = k.id
WHERE s.id IS NOT NULL OR l.id IS NOT NULL
ORDER BY score DESC
LIMIT %(k)s
"""


def hybrid_search(query: str, embedding, k: int) -> list[StoredClaim]:
    """Semantic + lexical, fused with RRF. This is what `ask` and search use."""
    with pool().connection() as conn, conn.cursor() as cur:
        cur.execute(
            _HYBRID_SQL,
            {
                "vec": embedding,
                "q": query,
                "pool": max(k * 4, 20),  # over-fetch per channel, then fuse
                "rrf_k": config.RRF_K,
                "k": k,
            },
        )
        return [StoredClaim(**r) for r in _rows(cur)]


def neighbours(embedding, k: int, max_distance: float) -> list[StoredClaim]:
    """Pure semantic nearest neighbours. This is what conflict detection uses:
    a lexical channel would surface claims that merely share vocabulary."""
    with pool().connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            -- The ::vector casts are required: a plain list parameter would be
            -- inferred as double precision[], which has no <=> operator.
            SELECT id, title, statement, tags, author, source,
                   embedding <=> %s::vector AS distance
            FROM knowledge
            WHERE superseded_by IS NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (embedding, embedding, k),
        )
        rows = _rows(cur)
    return [StoredClaim(**r) for r in rows if r["distance"] <= max_distance]


def live(limit: int = 200) -> list[StoredClaim]:
    with pool().connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, title, statement, tags, author, source
            FROM knowledge WHERE superseded_by IS NULL
            ORDER BY created_at DESC LIMIT %s
            """,
            (limit,),
        )
        return [StoredClaim(**r) for r in _rows(cur)]


def history(claim_id: str) -> list[dict]:
    """The chain of claims this one replaced, newest first."""
    with pool().connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            WITH RECURSIVE chain AS (
                SELECT id, title, statement, superseded_by, created_at, 0 AS depth
                FROM knowledge WHERE id = %s
                UNION ALL
                SELECT k.id, k.title, k.statement, k.superseded_by, k.created_at,
                       chain.depth + 1
                FROM knowledge k JOIN chain ON k.superseded_by = chain.id
            )
            SELECT id, title, statement, created_at, depth FROM chain ORDER BY depth
            """,
            (claim_id,),
        )
        return _rows(cur)


# --- writes -------------------------------------------------------------


def insert(title: str, statement: str, tags, embedding, author, source) -> str:
    with pool().connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO knowledge (title, statement, tags, author, source, embedding)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (title, statement, list(tags or []), author, source, embedding),
        )
        return str(cur.fetchone()[0])


def supersede(old_id: str, new_id: str) -> None:
    with pool().connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE knowledge SET superseded_by = %s WHERE id = %s", (new_id, old_id)
        )
