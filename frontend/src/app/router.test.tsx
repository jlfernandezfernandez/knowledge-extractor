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
        id: "review-123", author_id: "user-1", author: "Ada Lovelace", source: "text", raw_text: "A fact", stage: "claims", revision: 1, summary: "A fact", created_at: "2026-07-30T08:00:00Z", committed_at: null, claim_count: 0, claims: [], conflicts: [],
      })));
      return Promise.resolve(new Response("{}", { status: 401 }));
    }));
  });

  afterEach(() => {
    Object.defineProperty(window, "innerWidth", { configurable: true, writable: true, value: 1024 });
    vi.unstubAllGlobals();
  });

  it.each([
    ["/", "Share what you know"],
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
    renderRoute("/interviews", false);

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("shows the signed-in person and the sign-out action", () => {
    renderRoute("/history");

    fireEvent.click(screen.getByRole("button", { name: "Account menu" }));
    expect(screen.getByText("Ada Lovelace")).toBeInTheDocument();
    expect(screen.getByText("ada@example.test")).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Sign out" })).toBeInTheDocument();
  });

  it("keeps every destination reachable from the header", () => {
    renderRoute("/");
    const primaryNavigation = within(screen.getByRole("navigation", { name: "Primary navigation" }));

    for (const label of ["Knowledge", "Interviews", "History"]) {
      expect(primaryNavigation.getByRole("link", { name: label })).toBeInTheDocument();
    }
  });
});
