import { cn } from "@/lib/utils";

type BrandProps = {
  className?: string;
  compact?: boolean;
  label: string;
};

export function Brand({ className, compact = false, label }: BrandProps) {
  return (
    <span className={cn("inline-flex items-center gap-2 font-semibold", className)}>
      <span aria-hidden="true" className="text-base leading-none">🦉</span>
      <span className={cn(compact && "sr-only", "group-data-[collapsible=icon]:hidden")}>{label}</span>
    </span>
  );
}
