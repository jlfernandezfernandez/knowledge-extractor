import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { ErrorNote } from "@/components/common/error-note";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { historyApi, type HistoryItem } from "./api";

function HistoryCard({ item }: { item: HistoryItem }) {
  const { t, i18n } = useTranslation();
  const date = new Intl.DateTimeFormat(i18n.resolvedLanguage ?? i18n.language, { dateStyle: "medium" }).format(new Date(item.created_at));

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{item.summary}</CardTitle>
          <Badge variant="secondary">{t(`history.sources.${item.source}`, { defaultValue: item.source })}</Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-1 text-sm text-muted-foreground">
        <p><span>{item.author}</span><span aria-hidden="true"> · </span><time dateTime={item.created_at}>{date}</time></p>
        <p>{t("history.claimCount", { count: item.claim_count })}</p>
      </CardContent>
      <CardFooter><Link className="text-sm font-medium text-primary underline-offset-4 hover:underline" to={`/review/${item.contribution_id}`}>{t("history.review")}</Link></CardFooter>
    </Card>
  );
}

function HistorySkeleton() {
  return <Card><CardHeader><Skeleton className="h-5 w-2/3" /></CardHeader><CardContent className="flex flex-col gap-2"><Skeleton className="h-4 w-1/3" /><Skeleton className="h-4 w-1/4" /></CardContent></Card>;
}

export function HistoryPage() {
  const { t } = useTranslation();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const hasInitialError = Boolean(error) && items.length === 0;

  async function load(cursorToLoad: string | null = null) {
    setLoading(true);
    setError(null);
    try {
      const page = await historyApi.list(cursorToLoad);
      setItems((current) => cursorToLoad ? [...current, ...page.items] : page.items);
      setCursor(page.next_cursor);
    } catch (failure) {
      setError(failure);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  return (
    <section className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-5 py-8 md:px-8 md:py-10">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">{t("history.title")}</h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">{t("history.lead")}</p>
      </header>
      <div className="flex flex-col gap-3">
        {loading && items.length === 0 && <><HistorySkeleton /><HistorySkeleton /></>}
        {!loading && !error && items.length === 0 && (
          <Empty className="border">
            <EmptyHeader><EmptyTitle>{t("history.empty")}</EmptyTitle></EmptyHeader>
          </Empty>
        )}
        {items.map((item) => <HistoryCard key={item.contribution_id} item={item} />)}
      </div>
      {(cursor || hasInitialError) && (
        <Button variant="outline" className="self-start" disabled={loading} onClick={() => void load(cursor)}>
          {loading ? t("history.loadingMore") : hasInitialError ? t("history.retry") : t("history.loadMore")}
        </Button>
      )}
      <ErrorNote error={error} />
    </section>
  );
}
