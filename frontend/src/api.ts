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

export const api = {
  capture: (text: string, author?: string) =>
    request<SessionState>("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ text, author: author || null, source: "web" }),
    }),

  confirm: (sessionId: string, claims: ClaimDraft[], clarification?: string) =>
    request<SessionState>(`/api/sessions/${sessionId}/confirm`, {
      method: "POST",
      body: JSON.stringify({ claims, clarification: clarification || null }),
    }),

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
