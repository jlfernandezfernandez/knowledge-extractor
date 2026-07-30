import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { ErrorNote } from "@/components/common/error-note";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { interviewsApi, type Interview, type InterviewView } from "./api";
import { rememberInterviewContext } from "./context";
import { InterviewDialog } from "./interview-dialog";

function InterviewRow({ interview, onStart }: { interview: Interview; onStart: (interview: Interview) => void }) {
  const { t } = useTranslation();
  return (
    <li className="flex items-center gap-3 border-b py-4 last:border-0">
      <div className="min-w-0 flex-1"><p className="font-medium">{interview.title}</p><p className="mt-1 text-sm text-muted-foreground">{new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(interview.created_at))}</p></div>
      <Badge variant="secondary">{t(`interviews.status.${interview.status}`)}</Badge>
      {interview.status === "pending" && <Button size="sm" onClick={() => onStart(interview)}>{t("interviews.start")}</Button>}
    </li>
  );
}

export function InterviewsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [view, setView] = useState<InterviewView>("pending");
  const [items, setItems] = useState<Interview[]>([]);
  const [error, setError] = useState<unknown>(null);
  const requestVersion = useRef(0);

  const load = useCallback((next: InterviewView) => {
    const version = ++requestVersion.current;
    setError(null);
    void interviewsApi.list(next).then((nextItems) => {
      if (version === requestVersion.current) setItems(nextItems);
    }).catch((failure) => {
      if (version === requestVersion.current) setError(failure);
    });
  }, []);
  useEffect(() => { load(view); }, [load, view]);

  async function start(interview: Interview) {
    setError(null);
    try {
      const started = await interviewsApi.start(interview.id);
      rememberInterviewContext(started.contribution_id, started.interview);
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
        {(["pending", "sent", "completed"] as const).map((tab) => <TabsContent key={tab} value={tab}><ul className="mt-4">{items.length ? items.map((item) => <InterviewRow key={item.id} interview={item} onStart={(item) => void start(item)} />) : <li className="py-6 text-sm text-muted-foreground">{t(`interviews.empty.${tab}`)}</li>}</ul></TabsContent>)}
      </Tabs>
      <ErrorNote error={error} />
    </div>
  );
}
