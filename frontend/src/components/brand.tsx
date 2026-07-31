import { cn } from "@/lib/utils";

type BrandProps = {
  className?: string;
  compact?: boolean;
  label: string;
};

export function Brand({ className, compact = false, label }: BrandProps) {
  return (
    <span className={cn("inline-flex items-center gap-2 font-semibold", className)}>
      <span aria-hidden="true">🦉</span>
      <span className={compact ? "sr-only" : ""}>{label}</span>
    </span>
  );
}
