import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { ClaimDraft, ConflictResolution, Contribution } from "@/features/contributions/types";

type ResolutionDraft = { action: ConflictResolution["action"]; replacement_statement?: string };

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
  onResolve: (resolutions: ConflictResolution[]) => void;
  onCommit: () => void;
  onBack: () => void;
}) {
  const { t } = useTranslation();
  const [resolutions, setResolutions] = useState<Record<string, ResolutionDraft>>({});
  useEffect(() => {
    if (contribution.stage === "conflicts") setResolutions({});
  }, [contribution.stage, contribution.revision]);

  if (contribution.stage === "claims") {
    return <section aria-labelledby="review-title" className="mt-4"><h1 id="review-title" className="text-2xl font-semibold">{t("review.stages.claims")}</h1><p className="mt-2 text-muted-foreground">{contribution.summary}</p><div className="mt-6 space-y-4">{drafts.map((claim) => <article key={claim.draft_key} className="space-y-2 rounded-lg border p-4"><Textarea aria-label={t("review.claimTitle")} value={claim.title} onChange={(event) => onEdit(claim.draft_key, "title", event.target.value)} /><Textarea aria-label={t("review.claimStatement")} value={claim.statement} onChange={(event) => onEdit(claim.draft_key, "statement", event.target.value)} /></article>)}</div><ReviewActions busy={busy} primary={t("review.confirm")} onPrimary={onConfirm} onBack={onBack} /></section>;
  }
  if (contribution.stage === "conflicts") {
    const resolutionFor = (draftKey: string) => resolutions[draftKey] ?? { action: "keep_new" as const };
    const selected = [...new Map(contribution.conflicts.map((conflict) => [conflict.claim_draft_key, resolutionFor(conflict.claim_draft_key)])).entries()];
    const invalidMerge = selected.some(([, resolution]) => resolution.action === "merge" && !resolution.replacement_statement?.trim());
    return <section aria-labelledby="review-title" className="mt-4"><h1 id="review-title" className="text-2xl font-semibold">{t("review.stages.conflicts")}</h1><p className="mt-2 text-muted-foreground">{contribution.summary}</p><ul className="mt-6 space-y-3">{contribution.conflicts.map((conflict) => {
      const resolution = resolutionFor(conflict.claim_draft_key);
      return <li key={`${conflict.claim_draft_key}-${conflict.existing_id}`} className="rounded-lg border p-4"><p>{conflict.reason}</p><div className="mt-3 flex flex-wrap gap-2">{(["keep_new", "keep_old", "keep_both", "merge"] as const).map((action) => <Button key={action} size="sm" variant={resolution.action === action ? "default" : "outline"} onClick={() => setResolutions((current) => ({ ...current, [conflict.claim_draft_key]: { ...resolution, action } }))}>{t(`conflicts.${action}`)}</Button>)}</div>{resolution.action === "merge" && <Textarea aria-label={t("review.mergedStatement")} className="mt-3" value={resolution.replacement_statement ?? ""} onChange={(event) => setResolutions((current) => ({ ...current, [conflict.claim_draft_key]: { ...resolution, replacement_statement: event.target.value } }))} />}</li>;
    })}</ul><ReviewActions busy={busy || invalidMerge} primary={t("review.resolve")} onPrimary={() => onResolve(selected.map(([claim_draft_key, resolution]) => ({ claim_draft_key, action: resolution.action, ...(resolution.action === "merge" ? { replacement_statement: resolution.replacement_statement?.trim() } : {}) })))} onBack={onBack} /></section>;
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
