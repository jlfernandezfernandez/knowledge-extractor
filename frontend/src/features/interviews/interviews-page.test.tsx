import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
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
  beforeEach(async () => {
    await i18n.changeLanguage("en");
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

  it("clears the previous tab rows while the next tab is loading", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(response({ items: [interview] }));
    fetchMock.mockReturnValueOnce(new Promise<Response>(() => {}));
    renderPage();

    await screen.findByText("Deployment retrospective");
    fireEvent.click(screen.getByRole("tab", { name: "Sent" }));
    expect(screen.queryByText("Deployment retrospective")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Loading interviews…");
    expect(screen.queryByText("No sent interviews.")).not.toBeInTheDocument();
  });

  it("ignores an older tab response that resolves after the active tab", async () => {
    let resolvePending!: (value: Response) => void;
    let resolveSent!: (value: Response) => void;
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockReset();
    fetchMock.mockReturnValueOnce(new Promise<Response>((resolve) => { resolvePending = resolve; }));
    fetchMock.mockReturnValueOnce(new Promise<Response>((resolve) => { resolveSent = resolve; }));
    renderPage();

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByRole("tab", { name: "Sent" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    resolveSent(response({ items: [{ ...interview, id: "sent-1", title: "Sent interview", status: "started" }] }));
    expect(await screen.findByText("Sent interview")).toBeInTheDocument();
    resolvePending(response({ items: [interview] }));

    await waitFor(() => expect(screen.queryByText("Deployment retrospective")).not.toBeInTheDocument());
    expect(screen.getByText("Sent interview")).toBeInTheDocument();
  });

  it("dates a row in the app's language, not the browser's", async () => {
    await i18n.changeLanguage("es");
    renderPage();

    await screen.findByText("Deployment retrospective");
    expect(
      screen.getByText(
        new Intl.DateTimeFormat("es", { dateStyle: "medium" }).format(
          new Date(interview.created_at),
        ),
      ),
    ).toBeInTheDocument();
  });

  it("does not name the people involved in an interview row", async () => {
    renderPage();

    await screen.findByText("Deployment retrospective");
    expect(screen.queryByText("Ada Lovelace")).not.toBeInTheDocument();
    expect(screen.queryByText("Grace Hopper")).not.toBeInTheDocument();
  });

  it("creates an interview with the requested title and optional brief", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(response({ items: [] }));
    fetchMock.mockResolvedValueOnce(response({
      items: [{ id: "assignee-1", display_name: "Grace Hopper", email: "grace@example.test" }],
    }));
    fetchMock.mockResolvedValueOnce(response(interview, 201));
    fetchMock.mockResolvedValueOnce(response({ items: [interview] }));
    renderPage();

    await screen.findByText("No pending interviews.");
    fireEvent.click(screen.getByRole("button", { name: "Request interview" }));
    const person = await screen.findByLabelText("Person");
    await waitFor(() => expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8000/api/users",
      expect.objectContaining({ credentials: "include" }),
    ));
    await waitFor(() => expect(person.querySelector("option[value='assignee-1']"))
      .toHaveTextContent("Grace Hopper · grace@example.test"));
    fireEvent.change(person, { target: { value: "assignee-1" } });
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: interview.title } });
    fireEvent.change(screen.getByLabelText("Brief (optional)"), { target: { value: interview.brief } });
    fireEvent.click(screen.getByRole("button", { name: "Send request" }));

    await waitFor(() => expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "http://localhost:8000/api/interviews",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ assignee_id: "assignee-1", title: interview.title, brief: interview.brief }),
      }),
    ));
  });
});
