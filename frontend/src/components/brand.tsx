import { cn } from "@/lib/utils";

type BrandProps = {
  className?: string;
  compact?: boolean;
  label: string;
};

export function Brand({ className, compact = false, label }: BrandProps) {
  return (
    <span className={cn("inline-flex items-center gap-2 font-semibold", className)}>
      <svg
        aria-hidden="true"
        className="size-6 shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M5 8.5 8.25 5 12 7l3.75-2L19 8.5v6.25C19 18.2 15.87 21 12 21s-7-2.8-7-6.25V8.5Z"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="1.75"
        />
        <path d="M8.5 12.25h.01M15.5 12.25h.01" stroke="currentColor" strokeLinecap="round" strokeWidth="2.5" />
        <path d="m10 16 2-1.5 2 1.5-2 1.5L10 16Z" fill="currentColor" />
      </svg>
      <span className={compact ? "sr-only" : ""}>{label}</span>
    </span>
  );
}
