import type { KnowledgeBase } from "@/types/knowledge";
import { post, request } from "./client";

export const knowledgeBases = {
  list: () => request<{ items: KnowledgeBase[] }>("/api/knowledge-bases").then((b) => b.items),

  /** The slug is derived from the name by the backend, and deduped there. */
  create: (name: string) => post<KnowledgeBase>("/api/knowledge-bases", { name }),
};
