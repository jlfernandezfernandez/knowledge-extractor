-- Stage the two legacy tables whose names collide with final tables. Their
-- foreign keys follow the rename, keeping the old graph intact for import.
DO $$
BEGIN
  IF to_regclass(format('%I.app_user', current_schema())) IS NOT NULL
     AND to_regclass(format('%I.legacy_app_user', current_schema())) IS NULL THEN
    IF EXISTS (
      SELECT 1
      FROM pg_constraint table_constraint
      JOIN pg_attribute attribute
        ON attribute.attrelid = table_constraint.conrelid
       AND attribute.attnum = ANY(table_constraint.conkey)
      WHERE table_constraint.conrelid = 'app_user'::regclass
        AND table_constraint.contype = 'u' AND attribute.attname = 'email'
    ) AND NOT EXISTS (
      SELECT 1 FROM pg_indexes
      WHERE schemaname = current_schema() AND tablename = 'app_user'
        AND indexdef LIKE '%lower(email)%'
    ) THEN
      ALTER TABLE app_user RENAME TO legacy_app_user;
    END IF;
  END IF;
  IF to_regclass(format('%I.interview', current_schema())) IS NOT NULL
     AND to_regclass(format('%I.legacy_interview', current_schema())) IS NULL THEN
    IF EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = current_schema() AND table_name = 'interview' AND column_name = 'team_id'
    ) THEN
      IF (SELECT count(*) FROM information_schema.columns
          WHERE table_schema = current_schema() AND table_name = 'interview'
            AND column_name IN (
              'team_id', 'requester_id', 'assignee_id', 'title', 'brief', 'session_id',
              'status', 'created_at', 'started_at', 'completed_at'
            )) <> 10 THEN
        RAISE EXCEPTION 'legacy interview has an unsupported shape';
      END IF;
      ALTER TABLE interview RENAME TO legacy_interview;
    END IF;
  END IF;
END $$;

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- A case-insensitive final email key cannot silently merge legacy accounts.
DO $$
BEGIN
  IF to_regclass(format('%I.legacy_app_user', current_schema())) IS NOT NULL THEN
    IF EXISTS (SELECT 1 FROM legacy_app_user GROUP BY lower(email) HAVING count(*) > 1) THEN
      RAISE EXCEPTION 'legacy emails collide when normalized';
    END IF;
  END IF;
  IF to_regclass(format('%I.knowledge', current_schema())) IS NOT NULL THEN
    IF EXISTS (
      SELECT 1 FROM pg_attribute attribute
      WHERE attribute.attrelid = 'knowledge'::regclass
        AND attribute.attname = 'embedding' AND NOT attribute.attisdropped
        AND format_type(attribute.atttypid, attribute.atttypmod) <> 'vector(384)'
    ) THEN
      RAISE EXCEPTION 'legacy embedding dimension is not compatible with vector(384)';
    END IF;
  END IF;
END $$;

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
