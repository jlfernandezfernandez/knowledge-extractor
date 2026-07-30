import { fireEvent, render, screen, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import { AuthProvider } from "@/features/auth/auth-provider";
import { createRoutes, type AuthenticatedUser } from "./router";

const user: AuthenticatedUser = {
  id: "user-1",
  email: "ada@example.test",
  display_name: "Ada Lovelace",
};

function renderRoute(path: string, authenticated = true) {
  const router = createMemoryRouter(createRoutes(authenticated ? user : null), {
    initialEntries: [path],
  });

  return render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
}

describe("application router", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
    vi.stubGlobal("EventSource", class { close() {} addEventListener() {} });
    vi.stubGlobal("fetch", vi.fn((input: string) => {
      if (input.includes("/api/auth/me")) return Promise.resolve(new Response("{}", { status: 401 }));
      if (input.includes("/api/interviews")) return Promise.resolve(new Response(JSON.stringify({ items: [] })));
      if (input.includes("/api/contributions/")) return Promise.resolve(new Response(JSON.stringify({
        id: "review-123", author_id: "user-1", author: "Ada Lovelace", kind: "contribution", source: "text", raw_text: "A fact", stage: "claims", revision: 1, summary: "A fact", created_at: "2026-07-30T08:00:00Z", committed_at: null, claim_count: 0, claims: [], conflicts: [],
      })));
      return Promise.resolve(new Response("{}", { status: 401 }));
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it.each([
    ["/", "Share what you know"],
    ["/ask", "Ask"],
    ["/interviews", "Interviews"],
    ["/history", "History"],
    ["/review/review-123", "Review claims"],
    ["/login", "Share what you know"],
    ["/register", "Share what you know"],
  ])("renders %s for an authenticated user", async (path, heading) => {
    renderRoute(path);

    expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
  });

  it("redirects an unauthenticated visitor to sign in", () => {
    renderRoute("/ask", false);

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("marks the current desktop navigation item", () => {
    renderRoute("/interviews");

    expect(screen.getAllByRole("link", { name: "Interviews" })[0]).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("opens a mobile navigation with all destinations", () => {
    renderRoute("/");
    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    const mobileNavigation = within(screen.getByRole("dialog"));

    for (const label of ["Knowledge", "Ask", "Interviews", "History"]) {
      expect(mobileNavigation.getByRole("link", { name: label })).toBeInTheDocument();
    }
  });
});
