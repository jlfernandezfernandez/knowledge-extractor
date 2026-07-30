import type { Interview } from "./api";

type InterviewContext = { contribution_id: string; interview: Interview };

const key = (contributionId: string) => `knowli.interview.${contributionId}`;

export function rememberInterviewContext(contributionId: string, interview: Interview) {
  sessionStorage.setItem(key(contributionId), JSON.stringify({ contribution_id: contributionId, interview }));
}

export function readInterviewContext(contributionId: string): Interview | null {
  try {
    const stored = JSON.parse(sessionStorage.getItem(key(contributionId)) ?? "null") as InterviewContext | null;
    return stored?.contribution_id === contributionId ? stored.interview : null;
  } catch {
    return null;
  }
}

export function clearInterviewContext(contributionId: string) {
  sessionStorage.removeItem(key(contributionId));
}
