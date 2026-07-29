// Mirrors backend/knowli/interfaces/http/schemas.py. Keep the two in step.

import type { StoredClaim } from "./knowledge";

/** How a new claim relates to one already stored. */
export type Verdict = "conflict" | "duplicate" | "refines" | "unrelated";

/** What the person decided to do about that relationship. */
export type DecisionAction = "keep_new" | "keep_old" | "keep_both" | "merge";

/** The stages the backend reports. `capture` is client-side: there is no
 *  session until the first claim has been extracted. */
export type ServerStage = "extracting" | "confirm" | "detecting" | "resolve" | "done";
export type Stage = "capture" | ServerStage;

export interface ClaimDraft {
  id: string;
  title: string;
  statement: string;
  topic: string;
  tags: string[];
}

export interface Conflict {
  key: string;
  draft_id: string;
  stored: StoredClaim;
  verdict: Verdict;
  reason: string;
  /** Which resolutions the backend will accept for this verdict. Keeping both
   *  sides of a contradiction is not one of them. */
  allowed: DecisionAction[];
  /** Pre-selected, so the common case needs no clicking. */
  recommended: DecisionAction;
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

/** One row of "what you were last working on". An index over the paused
 *  sessions, carrying only what a list needs to show. */
export interface SessionSummary {
  session_id: string;
  stage: ServerStage;
  summary: string;
  author?: string | null;
  knowledge_base: string;
  created_at: string;
  updated_at: string;
}

export interface SessionState {
  session_id: string;
  stage: ServerStage;
  /** Slug of the knowledge base this review writes into. */
  knowledge_base: string;
  /** What the person originally said. Used to refill the composer when they
   *  step back out of the review. */
  raw_text?: string;
  summary: string;
  open_questions: string[];
  claims: ClaimDraft[];
  conflicts: Conflict[];
  committed: CommittedClaim[];
}

/** Progress events, forwarded from LangGraph's own node updates. Every count
 *  is a real one — this is not a spinner with words on it. */
export type Progress =
  | { type: "progress"; step: "reading" }
  | { type: "progress"; step: "extracted"; count: number; against: number }
  | { type: "progress"; step: "compared"; count: number }
  | { type: "progress"; step: "committed"; count: number };
