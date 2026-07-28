// Mirrors backend/ke/schemas.py. Keep the two in step.

export type Verdict = "conflict" | "duplicate" | "refines" | "unrelated";
export type DecisionAction = "keep_new" | "keep_old" | "keep_both" | "merge";
export type Stage = "extracting" | "confirm" | "detecting" | "resolve" | "done";

export interface ClaimDraft {
  id: string;
  title: string;
  statement: string;
  tags: string[];
}

export interface StoredClaim {
  id: string;
  title: string;
  statement: string;
  tags: string[];
  author?: string | null;
  source?: string | null;
  score?: number | null;
  distance?: number | null;
}

export interface Conflict {
  key: string;
  draft_id: string;
  stored: StoredClaim;
  verdict: Verdict;
  reason: string;
}

export interface Resolution {
  action: DecisionAction;
  statement?: string | null;
}

export interface CommittedClaim {
  id: string;
  title: string;
  statement: string;
  superseded: string[];
}

export interface SessionState {
  session_id: string;
  stage: Stage;
  summary: string;
  open_questions: string[];
  claims: ClaimDraft[];
  conflicts: Conflict[];
  committed: CommittedClaim[];
}

export interface AskResponse {
  answer: string;
  sources: StoredClaim[];
}
