import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";
import { ErrorNote } from "@/components/common/error-note";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { contributionsApi } from "@/features/contributions/api";
import { interviewsApi, type Interview } from "@/features/interviews/api";

function PendingInterview({ interview, onStart }: { interview: Interview; onStart: (interview: Interview) => void }) {
  const { t } = useTranslation();
  return (
    <li className="flex items-center gap-3 border-b py-3 last:border-0">
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium">{interview.title}</p>
        <p className="text-sm text-muted-foreground">{new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(interview.created_at))}</p>
      </div>
      <Badge variant="secondary">{t("interviews.status.pending")}</Badge>
      <Button size="sm" onClick={() => onStart(interview)}>{t("interviews.start")}</Button>
    </li>
  );
}

export function HomePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [pending, setPending] = useState<Interview[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    void interviewsApi.list("pending").then(setPending).catch(setError);
  }, []);

  async function createContribution() {
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const contribution = await contributionsApi.create(text.trim());
      navigate(`/review/${contribution.id}`);
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  async function startInterview(interview: Interview) {
    setBusy(true);
    setError(null);
    try {
      const started = await interviewsApi.start(interview.id);
      navigate(`/review/${started.contribution_id}`, { state: { interview: started.interview } });
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[calc(100dvh-3.5rem)] w-full max-w-3xl flex-col justify-center px-4 py-10">
      <section aria-labelledby="contribution-heading">
        <h1 id="contribution-heading" className="text-center text-2xl font-semibold">{t("home.title")}</h1>
        <p className="mt-2 text-center text-muted-foreground">{t("home.lead")}</p>
        <Textarea
          aria-label={t("home.composerLabel")}
          value={text}
          onChange={(event) => setText(event.target.value)}
          className="mt-6 min-h-36 resize-y"
          placeholder={t("home.placeholder")}
        />
        <div className="mt-3 flex justify-end">
          <Button onClick={() => void createContribution()} disabled={busy || !text.trim()}>{t("home.submit")}</Button>
        </div>
      </section>

      <section className="mt-12" aria-labelledby="pending-heading">
        <div className="flex items-center justify-between gap-4">
          <h2 id="pending-heading" className="font-medium">{t("home.pendingTitle")}</h2>
          <Link to="/interviews" className="text-sm font-medium text-primary underline-offset-4 hover:underline">{t("home.allInterviews")}</Link>
        </div>
        {pending.length ? <ul className="mt-2">{pending.slice(0, 3).map((item) => <PendingInterview key={item.id} interview={item} onStart={(item) => void startInterview(item)} />)}</ul> : <p className="mt-3 text-sm text-muted-foreground">{t("interviews.empty.pending")}</p>}
      </section>
      <ErrorNote error={error} />
    </div>
  );
}
