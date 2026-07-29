"""The Postgres side: the knowledge store, and the catalog around it.

Two classes, two ports, one file — they share a pool, a row helper and a
dialect, and splitting them would buy a second import and nothing else. The
split that matters is the one in `domain/ports.py`: if the claims ever move to a
vector store, `PostgresKnowledgeRepository` is what gets a sibling and
`PostgresCatalog` is what stays exactly where it is.

Three design points worth knowing about:

1. Nothing is deleted. A claim that loses a conflict keeps its row and gets a
   `superseded_by` pointer to the claim that replaced it. Retrieval only ever
   looks at rows where that column is NULL, so the live view stays clean while
   the history stays auditable.

2. Retrieval is hybrid. Dense vectors find paraphrases and cross-language
   matches; lexical full-text finds exact tokens (error codes, product names,
   acronyms) that embeddings routinely miss. The two rankings are fused with
   Reciprocal Rank Fusion, which needs no score calibration between the two
   very different scales — it only uses each result's *rank*.

3. Every claim query is scoped to one knowledge base. For the lexical and the
   listing halves that is an indexed equality (see `schema.sql`). For the vector
   half it is a filter over an approximate scan, which is why both vector
   queries set `hnsw.iterative_scan` first.
"""

from ... import config
from ...domain.claim import StoredClaim
from ...domain.knowledge_base import KnowledgeBase
from .pool import pool

_HYBRID_SQL = """
WITH semantic AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> %(vec)s::vector) AS rank
    FROM knowledge
    WHERE superseded_by IS NULL AND knowledge_base_id = %(kb)s
    ORDER BY embedding <=> %(vec)s::vector
    LIMIT %(pool)s
),
lexical AS (
    SELECT k.id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(k.search, q) DESC) AS rank
    FROM knowledge k, websearch_to_tsquery('simple', %(q)s) q
    WHERE k.superseded_by IS NULL AND k.knowledge_base_id = %(kb)s AND k.search @@ q
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

# pgvector cannot index the scope alongside the vector, so a scoped ANN query is
# a filter on top of an approximate scan. Without this, the scan visits its
# ef_search candidates *in total* and hands back only those that happen to be in
# this knowledge base: five neighbours asked for, two returned, and a conflict
# detector that sees nothing and cheerfully reports no conflicts — the worst way
# to be wrong here. Iterative scan (pgvector 0.8) keeps pulling from the index
# until enough rows pass the filter. `strict_order` rather than `relaxed_order`
# because both callers care about order: RRF ranks by it and `neighbours` cuts
# by distance.
_ITERATIVE_SCAN = "SET LOCAL hnsw.iterative_scan = strict_order"


def _rows(cur) -> list[dict]:
    columns = [c.name for c in cur.description]
    return [
        {k: (str(v) if k == "id" else v) for k, v in zip(columns, row)}
        for row in cur.fetchall()
    ]


class PostgresKnowledgeRepository:
    """The one implementation of `domain.ports.KnowledgeRepository`."""

    # --- retrieval ------------------------------------------------------

    def hybrid_search(
        self, kb: KnowledgeBase, query: str, embedding, k: int
    ) -> list[StoredClaim]:
        """Semantic + lexical, fused with RRF. This is what `ask` and search use."""
        with pool().connection() as conn, conn.cursor() as cur:
            cur.execute(_ITERATIVE_SCAN)
            cur.execute(
                _HYBRID_SQL,
                {
                    "kb": kb.id,
                    "vec": embedding,
                    "q": query,
                    "pool": max(k * 4, 20),  # over-fetch per channel, then fuse
                    "rrf_k": config.RRF_K,
                    "k": k,
                },
            )
            return [StoredClaim(**r) for r in _rows(cur)]

    def neighbours(
        self, kb: KnowledgeBase, embedding, k: int, max_distance: float
    ) -> list[StoredClaim]:
        """Pure semantic nearest neighbours, inside one knowledge base. This is
        what conflict detection uses: a lexical channel would surface claims that
        merely share vocabulary, and an unscoped one would surface claims about a
        subject this capture has nothing to do with."""
        with pool().connection() as conn, conn.cursor() as cur:
            cur.execute(_ITERATIVE_SCAN)
            cur.execute(
                """
                -- The ::vector casts are required: a plain list parameter would be
                -- inferred as double precision[], which has no <=> operator.
                SELECT id, title, statement, tags, author, source,
                       embedding <=> %s::vector AS distance
                FROM knowledge
                WHERE superseded_by IS NULL AND knowledge_base_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding, kb.id, embedding, k),
            )
            rows = _rows(cur)
        return [StoredClaim(**r) for r in rows if r["distance"] <= max_distance]

    def count(self, kb: KnowledgeBase) -> int:
        """How many live claims exist. Shown in the progress UI so "comparing
        against 128 claims" is a real number rather than a reassuring noise."""
        with pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM knowledge "
                "WHERE superseded_by IS NULL AND knowledge_base_id = %s",
                (kb.id,),
            )
            return cur.fetchone()[0]

    def history(self, claim_id: str) -> list[dict]:
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

    # --- writes ---------------------------------------------------------

    def insert(
        self, kb: KnowledgeBase, title: str, statement: str, tags, embedding, author, source
    ) -> str:
        with pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO knowledge
                    (knowledge_base_id, title, statement, tags, author, source, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (kb.id, title, statement, list(tags or []), author, source, embedding),
            )
            return str(cur.fetchone()[0])

    def supersede(self, old_id: str, new_id: str) -> None:
        with pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE knowledge SET superseded_by = %s WHERE id = %s", (new_id, old_id)
            )


class PostgresCatalog:
    """The one implementation of `domain.ports.Catalog`.

    Everything here is scoped to `config.DEFAULT_WORKSPACE`, the only workspace
    anything can currently name. See the port for why that constant lives down
    here rather than being threaded through every signature.
    """

    # --- knowledge bases ------------------------------------------------

    def knowledge_bases(self) -> list[KnowledgeBase]:
        with pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT kb.id, kb.slug, kb.name,
                       count(k.id) FILTER (WHERE k.superseded_by IS NULL) AS claims
                FROM knowledge_base kb
                JOIN workspace w ON w.id = kb.workspace_id AND w.slug = %s
                LEFT JOIN knowledge k ON k.knowledge_base_id = kb.id
                GROUP BY kb.id, kb.slug, kb.name, kb.created_at
                ORDER BY kb.created_at
                """,
                (config.DEFAULT_WORKSPACE,),
            )
            return [KnowledgeBase(**r) for r in _rows(cur)]

    def knowledge_base(self, slug: str) -> KnowledgeBase | None:
        """No claim count here, on purpose: this runs on every capture, every ask
        and every state read, and counting a table to decide where to write into
        it would be a scan per request for a number nobody asked for."""
        with pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT kb.id, kb.slug, kb.name
                FROM knowledge_base kb
                JOIN workspace w ON w.id = kb.workspace_id AND w.slug = %s
                WHERE kb.slug = %s
                """,
                (config.DEFAULT_WORKSPACE, slug),
            )
            rows = _rows(cur)
        return KnowledgeBase(**rows[0]) if rows else None

    def create_knowledge_base(self, slug: str, name: str) -> KnowledgeBase | None:
        """`ON CONFLICT DO NOTHING RETURNING` turns a collision into an empty
        result instead of an exception, so the unique index stays the single
        arbiter of who got the name and no layer has to catch a driver error to
        find out who lost."""
        with pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO knowledge_base (workspace_id, slug, name)
                SELECT w.id, %s, %s FROM workspace w WHERE w.slug = %s
                ON CONFLICT (workspace_id, slug) DO NOTHING
                RETURNING id, slug, name
                """,
                (slug, name, config.DEFAULT_WORKSPACE),
            )
            rows = _rows(cur)
        return KnowledgeBase(**rows[0]) if rows else None

    # --- the review listing ---------------------------------------------

    def record_session(
        self, session_id: str, kb: KnowledgeBase, author: str | None, stage: str, summary: str
    ) -> None:
        """The `WHERE` on the upsert is what stops a polling UI reshuffling its
        own list: a read that finds the session exactly where it left it writes
        nothing, so `updated_at` only moves when the review actually did."""
        with pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO review_session (id, knowledge_base_id, author, stage, summary)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                   SET stage = EXCLUDED.stage,
                       summary = EXCLUDED.summary,
                       updated_at = now()
                 WHERE review_session.stage IS DISTINCT FROM EXCLUDED.stage
                    OR review_session.summary IS DISTINCT FROM EXCLUDED.summary
                """,
                (session_id, kb.id, author, stage, summary),
            )

    def sessions(self, kb: KnowledgeBase, limit: int) -> list[dict]:
        """Ordered by `created_at`, not `updated_at`: this is a list of captures
        in the order they were made, and a review someone came back to a day
        later should not jump over the three they have started since."""
        with pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id::text AS session_id, s.stage, s.summary, s.author,
                       %s AS knowledge_base, s.created_at, s.updated_at
                FROM review_session s
                WHERE s.knowledge_base_id = %s
                ORDER BY s.created_at DESC LIMIT %s
                """,
                (kb.slug, kb.id, limit),
            )
            return _rows(cur)
