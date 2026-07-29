import { useCallback, useEffect, useState } from "react";
import { knowledgeBases } from "@/lib/api/knowledge-bases";
import type { KnowledgeBase } from "@/types/knowledge";

const KEY = "knowli.knowledge-base";

/**
 * Which knowledge base you are feeding.
 *
 * The choice is remembered, because it changes rarely and re-picking it every
 * morning would be the kind of friction this product exists to remove. A
 * remembered slug that no longer exists falls back to the first one rather
 * than leaving the app pointed at nothing.
 */
export function useKnowledgeBases() {
  const [items, setItems] = useState<KnowledgeBase[]>([]);
  const [slug, setSlug] = useState(() => localStorage.getItem(KEY) ?? "");
  const [error, setError] = useState<unknown>(null);

  const refresh = useCallback(async () => {
    const bases = await knowledgeBases.list();
    setItems(bases);
    setSlug((current) => {
      const next = bases.some((base) => base.slug === current) ? current : (bases[0]?.slug ?? "");
      localStorage.setItem(KEY, next);
      return next;
    });
  }, []);

  useEffect(() => {
    refresh().catch(setError);
  }, [refresh]);

  const select = useCallback((next: string) => {
    localStorage.setItem(KEY, next);
    setSlug(next);
  }, []);

  const create = useCallback(
    async (name: string) => {
      const created = await knowledgeBases.create(name);
      await refresh();
      select(created.slug);
      return created;
    },
    [refresh, select],
  );

  return {
    items,
    slug,
    current: items.find((base) => base.slug === slug) ?? null,
    error,
    select,
    create,
    refresh,
  };
}

export type KnowledgeBases = ReturnType<typeof useKnowledgeBases>;
