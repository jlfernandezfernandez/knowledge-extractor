import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import type { Resolution, SessionState } from "@/types/review";
import { ConflictCard } from "./conflict-card";
import { Step } from "./step";

interface ResolveStepProps {
  session: SessionState;
  busy: boolean;
  onSubmit: (resolutions: Record<string, Resolution>) => void;
}

/** Step 3, the second human gate: which claim wins? */
export function ResolveStep({ session, busy, onSubmit }: ResolveStepProps) {
  const { t } = useTranslation();
  const none = session.conflicts.length === 0;

  /* Every overlap starts on the recommendation its verdict carries, so the
     common case is read-and-continue rather than click-every-card. The human
     gate is still the Save button. */
  const [resolutions, setResolutions] = useState<Record<string, Resolution>>(() =>
    Object.fromEntries(
      session.conflicts.map((conflict) => [
        conflict.key,
        { action: conflict.recommended, statement: null },
      ]),
    ),
  );

  const changed = session.conflicts.filter(
    (conflict) => resolutions[conflict.key]?.action !== conflict.recommended,
  ).length;

  return (
    <Step
      step={t("conflicts.step")}
      title={
        none ? t("conflicts.titleNone") : t("conflicts.title", { count: session.conflicts.length })
      }
      lead={none ? t("conflicts.leadNone") : t("conflicts.lead")}
      actions={
        <>
          <Button size="lg" onClick={() => onSubmit(resolutions)} disabled={busy}>
            {t("conflicts.submit")}
          </Button>
          {changed > 0 && (
            <span className="text-sm text-muted-foreground">
              {t("conflicts.changed", { count: changed })}
            </span>
          )}
        </>
      }
    >
      <ul className="stagger mt-8 space-y-3">
        {session.conflicts.map((conflict, index) => (
          <ConflictCard
            key={conflict.key}
            index={index}
            conflict={conflict}
            incoming={session.claims.find((c) => c.id === conflict.draft_id)?.statement ?? ""}
            resolution={resolutions[conflict.key] ?? { action: conflict.recommended }}
            onChange={(resolution) =>
              setResolutions((previous) => ({ ...previous, [conflict.key]: resolution }))
            }
          />
        ))}
      </ul>
    </Step>
  );
}
