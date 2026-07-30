ALTER TABLE contribution ADD COLUMN revision integer NOT NULL DEFAULT 0;
ALTER TABLE contribution
  ADD CONSTRAINT contribution_revision_non_negative CHECK (revision >= 0);
