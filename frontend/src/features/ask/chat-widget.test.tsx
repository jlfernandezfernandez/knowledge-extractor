import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import { Toaster } from "@/components/ui/toast";
import { ChatWidget } from "./chat-widget";

class FakeEventSource {
  static last: FakeEventSource | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;

  url: string;

  constructor(url: string) {
    this.url = url;
    FakeEventSource.last = this;
  }

  close() {
    this.closed = true;
  }

  emit(payload: unknown) {
    act(() => this.onmessage?.({ data: JSON.stringify(payload) }));
  }
}

async function openChat() {
  // The shell owns the Toaster, so a widget under test needs it to show failures.
  render(<><ChatWidget /><Toaster /></>);
  fireEvent.click(screen.getByRole("button", { name: "Open assistant" }));
  return screen.findByRole("textbox", { name: "Message" });
}

function ask(composer: HTMLElement, question: string) {
  fireEvent.change(composer, { target: { value: question } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
  return FakeEventSource.last!;
}

describe("chat widget", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
    FakeEventSource.last = null;
    vi.stubGlobal("EventSource", FakeEventSource);
  });

  afterEach(() => vi.unstubAllGlobals());

  it("streams the answer as markdown and reports the tools the agent used", async () => {
    const composer = await openChat();
    const stream = ask(composer, "What interviews do I have?");

    expect(stream.url).toContain("thread_id=");
    stream.emit({ type: "tool", name: "list_my_interviews", done: false });
    expect(await screen.findByText("Checking your interviews")).toBeInTheDocument();

    stream.emit({ type: "tool", name: "list_my_interviews", done: true });
    expect(await screen.findByText("Checked your interviews")).toBeInTheDocument();
    expect(screen.queryByText("Checking your interviews")).not.toBeInTheDocument();

    stream.emit({ type: "token", content: "You have **one** interview." });
    stream.emit({ type: "done" });

    expect(await screen.findByText("one")).toHaveRole("strong");
    expect(stream.closed).toBe(true);
  });

  it("keeps the same conversation thread across turns", async () => {
    const composer = await openChat();
    const first = ask(composer, "When do we deploy?");
    first.emit({ type: "done" });

    const second = ask(await screen.findByRole("textbox", { name: "Message" }), "And staging?");

    expect(new URL(second.url, "http://localhost").searchParams.get("thread_id")).toBe(
      new URL(first.url, "http://localhost").searchParams.get("thread_id"),
    );
  });

  it("stops a running answer and keeps what it had already said", async () => {
    const composer = await openChat();
    const stream = ask(composer, "When do we deploy?");
    stream.emit({ type: "token", content: "Every Tuesday" });

    fireEvent.click(screen.getByRole("button", { name: "Stop" }));

    expect(stream.closed).toBe(true);
    expect(await screen.findByText("Every Tuesday")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Send" })).toBeInTheDocument();
  });

  it("drops the answer bubble when the turn is stopped before it says anything", async () => {
    const composer = await openChat();
    ask(composer, "When do we deploy?");

    fireEvent.click(screen.getByRole("button", { name: "Stop" }));

    expect(await screen.findByText("When do we deploy?")).toBeInTheDocument();
    expect(screen.queryByText("Thinking")).not.toBeInTheDocument();
  });

  it("says the assistant failed instead of leaving a silent empty answer", async () => {
    const composer = await openChat();
    const stream = ask(composer, "When do we deploy?");

    stream.emit({ type: "error", code: "model_unavailable" });

    expect(await screen.findByText("Configure a model to use Ask.")).toBeInTheDocument();
  });
});
