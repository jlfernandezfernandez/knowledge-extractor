import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";

/**
 * The mark: an owl in a rounded tile, then the name.
 *
 * An emoji rather than a drawn logo, deliberately — it inherits the platform's
 * own artwork, so it looks native on every OS, needs no dark-mode variant and
 * costs nothing to load. The tile behind it is what keeps it from reading as a
 * stray character in a sentence.
 */
export function Brand({ className }: { className?: string }) {
  const { t } = useTranslation();
  return (
    <span className={cn("flex items-center gap-2", className)}>
      <span
        aria-hidden
        className="grid size-7 shrink-0 place-items-center rounded-lg bg-muted text-[15px] leading-none"
      >
        🦉
      </span>
      <span className="text-[15px] font-semibold tracking-[-0.02em]">{t("app.name")}</span>
    </span>
  );
}
