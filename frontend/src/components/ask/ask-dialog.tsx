import { useState } from "react";
import { useTranslation } from "react-i18next";
import { SearchIcon } from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Kbd } from "@/components/ui/kbd";
import { ErrorNote } from "@/components/common/error-note";
import { knowledge } from "@/lib/api/knowledge";
import type { AskResponse } from "@/types/knowledge";
import { SourceList } from "./source-list";

/**
 * The question surface, as a command palette.
 *
 * Anchored near the top rather than centred: the answer below it grows and
 * shrinks with every question, and a centred panel would slide the input up
 * and down under the cursor while you read.
 */
export function AskDialog({
  open,
  onClose,
  knowledgeBase,
  knowledgeBaseName,
}: {
  open: boolean;
  onClose: () => void;
  knowledgeBase: string;
  /** Named on screen, because the same question has different answers in
   *  different knowledge bases and the palette hides the rail. */
  knowledgeBaseName: string;
}) {
  const { t } = useTranslation();
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await knowledge.ask(question, knowledgeBase));
    } catch (failed) {
      setError(failed);
    } finally {
      setBusy(false);
    }
  }

  const nothingFound = result && result.sources.length === 0;

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent
        showCloseButton={false}
        className="top-[12vh] translate-y-0 gap-0 p-0 shadow-float sm:max-w-2xl"
      >
        <DialogTitle className="sr-only">{t("ask.title")}</DialogTitle>

        <form onSubmit={submit} className="flex items-center gap-3 border-b border-border px-4">
          <SearchIcon aria-hidden className="size-4 shrink-0 text-muted-foreground" />
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={t("ask.placeholder")}
            aria-label={t("ask.title")}
            className="min-w-0 flex-1 bg-transparent py-4 text-[16px] outline-none placeholder:text-muted-foreground"
          />
          {knowledgeBaseName && (
            <span className="shrink-0 truncate text-[12px] text-muted-foreground max-sm:hidden">
              {knowledgeBaseName}
            </span>
          )}
          <Kbd className="shrink-0 max-sm:hidden">esc</Kbd>
        </form>

        <div className="max-h-[55vh] overflow-y-auto p-4">
          {busy && (
            <p className="flex items-center gap-2.5 text-[15px] text-muted-foreground" aria-live="polite">
              <span aria-hidden className="breathe size-1.5 rounded-full bg-foreground" />
              {t("ask.thinking")}
            </p>
          )}

          {!busy && !result && !error && (
            <p className="text-[15px] leading-relaxed text-muted-foreground">{t("ask.hint")}</p>
          )}

          {!busy && nothingFound && (
            <p className="text-[15px] leading-relaxed text-muted-foreground">{t("ask.noResults")}</p>
          )}

          {!busy && result && !nothingFound && (
            <div className="enter">
              <p className="text-[15px] leading-relaxed">{result.answer}</p>
              <SourceList sources={result.sources} />
            </div>
          )}

          <ErrorNote error={error} />
        </div>
      </DialogContent>
    </Dialog>
  );
}
