CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE app_user (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text NOT NULL,
  display_name text NOT NULL,
  password_hash text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX app_user_email_ci_idx ON app_user (lower(email));

CREATE TABLE login_session (
  token_hash text PRIMARY KEY CHECK (token_hash ~ '^[0-9a-f]{64}$'),
  user_id uuid NOT NULL REFERENCES app_user(id),
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE interview (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  requester_id uuid NOT NULL REFERENCES app_user(id),
  assignee_id uuid NOT NULL REFERENCES app_user(id),
  title text NOT NULL,
  brief text,
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'started', 'completed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  started_at timestamptz,
  completed_at timestamptz
);
CREATE INDEX interview_assignee_status_created_idx
  ON interview (assignee_id, status, created_at DESC);

CREATE TABLE contribution (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  author_id uuid NOT NULL REFERENCES app_user(id),
  kind text NOT NULL CHECK (kind IN ('voluntary', 'interview')),
  interview_id uuid UNIQUE REFERENCES interview(id),
  source text NOT NULL,
  raw_text text NOT NULL DEFAULT '',
  stage text NOT NULL CHECK (stage IN ('claims', 'conflicts', 'commit', 'committed')),
  summary text NOT NULL DEFAULT '',
  revision integer NOT NULL DEFAULT 0 CHECK (revision >= 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  committed_at timestamptz
);

CREATE TABLE claim (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contribution_id uuid NOT NULL REFERENCES contribution(id),
  draft_key text NOT NULL,
  title text NOT NULL,
  statement text NOT NULL,
  tags text[] NOT NULL DEFAULT '{}',
  embedding vector(384) NOT NULL,
  search_vector tsvector GENERATED ALWAYS AS (
    to_tsvector('simple', title || ' ' || statement)
  ) STORED,
  superseded_by uuid REFERENCES claim(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (contribution_id, draft_key)
);
CREATE INDEX claim_embedding_idx ON claim USING hnsw (embedding vector_cosine_ops);
CREATE INDEX claim_search_idx ON claim USING gin (search_vector);
