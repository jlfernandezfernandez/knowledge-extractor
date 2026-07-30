import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import "@/i18n";
import { ReviewPage } from "./review-page";

const claim = { draft_key: "draft-1", title: "Friday deployment", statement: "Production deployments happen Friday.", tags: ["release"] };
const base = {
  id: "contribution-1",
  author_id: "user-1",
  author: "Ada Lovelace",
  kind: "contribution",
  source: "text",
  raw_text: "Production deployments happen Friday.",
  revision: 2,
  summary: "Production deployments happen Friday.",
  created_at: "2026-07-30T08:00:00Z",
  committed_at: null,
  claim_count: 0,
  claims: [claim],
  conflicts: [],
};

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function renderReview() {
  return render(
    <MemoryRouter initialEntries={["/review/contribution-1"]}>
      <Routes>
        <Route path="/review/:id" element={<ReviewPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("contribution review", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ ...base, stage: "claims" })));
    vi.stubGlobal("EventSource", class { close() {} addEventListener() {} });
  });

  afterEach(() => { sessionStorage.clear(); vi.unstubAllGlobals(); });

  it.each([
    ["claims", "Review claims"],
    ["conflicts", "Resolve conflicts"],
    ["commit", "Ready to save"],
    ["committed", "Saved"],
  ])("shows the %s review stage", async (stage, heading) => {
    vi.mocked(fetch).mockResolvedValueOnce(response({ ...base, stage, committed_at: stage === "committed" ? "2026-07-30T09:00:00Z" : null }));
    renderReview();
    expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
  });

  it("refreshes the contribution after a stale revision response", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(response({ ...base, stage: "claims" }));
    fetchMock.mockResolvedValueOnce(response({ code: "stale_revision", message: "contribution changed; refresh and try again" }, 409));
    fetchMock.mockResolvedValueOnce(response({ ...base, stage: "claims", revision: 3, summary: "Fresh server state" }));
    renderReview();

    fireEvent.click(await screen.findByRole("button", { name: "Continue to conflicts" }));
    expect(await screen.findByText("Fresh server state")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://localhost:8000/api/contributions/contribution-1",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("commits with the current server revision and shows the saved stage", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(response({ ...base, stage: "commit", revision: 7 }));
    fetchMock.mockResolvedValueOnce(response({ ...base, stage: "committed", revision: 8, committed_at: "2026-07-30T09:00:00Z", claim_count: 1 }));
    renderReview();

    fireEvent.click(await screen.findByRole("button", { name: "Save contribution" }));
    expect(await screen.findByRole("heading", { name: "Saved" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://localhost:8000/api/contributions/contribution-1/commit",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ revision: 7 }) }),
    );
  });

  it("restores interview context on a direct review route and submits only the answer", async () => {
    sessionStorage.setItem("knowli.interview.contribution-1", JSON.stringify({
      contribution_id: "contribution-1",
      interview: {
        id: "interview-1", requester_id: "requester-1", assignee_id: "user-1", title: "Deployment retrospective", brief: "Explain the Friday release process.", status: "started", created_at: "2026-07-30T08:00:00Z", started_at: "2026-07-30T08:01:00Z", completed_at: null,
      },
    }));
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(response({ ...base, kind: "interview", raw_text: "", stage: "claims" }));
    fetchMock.mockResolvedValueOnce(response({ ...base, kind: "interview", raw_text: "We deploy on Fridays.", stage: "claims" }));
    renderReview();

    expect(await screen.findByRole("heading", { name: "Deployment retrospective" })).toBeInTheDocument();
    expect(screen.getByText("Explain the Friday release process.")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Your interview answer" }), { target: { value: "We deploy on Fridays." } });
    fireEvent.click(screen.getByRole("button", { name: "Submit answer" }));

    expect(await screen.findByRole("heading", { name: "Review claims" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://localhost:8000/api/interviews/interview-1/answer",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ raw_text: "We deploy on Fridays." }) }),
    );
    expect(sessionStorage.getItem("knowli.interview.contribution-1")).toBeNull();
  });

  it("sends the human-selected conflict resolution, including merge text", async () => {
    const fetchMock = vi.mocked(fetch);
    const conflict = { claim_draft_key: "draft-1", existing_id: "claim-1", verdict: "conflict", reason: "The deployment date differs." };
    fetchMock.mockResolvedValueOnce(response({ ...base, stage: "conflicts", conflicts: [conflict] }));
    fetchMock.mockResolvedValueOnce(response({ ...base, stage: "commit", revision: 3 }));
    renderReview();

    fireEvent.click(await screen.findByRole("button", { name: "Combine" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Merged statement" }), { target: { value: "Deploy after Friday review." } });
    fireEvent.click(screen.getByRole("button", { name: "Continue to save" }));

    expect(await screen.findByRole("heading", { name: "Ready to save" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://localhost:8000/api/contributions/contribution-1/resolve",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ revision: 2, resolutions: [{ claim_draft_key: "draft-1", action: "merge", replacement_statement: "Deploy after Friday review." }] }) }),
    );
  });
});
