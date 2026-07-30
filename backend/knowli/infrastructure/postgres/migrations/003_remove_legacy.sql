-- No CASCADE: an unexpected dependency is data we do not understand well
-- enough to delete, so it must abort this migration. Qualifying current_schema
-- also makes an isolated integration schema unable to touch another install.
DO $$
DECLARE table_name text;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'audit_event', 'team_member', 'team', 'organisation', 'legacy_interview',
    'knowledge', 'review_session', 'knowledge_base', 'workspace', 'app_session',
    'legacy_app_user'
  ] LOOP
    IF to_regclass(format('%I.%I', current_schema(), table_name)) IS NOT NULL THEN
      EXECUTE format('DROP TABLE IF EXISTS %I.%I', current_schema(), table_name);
    END IF;
  END LOOP;
END $$;
