import type { ButtonHTMLAttributes, ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { Progress } from "./api";
import type { Stage } from "./types";

/* Press feedback is the one animation felt on every interaction: fast (160ms)
   and small (0.97). Hover is gated behind a media query because touch devices
   fire it on tap. */
export function Button({
  variant = "quiet",
  size = "md",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "quiet" | "chosen" | "ghost";
  size?: "md" | "lg";
}) {
  const looks = {
    primary: "bg-verdigris text-white shadow-card hover:brightness-110 active:brightness-95",
    quiet: "border border-line bg-surface text-ink hover:border-line-strong",
    chosen: "border border-verdigris bg-verdigris-soft text-verdigris-ink font-semibold",
    ghost: "text-muted hover:text-ink",
  };
  const sizes = { md: "px-3.5 py-2 text-sm", lg: "px-5 py-2.5 text-[15px]" };
  return (
    <button
      className={`inline-flex items-center gap-2 rounded-full font-medium
                  transition-[transform,background-color,border-color,color,filter]
                  duration-[--press] ease-[--ease-out] active:scale-[0.97]
                  disabled:pointer-events-none disabled:opacity-35
                  ${looks[variant]} ${sizes[size]} ${className}`}
      {...props}
    />
  );
}

/* ── The deck's position indicator ────────────────────────────────────────
   Wayfinding: where am I, what is behind me, what is left. A single track
   fills as you advance, so progress reads at a glance without counting. */
const STEPS: { id: Stage | "capture"; key: string }[] = [
  { id: "capture", key: "say" },
  { id: "confirm", key: "review" },
  { id: "resolve", key: "decide" },
  { id: "done", key: "commit" },
];
// `detecting` sits between review and decide: it is a loading state, not a
// slide, so it advances the stepper without adding a dot of its own.
const STEP_ORDER: (Stage | "capture")[] = [
  "capture",
  "confirm",
  "detecting",
  "resolve",
  "done",
];

export function Stepper({ stage }: { stage: Stage | "capture" }) {
  const { t } = useTranslation();
  const current = STEP_ORDER.indexOf(stage);

  return (
    <ol className="flex items-center gap-1.5 sm:gap-2" aria-label={t("stepper.label")}>
      {STEPS.map(({ id, key }, index) => {
        const position = STEP_ORDER.indexOf(id);
        const done = position < current;
        const now = position === current;
        return (
          <li key={id} className="flex items-center gap-1.5 sm:gap-2">
            {index > 0 && (
              <span
                aria-hidden
                className={`h-px w-4 transition-colors duration-[--slide] sm:w-7
                            ${done || now ? "bg-verdigris" : "bg-line"}`}
              />
            )}
            <span
              aria-current={now ? "step" : undefined}
              className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px]
                          transition-colors duration-[--slide]
                          ${now ? "bg-verdigris-soft text-verdigris-ink font-semibold" : ""}
                          ${done ? "text-muted" : ""}
                          ${!done && !now ? "text-faint" : ""}`}
            >
              <span
                aria-hidden
                className={`h-1.5 w-1.5 rounded-full transition-colors duration-[--slide]
                            ${done || now ? "bg-verdigris" : "bg-line-strong"}`}
              />
              <span className="hidden sm:inline">{t(`stepper.${key}`)}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}

/* ── Slide furniture ─────────────────────────────────────────────────────── */

export function Kicker({ children }: { children: ReactNode }) {
  return (
    <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.2em] text-verdigris">
      {children}
    </p>
  );
}

/* Tracking tightens as size grows: at display sizes letters read too far
   apart with default spacing. */
export function Headline({ children }: { children: ReactNode }) {
  return (
    <h2 className="font-display text-[clamp(1.75rem,4.2vw,2.6rem)] leading-[1.05] font-semibold tracking-[-0.03em] text-balance">
      {children}
    </h2>
  );
}

export function Lede({ children }: { children: ReactNode }) {
  return (
    <p className="mt-4 max-w-[52ch] text-[16px] leading-[1.6] text-muted text-pretty">
      {children}
    </p>
  );
}

/* Real progress, not a spinner. Each line is a graph node that actually
   finished, so the counts are true. Finished lines stay, because seeing how
   far it got is what makes a slow local model bearable. */
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
    <div className="enter" role="status" aria-live="polite">
      <ul className="stagger space-y-3">
        {events.map((event, index) => {
          const last = index === events.length - 1;
          return (
            <li
              key={`${event.step}-${index}`}
              style={{ "--i": index } as React.CSSProperties}
              className={`flex items-center gap-3 text-[17px] ${last ? "text-ink" : "text-faint"}`}
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
      className="enter mt-4 rounded-xl border border-clay/40 bg-clay-soft px-3.5 py-2.5 text-sm text-clay"
    >
      {error instanceof Error ? error.message : String(error)}
    </p>
  );
}

export function Tags({ tags }: { tags: string[] }) {
  if (!tags?.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {tags.map((tag) => (
        <span
          key={tag}
          className="rounded-full bg-sunken px-2 py-0.5 font-mono text-[11px] text-muted"
        >
          {tag}
        </span>
      ))}
    </div>
  );
}
