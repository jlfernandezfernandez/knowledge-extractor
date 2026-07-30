-- Copy legacy users into their staged final table before resolving authors.
DO $$
BEGIN
  IF to_regclass(format('%I.legacy_app_user', current_schema())) IS NOT NULL THEN
    INSERT INTO app_user (id, email, display_name, password_hash, created_at)
    SELECT id, email, display_name, password_hash, created_at
    FROM legacy_app_user;
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass(format('%I.app_session', current_schema())) IS NOT NULL THEN
    INSERT INTO login_session (token_hash, user_id, expires_at, created_at)
    SELECT token_hash, user_id, expires_at, created_at FROM app_session;
  END IF;
END $$;

-- The final UNIQUE contribution.interview_id needs an explicit preflight.
DO $$
BEGIN
  IF to_regclass(format('%I.legacy_interview', current_schema())) IS NOT NULL THEN
    IF EXISTS (
      SELECT 1 FROM legacy_interview WHERE session_id IS NOT NULL
      GROUP BY session_id HAVING count(*) > 1
    ) THEN
      RAISE EXCEPTION 'multiple legacy interviews share one review session';
    END IF;
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass(format('%I.legacy_interview', current_schema())) IS NOT NULL THEN
    INSERT INTO interview (
      id, requester_id, assignee_id, title, brief, status,
      created_at, started_at, completed_at
    )
    SELECT id, requester_id, assignee_id, title, brief,
           CASE status WHEN 'done' THEN 'completed'
                       WHEN 'started' THEN 'started' ELSE 'pending' END,
           created_at, started_at, completed_at
    FROM legacy_interview;
  END IF;
END $$;

-- Give every unresolved legacy author a deterministic, separate account.
-- Null/blank authors share the documented generic legacy address.
DO $$
BEGIN
  IF to_regclass(format('%I.review_session', current_schema())) IS NOT NULL THEN
    WITH unresolved AS (
      SELECT DISTINCT author FROM review_session author_name
      WHERE (SELECT count(*) FROM app_user user_account
             WHERE user_account.display_name = author_name.author) <> 1
    )
    INSERT INTO app_user (email, display_name, password_hash)
    SELECT CASE WHEN author IS NULL OR btrim(author) = '' THEN 'legacy@local.invalid'
                ELSE 'legacy-' || md5(author) || '@local.invalid' END,
           COALESCE(NULLIF(btrim(author), ''), 'Legacy import'),
           '!legacy-imported-account!'
    FROM unresolved
    ON CONFLICT DO NOTHING;
  END IF;
  IF to_regclass(format('%I.knowledge', current_schema())) IS NOT NULL THEN
    WITH unresolved AS (
      SELECT DISTINCT author FROM knowledge author_name
      WHERE (SELECT count(*) FROM app_user user_account
             WHERE user_account.display_name = author_name.author) <> 1
    )
    INSERT INTO app_user (email, display_name, password_hash)
    SELECT CASE WHEN author IS NULL OR btrim(author) = '' THEN 'legacy@local.invalid'
                ELSE 'legacy-' || md5(author) || '@local.invalid' END,
           COALESCE(NULLIF(btrim(author), ''), 'Legacy import'),
           '!legacy-imported-account!'
    FROM unresolved
    ON CONFLICT DO NOTHING;
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass(format('%I.review_session', current_schema())) IS NOT NULL
     AND to_regclass(format('%I.legacy_interview', current_schema())) IS NOT NULL THEN
    INSERT INTO contribution (
      id, author_id, kind, interview_id, source, raw_text, stage, summary,
      created_at, updated_at, committed_at
    )
    SELECT review.id,
           COALESCE(by_contributor.id, by_name.id, fallback.id),
           CASE WHEN review.contribution_kind = 'interview' THEN 'interview'
                ELSE 'voluntary' END,
           imported_interview.id,
           'text', '',
           CASE review.stage WHEN 'confirm' THEN 'claims'
                             WHEN 'resolve' THEN 'conflicts'
                             WHEN 'done' THEN 'committed'
                             ELSE 'claims' END,
           review.summary, review.created_at, review.updated_at,
           CASE WHEN review.stage = 'done' THEN review.updated_at END
    FROM review_session review
    LEFT JOIN app_user by_contributor ON by_contributor.id = review.contributor_id
    LEFT JOIN LATERAL (
      SELECT (array_agg(id))[1] AS id FROM app_user WHERE display_name = review.author
      HAVING count(*) = 1
    ) by_name ON true
    LEFT JOIN app_user fallback ON fallback.email = CASE
      WHEN review.author IS NULL OR btrim(review.author) = '' THEN 'legacy@local.invalid'
      ELSE 'legacy-' || md5(review.author) || '@local.invalid' END
    LEFT JOIN legacy_interview old_interview ON old_interview.session_id = review.id
    LEFT JOIN interview imported_interview ON imported_interview.id = old_interview.id;
  END IF;
  IF to_regclass(format('%I.review_session', current_schema())) IS NOT NULL
     AND to_regclass(format('%I.legacy_interview', current_schema())) IS NULL THEN
    INSERT INTO contribution (
      id, author_id, kind, source, raw_text, stage, summary,
      created_at, updated_at, committed_at
    )
    SELECT review.id,
           COALESCE(by_contributor.id, by_name.id, fallback.id),
           CASE WHEN review.contribution_kind = 'interview' THEN 'interview'
                ELSE 'voluntary' END,
           'text', '',
           CASE review.stage WHEN 'confirm' THEN 'claims'
                             WHEN 'resolve' THEN 'conflicts'
                             WHEN 'done' THEN 'committed'
                             ELSE 'claims' END,
           review.summary, review.created_at, review.updated_at,
           CASE WHEN review.stage = 'done' THEN review.updated_at END
    FROM review_session review
    LEFT JOIN app_user by_contributor ON by_contributor.id = review.contributor_id
    LEFT JOIN LATERAL (
      SELECT (array_agg(id))[1] AS id FROM app_user WHERE display_name = review.author
      HAVING count(*) = 1
    ) by_name ON true
    LEFT JOIN app_user fallback ON fallback.email = CASE
      WHEN review.author IS NULL OR btrim(review.author) = '' THEN 'legacy@local.invalid'
      ELSE 'legacy-' || md5(review.author) || '@local.invalid' END;
  END IF;
END $$;

-- A legacy knowledge row had no durable review relationship. Preserve it as a
-- committed synthetic contribution, retaining the old claim UUID and lineage.
DO $$
BEGIN
  IF to_regclass(format('%I.knowledge', current_schema())) IS NOT NULL THEN
    INSERT INTO contribution (
      id, author_id, kind, source, raw_text, stage, summary,
      created_at, updated_at, committed_at
    )
    SELECT (
             substr(md5('knowli:legacy-contribution:' || knowledge.id::text), 1, 8) || '-' ||
             substr(md5('knowli:legacy-contribution:' || knowledge.id::text), 9, 4) || '-' ||
             substr(md5('knowli:legacy-contribution:' || knowledge.id::text), 13, 4) || '-' ||
             substr(md5('knowli:legacy-contribution:' || knowledge.id::text), 17, 4) || '-' ||
             substr(md5('knowli:legacy-contribution:' || knowledge.id::text), 21, 12)
           )::uuid,
           COALESCE(by_name.id, fallback.id), 'voluntary',
           COALESCE(knowledge.source, 'legacy'), '', 'committed',
           'Imported legacy knowledge', knowledge.created_at, knowledge.created_at,
           knowledge.created_at
    FROM knowledge
    LEFT JOIN LATERAL (
      SELECT (array_agg(id))[1] AS id FROM app_user WHERE display_name = knowledge.author
      HAVING count(*) = 1
    ) by_name ON true
    LEFT JOIN app_user fallback ON fallback.email = CASE
      WHEN knowledge.author IS NULL OR btrim(knowledge.author) = '' THEN 'legacy@local.invalid'
      ELSE 'legacy-' || md5(knowledge.author) || '@local.invalid' END;

    INSERT INTO claim (
      id, contribution_id, draft_key, title, statement, tags, embedding,
      superseded_by, created_at
    )
    SELECT knowledge.id,
           (
             substr(md5('knowli:legacy-contribution:' || knowledge.id::text), 1, 8) || '-' ||
             substr(md5('knowli:legacy-contribution:' || knowledge.id::text), 9, 4) || '-' ||
             substr(md5('knowli:legacy-contribution:' || knowledge.id::text), 13, 4) || '-' ||
             substr(md5('knowli:legacy-contribution:' || knowledge.id::text), 17, 4) || '-' ||
             substr(md5('knowli:legacy-contribution:' || knowledge.id::text), 21, 12)
           )::uuid,
           'legacy-' || knowledge.id::text, knowledge.title, knowledge.statement,
           knowledge.tags, knowledge.embedding, knowledge.superseded_by, knowledge.created_at
    FROM knowledge;
  END IF;
END $$;

-- Counts catch broad loss; anti-joins name the exact rows that went missing.
DO $$
BEGIN
  IF to_regclass(format('%I.knowledge', current_schema())) IS NOT NULL THEN
    IF (SELECT count(*) FROM claim) < (SELECT count(*) FROM knowledge) THEN
      RAISE EXCEPTION 'legacy claim import lost rows';
    END IF;
  END IF;
  IF to_regclass(format('%I.review_session', current_schema())) IS NOT NULL THEN
    IF (SELECT count(*) FROM contribution) < (SELECT count(*) FROM review_session) THEN
      RAISE EXCEPTION 'legacy contribution import lost rows';
    END IF;
  END IF;
  IF to_regclass(format('%I.legacy_app_user', current_schema())) IS NOT NULL THEN
    IF EXISTS (SELECT 1 FROM legacy_app_user old WHERE NOT EXISTS (
      SELECT 1 FROM app_user new WHERE new.id = old.id
    )) THEN RAISE EXCEPTION 'legacy user import lost rows'; END IF;
  END IF;
  IF to_regclass(format('%I.app_session', current_schema())) IS NOT NULL THEN
    IF EXISTS (SELECT 1 FROM app_session old WHERE NOT EXISTS (
      SELECT 1 FROM login_session new WHERE new.token_hash = old.token_hash
    )) THEN RAISE EXCEPTION 'legacy session import lost rows'; END IF;
  END IF;
  IF to_regclass(format('%I.legacy_interview', current_schema())) IS NOT NULL THEN
    IF EXISTS (SELECT 1 FROM legacy_interview old WHERE NOT EXISTS (
      SELECT 1 FROM interview new WHERE new.id = old.id
    )) THEN RAISE EXCEPTION 'legacy interview import lost rows'; END IF;
  END IF;
  IF to_regclass(format('%I.review_session', current_schema())) IS NOT NULL THEN
    IF EXISTS (SELECT 1 FROM review_session old WHERE NOT EXISTS (
      SELECT 1 FROM contribution new WHERE new.id = old.id
    )) THEN RAISE EXCEPTION 'legacy contribution import lost rows'; END IF;
  END IF;
  IF to_regclass(format('%I.knowledge', current_schema())) IS NOT NULL THEN
    IF EXISTS (SELECT 1 FROM knowledge old WHERE NOT EXISTS (
      SELECT 1 FROM claim new WHERE new.id = old.id
    )) THEN RAISE EXCEPTION 'legacy claim import lost rows'; END IF;
  END IF;
END $$;

-- Release old team/session foreign keys before the legacy cleanup. The renamed
-- table keeps PostgreSQL's old constraint names, so discover those exact names.
DO $$
DECLARE constraint_name text;
BEGIN
  IF to_regclass(format('%I.legacy_interview', current_schema())) IS NOT NULL THEN
    FOR constraint_name IN
      SELECT conname FROM pg_constraint
      WHERE conrelid = 'legacy_interview'::regclass AND contype = 'f'
    LOOP
      EXECUTE format('ALTER TABLE legacy_interview DROP CONSTRAINT %I', constraint_name);
    END LOOP;
  END IF;
END $$;
