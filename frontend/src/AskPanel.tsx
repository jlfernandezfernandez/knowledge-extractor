import { useState } from "react";
import { api } from "./api";
import type { AskResponse } from "./types";
import { Button, Eyebrow, Problem } from "./ui";

/** The other half of the product: everything captured is only worth the
 *  answers you can get back out of it. Retrieval is hybrid on the backend, so
 *  exact tokens and paraphrases both land. */
export function AskPanel({ onClose }: { onClose: () => void }) {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.ask(question));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside
      className="settle fixed inset-y-0 right-0 z-20 flex w-full max-w-lg flex-col
                 border-l border-line bg-surface shadow-2xl"
      aria-label="Ask the knowledge base"
    >
      <header className="flex items-center justify-between border-b border-line px-6 py-4">
        <h2 className="font-display text-lg font-semibold">Ask what we know</h2>
        <Button onClick={onClose}>Close</Button>
      </header>

      <form onSubmit={submit} className="border-b border-line px-6 py-4">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="When do we deploy to production?"
          autoFocus
          className="w-full rounded-lg border border-line bg-paper px-3 py-2.5 text-[15px] outline-none focus:border-verdigris"
        />
        <Button variant="primary" className="mt-3" disabled={busy || !question.trim()}>
          {busy ? "Looking…" : "Ask"}
        </Button>
        <Problem error={error} />
      </form>

      <div className="flex-1 overflow-y-auto px-6 py-5">
        {!result && !busy && (
          <p className="text-sm text-muted">
            Answers come only from claims a person approved, and each one names the
            claims it used.
          </p>
        )}
        {result && (
          <>
            <p className="text-[15px] leading-relaxed">{result.answer}</p>
            {result.sources.length > 0 && (
              <>
                <div className="mt-6">
                  <Eyebrow>Drawn from</Eyebrow>
                </div>
                <ul className="space-y-3">
                  {result.sources.map((claim) => (
                    <li key={claim.id} className="rounded-lg bg-sunken p-3">
                      <p className="font-display text-sm font-semibold">{claim.title}</p>
                      <p className="mt-0.5 text-sm leading-relaxed text-muted">
                        {claim.statement}
                      </p>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </>
        )}
      </div>
    </aside>
  );
}
