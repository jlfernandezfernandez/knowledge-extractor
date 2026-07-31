import { post } from "@/lib/api";

export type Citation = {
  id: string;
  title: string;
  statement: string;
  author: string;
  contribution_id: string;
  contribution_created_at: string;
};

export type AskResponse = {
  answer: string;
  citations: Citation[];
  sufficient_evidence: boolean;
};

export const askApi = {
  ask: (question: string) => post<AskResponse>("/api/ask", { question }),
};
