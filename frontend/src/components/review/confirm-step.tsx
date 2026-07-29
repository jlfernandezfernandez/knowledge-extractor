import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { ClaimDraft, SessionState } from "@/types/review";
import { ClaimCard } from "./claim-card";
import { Step } from "./step";

interface ConfirmStepProps {
  session: SessionState;
  busy: boolean;
  onSubmit: (claims: ClaimDraft[], clarification: string | null) => void;
}

/**
 * Step 2, the first human gate: did the model understand correctly?
 *
 * Claims are grouped by the topic the model assigned. A flat list of eight
 * claims is something you skim; the same eight under three headings is
 * something you can check, because you see the shape of what it heard before
 * reading a word of it.
 */
export function ConfirmStep({ session, busy, onSubmit }: ConfirmStepProps) {
  const { t } = useTranslation();
  const [claims, setClaims] = useState<ClaimDraft[]>(session.claims);
  const [clarification, setClarification] = useState("");

  const groups = useMemo(() => {
    const byTopic = new Map<string, ClaimDraft[]>();
    for (const claim of claims) {
      // Models reach for snake_case when asked for a one-word topic. It is a
      // heading a person reads, so it is shown as words.
      const topic = claim.topic?.trim().replace(/_/g, " ") || t("confirm.untopiced");
      byTopic.set(topic, [...(byTopic.get(topic) ?? []), claim]);
    }
    return [...byTopic.entries()];
  }, [claims, t]);

  const edit = (id: string, patch: Partial<ClaimDraft>) =>
    setClaims((all) => all.map((claim) => (claim.id === id ? { ...claim, ...patch } : claim)));

  return (
    <Step
      step={t("confirm.step")}
      title={t("confirm.title")}
      lead={session.summary || undefined}
      actions={
        <Button size="lg" onClick={() => onSubmit(claims, null)} disabled={busy || !claims.length}>
          {t("confirm.submit")}
        </Button>
      }
    >
      <div className="mt-8 space-y-7">
        {groups.map(([topic, group], groupIndex) => (
          <section key={topic}>
            <div className="mb-2.5 flex items-baseline gap-2.5">
              <h2 className="text-[13px] font-semibold">{topic}</h2>
              <span className="font-mono text-[11px] text-muted-foreground">
                {t("confirm.count", { count: group.length })}
              </span>
              <span aria-hidden className="h-px flex-1 bg-border" />
            </div>
            <ul className="stagger space-y-2">
              {group.map((claim, index) => (
                <ClaimCard
                  key={claim.id}
                  claim={claim}
                  topic={topic}
                  index={groupIndex * 2 + index}
                  onEdit={(patch) => edit(claim.id, patch)}
                  onRemove={() => setClaims((all) => all.filter((c) => c.id !== claim.id))}
                />
              ))}
            </ul>
          </section>
        ))}
      </div>

      {claims.length === 0 && (
        <p className="mt-8 rounded-2xl border border-dashed border-border p-8 text-[15px] text-muted-foreground">
          {t("confirm.empty")}
        </p>
      )}

      {/* Answering an open question sends the review back through extraction
          with the extra context, rather than moving it forward. */}
      {session.open_questions.length > 0 && (
        <div className="enter mt-8 rounded-2xl bg-muted p-5">
          <p className="mb-3 text-xs font-medium text-muted-foreground">
            {t("confirm.unclear", { count: session.open_questions.length })}
          </p>
          <ul className="space-y-2 text-[15px]">
            {session.open_questions.map((question) => (
              <li key={question}>{question}</li>
            ))}
          </ul>
          <Textarea
            value={clarification}
            onChange={(event) => setClarification(event.target.value)}
            rows={1}
            placeholder={t("confirm.clarifyPlaceholder")}
            className="autosize mt-4 min-h-0 resize-none rounded-xl bg-background p-3.5 text-[15px]"
          />
          <Button
            variant="outline"
            className="mt-3"
            onClick={() => onSubmit(claims, clarification)}
            disabled={!clarification.trim() || busy}
          >
            {t("confirm.reread")}
          </Button>
        </div>
      )}
    </Step>
  );
}
