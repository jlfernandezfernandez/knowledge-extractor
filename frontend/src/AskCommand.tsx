import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "./api";
import type { AskResponse } from "./types";
import { Eyebrow, Problem } from "./ui";

/**
 * The question surface, as a command palette.
 *
 * Deliberately **not animated**. It is keyboard-initiated (⌘K) and, in a tool
 * whose whole point is answering questions, opened dozens of times a day —
 * exactly the frequency where an entrance animation stops reading as polish
 * and starts reading as lag. Raycast opens instantly for the same reason.
 * The backdrop fades because that is a colour change, not movement.
 */
export function AskCommand({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const input = useRef<HTMLInputElement>(null);
  const restoreFocusTo = useRef<Element | null>(null);

  useEffect(() => {
    if (!open) return;
    restoreFocusTo.current = document.activeElement;
    input.current?.focus();
    input.current?.select();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    // Keep the page behind from scrolling under the palette.
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
      (restoreFocusTo.current as HTMLElement | null)?.focus?.();
    };
  }, [open, onClose]);

  if (!open) return null;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.ask(question));
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  const empty = result && result.sources.length === 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-ink/25 px-4 pt-[12vh]
                 backdrop-blur-[2px] transition-opacity duration-[--press]"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={t("ask.title")}
        className="w-full max-w-2xl overflow-hidden rounded-2xl border border-line
                   bg-raised shadow-lifted"
      >
        <form onSubmit={submit} className="flex items-center gap-3 border-b border-line px-4">
          <span aria-hidden className="font-mono text-sm text-faint">
            ?
          </span>
          <input
            ref={input}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={t("ask.placeholder")}
            className="min-w-0 flex-1 bg-transparent py-4 text-[16px] outline-none placeholder:text-faint"
          />
          <kbd className="hidden shrink-0 rounded border border-line px-1.5 py-0.5 font-mono text-[11px] text-faint sm:block">
            esc
          </kbd>
        </form>

        <div className="max-h-[55vh] overflow-y-auto px-4 py-4">
          {busy && (
            <p className="flex items-center gap-2.5 text-[15px] text-muted" aria-live="polite">
              <span
                aria-hidden
                className="h-1.5 w-1.5 rounded-full bg-verdigris"
                style={{ animation: "breathe 1.4s ease-in-out infinite" }}
              />
              {t("ask.thinking")}
            </p>
          )}

          {!busy && !result && !error && (
            <p className="text-[15px] leading-relaxed text-muted">{t("ask.hint")}</p>
          )}

          {!busy && empty && (
            <p className="text-[15px] leading-relaxed text-muted">{t("ask.noResults")}</p>
          )}

          {!busy && result && !empty && (
            <div className="enter">
              <p className="text-[15px] leading-relaxed">{result.answer}</p>
              <div className="mt-6">
                <Eyebrow>{t("ask.drawnFrom")}</Eyebrow>
              </div>
              <ul className="stagger space-y-2">
                {result.sources.map((claim, index) => (
                  <li
                    key={claim.id}
                    style={{ "--i": index } as React.CSSProperties}
                    className="rounded-lg bg-sunken p-3"
                  >
                    <p className="font-display text-[14px] font-semibold">{claim.title}</p>
                    <p className="mt-0.5 text-[14px] leading-relaxed text-muted">
                      {claim.statement}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <Problem error={error} />
        </div>
      </div>
    </div>
  );
}
