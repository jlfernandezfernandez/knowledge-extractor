import type { Progress, SessionState } from "@/types/review";
import { API_URL, failure } from "./client";

/**
 * POST a step of the review and read the Server-Sent Events response.
 *
 * `EventSource` only speaks GET, so the stream is read off `fetch`. Frames are
 * split on the blank-line delimiter and the tail is carried between chunks —
 * an SSE frame is not guaranteed to arrive whole.
 *
 * The stream ends with the full session state, which is what the caller wants;
 * everything before it is progress the UI shows while waiting.
 */
export async function streamStep(
  path: string,
  body: unknown,
  onProgress: (event: Progress) => void,
): Promise<SessionState> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
  });
  if (!response.ok || !response.body) throw await failure(response);

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
