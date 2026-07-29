import type {
  ClaimDraft,
  Progress,
  Resolution,
  SessionState,
  SessionSummary,
} from "@/types/review";
import { post, request } from "./client";
import { streamStep } from "./sse";

type OnProgress = (event: Progress) => void;

/** The four-step review. Two of these pause on a human gate in the graph. */
export const review = {
  /** Step 1 → 2. Extract claims, then wait for the person to confirm them. */
  start: (text: string, author: string | null, knowledgeBase: string, onProgress: OnProgress) =>
    streamStep(
      "/api/sessions",
      { text, author: author || null, source: "web", knowledge_base: knowledgeBase },
      onProgress,
    ),

  /** Step 2 → 3. Accept the claims, or send a clarification to re-extract. */
  confirm: (
    sessionId: string,
    claims: ClaimDraft[],
    clarification: string | null,
    onProgress: OnProgress,
  ) =>
    streamStep(
      `/api/sessions/${sessionId}/confirm`,
      { claims, clarification: clarification || null },
      onProgress,
    ),

  /** Step 3 → 4. Apply the decisions and write. Fast enough not to stream. */
  resolve: (sessionId: string, resolutions: Record<string, Resolution>) =>
    post<SessionState>(`/api/sessions/${sessionId}/resolve`, { resolutions }),

  /** Rewind the graph to the previous human gate. Nothing has been written
   *  yet at this point, so going back costs nothing but a replay. */
  back: (sessionId: string) => post<SessionState>(`/api/sessions/${sessionId}/back`),

  /** Resume a review: a deep link from /review/<id>, or a click in the rail. */
  get: (sessionId: string) => request<SessionState>(`/api/sessions/${sessionId}`),

  /** What you were last working on, newest first. */
  recent: (knowledgeBase: string, limit = 20) =>
    request<{ items: SessionSummary[] }>(
      `/api/sessions?knowledge_base=${encodeURIComponent(knowledgeBase)}&limit=${limit}`,
    ).then((body) => body.items),
};
