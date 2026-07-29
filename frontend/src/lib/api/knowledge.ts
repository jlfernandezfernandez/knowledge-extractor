import type { AskResponse } from "@/types/knowledge";
import { post } from "./client";

export const knowledge = {
  /** Hybrid retrieval plus a cited answer, over one knowledge base. Only ever
   *  reads claims a person approved. */
  ask: (question: string, knowledgeBase: string) =>
    post<AskResponse>("/api/ask", { question, knowledge_base: knowledgeBase }),
};
