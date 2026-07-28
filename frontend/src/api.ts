import type {
  AskResponse,
  ClaimDraft,
  Resolution,
  SessionState,
  StoredClaim,
} from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: init?.body instanceof FormData ? {} : { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `${response.status} ${response.statusText}`);
  }
  return response.json();
}

/** Progress events the backend forwards from LangGraph's own node updates. */
export type Progress =
  | { type: "progress"; step: "reading" }
  | { type: "progress"; step: "extracted"; count: number; against: number }
  | { type: "progress"; step: "compared"; count: number }
  | { type: "progress"; step: "committed"; count: number };

/**
 * POST and read the Server-Sent Events response.
 *
 * `EventSource` only speaks GET, so the stream is read off `fetch`. Events are
 * split on the blank-line delimiter and the tail is carried between chunks —
 * an SSE frame is not guaranteed to arrive whole.
 */
async function stream(
  path: string,
  body: unknown,
  onProgress: (event: Progress) => void,
): Promise<SessionState> {
  const response = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
  });
  if (!response.ok || !response.body) {
    const failed = await response.json().catch(() => ({}));
    throw new Error(failed.detail ?? `${response.status} ${response.statusText}`);
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  let final: SessionState | null = null;

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += value;
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const line = frame.trim();
      if (!line.startsWith("data:")) continue;
      const event = JSON.parse(line.slice(5));
      if (event.type === "state") final = event.state as SessionState;
      else if (event.type === "error") throw new Error(event.detail);
      else onProgress(event as Progress);
    }
  }
  if (!final) throw new Error("The stream ended before the review reached a step.");
  return final;
}

export const api = {
  capture: (text: string, author: string | undefined, onProgress: (e: Progress) => void) =>
    stream("/api/sessions", { text, author: author || null, source: "web" }, onProgress),

  confirm: (
    sessionId: string,
    claims: ClaimDraft[],
    clarification: string | undefined,
    onProgress: (e: Progress) => void,
  ) =>
    stream(
      `/api/sessions/${sessionId}/confirm`,
      { claims, clarification: clarification || null },
      onProgress,
    ),

  resolve: (sessionId: string, resolutions: Record<string, Resolution>) =>
    request<SessionState>(`/api/sessions/${sessionId}/resolve`, {
      method: "POST",
      body: JSON.stringify({ resolutions }),
    }),

  session: (sessionId: string) => request<SessionState>(`/api/sessions/${sessionId}`),

  ask: (question: string) =>
    request<AskResponse>("/api/ask", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),

  knowledge: (q?: string) =>
    request<{ items: StoredClaim[] }>(
      q ? `/api/knowledge?q=${encodeURIComponent(q)}` : "/api/knowledge",
    ),

  transcribe: (blob: Blob) => {
    const form = new FormData();
    form.append("file", blob, "capture.webm");
    return request<{ text: string }>("/api/transcribe", { method: "POST", body: form });
  },
};
