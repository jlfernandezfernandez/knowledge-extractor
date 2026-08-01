import { useCallback, useEffect, useReducer, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useParams } from "react-router";
import { ErrorNote } from "@/components/common/error-note";
import { ReviewFlow } from "@/components/review/review-flow";
import { Spinner } from "@/components/ui/spinner";
import { ApiError, API_URL } from "@/lib/api";
import { contributionsApi } from "@/features/contributions/api";
import { ContributionInput } from "@/features/contributions/contribution-input";
import type { ClaimDraft, Contribution } from "@/features/contributions/types";
import { interviewsApi, type Interview } from "@/features/interviews/api";

type DraftAction =
  | { type: "reset"; claims: ClaimDraft[] }
  | { type: "edit"; draftKey: string; field: "title" | "statement"; value: string };

function draftReducer(claims: ClaimDraft[], action: DraftAction): ClaimDraft[] {
  if (action.type === "reset") return action.claims;
  return claims.map((claim) => claim.draft_key === action.draftKey ? { ...claim, [action.field]: action.value } : claim);
}

function stageTitle(stage: Contribution["stage"], t: (key: string) => string) {
  return t(`review.stages.${stage}`);
}

export function ReviewPage() {
  const { t } = useTranslation();
  const { id = "" } = useParams();
  const location = useLocation();
  const routeInterview = (location.state as { interview?: Interview } | null)?.interview;
  const [interview, setInterview] = useState<Interview | null>(routeInterview ?? null);
  const [contribution, setContribution] = useState<Contribution | null>(null);
  const [drafts, dispatch] = useReducer(draftReducer, []);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const update = (next: Contribution) => {
    setContribution(next);
    dispatch({ type: "reset", claims: next.claims });
  };

  const refresh = useCallback(async () => update(await contributionsApi.get(id)), [id]);

  useEffect(() => {
    void refresh().catch(setError);
    if (typeof EventSource === "undefined") return;
    const stream = new EventSource(`${API_URL}/api/contributions/${id}/events`, { withCredentials: true });
    stream.addEventListener("review", (event) => {
      try { update(JSON.parse((event as MessageEvent).data) as Contribution); } catch { /* Ignore malformed transport events. */ }
    });
    return () => stream.close();
  }, [id, refresh]);

  useEffect(() => {
    setInterview(routeInterview ?? null);
  }, [id, location.key, routeInterview]);

  useEffect(() => {
    if (!contribution || contribution.source !== "interview" || contribution.raw_text || interview) return;
    void interviewsApi.byContribution(id).then((recovered) => {
      setInterview(recovered);
    }).catch(setError);
  }, [contribution, id, interview]);

  async function perform(action: () => Promise<Contribution>) {
    setBusy(true);
    setError(null);
    try {
      update(await action());
    } catch (failure) {
      if (failure instanceof ApiError && failure.code === "stale_revision") {
        try { await refresh(); } catch (refreshFailure) { setError(refreshFailure); }
      } else {
        setError(failure);
      }
    } finally {
      setBusy(false);
    }
  }

  async function submitAnswer(text: string) {
    if (!interview || !text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      update(await interviewsApi.answer(interview.id, text.trim()));
    } catch (failure) { setError(failure); } finally { setBusy(false); }
  }

  if (!contribution) return <div className="mx-auto max-w-3xl px-4 py-10"><p className="flex items-center gap-2 text-muted-foreground"><Spinner />{t("review.loading")}</p><ErrorNote error={error} /></div>;

  const interviewCapture = interview && contribution.source === "interview" && !contribution.raw_text;
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-10">
      <p className="text-sm font-medium text-muted-foreground">{t("review.progress", { stage: stageTitle(contribution.stage, t) })}</p>
      {interviewCapture ? (
        <div className="mt-4">
          <ContributionInput
            title={interview.title}
            subtitle={interview.brief}
            placeholder={t("review.answerPlaceholder")}
            textareaAriaLabel={t("review.answerLabel")}
            submitLabel={t("review.submitAnswer")}
            busy={busy}
            onSubmit={(text) => submitAnswer(text)}
          />
        </div>
      ) : <ReviewFlow
        contribution={contribution}
        drafts={drafts}
        busy={busy}
        onEdit={(draftKey, field, value) => dispatch({ type: "edit", draftKey, field, value })}
        onConfirm={() => void perform(() => contributionsApi.confirm(id, contribution.revision, drafts))}
        onResolve={(resolutions) => void perform(() => contributionsApi.resolve(id, contribution.revision, resolutions))}
        onCommit={() => void perform(() => contributionsApi.commit(id, contribution.revision))}
        onBack={() => void perform(() => contributionsApi.back(id, contribution.revision))}
      />}
      <ErrorNote error={error} />
    </div>
  );
}
