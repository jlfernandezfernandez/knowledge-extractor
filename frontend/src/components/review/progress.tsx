import { useTranslation } from "react-i18next";
import type { Progress as ProgressEvent } from "@/types/review";
import { cn } from "@/lib/utils";

/**
 * What the graph is actually doing, not a spinner.
 *
 * Each line is a node that really finished, so every count on screen is a
 * measured one. Finished lines stay: seeing how far it got is what makes a
 * slow local model bearable.
 */
export function Progress({ events }: { events: ProgressEvent[] }) {
  const { t } = useTranslation();

  const label = (event: ProgressEvent): string => {
    switch (event.step) {
      case "reading":
        return t("progress.reading");
      case "extracted":
        return event.against === 0
          ? t("progress.comparingEmpty")
          : `${t("progress.extracted", { count: event.count })} · ${t("progress.comparing", { count: event.against })}`;
      case "compared":
        return t("progress.compared", { count: event.count });
      case "committed":
        return t("progress.committing");
    }
  };

  return (
    <div className="enter" role="status" aria-live="polite">
      <ul className="stagger space-y-3">
        {events.map((event, index) => {
          const last = index === events.length - 1;
          return (
            <li
              key={`${event.step}-${index}`}
              style={{ "--i": index } as React.CSSProperties}
              className={cn(
                "flex items-center gap-3 text-[16px]",
                last ? "text-foreground" : "text-muted-foreground/60",
              )}
            >
              <span
                aria-hidden
                className={cn(
                  "size-1.5 shrink-0 rounded-full",
                  last ? "breathe bg-foreground" : "bg-border",
                )}
              />
              {label(event)}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
