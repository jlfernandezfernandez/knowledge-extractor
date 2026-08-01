import { cn } from "@/lib/utils";

type BrandProps = {
  className?: string;
  compact?: boolean;
  label: string;
};

export function Brand({ className, compact = false, label }: BrandProps) {
  return (
    <span className={cn("inline-flex items-center gap-2.5 font-semibold tracking-tight", className)}>
      <span className="flex aspect-square size-8 items-center justify-center rounded-lg bg-zinc-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/60 shadow-2xs shrink-0 select-none">
        <span aria-hidden="true" className="text-base leading-none">🦉</span>
      </span>
      <span className={cn(compact && "sr-only", "group-data-[collapsible=icon]:hidden")}>{label}</span>
    </span>
  );
}
