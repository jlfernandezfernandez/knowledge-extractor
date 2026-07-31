export type ContributionStage = "claims" | "conflicts" | "commit" | "committed";

export type ClaimDraft = {
  draft_key: string;
  title: string;
  statement: string;
  tags: string[];
};

export type ConflictResolution = {
  claim_draft_key: string;
  action: "keep_new" | "keep_old" | "keep_both" | "merge";
  replacement_statement?: string | null;
};

export type ContributionConflict = {
  claim_draft_key: string;
  existing_id: string;
  verdict: string;
  reason: string;
};

export type Contribution = {
  id: string;
  author_id: string;
  author: string;
  source: "text" | "interview";
  raw_text: string;
  stage: ContributionStage;
  revision: number;
  summary: string;
  created_at: string;
  committed_at: string | null;
  claim_count: number;
  claims: ClaimDraft[];
  conflicts: ContributionConflict[];
};
