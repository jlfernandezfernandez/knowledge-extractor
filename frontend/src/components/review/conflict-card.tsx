import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Conflict, Resolution } from "@/types/review";
import { cn } from "@/lib/utils";

interface ConflictCardProps {
  conflict: Conflict;
  /** The incoming claim's statement, which is the right-hand side. */
  incoming: string;
  resolution: Resolution;
  onChange: (resolution: Resolution) => void;
  index: number;
}

/**
 * The one place in this product where a person has to decide something — and
 * the one place colour is allowed, on the badge, when the two claims genuinely
 * cannot both be true.
 *
 * Stored and yours sit side by side across a hairline seam. Choosing does not
 * move anything: the side that loses simply recedes, so the decision is
 * visible as a state of the pair rather than as a control you have to read
 * back. That is the whole review in one card.
 */
export function ConflictCard({
  conflict,
  incoming,
  resolution,
  onChange,
  index,
}: ConflictCardProps) {
  const { t } = useTranslation();
  const chosen = resolution.action;
  const merging = chosen === "merge";
  const storedLoses = chosen === "keep_new" || merging;
  const yoursLoses = chosen === "keep_old";

  return (
    <li
      style={{ "--i": index } as React.CSSProperties}
      className="overflow-hidden rounded-2xl border border-border bg-card"
    >
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-5 pt-4 pb-3">
        <Badge variant={conflict.verdict === "conflict" ? "destructive" : "secondary"}>
          {t(`conflicts.verdict.${conflict.verdict}`, conflict.verdict)}
        </Badge>
        <h3 className="text-[15px] font-semibold tracking-[-0.01em]">{conflict.stored.title}</h3>
        <p className="text-[13px] text-muted-foreground">{conflict.reason}</p>
      </header>

      <div className="grid grid-cols-1 border-t border-border sm:grid-cols-2">
        <Side
          label={t("conflicts.stored")}
          text={conflict.stored.statement}
          receded={storedLoses}
          className="border-b border-border sm:border-r sm:border-b-0"
        />
        <Side label={t("conflicts.yours")} text={incoming} receded={yoursLoses} />
      </div>

      {/* Only the resolutions that make sense for this verdict. Keeping both
          sides of a contradiction is never offered: retrieval would surface
          two incompatible claims and leave the model to pick one. */}
      <div className="flex flex-wrap gap-2 p-4">
        {conflict.allowed.map((action) => (
          <Button
            key={action}
            variant={chosen === action ? "default" : "outline"}
            size="sm"
            aria-pressed={chosen === action}
            onClick={() =>
              onChange({
                action,
                statement: action === "merge" ? (resolution.statement ?? incoming) : null,
              })
            }
          >
            {t(`conflicts.${action}`)}
          </Button>
        ))}
      </div>

      <div className="reveal" data-open={merging}>
        <div>
          <div className="border-t border-border px-5 py-4">
            <label className="mb-2 block font-mono text-[11px] tracking-wide text-muted-foreground uppercase">
              {t("conflicts.mergeLabel")}
            </label>
            <textarea
              value={resolution.statement ?? incoming}
              onChange={(event) => onChange({ action: "merge", statement: event.target.value })}
              rows={2}
              className="autosize w-full resize-none rounded-xl border border-input bg-muted p-3.5
                         font-mono text-[13px] leading-relaxed outline-none
                         transition-colors duration-[--state] focus:border-foreground/25"
            />
          </div>
        </div>
      </div>
    </li>
  );
}

/* The fade is applied to the contents, never to the pane: a translucent pane
   would let the seam and the card edge show through, which reads as a
   highlight — the exact opposite of the side that lost. */
function Side({
  label,
  text,
  receded,
  className,
}: {
  label: string;
  text: string;
  receded: boolean;
  className?: string;
}) {
  return (
    <div className={cn("p-5", className)}>
      <div
        className={cn(
          "transition-opacity duration-[--state] ease-[--ease-out]",
          receded && "opacity-35",
        )}
      >
        <p className="mb-2 font-mono text-[11px] tracking-wide text-muted-foreground uppercase">
          {label}
        </p>
        <p className="font-mono text-[13px] leading-relaxed">{text}</p>
      </div>
    </div>
  );
}
