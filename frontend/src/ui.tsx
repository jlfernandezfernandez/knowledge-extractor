import type { ButtonHTMLAttributes, ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { Progress } from "./api";
import { LANGUAGES, type Language } from "./i18n";
import type { Stage } from "./types";

/* Press feedback is the one animation every user feels on every interaction,
   so it is fast (160ms) and small (0.97). Hover is gated behind a media query
   because touch devices fire it on tap. */
export function Button({
  variant = "quiet",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "quiet" | "chosen" | "ghost";
}) {
  const looks = {
    primary:
      "bg-verdigris text-white shadow-card hover:brightness-108 active:brightness-95",
    quiet: "border border-line bg-surface text-ink hover:border-line-strong",
    chosen: "border border-verdigris bg-verdigris-soft text-verdigris-ink font-semibold",
    ghost: "text-muted hover:text-ink",
  };
  return (
    <button
      className={`inline-flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium
                  transition-[transform,background-color,border-color,color,filter]
                  duration-[--press] ease-[--ease-out] active:scale-[0.97]
                  disabled:pointer-events-none disabled:opacity-40
                  ${looks[variant]} ${className}`}
      {...props}
    />
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <p className="mb-2.5 font-mono text-[11px] uppercase tracking-[0.18em] text-faint">
      {children}
    </p>
  );
}

export function Title({ children }: { children: ReactNode }) {
  return (
    <h2 className="font-display text-[27px] leading-[1.15] font-semibold tracking-[-0.02em]">
      {children}
    </h2>
  );
}

export function Lead({ children }: { children: ReactNode }) {
  return <p className="mt-2.5 max-w-[58ch] text-[15px] leading-relaxed text-muted">{children}</p>;
}

/* The stage rail: completed stages stay filled rather than draining, so the
   review reads as sediment accumulating. Not numbered — the sequence is
   already carried by the order and the filled bars. */
const STAGES: { id: Stage; key: string }[] = [
  { id: "confirm", key: "understand" },
  { id: "detecting", key: "compare" },
  { id: "resolve", key: "decide" },
  { id: "done", key: "commit" },
];

export function Rail({ stage }: { stage: Stage | "capture" }) {
  const { t } = useTranslation();
  const order: (Stage | "capture")[] = ["capture", "confirm", "detecting", "resolve", "done"];
  const current = order.indexOf(stage);

  return (
    <nav aria-label={t("rail.understand")} className="flex flex-col">
      {STAGES.map(({ id, key }) => {
        const index = order.indexOf(id);
        const done = index < current;
        const now = index === current;
        return (
          <div key={id} className="flex items-stretch gap-3">
            <span
              aria-hidden
              className={`w-[3px] rounded-full transition-colors duration-[--step] ease-[--ease-out]
                          ${done || now ? "bg-verdigris" : "bg-line"}`}
            />
            <div
              className={`py-2.5 transition-opacity duration-[--step] ease-[--ease-out]
                          ${index > current ? "opacity-40" : ""}`}
            >
              <div className={`text-[13px] ${now ? "font-semibold text-ink" : "text-muted"}`}>
                {t(`rail.${key}`)}
              </div>
              <div className="text-[12px] leading-snug text-faint">{t(`rail.${key}Note`)}</div>
            </div>
          </div>
        );
      })}
    </nav>
  );
}

/* Real progress, not a spinner. Each line is a LangGraph node that actually
   finished, so the counts are true. Completed lines stay so you can see how
   far it got — which is what makes a slow model bearable. */
export function Working({ events }: { events: Progress[] }) {
  const { t } = useTranslation();

  const label = (event: Progress): string => {
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
    <div className="enter py-10" role="status" aria-live="polite">
      <ul className="stagger space-y-2.5">
        {events.map((event, index) => {
          const last = index === events.length - 1;
          return (
            <li
              key={`${event.step}-${index}`}
              style={{ "--i": index } as React.CSSProperties}
              className={`flex items-center gap-3 text-[15px] ${last ? "text-ink" : "text-faint"}`}
            >
              <span
                aria-hidden
                className={`h-1.5 w-1.5 shrink-0 rounded-full ${last ? "bg-verdigris" : "bg-line-strong"}`}
                style={last ? { animation: "breathe 1.4s ease-in-out infinite" } : undefined}
              />
              {label(event)}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function Problem({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <p
      role="alert"
      className="enter mt-3 rounded-lg border border-clay/40 bg-clay-soft px-3 py-2 text-sm text-clay"
    >
      {error instanceof Error ? error.message : String(error)}
    </p>
  );
}

export function Tags({ tags }: { tags: string[] }) {
  if (!tags?.length) return null;
  return (
    <div className="mt-2.5 flex flex-wrap gap-1.5">
      {tags.map((tag) => (
        <span
          key={tag}
          className="rounded bg-sunken px-1.5 py-0.5 font-mono text-[11px] text-muted"
        >
          {tag}
        </span>
      ))}
    </div>
  );
}

export function LanguagePicker() {
  const { i18n, t } = useTranslation();
  return (
    <label className="flex items-center">
      <span className="sr-only">{t("app.language")}</span>
      <select
        value={i18n.resolvedLanguage}
        onChange={(e) => i18n.changeLanguage(e.target.value)}
        className="cursor-pointer rounded-lg border border-line bg-surface px-2.5 py-2 text-sm
                   text-muted transition-colors duration-[--press] hover:text-ink focus:text-ink"
      >
        {Object.entries(LANGUAGES).map(([code, name]) => (
          <option key={code} value={code as Language}>
            {name}
          </option>
        ))}
      </select>
    </label>
  );
}
