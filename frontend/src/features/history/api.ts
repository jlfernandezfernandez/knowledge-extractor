import { request } from "@/lib/api";

export type HistoryItem = {
  contribution_id: string;
  author: string;
  source: string;
  summary: string;
  claim_count: number;
  created_at: string;
};

type HistoryPage = {
  items: HistoryItem[];
  next_cursor: string | null;
};

const PAGE_SIZE = 20;

export const historyApi = {
  list: (cursor?: string | null) => {
    const query = cursor ? `cursor=${encodeURIComponent(cursor)}&limit=${PAGE_SIZE}` : `limit=${PAGE_SIZE}`;
    return request<HistoryPage>(`/api/history?${query}`);
  },
};
