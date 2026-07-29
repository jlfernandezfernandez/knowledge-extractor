import { useTranslation } from "react-i18next";
import { PlusIcon, SearchIcon, XIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import type { KnowledgeBases } from "@/hooks/use-knowledge-bases";
import { Brand } from "./brand";
import { KnowledgeBasePicker } from "./knowledge-base-picker";
import { RecentCaptures } from "./recent-captures";
import { cn } from "@/lib/utils";

interface SidebarProps {
  bases: KnowledgeBases;
  /** Bumped whenever a review moves, so the capture list reflects it. */
  version: number;
  activeSessionId?: string;
  onOpenSession: (sessionId: string) => void;
  author: string;
  onAuthorChange: (name: string) => void;
  onNewCapture: () => void;
  onAsk: () => void;
  /** Mobile only: the rail is a drawer below `md`. */
  open: boolean;
  onClose: () => void;
}

export function Sidebar({
  bases,
  version,
  activeSessionId,
  onOpenSession,
  author,
  onAuthorChange,
  onNewCapture,
  onAsk,
  open,
  onClose,
}: SidebarProps) {
  const { t } = useTranslation();

  return (
    <>
      {/* The drawer's backdrop. Below `md` only; a button so it is reachable
          without a pointer. */}
      <button
        type="button"
        aria-label={t("app.closeMenu")}
        onClick={onClose}
        className={cn(
          "fixed inset-0 z-30 bg-foreground/20 transition-opacity duration-[--state] md:hidden",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      />

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col gap-3 border-r border-sidebar-border",
          "bg-sidebar p-3 text-sidebar-foreground transition-transform duration-[--state] ease-[--ease-out]",
          "md:static md:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center justify-between">
          <Brand className="px-1" />
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onClose}
            aria-label={t("app.closeMenu")}
            className="md:hidden"
          >
            <XIcon />
          </Button>
        </div>

        <KnowledgeBasePicker bases={bases} />

        <div className="space-y-0.5">
          <Button
            variant="ghost"
            className="h-9 w-full justify-start gap-2 px-2 text-[13px]"
            onClick={onNewCapture}
          >
            <PlusIcon />
            {t("app.newCapture")}
          </Button>
          <Button
            variant="ghost"
            className="h-9 w-full justify-start gap-2 px-2 text-[13px]"
            onClick={onAsk}
          >
            <SearchIcon />
            {t("app.ask")}
            <Kbd className="ml-auto bg-transparent">⌘K</Kbd>
          </Button>
        </div>

        <RecentCaptures
          knowledgeBase={bases.slug}
          version={version}
          activeSessionId={activeSessionId}
          onOpen={onOpenSession}
        />

        <label className="shrink-0 border-t border-sidebar-border pt-3">
          <span className="sr-only">{t("sidebar.signedAs")}</span>
          <input
            value={author}
            onChange={(event) => onAuthorChange(event.target.value)}
            placeholder={t("sidebar.signedAs")}
            className="h-8 w-full rounded-lg px-2 text-[13px] outline-none transition-colors
                       placeholder:text-muted-foreground hover:bg-sidebar-accent/70 focus:bg-sidebar-accent"
          />
        </label>
      </aside>
    </>
  );
}
