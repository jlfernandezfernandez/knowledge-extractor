import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { ClaimDraft, Contribution } from "@/features/contributions/types";

export function ReviewFlow({
  contribution,
  drafts,
  busy,
  onEdit,
  onConfirm,
  onResolve,
  onCommit,
  onBack,
}: {
  contribution: Contribution;
  drafts: ClaimDraft[];
  busy: boolean;
  onEdit: (draftKey: string, field: "title" | "statement", value: string) => void;
  onConfirm: () => void;
  onResolve: () => void;
  onCommit: () => void;
  onBack: () => void;
}) {
  const { t } = useTranslation();
  if (contribution.stage === "claims") {
    return <section aria-labelledby="review-title" className="mt-4"><h1 id="review-title" className="text-2xl font-semibold">{t("review.stages.claims")}</h1><p className="mt-2 text-muted-foreground">{contribution.summary}</p><div className="mt-6 space-y-4">{drafts.map((claim) => <article key={claim.draft_key} className="space-y-2 rounded-lg border p-4"><Textarea aria-label={t("review.claimTitle")} value={claim.title} onChange={(event) => onEdit(claim.draft_key, "title", event.target.value)} /><Textarea aria-label={t("review.claimStatement")} value={claim.statement} onChange={(event) => onEdit(claim.draft_key, "statement", event.target.value)} /></article>)}</div><ReviewActions busy={busy} primary={t("review.confirm")} onPrimary={onConfirm} onBack={onBack} /></section>;
  }
  if (contribution.stage === "conflicts") {
    return <section aria-labelledby="review-title" className="mt-4"><h1 id="review-title" className="text-2xl font-semibold">{t("review.stages.conflicts")}</h1><p className="mt-2 text-muted-foreground">{contribution.summary}</p><ul className="mt-6 space-y-3">{contribution.conflicts.map((conflict) => <li key={`${conflict.claim_draft_key}-${conflict.existing_id}`} className="rounded-lg border p-4">{conflict.reason}</li>)}</ul><ReviewActions busy={busy} primary={t("review.resolve")} onPrimary={onResolve} onBack={onBack} /></section>;
  }
  if (contribution.stage === "commit") {
    return <section aria-labelledby="review-title" className="mt-4"><h1 id="review-title" className="text-2xl font-semibold">{t("review.stages.commit")}</h1><p className="mt-2 text-muted-foreground">{contribution.summary}</p><ReviewActions busy={busy} primary={t("review.commit")} onPrimary={onCommit} onBack={onBack} /></section>;
  }
  return <section aria-labelledby="review-title" className="mt-4"><h1 id="review-title" className="text-2xl font-semibold">{t("review.stages.committed")}</h1><p className="mt-2 text-muted-foreground">{contribution.summary}</p></section>;
}

function ReviewActions({ busy, primary, onPrimary, onBack }: { busy: boolean; primary: string; onPrimary: () => void; onBack: () => void }) {
  const { t } = useTranslation();
  return <div className="mt-6 flex gap-3"><Button onClick={onPrimary} disabled={busy}>{primary}</Button><Button variant="outline" onClick={onBack} disabled={busy}>{t("review.back")}</Button></div>;
}
