import { useEffect, useState } from "react";
import { api } from "./api";
import { AskPanel } from "./AskPanel";
import { CaptureStep, ConfirmStep, ConflictStep, DoneStep } from "./steps";
import type { SessionState } from "./types";
import { Button, Problem, Rail, Working } from "./ui";

export default function App() {
  const [session, setSession] = useState<SessionState | null>(null);
  const [busy, setBusy] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<unknown>(null);

  // Deep link: /review/<id> resumes a review opened by an agent over MCP or A2A.
  useEffect(() => {
    const id = window.location.pathname.match(/^\/review\/([\w-]+)/)?.[1];
    if (!id) return;
    setBusy(true);
    api
      .session(id)
      .then(setSession)
      .catch(setError)
      .finally(() => setBusy(false));
  }, []);

  const stage = session?.stage ?? "capture";
  const waiting =
    busy && (!session || stage === "confirm" ? "Reading what you said" : "Comparing against the knowledge base");

  function restart() {
    setSession(null);
    window.history.replaceState(null, "", "/");
  }

  return (
    <div className="min-h-dvh">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-5xl items-center gap-4 px-6 py-4">
          <button onClick={restart} className="text-left">
            <span className="font-display text-lg font-bold tracking-tight">
              Knowledge&nbsp;Extractor
            </span>
          </button>
          <p className="hidden text-sm text-muted sm:block">
            Get what one person knows into what everyone can query
          </p>
          <div className="ml-auto">
            <Button onClick={() => setAsking(true)}>Ask what we know</Button>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-5xl gap-10 px-6 py-10 md:grid-cols-[168px_1fr]">
        <div className="hidden md:block">
          <Rail stage={stage} />
        </div>

        <div className="min-w-0">
          {busy ? (
            <Working label={waiting as string} />
          ) : !session ? (
            <CaptureStep onDone={setSession} busy={busy} setBusy={setBusy} />
          ) : stage === "confirm" ? (
            <ConfirmStep state={session} onDone={setSession} busy={busy} setBusy={setBusy} />
          ) : stage === "resolve" ? (
            <ConflictStep state={session} onDone={setSession} busy={busy} setBusy={setBusy} />
          ) : (
            <DoneStep state={session} onRestart={restart} />
          )}
          <Problem error={error} />
        </div>
      </main>

      {asking && <AskPanel onClose={() => setAsking(false)} />}
    </div>
  );
}
