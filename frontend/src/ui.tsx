import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { Stage } from "./types";

export function Button({
  variant = "quiet",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "quiet" | "chosen";
}) {
  const base =
    "inline-flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium " +
    "transition-colors disabled:opacity-45 disabled:pointer-events-none";
  const looks = {
    primary: "bg-verdigris text-white hover:brightness-110",
    quiet: "border border-line bg-surface text-ink hover:border-verdigris",
    chosen: "border border-verdigris bg-verdigris-soft text-verdigris",
  };
  return <button className={`${base} ${looks[variant]} ${className}`} {...props} />;
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
      {children}
    </p>
  );
}

export function Title({ children }: { children: ReactNode }) {
  return (
    <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">
      {children}
    </h2>
  );
}

/* The stage rail. Knowledge accumulates in layers here rather than counting
   1/2/3/4: each completed stage stays visible as a filled stratum, so the
   review reads as sediment building up, not as a progress bar draining. */
const STAGES: { id: Stage; label: string; note: string }[] = [
  { id: "confirm", label: "Understand", note: "what the model heard" },
  { id: "detecting", label: "Compare", note: "against what is stored" },
  { id: "resolve", label: "Decide", note: "which claim wins" },
  { id: "done", label: "Commit", note: "written and indexed" },
];

export function Rail({ stage }: { stage: Stage | "capture" }) {
  const order: (Stage | "capture")[] = ["capture", "confirm", "detecting", "resolve", "done"];
  const current = order.indexOf(stage);
  return (
    <nav aria-label="Review progress" className="flex flex-col gap-px">
      {STAGES.map((s) => {
        const index = order.indexOf(s.id);
        const state = index < current ? "past" : index === current ? "now" : "ahead";
        return (
          <div key={s.id} className="flex items-stretch gap-3">
            <div
              aria-hidden
              className={
                "w-1 rounded-full transition-colors " +
                (state === "ahead" ? "bg-line" : "bg-verdigris")
              }
            />
            <div className={`py-2 ${state === "ahead" ? "opacity-45" : ""}`}>
              <div
                className={
                  "text-sm " + (state === "now" ? "font-semibold text-ink" : "text-muted")
                }
              >
                {s.label}
              </div>
              <div className="text-xs text-muted">{s.note}</div>
            </div>
          </div>
        );
      })}
    </nav>
  );
}

export function Working({ label }: { label: string }) {
  return (
    <div className="settle flex items-center gap-3 py-16" role="status">
      <span className="flex gap-1" aria-hidden>
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 rounded-full bg-verdigris"
            style={{ animation: `settle 0.9s ${i * 0.15}s infinite alternate` }}
          />
        ))}
      </span>
      <span className="text-sm text-muted">{label}</span>
    </div>
  );
}

export function Problem({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <p className="mt-3 rounded-lg border border-clay bg-clay-soft px-3 py-2 text-sm text-clay">
      {error instanceof Error ? error.message : String(error)}
    </p>
  );
}

export function Tags({ tags }: { tags: string[] }) {
  if (!tags?.length) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {tags.map((t) => (
        <span
          key={t}
          className="rounded bg-sunken px-1.5 py-0.5 font-mono text-[11px] text-muted"
        >
          {t}
        </span>
      ))}
    </div>
  );
}
