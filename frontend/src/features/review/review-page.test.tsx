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

  afterEach(() => vi.unstubAllGlobals());

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
});
