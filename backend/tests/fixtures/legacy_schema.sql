-- Snapshot of the pre-migration schema used to prove an in-place upgrade.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS btree_gin;

CREATE TABLE workspace (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), slug text UNIQUE NOT NULL,
  name text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE knowledge_base (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), workspace_id uuid NOT NULL REFERENCES workspace(id),
  slug text NOT NULL, name text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, slug)
);
CREATE TABLE knowledge (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), title text NOT NULL, statement text NOT NULL,
  tags text[] NOT NULL DEFAULT '{}', author text, source text, embedding vector(384) NOT NULL,
  superseded_by uuid REFERENCES knowledge(id), created_at timestamptz NOT NULL DEFAULT now(),
  knowledge_base_id uuid NOT NULL REFERENCES knowledge_base(id),
  search tsvector GENERATED ALWAYS AS (to_tsvector('simple', title || ' ' || statement)) STORED
);
CREATE INDEX knowledge_embedding_idx ON knowledge USING hnsw (embedding vector_cosine_ops);
CREATE INDEX knowledge_scoped_search_idx ON knowledge USING gin (knowledge_base_id, search);
CREATE TABLE review_session (
  id uuid PRIMARY KEY, knowledge_base_id uuid NOT NULL REFERENCES knowledge_base(id), author text,
  stage text NOT NULL, summary text NOT NULL DEFAULT '', created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(), contributor_id uuid, interview_id uuid,
  contribution_kind text NOT NULL DEFAULT 'voluntary'
);
CREATE TABLE app_user (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), email text UNIQUE NOT NULL,
  display_name text NOT NULL, password_hash text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE review_session ADD FOREIGN KEY (contributor_id) REFERENCES app_user(id);
CREATE INDEX review_session_recent_idx ON review_session (knowledge_base_id, created_at DESC);
CREATE TABLE organisation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE team (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), organisation_id uuid NOT NULL REFERENCES organisation(id),
  name text NOT NULL, knowledge_base_id uuid NOT NULL REFERENCES knowledge_base(id),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE team_member (
  team_id uuid NOT NULL REFERENCES team(id), user_id uuid NOT NULL REFERENCES app_user(id),
  PRIMARY KEY (team_id, user_id)
);
CREATE TABLE app_session (
  token_hash text PRIMARY KEY, user_id uuid NOT NULL REFERENCES app_user(id),
  expires_at timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE interview (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), team_id uuid NOT NULL REFERENCES team(id),
  requester_id uuid NOT NULL REFERENCES app_user(id), assignee_id uuid NOT NULL REFERENCES app_user(id),
  title text NOT NULL, brief text NOT NULL DEFAULT '', session_id uuid REFERENCES review_session(id),
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'started', 'done')),
  created_at timestamptz NOT NULL DEFAULT now(), started_at timestamptz, completed_at timestamptz
);
CREATE TABLE audit_event (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), team_id uuid NOT NULL REFERENCES team(id),
  actor_id uuid NOT NULL REFERENCES app_user(id), kind text NOT NULL, subject_id uuid,
  detail jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX interview_assignee_idx ON interview (assignee_id, status, created_at DESC);
