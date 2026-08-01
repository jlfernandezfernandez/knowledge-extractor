import { Fragment, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";
import { ErrorNote } from "@/components/common/error-note";
import { Empty, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { ItemGroup, ItemSeparator } from "@/components/ui/item";
import { contributionsApi } from "@/features/contributions/api";
import { ContributionInput } from "@/features/contributions/contribution-input";
import { interviewsApi, type Interview } from "@/features/interviews/api";
import { InterviewItem } from "@/features/interviews/interview-item";

export function HomePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [pending, setPending] = useState<Interview[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    void interviewsApi.list("pending").then(setPending).catch(setError);
  }, []);

  async function createContribution(text: string) {
    setBusy(true);
    setError(null);
    try {
      const contribution = await contributionsApi.create(text);
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
    <div className="mx-auto flex min-h-dvh w-full max-w-3xl flex-col justify-center px-4 py-10">
      <ContributionInput
        title={t("home.title")}
        subtitle={t("home.lead")}
        placeholder={t("home.placeholder")}
        submitLabel={t("home.submit")}
        busy={busy}
        onSubmit={createContribution}
      />

      <section className="mt-12" aria-labelledby="pending-heading">
        <div className="flex items-center justify-between gap-4">
          <h2 id="pending-heading" className="font-medium">{t("home.pendingTitle")}</h2>
          <Link to="/interviews" className="text-sm font-medium text-primary underline-offset-4 hover:underline">{t("home.allInterviews")}</Link>
        </div>
        {pending.length ? (
          <ItemGroup className="mt-2 gap-0">
            {pending.slice(0, 3).map((item, index) => (
              <Fragment key={item.id}>
                {index > 0 && <ItemSeparator />}
                <InterviewItem interview={item} onOpen={(next) => void startInterview(next)} />
              </Fragment>
            ))}
          </ItemGroup>
        ) : (
          <Empty className="mt-3 border">
            <EmptyHeader><EmptyTitle>{t("interviews.empty.pending")}</EmptyTitle></EmptyHeader>
          </Empty>
        )}
      </section>
      <ErrorNote error={error} />
    </div>
  );
}
