import { useState } from "react";

const KEY = "knowli.author";

/** Who is speaking. Asked once, remembered, and attached to everything they
 *  save — a claim without an author is a claim nobody can be asked about. */
export function useAuthor() {
  const [author, set] = useState(() => localStorage.getItem(KEY) ?? "");
  return [
    author,
    (name: string) => {
      localStorage.setItem(KEY, name);
      set(name);
    },
  ] as const;
}
