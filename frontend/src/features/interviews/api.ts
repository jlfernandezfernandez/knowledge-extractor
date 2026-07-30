import { post, request } from "@/lib/api/client";
import type { AuthenticatedUser } from "@/features/auth/types";
import type { Contribution } from "@/features/contributions/types";

export type InterviewStatus = "pending" | "started" | "completed";
export type InterviewView = "pending" | "sent" | "completed";

export type Interview = {
  id: string;
  requester_id: string;
  assignee_id: string;
  title: string;
  brief: string;
  status: InterviewStatus;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};

export const interviewsApi = {
  users: () => request<{ items: AuthenticatedUser[] }>("/api/users").then((body) => body.items),
  list: (view: InterviewView) =>
    request<{ items: Interview[] }>(`/api/interviews?view=${view}`).then((body) => body.items),
  create: (input: { assignee_id: string; title: string; brief: string }) =>
    post<Interview>("/api/interviews", input),
  start: (id: string) => post<{ interview: Interview; contribution_id: string }>(`/api/interviews/${id}/start`),
  byContribution: (contributionId: string) => request<Interview>(`/api/interviews/by-contribution/${contributionId}`),
  answer: (id: string, raw_text: string) => post<Contribution>(`/api/interviews/${id}/answer`, { raw_text }),
};
