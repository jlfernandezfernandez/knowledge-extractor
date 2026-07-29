-- The knowledge table. `{dim}` is filled in from EMBED_DIM before this runs,
-- because pgvector needs the dimension baked into the column type.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
-- btree_gin is what lets a GIN index mix a plain column with a tsvector. It is
-- the difference between a lexical index over the whole table and one scoped to
-- a knowledge base; it ships with Postgres, so this is not a new dependency.
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- --- The container ------------------------------------------------------
--
-- One flat pile of claims is fine for one person and useless for a support org:
-- a claim about kitchen returns must not be compared against one about sofa
-- deliveries, and conflict detection cannot tell them apart from the text
-- alone. So claims live in a knowledge base, and a knowledge base lives in a
-- workspace. Both are created automatically below, so a solo user never meets
-- the concept unless they go looking for it.
--
-- There is no user table and no owner column: users and auth are out of scope.
-- These tables exist now so that adding people later is a new table plus a
-- join, rather than a migration that has to touch every claim ever written.

CREATE TABLE IF NOT EXISTS workspace (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug       text UNIQUE NOT NULL,
    name       text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_base (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id uuid NOT NULL REFERENCES workspace(id),
    slug         text NOT NULL,
    name         text NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    -- Unique per workspace, not globally: two companies may both want a
    -- "support" knowledge base and neither should be told the name is taken.
    UNIQUE (workspace_id, slug)
);

-- The default pair. `ON CONFLICT DO NOTHING` is the whole idempotency story:
-- this file runs on every startup and has to be a no-op after the first one.
INSERT INTO workspace (slug, name) VALUES ('{workspace}', '{workspace_name}')
    ON CONFLICT (slug) DO NOTHING;
INSERT INTO knowledge_base (workspace_id, slug, name)
    SELECT id, '{knowledge_base}', '{knowledge_base_name}'
    FROM workspace WHERE slug = '{workspace}'
    ON CONFLICT (workspace_id, slug) DO NOTHING;

-- --- The claims ---------------------------------------------------------

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

-- The scope, added the same way and for the same reason: an install that has
-- been collecting claims for months has to migrate in place, not start over.
-- The column arrives nullable with its foreign key already attached — ADD
-- COLUMN IF NOT EXISTS covers the constraint too, which a separate ADD
-- CONSTRAINT has no way to do — then every existing row is backfilled into the
-- default knowledge base, and only then does it become NOT NULL. On a fresh
-- database the backfill matches nothing and the same three statements hold.
ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS knowledge_base_id uuid
    REFERENCES knowledge_base(id);

UPDATE knowledge SET knowledge_base_id = (
        SELECT kb.id FROM knowledge_base kb
        JOIN workspace w ON w.id = kb.workspace_id
        WHERE w.slug = '{workspace}' AND kb.slug = '{knowledge_base}'
    )
    WHERE knowledge_base_id IS NULL;

ALTER TABLE knowledge ALTER COLUMN knowledge_base_id SET NOT NULL;

-- --- Indexes ------------------------------------------------------------
--
-- All three retrieval indexes had to be reconsidered, and they did not get the
-- same answer.
--
-- HNSW stays global and alone on the vector column, because pgvector indexes
-- exactly one vector and nothing beside it: there is no composite HNSW to
-- build. The scope is therefore a filter over an approximate scan, which on its
-- own means a query can quietly come back with three neighbours instead of five
-- because the other two belonged to another knowledge base — the worst kind of
-- bug, since missing neighbours look exactly like "no conflicts". pgvector 0.8's
-- iterative scan is the fix and the repository turns it on for both vector
-- queries; see `SET LOCAL hnsw.iterative_scan` there. Partitioning the table by
-- knowledge base would give a genuinely scoped vector index and is the thing to
-- reach for when one base grows big enough to swamp the others. It is not worth
-- the machinery at a few thousand claims.
CREATE INDEX IF NOT EXISTS knowledge_embedding_idx
    ON knowledge USING hnsw (embedding vector_cosine_ops);

-- The lexical index *can* be scoped, so it is, with the knowledge base leading:
-- the query filters on it by equality and only then ranks, which is the order a
-- composite index wants. The old global version is dropped rather than left
-- alongside — it would be a second copy of the same rows for the planner to
-- weigh and for every write to maintain. Dropping it by its old name is what
-- migrates an existing install; on a fresh one it does nothing.
DROP INDEX IF EXISTS knowledge_search_idx;
CREATE INDEX IF NOT EXISTS knowledge_scoped_search_idx
    ON knowledge USING gin (knowledge_base_id, search);

-- There is no index ordering a knowledge base by date. There was one, for a
-- "browse everything" read that no surface asked for once the sidebar stopped
-- listing the store. `count` uses the equality half and is happy with a scan at
-- this size. Add it back with the query that needs it.
DROP INDEX IF EXISTS knowledge_live_idx;
DROP INDEX IF EXISTS knowledge_scoped_live_idx;

-- --- Recent reviews -----------------------------------------------------
--
-- An index over LangGraph's checkpointer, not a second source of truth. The
-- session state — the claims, the conflicts, which gate it is parked on — still
-- lives in the checkpoint tables and is still read from there. This row carries
-- only what a list needs, because listing the last twenty captures out of the
-- checkpointer would mean deserialising twenty whole graph states to read a
-- stage and one sentence off each.
CREATE TABLE IF NOT EXISTS review_session (
    id                uuid PRIMARY KEY,  -- the LangGraph thread id
    knowledge_base_id uuid NOT NULL REFERENCES knowledge_base(id),
    author            text,
    stage             text NOT NULL,
    summary           text NOT NULL DEFAULT '',
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS review_session_recent_idx
    ON review_session (knowledge_base_id, created_at DESC);
