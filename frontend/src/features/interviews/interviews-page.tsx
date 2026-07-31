import { useCallback, useEffect, useRef, useState, Fragment } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { ErrorNote } from "@/components/common/error-note";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Empty, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { Item, ItemActions, ItemContent, ItemDescription, ItemGroup, ItemSeparator, ItemTitle } from "@/components/ui/item";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { interviewsApi, type Interview, type InterviewView } from "./api";
import { InterviewDialog } from "./interview-dialog";

function InterviewRow({ interview, onStart }: { interview: Interview; onStart: (interview: Interview) => void }) {
  const { t } = useTranslation();
  return (
    <Item>
      <ItemContent>
        <ItemTitle>{interview.title}</ItemTitle>
        <ItemDescription>{new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(interview.created_at))}</ItemDescription>
      </ItemContent>
      <ItemActions>
        <Badge variant="secondary">{t(`interviews.status.${interview.status}`)}</Badge>
        {interview.status === "pending" && <Button size="sm" onClick={() => onStart(interview)}>{t("interviews.start")}</Button>}
      </ItemActions>
    </Item>
  );
}

function InterviewRowsSkeleton() {
  return (
    <div aria-hidden="true" className="flex flex-col gap-4">
      {[0, 1].map((row) => (
        <div key={row} className="flex flex-col gap-2 px-3 py-2.5">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-3 w-28" />
        </div>
      ))}
    </div>
  );
}

export function InterviewsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [view, setView] = useState<InterviewView>("pending");
  const [items, setItems] = useState<Interview[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const requestVersion = useRef(0);

  const load = useCallback((next: InterviewView) => {
    const version = ++requestVersion.current;
    setError(null);
    setLoading(true);
    void interviewsApi.list(next).then((nextItems) => {
      if (version === requestVersion.current) {
        setItems(nextItems);
        setLoading(false);
      }
    }).catch((failure) => {
      if (version === requestVersion.current) {
        setError(failure);
        setLoading(false);
      }
    });
  }, []);
  useEffect(() => { load(view); }, [load, view]);

  async function start(interview: Interview) {
    setError(null);
    try {
      const started = await interviewsApi.start(interview.id);
      navigate(`/review/${started.contribution_id}`, { state: { interview: started.interview } });
    } catch (failure) {
      setError(failure);
    }
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-10">
      <div className="flex items-center justify-between gap-4"><div><h1 className="text-2xl font-semibold">{t("interviews.title")}</h1><p className="mt-1 text-muted-foreground">{t("interviews.lead")}</p></div><InterviewDialog onCreated={() => load(view)} /></div>
      <Tabs value={view} onValueChange={(value) => { requestVersion.current += 1; setItems([]); setView(value as InterviewView); }} className="mt-8">
        <TabsList><TabsTrigger value="pending">{t("interviews.tabs.pending")}</TabsTrigger><TabsTrigger value="sent">{t("interviews.tabs.sent")}</TabsTrigger><TabsTrigger value="completed">{t("interviews.tabs.completed")}</TabsTrigger></TabsList>
        {(["pending", "sent", "completed"] as const).map((tab) => (
          <TabsContent key={tab} value={tab} className="mt-4" aria-busy={loading}>
            {loading ? (
              <div role="status">
                <span className="sr-only">{t("interviews.loading")}</span>
                <InterviewRowsSkeleton />
              </div>
            ) : items.length ? (
              <ItemGroup className="gap-0">
                {items.map((item, index) => (
                  <Fragment key={item.id}>
                    {index > 0 && <ItemSeparator />}
                    <InterviewRow interview={item} onStart={(next) => void start(next)} />
                  </Fragment>
                ))}
              </ItemGroup>
            ) : (
              <Empty className="border">
                <EmptyHeader><EmptyTitle>{t(`interviews.empty.${tab}`)}</EmptyTitle></EmptyHeader>
              </Empty>
            )}
          </TabsContent>
        ))}
      </Tabs>
      <ErrorNote error={error} />
    </div>
  );
}
