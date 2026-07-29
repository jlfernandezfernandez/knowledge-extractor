import { useCallback, useEffect, useState } from "react";
import { review } from "@/lib/api/review";
import { stepTo, type Direction } from "@/lib/transition";
import type {
  ClaimDraft,
  Progress,
  Resolution,
  SessionState,
  Stage,
} from "@/types/review";

/**
 * The review, as one state machine.
 *
 * Everything the four steps share lives here: which step we are on, what the
 * graph is doing right now, and how to move in either direction. The steps
 * themselves only render and call back.
 *
 * `draft` is kept alongside the session because stepping back out of the
 * confirm gate means leaving the graph entirely — there is no session to
 * return to, only the words the person typed. The backend also echoes them as
 * `raw_text`, which is what makes a review opened by an agent resumable.
 */
export function useReview() {
  const [session, setSession] = useState<SessionState | null>(null);
  const [draft, setDraft] = useState("");
  const [progress, setProgress] = useState<Progress[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  // Counts every move the review makes. The rail lists sessions, so it goes
  // stale the moment one starts, advances or is abandoned.
  const [moves, setMoves] = useState(0);

  const stage: Stage = session?.stage ?? "capture";

  // Deep link: /review/<id> resumes a review an agent opened over MCP or A2A.
  useEffect(() => {
    const id = window.location.pathname.match(/^\/review\/([\w-]+)/)?.[1];
    if (!id) return;
    review.get(id).then(setSession).catch(setError);
  }, []);

  const arrive = useCallback((next: SessionState, direction: Direction) => {
    stepTo(direction, () => {
      setSession(next);
      setProgress([]);
      setBusy(false);
      setMoves((n) => n + 1);
    });
  }, []);

  /** Run one step of the graph, showing its progress and surfacing failures
   *  in place rather than throwing them away. Returns the state it landed on,
   *  or nothing if the step failed. */
  const run = useCallback(
    async (step: () => Promise<SessionState>, direction: Direction = "forward") => {
      setBusy(true);
      setError(null);
      try {
        const next = await step();
        arrive(next, direction);
        return next;
      } catch (failed) {
        setError(failed);
        setBusy(false);
      }
    },
    [arrive],
  );

  const onProgress = useCallback(
    (event: Progress) => setProgress((events) => [...events, event]),
    [],
  );

  /** Leave the graph and go back to the composer, carrying `text` into it. */
  const leave = useCallback((text: string) => {
    stepTo("back", () => {
      setSession(null);
      setProgress([]);
      setError(null);
      setDraft(text);
      setMoves((n) => n + 1);
    });
    window.history.replaceState(null, "", "/");
  }, []);

  const reset = useCallback(() => leave(""), [leave]);

  /** Open a review that already exists: a click in the rail, or a deep link
   *  from a review an agent opened over MCP or A2A. */
  const resume = useCallback(
    (sessionId: string) => run(() => review.get(sessionId)),
    [run],
  );

  const start = useCallback(
    (text: string, author: string | null, knowledgeBase: string) =>
      run(() => review.start(text, author, knowledgeBase, onProgress)),
    [run, onProgress],
  );

  const confirm = useCallback(
    (claims: ClaimDraft[], clarification: string | null = null) =>
      run(() => review.confirm(session!.session_id, claims, clarification, onProgress)),
    [run, onProgress, session],
  );

  const resolve = useCallback(
    (resolutions: Record<string, Resolution>) =>
      run(() => review.resolve(session!.session_id, resolutions)),
    [run, session],
  );

  /**
   * One step back.
   *
   * From the confirm gate there is nothing earlier inside the graph — the
   * session is abandoned and the composer refills with what was said. From
   * the resolve gate the graph itself rewinds to the confirm gate, because
   * the checkpointer still holds every state it passed through.
   */
  const back = useCallback(() => {
    if (!session || stage === "confirm") return leave(session?.raw_text ?? draft);
    void run(() => review.back(session.session_id), "back");
  }, [session, stage, draft, leave, run]);

  return {
    stage,
    session,
    draft,
    setDraft,
    progress,
    busy,
    error,
    setError,
    version: moves,
    canGoBack: stage === "confirm" || stage === "resolve",
    start,
    resume,
    confirm,
    resolve,
    back,
    reset,
  };
}

export type Review = ReturnType<typeof useReview>;
