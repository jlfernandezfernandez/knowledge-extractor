import { useEffect } from "react";

/**
 * A ⌘/Ctrl-modified key, bound for the life of the component.
 *
 * `handler` is read through a ref-free closure on every event, so callers do
 * not need to memoise it.
 */
export function useHotkey(key: string, handler: () => void) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() === key && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        handler();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  });
}
