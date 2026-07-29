import { useTranslation } from "react-i18next";
import { ArrowLeftIcon, PanelLeftIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import type { Stage } from "@/types/review";
import { Stepper } from "./stepper";

interface TopBarProps {
  stage: Stage;
  canGoBack: boolean;
  onBack: () => void;
  onAsk: () => void;
  onOpenMenu: () => void;
}

/**
 * Translucent, with the review running underneath rather than an opaque strip
 * eating the top of every step. Back sits on the left because that is where
 * every back control the reader has ever used sits.
 */
export function TopBar({ stage, canGoBack, onBack, onAsk, onOpenMenu }: TopBarProps) {
  const { t } = useTranslation();

  return (
    <header className="z-10 shrink-0 bg-background/75 backdrop-blur-xl">
      <div className="flex h-14 items-center gap-2 px-3 sm:px-4">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onOpenMenu}
          aria-label={t("app.openMenu")}
          className="md:hidden"
        >
          <PanelLeftIcon />
        </Button>

        {canGoBack && (
          <Button variant="ghost" size="sm" onClick={onBack} className="gap-1.5">
            <ArrowLeftIcon />
            <span className="max-sm:sr-only">{t("nav.back")}</span>
          </Button>
        )}

        <div className="mx-auto">
          <Stepper stage={stage} />
        </div>

        <Button variant="ghost" size="sm" onClick={onAsk} className="gap-1.5">
          {t("app.ask")}
          <Kbd className="max-sm:hidden">⌘K</Kbd>
        </Button>
      </div>
    </header>
  );
}
