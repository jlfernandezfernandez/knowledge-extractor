// Mirrors the claim shapes in backend/knowli/domain/claim.py. Keep the two in step.

/** A claim that is live in the knowledge base. */
export interface StoredClaim {
  id: string;
  title: string;
  statement: string;
  tags: string[];
  author?: string | null;
  source?: string | null;
  /** Hybrid-retrieval fusion score. Present on search results only. */
  score?: number | null;
  /** Cosine distance. Present on conflict candidates only. */
  distance?: number | null;
}

/**
 * A container of claims — what a vector store calls a collection or a
 * namespace, and what a team calls "our knowledge".
 *
 * It is the unit retrieval and conflict detection are scoped to, which is the
 * point: a support org's claims about kitchen returns must never be weighed
 * against its claims about sofa deliveries. One person working locally never
 * has to think about it; there is always a default.
 */
export interface KnowledgeBase {
  id: string;
  slug: string;
  name: string;
  claims: number;
}

export interface AskResponse {
  answer: string;
  /** Cited claims first, so the UI can show what the answer actually used. */
  sources: StoredClaim[];
}
