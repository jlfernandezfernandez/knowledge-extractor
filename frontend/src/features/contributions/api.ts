import { post, request } from "@/lib/api";
import type { ClaimDraft, ConflictResolution, Contribution } from "./types";

export const contributionsApi = {
  create: (raw_text: string) =>
    post<Pick<Contribution, "id" | "stage" | "revision">>("/api/contributions", { raw_text }),
  get: (id: string) => request<Contribution>(`/api/contributions/${id}`),
  confirm: (id: string, revision: number, claims: ClaimDraft[]) =>
    post<Contribution>(`/api/contributions/${id}/confirm`, { revision, claims }),
  resolve: (id: string, revision: number, resolutions: ConflictResolution[]) =>
    post<Contribution>(`/api/contributions/${id}/resolve`, { revision, resolutions }),
  commit: (id: string, revision: number) =>
    post<Contribution>(`/api/contributions/${id}/commit`, { revision }),
  back: (id: string, revision: number) =>
    post<Contribution>(`/api/contributions/${id}/back`, { revision }),
};
