import { useState } from "react";
import { ArrowUpIcon, ChevronDownIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { ErrorNote } from "@/components/common/error-note";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { askApi, type AskResponse, type Citation } from "./api";

function CitationCard({ citation }: { citation: Citation }) {
  const { i18n } = useTranslation();
  const date = new Intl.DateTimeFormat(i18n.resolvedLanguage ?? i18n.language, { dateStyle: "medium" }).format(new Date(citation.contribution_created_at));

  return (
    <Collapsible>
      <Card size="sm">
        <CardHeader>
          <CollapsibleTrigger className="group flex w-full items-center justify-between gap-2 text-left font-medium">
            {citation.title}
            <ChevronDownIcon aria-hidden="true" className="size-4 shrink-0 transition-transform group-data-[state=open]:rotate-180" />
          </CollapsibleTrigger>
        </CardHeader>
        <CollapsibleContent>
          <CardContent className="flex flex-col gap-2">
            <p>{citation.statement}</p>
            <p className="text-sm text-muted-foreground"><span>{citation.author}</span><span aria-hidden="true"> · </span><time dateTime={citation.contribution_created_at}>{date}</time></p>
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
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
      <CardContent className="flex flex-col gap-5">
        {result.sufficient_evidence && <p className="whitespace-pre-wrap leading-7">{result.answer}</p>}
        {result.citations.length > 0 && (
          <section aria-labelledby="citations-title">
            <h2 id="citations-title" className="mb-3 text-sm font-medium">{t("ask.citations")}</h2>
            <div className="flex flex-col gap-2">{result.citations.map((citation) => <CitationCard key={citation.id} citation={citation} />)}</div>
          </section>
        )}
      </CardContent>
    </Card>
  );
}

export function AskPage() {
  const { t } = useTranslation();
  const [question, setQuestion] = useState("");
  const [submittedQuestion, setSubmittedQuestion] = useState<string | null>(null);
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
    setSubmittedQuestion(trimmedQuestion);
    setQuestion("");
    try {
      setResult(await askApi.ask(trimmedQuestion));
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mx-auto flex min-h-[calc(100dvh-3.5rem)] w-full max-w-3xl flex-col gap-6 px-5 py-8 md:px-8 md:py-10">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">{t("ask.title")}</h1>
      </header>
      <div className="flex flex-1 flex-col gap-4">
        {submittedQuestion && (
          <Card className="ml-auto w-full max-w-[85%]" size="sm">
            <CardContent><p className="whitespace-pre-wrap leading-6">{submittedQuestion}</p></CardContent>
          </Card>
        )}
        {busy && (
          <Card aria-live="polite">
            <CardHeader><CardTitle>{t("ask.thinking")}</CardTitle></CardHeader>
            <CardContent className="flex flex-col gap-3"><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-4/5" /></CardContent>
          </Card>
        )}
        {!busy && result && <Answer result={result} />}
        <ErrorNote error={error} />
      </div>
      <form className="flex items-end gap-2" onSubmit={(event) => void submit(event)}>
        <Textarea
          aria-label={t("ask.question")}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
          placeholder={t("ask.placeholder")}
          rows={1}
        />
        <Button aria-label={t("ask.submit")} disabled={busy || !question.trim()} size="icon" type="submit">
          <ArrowUpIcon data-icon="inline-start" />
        </Button>
      </form>
    </section>
  );
}
