/** A failure, said where it happened. Never a toast: the thing that failed is
 *  on screen, and the message belongs next to it. */
export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <p
      role="alert"
      className="enter mt-4 rounded-xl bg-destructive/10 px-3.5 py-2.5 text-sm text-destructive"
    >
      {error instanceof Error ? error.message : String(error)}
    </p>
  );
}
