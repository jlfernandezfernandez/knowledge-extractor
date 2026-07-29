import { useTranslation } from "react-i18next";
import type { StoredClaim } from "@/types/knowledge";

/** The claims the answer was built from, cited ones first. This is the whole
 *  argument for the product: an answer you can check. */
export function SourceList({ sources }: { sources: StoredClaim[] }) {
  const { t } = useTranslation();
  if (!sources.length) return null;

  return (
    <>
      <p className="mt-6 mb-2 text-xs font-medium text-muted-foreground">{t("ask.drawnFrom")}</p>
      <ul className="stagger space-y-1.5">
        {sources.map((claim, index) => (
          <li
            key={claim.id}
            style={{ "--i": index } as React.CSSProperties}
            className="rounded-xl bg-muted p-3"
          >
            <p className="text-[14px] font-semibold">{claim.title}</p>
            <p className="mt-0.5 text-[14px] leading-relaxed text-muted-foreground">
              {claim.statement}
            </p>
          </li>
        ))}
      </ul>
    </>
  );
}
