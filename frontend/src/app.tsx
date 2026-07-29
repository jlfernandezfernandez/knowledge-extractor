import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Toaster } from "sonner";
import { api, type Progress } from "./api";
import { AskCommand } from "./AskCommand";
import { CaptureStep, ConfirmStep, ConflictStep, DoneStep } from "./steps";
import type { SessionState } from "./types";
import { Button, Problem, Stepper, Working } from "./ui";

/**
 * Advance the deck.
 *
 * View Transitions let the browser snapshot the old and new slide itself, so
 * they cross without the outgoing React tree staying mounted and without a
 * layout jump when the two slides are different heights. The direction is
 * written to the document so the CSS can send the slide out the way the next
 * one comes in — enter and exit along the same path.
 */
function slideTo(direction: "forward" | "back", update: () => void) {
  document.documentElement.dataset.direction = direction;
  if (!document.startViewTransition) return update();
  document.startViewTransition(update);
}

export default function App() {
  const { t } = useTranslation();
  const [session, setSession] = useState<SessionState | null>(null);
  const [progress, setProgress] = useState<Progress[]>([]);
  const [busy, setBusy] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const stageRef = useRef<HTMLDivElement>(null);

  // ⌘K, the shortcut every tool this sits next to already uses.
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

  const stage = session?.stage ?? "capture";

  const advance = useCallback((next: SessionState) => {
    slideTo("forward", () => {
      setSession(next);
      setProgress([]);
      setBusy(false);
    });
    stageRef.current?.scrollTo({ top: 0 });
  }, []);

  const onProgress = useCallback(
    (event: Progress) => setProgress((events) => [...events, event]),
    [],
  );

  function restart() {
    slideTo("back", () => {
      setSession(null);
      setProgress([]);
      setError(null);
    });
    window.history.replaceState(null, "", "/");
  }

  const steps = { onProgress, setBusy, busy, onDone: advance, onRestart: restart };

  return (
    <div className="flex h-dvh flex-col">
      {/* Translucent chrome with the deck running underneath it, rather than an
          opaque bar that eats a fixed strip of the slide. */}
      <header className="chrome z-10 shrink-0 bg-paper/70 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-3xl items-center gap-4 px-6">
          <button
            onClick={restart}
            className="font-display text-[15px] font-bold tracking-[-0.02em] transition-opacity
                       duration-[--press] hover:opacity-60"
          >
            KE
          </button>
          <div className="mx-auto">
            <Stepper stage={stage} />
          </div>
          <Button variant="ghost" onClick={() => setAsking(true)}>
            {t("app.ask")}
            <kbd className="hidden rounded border border-line px-1 font-mono text-[10px] sm:block">
              ⌘K
            </kbd>
          </Button>
        </div>
      </header>

      {/* The stage. `view-transition-name` marks this subtree as the thing that
          slides; everything else (the chrome) stays put. */}
      <main
        ref={stageRef}
        className="min-h-0 flex-1 overflow-y-auto"
        style={{ viewTransitionName: "slide" }}
      >
        <div className="mx-auto h-full max-w-3xl px-6">
          {busy ? (
            <div className="flex h-full items-center">
              <Working events={progress} />
            </div>
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
