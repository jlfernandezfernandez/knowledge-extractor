export type ClaimItem = {
  id: string;
  title: string;
  statement: string;
  tags?: string[];
};

export type AskEvent =
  | { type: "claims"; items: ClaimItem[] }
  | { type: "token"; content: string }
  | { type: "tool"; name: string; done: boolean }
  | { type: "done" }
  | { type: "error"; code?: string };

/** One agent turn over SSE. `thread_id` is the client's half of the conversation
 *  key; the server namespaces it by user, so it never selects someone else's thread. */
export function askStream(question: string, threadId: string) {
  return new EventSource(
    `/api/ask/stream?question=${encodeURIComponent(question)}&thread_id=${encodeURIComponent(threadId)}`,
  );
}
