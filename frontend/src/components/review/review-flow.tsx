import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { ClaimDraft, ConflictResolution, Contribution } from "@/features/contributions/types";

type ResolutionDraft = { action: ConflictResolution["action"]; replacement_statement?: string };

type ReviewFlowProps = {
  contribution: Contribution;
  drafts: ClaimDraft[];
  busy: boolean;
  onEdit: (draftKey: string, field: "title" | "statement", value: string) => void;
  onConfirm: () => void;
  onResolve: (resolutions: ConflictResolution[]) => void;
  onCommit: () => void;
  onBack: () => void;
};

function ReviewHeading({ title, summary }: { title: string; summary: string }) {
  return (
    <header className="flex flex-col gap-2">
      <h1 id="review-title" className="text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="text-muted-foreground">{summary}</p>
    </header>
  );
}

function ReviewActions({ busy, primary, onPrimary, onBack }: { busy: boolean; primary: string; onPrimary: () => void; onBack: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-wrap gap-3">
      <Button onClick={onPrimary} disabled={busy}>{primary}</Button>
      <Button variant="outline" onClick={onBack} disabled={busy}>{t("review.back")}</Button>
    </div>
  );
}

export function ReviewFlow({
  contribution,
  drafts,
  busy,
  onEdit,
  onConfirm,
  onResolve,
  onCommit,
  onBack,
}: ReviewFlowProps) {
  const { t } = useTranslation();
  const [resolutions, setResolutions] = useState<Record<string, ResolutionDraft>>({});

  useEffect(() => {
    if (contribution.stage === "conflicts") setResolutions({});
  }, [contribution.stage, contribution.revision]);

  if (contribution.stage === "claims") {
    return (
      <section aria-labelledby="review-title" className="mt-4 flex flex-col gap-6">
        <ReviewHeading title={t("review.stages.claims")} summary={contribution.summary} />
        <div className="flex flex-col gap-4">
          {drafts.map((claim) => (
            <Card key={claim.draft_key} size="sm">
              <CardContent className="flex flex-col gap-3">
                <div className="flex flex-col gap-2">
                  <Label htmlFor={`${claim.draft_key}-title`}>{t("review.claimTitle")}</Label>
                  <Textarea id={`${claim.draft_key}-title`} aria-label={t("review.claimTitle")} value={claim.title} onChange={(event) => onEdit(claim.draft_key, "title", event.target.value)} />
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor={`${claim.draft_key}-statement`}>{t("review.claimStatement")}</Label>
                  <Textarea id={`${claim.draft_key}-statement`} aria-label={t("review.claimStatement")} value={claim.statement} onChange={(event) => onEdit(claim.draft_key, "statement", event.target.value)} />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
        <ReviewActions busy={busy} primary={t("review.confirm")} onPrimary={onConfirm} onBack={onBack} />
      </section>
    );
  }

  if (contribution.stage === "conflicts") {
    const resolutionFor = (draftKey: string) => resolutions[draftKey] ?? { action: "keep_new" as const };
    const selected = [...new Map(contribution.conflicts.map((conflict) => [conflict.claim_draft_key, resolutionFor(conflict.claim_draft_key)])).entries()];
    const invalidMerge = selected.some(([, resolution]) => resolution.action === "merge" && !resolution.replacement_statement?.trim());

    return (
      <section aria-labelledby="review-title" className="mt-4 flex flex-col gap-6">
        <ReviewHeading title={t("review.stages.conflicts")} summary={contribution.summary} />
        <ul className="flex flex-col gap-3">
          {contribution.conflicts.map((conflict) => {
            const resolution = resolutionFor(conflict.claim_draft_key);
            return (
              <li key={`${conflict.claim_draft_key}-${conflict.existing_id}`}>
                <Card size="sm">
                  <CardHeader>
                    <CardTitle>{t(`conflicts.${resolution.action}`)}</CardTitle>
                    <CardDescription>{conflict.reason}</CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-3">
                    <div className="flex flex-wrap gap-2">
                      {(["keep_new", "keep_old", "keep_both", "merge"] as const).map((action) => (
                        <Button key={action} size="sm" variant={resolution.action === action ? "default" : "outline"} onClick={() => setResolutions((current) => ({ ...current, [conflict.claim_draft_key]: { ...resolution, action } }))}>{t(`conflicts.${action}`)}</Button>
                      ))}
                    </div>
                    {resolution.action === "merge" && (
                      <div className="flex flex-col gap-2">
                        <Label htmlFor={`${conflict.claim_draft_key}-merge`}>{t("review.mergedStatement")}</Label>
                        <Textarea id={`${conflict.claim_draft_key}-merge`} aria-label={t("review.mergedStatement")} value={resolution.replacement_statement ?? ""} onChange={(event) => setResolutions((current) => ({ ...current, [conflict.claim_draft_key]: { ...resolution, replacement_statement: event.target.value } }))} />
                      </div>
                    )}
                  </CardContent>
                </Card>
              </li>
            );
          })}
        </ul>
        <ReviewActions busy={busy || invalidMerge} primary={t("review.resolve")} onPrimary={() => onResolve(selected.map(([claim_draft_key, resolution]) => ({ claim_draft_key, action: resolution.action, ...(resolution.action === "merge" ? { replacement_statement: resolution.replacement_statement?.trim() } : {}) })))} onBack={onBack} />
      </section>
    );
  }

  if (contribution.stage === "commit") {
    return (
      <section aria-labelledby="review-title" className="mt-4 flex flex-col gap-6">
        <ReviewHeading title={t("review.stages.commit")} summary={contribution.summary} />
        <ReviewActions busy={busy} primary={t("review.commit")} onPrimary={onCommit} onBack={onBack} />
      </section>
    );
  }

  return (
    <section aria-labelledby="review-title" className="mt-4">
      <ReviewHeading title={t("review.stages.committed")} summary={contribution.summary} />
    </section>
  );
}
