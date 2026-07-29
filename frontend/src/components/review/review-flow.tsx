import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { ErrorNote } from "@/components/common/error-note";
import type { Review } from "@/hooks/use-review";
import type { Resolution } from "@/types/review";
import { CaptureStep } from "./capture-step";
import { ConfirmStep } from "./confirm-step";
import { DoneStep } from "./done-step";
import { Progress } from "./progress";
import { ResolveStep } from "./resolve-step";

/**
 * Which step is on the stage.
 *
 * The steps know nothing about each other or about the graph; this picks one
 * and hands it what it needs. While a step is running, the stage shows the
 * graph's progress instead — the review has not moved yet, so neither has the
 * step it is leaving.
 */
export function ReviewFlow({
  review,
  author,
  knowledgeBase,
  onCommitted,
}: {
  review: Review;
  author: string;
  /** Slug of the knowledge base a new capture goes into. */
  knowledgeBase: string;
  /** Fired once claims are written, so the rail can refetch its counts. */
  onCommitted: () => void;
}) {
  const { t } = useTranslation();
  const { stage, session, busy, progress, error } = review;

  if (busy) {
    return (
      <div className="flex h-full items-center">
        <Progress events={progress} />
      </div>
    );
  }

  async function save(resolutions: Record<string, Resolution>) {
    const saved = await review.resolve(resolutions);
    if (saved && saved.committed.length > 0) {
      toast.success(t("done.toast", { count: saved.committed.length }));
      onCommitted();
    }
  }

  return (
    <>
      {!session ? (
        <CaptureStep
          value={review.draft}
          onChange={review.setDraft}
          onSubmit={() => review.start(review.draft, author, knowledgeBase)}
          busy={busy || !knowledgeBase}
        />
      ) : stage === "confirm" ? (
        <ConfirmStep session={session} busy={busy} onSubmit={review.confirm} />
      ) : stage === "resolve" ? (
        <ResolveStep session={session} busy={busy} onSubmit={save} />
      ) : (
        <DoneStep session={session} onRestart={review.reset} />
      )}
      <ErrorNote error={error} />
    </>
  );
}
