import { useTranslation } from "react-i18next";
import { XIcon } from "lucide-react";
import { TagList } from "@/components/common/tag-list";
import type { ClaimDraft } from "@/types/review";

interface ClaimCardProps {
  claim: ClaimDraft;
  /** The heading this claim already sits under, so the card can stay quiet. */
  topic: string;
  index: number;
  onEdit: (patch: Partial<ClaimDraft>) => void;
  onRemove: () => void;
}

/**
 * One claim, editable in place.
 *
 * The statement leads, because the statement is the thing being checked. The
 * title only appears when it says something the statement and the topic
 * heading above do not — repeating the topic as a card title was pure noise.
 */
export function ClaimCard({ claim, topic, index, onEdit, onRemove }: ClaimCardProps) {
  const { t } = useTranslation();
  const titleAddsNothing = claim.title.trim().toLowerCase() === topic.trim().toLowerCase();

  return (
    <li
      style={{ "--i": index } as React.CSSProperties}
      className="group rounded-2xl border border-border bg-card p-4 transition-colors duration-[--state]
                 focus-within:border-foreground/25 hover:border-foreground/15"
    >
      <div className="flex items-start gap-2">
        <textarea
          value={claim.statement}
          onChange={(event) => onEdit({ statement: event.target.value })}
          aria-label={t("confirm.claim")}
          rows={1}
          className="autosize min-w-0 flex-1 resize-none bg-transparent text-[15px] leading-relaxed outline-none"
        />
        <button
          type="button"
          onClick={onRemove}
          aria-label={t("confirm.discard")}
          className="grid size-7 shrink-0 place-items-center rounded-lg text-muted-foreground opacity-0
                     transition-[opacity,background-color,color] duration-[--press]
                     hover:bg-muted hover:text-foreground focus-visible:opacity-100
                     group-hover:opacity-100 max-sm:opacity-100"
        >
          <XIcon className="size-4" />
        </button>
      </div>

      {!titleAddsNothing && (
        <input
          value={claim.title}
          onChange={(event) => onEdit({ title: event.target.value })}
          aria-label={t("confirm.claimTitle")}
          className="mt-1.5 w-full bg-transparent font-mono text-[11px] tracking-wide text-muted-foreground
                     uppercase outline-none"
        />
      )}

      <TagList tags={claim.tags} />
    </li>
  );
}
