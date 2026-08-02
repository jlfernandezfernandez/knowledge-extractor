import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import "@/i18n";
import { HomePage } from "./home-page";

const pending = {
  id: "interview-1",
  requester_id: "requester-1",
  assignee_id: "assignee-1",
  title: "Deployment retrospective",
  brief: "Explain the Friday release process.",
  status: "pending" as const,
  created_at: "2026-07-30T08:00:00Z",
  started_at: null,
  completed_at: null,
};

class FakeSocket {
  static last: FakeSocket | null = null;
  static readonly OPEN = 1;

  readyState = FakeSocket.OPEN;
  sent: unknown[] = [];
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(readonly url: string) {
    FakeSocket.last = this;
  }

  send(data: unknown) {
    this.sent.push(data);
  }

  close() {
    this.readyState = 3;
    this.onclose?.();
  }

  say(event: unknown) {
    this.onmessage?.({ data: JSON.stringify(event) } as MessageEvent);
  }
}

class FakeAudioContext {
  audioWorklet = { addModule: vi.fn().mockResolvedValue(undefined) };
  destination = {};
  close = vi.fn().mockResolvedValue(undefined);
  createMediaStreamSource() {
    const node = { connect: () => node };
    return node;
  }
}

class FakeWorkletNode {
  port: { onmessage: ((event: MessageEvent) => void) | null } = { onmessage: null };
  connect<T>(target: T) {
    return target;
  }
}

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function renderHome() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/review/:id" element={<h1>Review destination</h1>} />
        <Route path="/interviews" element={<h1>Interview destination</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("home contribution composer", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ items: [] })));
    vi.stubGlobal("WebSocket", FakeSocket);
    vi.stubGlobal("AudioContext", FakeAudioContext);
    vi.stubGlobal("AudioWorkletNode", FakeWorkletNode);
    vi.stubGlobal("GainNode", class {});
    URL.createObjectURL = vi.fn(() => "blob:worklet");
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] }) },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: undefined });
  });

  it("keeps the empty composer disabled without a duplicate add-knowledge action", async () => {
    renderHome();

    await screen.findByText("No pending interviews.");
    expect(screen.getByRole("button", { name: "Create contribution" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: /add knowledge/i })).not.toBeInTheDocument();
  });

  it("creates a contribution from the filled composer and opens its review", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(response({ items: [] }));
    fetchMock.mockResolvedValueOnce(response({ id: "contribution-1", stage: "claims", revision: 2 }));
    renderHome();

    fireEvent.change(screen.getByRole("textbox", { name: "Your contribution" }), {
      target: { value: "Deploy production on Friday." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create contribution" }));

    await screen.findByRole("heading", { name: "Review destination" });
    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://localhost:8000/api/contributions",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        body: JSON.stringify({ raw_text: "Deploy production on Friday." }),
      }),
    );
  });

  it("adds each transcribed turn to the composer while the microphone is still open", async () => {
    renderHome();

    fireEvent.click(screen.getByRole("button", { name: "Record audio" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Stop recording" })).toBeInTheDocument());

    const socket = FakeSocket.last!;
    expect(socket.url).toBe("ws://localhost:8000/api/transcriptions");

    socket.say({ type: "transcript", text: "Deploy production on Tuesdays." });
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Your contribution" })).toHaveValue("Deploy production on Tuesdays."));

    socket.say({ type: "transcript", text: "The team froze Friday releases." });
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Your contribution" })).toHaveValue(
      "Deploy production on Tuesdays. The team froze Friday releases.",
    ));

    fireEvent.click(screen.getByRole("button", { name: "Stop recording" }));
    expect(socket.sent.at(-1)).toEqual(new ArrayBuffer(0));

    // The server closes once the final turn is transcribed, and that ends the dictation.
    socket.close();
    await waitFor(() => expect(screen.getByRole("button", { name: "Record audio" })).toBeEnabled());
  });

  it("shows the failure the live session reports on its own socket", async () => {
    renderHome();

    fireEvent.click(screen.getByRole("button", { name: "Record audio" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Stop recording" })).toBeInTheDocument());
    FakeSocket.last!.say({ type: "error", code: "transcription_unavailable" });

    expect(await screen.findByRole("alert")).toHaveTextContent("Transcription is unavailable.");
  });

  it("shows one localized microphone error for an unavailable recording context", async () => {
    Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: undefined });
    renderHome();

    fireEvent.click(screen.getByRole("button", { name: "Record audio" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Microphone unavailable");
  });

  it("shows at most three pending interviews and starts the selected interview", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(response({ items: [pending, { ...pending, id: "two", title: "Second" }, { ...pending, id: "three", title: "Third" }, { ...pending, id: "four", title: "Hidden fourth" }] }));
    fetchMock.mockResolvedValueOnce(response({ interview: { ...pending, status: "started" }, contribution_id: "contribution-1" }));
    renderHome();

    await screen.findByText("Deployment retrospective");
    expect(screen.getByText("Second")).toBeInTheDocument();
    expect(screen.getByText("Third")).toBeInTheDocument();
    expect(screen.queryByText("Hidden fourth")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Deployment retrospective/ }));

    await screen.findByRole("heading", { name: "Review destination" });
    await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith(
      "http://localhost:8000/api/interviews/interview-1/start",
      expect.objectContaining({ method: "POST", credentials: "include" }),
    ));
  });
});
