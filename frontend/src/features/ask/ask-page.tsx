import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ErrorNote } from "@/components/common/error-note";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { askApi, type AskResponse, type Citation } from "./api";

function CitationCard({ citation }: { citation: Citation }) {
  const { i18n } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const date = new Intl.DateTimeFormat(i18n.resolvedLanguage ?? i18n.language, { dateStyle: "medium" }).format(new Date(citation.contribution_created_at));

  return (
    <Card size="sm">
      <CardHeader>
        <Button
          variant="ghost"
          className="h-auto w-full justify-between px-0 py-0 text-left font-medium hover:bg-transparent"
          aria-expanded={expanded}
          onClick={() => setExpanded((value) => !value)}
        >
          {citation.title}
        </Button>
      </CardHeader>
      {expanded && (
        <CardContent className="space-y-2">
          <p>{citation.statement}</p>
          <p className="text-sm text-muted-foreground"><span>{citation.author}</span><span aria-hidden="true"> · </span><time dateTime={citation.contribution_created_at}>{date}</time></p>
        </CardContent>
      )}
    </Card>
  );
}

function Answer({ result }: { result: AskResponse }) {
  const { t } = useTranslation();

  return (
    <Card aria-live="polite">
      <CardHeader>
        <CardTitle>{t("ask.answer")}</CardTitle>
        {!result.sufficient_evidence && <CardDescription>{t("ask.insufficientEvidence")}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-5">
        <p className="whitespace-pre-wrap leading-7">{result.answer}</p>
        {result.citations.length > 0 && (
          <section aria-labelledby="citations-title">
            <h2 id="citations-title" className="mb-3 text-sm font-medium">{t("ask.citations")}</h2>
            <div className="space-y-2">{result.citations.map((citation) => <CitationCard key={citation.id} citation={citation} />)}</div>
          </section>
        )}
      </CardContent>
    </Card>
  );
}

export function AskPage() {
  const { t } = useTranslation();
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || busy) return;

    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await askApi.ask(trimmedQuestion));
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-5 py-8 md:px-8 md:py-10">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">{t("ask.title")}</h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">{t("ask.lead")}</p>
      </header>
      <Card>
        <CardContent>
          <form className="flex gap-3" onSubmit={(event) => void submit(event)}>
            <Input aria-label={t("ask.question")} value={question} onChange={(event) => setQuestion(event.target.value)} placeholder={t("ask.placeholder")} />
            <Button type="submit" disabled={busy || !question.trim()}>{busy ? t("ask.thinking") : t("ask.submit")}</Button>
          </form>
        </CardContent>
      </Card>
      {busy && (
        <Card aria-live="polite">
          <CardHeader><CardTitle>{t("ask.thinking")}</CardTitle></CardHeader>
          <CardContent className="space-y-3"><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-4/5" /></CardContent>
        </Card>
      )}
      {!busy && result && <ScrollArea className="max-h-[calc(100dvh-18rem)]"><Answer result={result} /></ScrollArea>}
      <ErrorNote error={error} />
    </section>
  );
}
