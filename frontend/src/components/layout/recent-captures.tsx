import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { review } from "@/lib/api/review";
import type { SessionSummary } from "@/types/review";
import { cn } from "@/lib/utils";

/**
 * What you were last working on — not what the company knows.
 *
 * The rail used to list the whole store, which is fine with four claims and
 * meaningless with four million. This lists only your own captures, so it is
 * the same size on day one and at IKEA scale. Its real job is the unfinished
 * ones: a review parked on a human gate is invisible otherwise.
 */
export function RecentCaptures({
  knowledgeBase,
  version,
  activeSessionId,
  onOpen,
}: {
  knowledgeBase: string;
  /** Bumped whenever a review moves, so the list reflects it. */
  version: number;
  activeSessionId?: string;
  onOpen: (sessionId: string) => void;
}) {
  const { t } = useTranslation();
  const [items, setItems] = useState<SessionSummary[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!knowledgeBase) return;
    review
      .recent(knowledgeBase)
      .then((sessions) => {
        setItems(sessions);
        setFailed(false);
      })
      .catch(() => setFailed(true));
  }, [knowledgeBase, version]);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-1.5">
      <p className="px-2 text-xs font-medium text-muted-foreground">{t("recent.title")}</p>

      <div className="-mx-1 min-h-0 flex-1 overflow-y-auto px-1">
        {failed && <Note>{t("recent.failed")}</Note>}
        {!failed && items?.length === 0 && <Note>{t("recent.empty")}</Note>}

        {/* Two lines per row, so rows need more air between them than the
            two lines need from each other. */}
        <ul className="space-y-1">
          {items?.map((session) => {
            const unfinished = session.stage !== "done";
            const ago = since(session.updated_at);
            return (
              <li key={session.session_id}>
                <button
                  type="button"
                  onClick={() => onOpen(session.session_id)}
                  className={cn(
                    "w-full rounded-lg px-2 py-1.5 text-left transition-colors",
                    session.session_id === activeSessionId
                      ? "bg-sidebar-accent"
                      : "hover:bg-sidebar-accent/70",
                  )}
                >
                  <span className="flex items-center gap-1.5">
                    {unfinished && (
                      <span
                        aria-hidden
                        className="size-1.5 shrink-0 rounded-full bg-foreground/60"
                      />
                    )}
                    <span className="truncate text-[13px]">
                      {session.summary || t("recent.untitled")}
                    </span>
                  </span>
                  <span className="mt-0.5 block text-[11px] text-muted-foreground">
                    {unfinished
                      ? t(`recent.stage.${session.stage}`)
                      : t(ago.key, { count: ago.count })}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}

function Note({ children }: { children: React.ReactNode }) {
  return <p className="px-2 py-3 text-[13px] leading-relaxed text-muted-foreground">{children}</p>;
}

/** The coarsest unit that is still true, as a catalogue key and its count. */
function since(iso: string): { key: string; count: number } {
  const minutes = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (minutes < 1) return { key: "recent.justNow", count: 0 };
  if (minutes < 60) return { key: "recent.minutes", count: minutes };
  const hours = Math.round(minutes / 60);
  if (hours < 24) return { key: "recent.hours", count: hours };
  return { key: "recent.days", count: Math.round(hours / 24) };
}
