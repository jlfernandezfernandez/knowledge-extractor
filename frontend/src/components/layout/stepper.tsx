import { useTranslation } from "react-i18next";
import type { Stage } from "@/types/review";
import { cn } from "@/lib/utils";

/**
 * Where am I, what is behind me, what is left.
 *
 * `extracting` and `detecting` are loading states rather than steps, so they
 * advance the track without earning a marker of their own — otherwise the
 * count of steps would change while you wait.
 */
const STEPS = [
  { id: "capture", label: "say" },
  { id: "confirm", label: "readback" },
  { id: "resolve", label: "decide" },
  { id: "done", label: "saved" },
] as const;

const ORDER: Stage[] = ["capture", "extracting", "confirm", "detecting", "resolve", "done"];

export function Stepper({ stage }: { stage: Stage }) {
  const { t } = useTranslation();
  const current = ORDER.indexOf(stage);

  return (
    <ol className="flex items-center gap-1" aria-label={t("stepper.label")}>
      {STEPS.map(({ id, label }, index) => {
        const position = ORDER.indexOf(id);
        const passed = position < current;
        const here = position === current;
        return (
          <li key={id} className="flex items-center gap-1">
            {index > 0 && (
              <span
                aria-hidden
                className={cn(
                  "h-px w-3 transition-colors duration-[--state] sm:w-5",
                  passed || here ? "bg-foreground/40" : "bg-border",
                )}
              />
            )}
            <span
              aria-current={here ? "step" : undefined}
              className={cn(
                "flex items-center gap-1.5 rounded-full px-2 py-1 text-xs transition-colors duration-[--state]",
                here && "bg-muted font-medium text-foreground",
                passed && "text-muted-foreground",
                !passed && !here && "text-muted-foreground/50",
              )}
            >
              <span
                aria-hidden
                className={cn(
                  "size-1.5 rounded-full transition-colors duration-[--state]",
                  passed || here ? "bg-foreground/60" : "bg-border",
                )}
              />
              <span className="hidden sm:inline">{t(`stepper.${label}`)}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
