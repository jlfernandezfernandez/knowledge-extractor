import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Toaster } from "sonner";
import { api, type Progress } from "./api";
import { AskCommand } from "./AskCommand";
import { CaptureStep, ConfirmStep, ConflictStep, DoneStep } from "./steps";
import type { SessionState } from "./types";
import { Button, LanguagePicker, Problem, Rail, Working } from "./ui";

export default function App() {
  const { t } = useTranslation();
  const [session, setSession] = useState<SessionState | null>(null);
  const [progress, setProgress] = useState<Progress[]>([]);
  const [busy, setBusy] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<unknown>(null);

  // ⌘K / Ctrl+K, the shortcut every tool this sits next to already uses.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setAsking((open) => !open);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  // Deep link: /review/<id> resumes a review opened by an agent over MCP or A2A.
  useEffect(() => {
    const id = window.location.pathname.match(/^\/review\/([\w-]+)/)?.[1];
    if (!id) return;
    api.session(id).then(setSession).catch(setError);
  }, []);

  const advance = useCallback((next: SessionState) => {
    setSession(next);
    setProgress([]);
    setBusy(false);
  }, []);

  const onProgress = useCallback(
    (event: Progress) => setProgress((events) => [...events, event]),
    [],
  );

  function restart() {
    setSession(null);
    setProgress([]);
    setError(null);
    window.history.replaceState(null, "", "/");
  }

  const stage = session?.stage ?? "capture";
  const steps = { onProgress, setBusy, busy, onDone: advance };

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-10 border-b border-line bg-paper/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-5xl items-center gap-4 px-6 py-3.5">
          <button
            onClick={restart}
            className="font-display text-[17px] font-bold tracking-[-0.02em] transition-opacity
                       duration-[--press] hover:opacity-70"
          >
            Knowledge Extractor
          </button>
          <p className="hidden text-[13px] text-muted lg:block">{t("app.tagline")}</p>
          <div className="ml-auto flex items-center gap-2">
            <LanguagePicker />
            <Button onClick={() => setAsking(true)}>
              {t("app.ask")}
              <kbd className="hidden rounded border border-line-strong/60 px-1 font-mono text-[10px] text-faint sm:block">
                ⌘K
              </kbd>
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-5xl gap-10 px-6 py-10 md:grid-cols-[170px_1fr]">
        <div className="hidden md:block">
          <Rail stage={stage} />
        </div>

        <div className="min-w-0">
          {busy ? (
            <Working events={progress} />
          ) : !session ? (
            <CaptureStep {...steps} />
          ) : stage === "confirm" ? (
            <ConfirmStep state={session} {...steps} />
          ) : stage === "resolve" ? (
            <ConflictStep state={session} {...steps} />
          ) : (
            <DoneStep state={session} onRestart={restart} />
          )}
          <Problem error={error} />
        </div>
      </main>

      <AskCommand open={asking} onClose={() => setAsking(false)} />
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: "var(--raised)",
            color: "var(--ink)",
            border: "1px solid var(--line)",
            fontFamily: "var(--font-sans)",
          },
        }}
      />
    </div>
  );
}
