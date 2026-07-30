import { fireEvent, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { beforeEach, describe, expect, it } from "vitest";
import i18n from "@/i18n";
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

  return render(<RouterProvider router={router} />);
}

describe("application router", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it.each([
    ["/", "Knowledge"],
    ["/ask", "Ask"],
    ["/interviews", "Interviews"],
    ["/history", "History"],
    ["/review/review-123", "Review"],
    ["/login", "Knowledge"],
    ["/register", "Knowledge"],
  ])("renders %s for an authenticated user", (path, heading) => {
    renderRoute(path);

    expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
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

    for (const label of ["Knowledge", "Ask", "Interviews", "History"]) {
      expect(screen.getAllByRole("link", { name: label }).length).toBeGreaterThan(0);
    }
  });
});
