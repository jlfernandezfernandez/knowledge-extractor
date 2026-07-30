import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import "@/i18n";
import { InterviewsPage } from "./interviews-page";

const interview = {
  id: "interview-1",
  requester_id: "requester-1",
  assignee_id: "assignee-1",
  requester_name: "Ada Lovelace",
  assignee_name: "Grace Hopper",
  title: "Deployment retrospective",
  brief: "Explain the Friday release process.",
  status: "pending" as const,
  created_at: "2026-07-30T08:00:00Z",
  started_at: null,
  completed_at: null,
};

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function renderPage() {
  return render(<MemoryRouter><InterviewsPage /></MemoryRouter>);
}

describe("interviews", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ items: [interview] })));
  });

  afterEach(() => vi.unstubAllGlobals());

  it("loads pending, sent, and completed tabs", async () => {
    renderPage();

    await screen.findByText("Deployment retrospective");
    for (const tab of ["Pending", "Sent", "Completed"]) {
      expect(screen.getByRole("tab", { name: tab })).toBeInTheDocument();
    }
    fireEvent.click(screen.getByRole("tab", { name: "Sent" }));
    await waitFor(() => expect(fetch).toHaveBeenLastCalledWith(
      "http://localhost:8000/api/interviews?view=sent",
      expect.objectContaining({ credentials: "include" }),
    ));
  });

  it("does not reveal people or person imagery in interview rows", async () => {
    renderPage();

    await screen.findByText("Deployment retrospective");
    expect(screen.queryByText("Ada Lovelace")).not.toBeInTheDocument();
    expect(screen.queryByText("Grace Hopper")).not.toBeInTheDocument();
    expect(document.querySelector('[data-slot="avatar"]')).not.toBeInTheDocument();
    expect(document.querySelector('svg[data-lucide="user"]')).not.toBeInTheDocument();
  });

  it("creates an interview with the requested title and optional brief", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(response({ items: [] }));
    fetchMock.mockResolvedValueOnce(response(interview, 201));
    fetchMock.mockResolvedValueOnce(response({ items: [interview] }));
    renderPage();

    await screen.findByText("No pending interviews.");
    fireEvent.click(screen.getByRole("button", { name: "Request interview" }));
    fireEvent.change(screen.getByLabelText("Assignee ID"), { target: { value: "assignee-1" } });
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: interview.title } });
    fireEvent.change(screen.getByLabelText("Brief (optional)"), { target: { value: interview.brief } });
    fireEvent.click(screen.getByRole("button", { name: "Send request" }));

    await waitFor(() => expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8000/api/interviews",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ assignee_id: "assignee-1", title: interview.title, brief: interview.brief }),
      }),
    ));
  });
});
