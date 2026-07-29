import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import type { SessionState } from "@/types/review";
import { Step } from "./step";

/** Step 4. Written, and nothing that lost was deleted. */
export function DoneStep({
  session,
  onRestart,
}: {
  session: SessionState;
  onRestart: () => void;
}) {
  const { t } = useTranslation();
  const none = session.committed.length === 0;

  return (
    <Step
      step={t("done.step")}
      title={none ? t("done.titleNone") : t("done.title", { count: session.committed.length })}
      lead={none ? undefined : t("done.lead")}
      actions={
        <Button size="lg" onClick={onRestart}>
          {t("done.restart")}
        </Button>
      }
    >
      <ul className="stagger mt-8 space-y-2.5">
        {session.committed.map((claim, index) => (
          <li
            key={claim.id}
            style={{ "--i": index } as React.CSSProperties}
            className="rounded-2xl border border-border bg-card p-5"
          >
            <h3 className="text-[15px] font-semibold tracking-[-0.01em]">{claim.title}</h3>
            <p className="mt-1.5 text-[15px] leading-relaxed">{claim.statement}</p>
            {claim.superseded.length > 0 && (
              <p className="mt-3 font-mono text-[11px] text-muted-foreground">
                {t("done.replaced", { count: claim.superseded.length })}
              </p>
            )}
          </li>
        ))}
      </ul>
    </Step>
  );
}
