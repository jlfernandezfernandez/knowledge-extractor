import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import { AskPage } from "./ask-page";

const citation = {
  id: "claim-1",
  title: "Friday deployments",
  statement: "Production deployments happen on Friday.",
  author: "Ada Lovelace",
  contribution_id: "contribution-1",
  contribution_created_at: "2026-07-29T08:00:00Z",
};

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function renderPage() {
  return render(<MemoryRouter><AskPage /></MemoryRouter>);
}

describe("ask", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => vi.unstubAllGlobals());

  it("submits the entered question", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(response({ answer: "Friday.", citations: [citation], sufficient_evidence: true }));
    renderPage();

    fireEvent.change(screen.getByRole("textbox", { name: "Question" }), { target: { value: "When do we deploy?" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/ask",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        body: JSON.stringify({ question: "When do we deploy?" }),
      }),
    ));
  });

  it("shows a loading state while an answer is requested", () => {
    vi.mocked(fetch).mockReturnValueOnce(new Promise<Response>(() => {}));
    renderPage();

    fireEvent.change(screen.getByRole("textbox", { name: "Question" }), { target: { value: "When do we deploy?" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));

    expect(screen.getByRole("button", { name: "Searching" })).toBeDisabled();
    expect(document.querySelector('[data-slot="skeleton"]')).toBeInTheDocument();
  });

  it("shows an answer with expandable cited provenance", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(response({ answer: "Deploy on Friday.", citations: [citation], sufficient_evidence: true }));
    renderPage();

    fireEvent.change(screen.getByRole("textbox", { name: "Question" }), { target: { value: "When do we deploy?" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText("Deploy on Friday.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Friday deployments" }));
    expect(screen.getByText("Production deployments happen on Friday.")).toBeInTheDocument();
    expect(screen.getByText("Ada Lovelace")).toBeInTheDocument();
    expect(screen.getByText("Jul 29, 2026")).toBeInTheDocument();
  });

  it("marks an answer without sufficient evidence", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(response({ answer: "I do not have enough evidence.", citations: [], sufficient_evidence: false }));
    renderPage();

    fireEvent.change(screen.getByRole("textbox", { name: "Question" }), { target: { value: "What is undocumented?" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText("Not enough evidence to answer this question.")).toBeInTheDocument();
    expect(screen.getByText("I do not have enough evidence.")).toBeInTheDocument();
  });

  it("shows the request error next to the question", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(response({ code: "request_failed", message: "The answer service is unavailable." }, 503));
    renderPage();

    fireEvent.change(screen.getByRole("textbox", { name: "Question" }), { target: { value: "When do we deploy?" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The answer service is unavailable.");
  });
});
