import type { ReactNode } from "react";

/**
 * One step of the review.
 *
 * The action bar sticks to the bottom of the stage. A step can be taller than
 * the viewport — five claims to check, three overlaps to settle — and the way
 * forward must never be something you scroll to find.
 */
export function Step({
  step,
  title,
  lead,
  children,
  actions,
}: {
  step: string;
  title: ReactNode;
  lead?: ReactNode;
  children?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex min-h-full flex-col">
      <div className="pt-8 pb-6">
        <p className="mb-2 text-xs font-medium text-muted-foreground">{step}</p>
        <h1 className="text-[clamp(1.5rem,3.4vw,1.875rem)] leading-tight font-semibold tracking-[-0.02em] text-balance">
          {title}
        </h1>
        {lead && (
          <p className="mt-3 max-w-[58ch] text-[15px] leading-relaxed text-muted-foreground text-pretty">
            {lead}
          </p>
        )}
        {children}
      </div>
      {actions && (
        <div className="sticky bottom-0 -mx-4 mt-auto flex flex-wrap items-center gap-2 bg-background/85 px-4 py-4 backdrop-blur-xl sm:-mx-6 sm:px-6">
          {actions}
        </div>
      )}
    </div>
  );
}
