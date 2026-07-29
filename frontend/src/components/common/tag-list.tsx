export function TagList({ tags }: { tags: string[] }) {
  if (!tags?.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {tags.map((tag) => (
        <span
          key={tag}
          className="rounded-md bg-muted px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground"
        >
          {tag}
        </span>
      ))}
    </div>
  );
}
