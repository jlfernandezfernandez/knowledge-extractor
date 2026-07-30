import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import { HistoryPage } from "./history-page";

const firstItem = {
  contribution_id: "contribution-1",
  author: "Ada Lovelace",
  source: "text",
  summary: "Production deployments happen on Friday.",
  claim_count: 2,
  created_at: "2026-07-29T08:00:00Z",
};

const secondItem = {
  contribution_id: "contribution-2",
  author: "Grace Hopper",
  source: "interview",
  summary: "Friday releases avoid sprint review.",
  claim_count: 1,
  created_at: "2026-07-28T08:00:00Z",
};

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function renderPage() {
  return render(<MemoryRouter><HistoryPage /></MemoryRouter>);
}

describe("history", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => vi.unstubAllGlobals());

  it("loads the next chronological page when requested", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(response({ items: [firstItem], next_cursor: "cursor-1" }));
    fetchMock.mockResolvedValueOnce(response({ items: [secondItem], next_cursor: null }));
    renderPage();

    expect(await screen.findByText(firstItem.summary)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load more" }));

    expect(await screen.findByText(secondItem.summary)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://localhost:8000/api/history?cursor=cursor-1&limit=20",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("shows an entry's author and source", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(response({ items: [firstItem], next_cursor: null }));
    renderPage();

    expect(await screen.findByText("Ada Lovelace")).toBeInTheDocument();
    expect(screen.getByText("Text")).toBeInTheDocument();
    expect(screen.getByText("2 claims")).toBeInTheDocument();
  });

  it("shows an empty state when there is no contribution history", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(response({ items: [], next_cursor: null }));
    renderPage();

    expect(await screen.findByText("No contributions yet.")).toBeInTheDocument();
  });

  it("retries the first page after a request error", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(response({ code: "request_failed", message: "History is temporarily unavailable." }, 503));
    fetchMock.mockResolvedValueOnce(response({ items: [firstItem], next_cursor: null }));
    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent("History is temporarily unavailable.");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText(firstItem.summary)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("localizes the speech source", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(response({ items: [{ ...firstItem, source: "speech" }], next_cursor: null }));
    renderPage();

    expect(await screen.findByText("Speech")).toBeInTheDocument();
  });

  it("links each entry to its contribution review", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(response({ items: [firstItem], next_cursor: null }));
    renderPage();

    expect(await screen.findByRole("link", { name: "Review contribution" })).toHaveAttribute("href", "/review/contribution-1");
  });
});
