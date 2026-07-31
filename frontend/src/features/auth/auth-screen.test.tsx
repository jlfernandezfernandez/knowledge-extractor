import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import "@/i18n";
import { AuthProvider, useAuth } from "./auth-provider";
import { AuthScreen } from "./auth-screen";

const ada = { id: "user-1", email: "ada@example.test", display_name: "Ada Lovelace" };

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function AuthStatus() {
  const { user, status, logout } = useAuth();
  return (
    <>
      <output>{status === "authenticated" ? user?.display_name : status}</output>
      <button type="button" onClick={() => void logout()}>Sign out</button>
    </>
  );
}

function renderAuth(mode: "login" | "register") {
  return render(
    <AuthProvider>
      <MemoryRouter>
        <AuthScreen mode={mode} />
        <AuthStatus />
      </MemoryRouter>
    </AuthProvider>,
  );
}

describe("authentication", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ code: "unauthenticated", message: "sign in required" }, 401)));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("signs in and exposes the authenticated user", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(response({ code: "unauthenticated", message: "sign in required" }, 401));
    fetchMock.mockResolvedValueOnce(response({ user: ada }));
    renderAuth("login");

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: ada.email } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct horse battery staple" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Ada Lovelace"));
    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://localhost:8000/api/auth/login",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        body: JSON.stringify({ email: ada.email, password: "correct horse battery staple" }),
      }),
    );
  });

  it("keeps sign-in copy to the action", () => {
    renderAuth("login");

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByText("Continue to Knowli.")).not.toBeInTheDocument();
  });

  it("keeps the app brand outside the sign-in card", () => {
    renderAuth("login");

    expect(screen.getByText("Knowli").closest('[data-slot="card"]')).toBeNull();
  });

  it("centers the app brand above the sign-in card", () => {
    renderAuth("login");

    expect(screen.getByText("Knowli").closest("div")).toHaveClass("justify-center");
  });

  it("only requires an eight-character password when creating an account", () => {
    const { unmount } = renderAuth("login");

    expect(screen.getByLabelText("Password")).not.toHaveAttribute("minlength");

    unmount();
    renderAuth("register");

    expect(screen.getByLabelText("Password")).toHaveAttribute("minlength", "8");
  });

  it("registers with the display name, email, and password", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(response({ code: "unauthenticated", message: "sign in required" }, 401));
    fetchMock.mockResolvedValueOnce(response({ user: ada }));
    renderAuth("register");

    fireEvent.change(screen.getByLabelText("Name"), { target: { value: ada.display_name } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: ada.email } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct horse battery staple" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Ada Lovelace"));
    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://localhost:8000/api/auth/register",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        body: JSON.stringify({ display_name: ada.display_name, email: ada.email, password: "correct horse battery staple" }),
      }),
    );
  });

  it("announces backend field errors next to the invalid field", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(response({ code: "unauthenticated", message: "sign in required" }, 401));
    fetchMock.mockResolvedValueOnce(response({
      code: "invalid_registration",
      message: "invalid registration",
      fields: { email: "email is required" },
    }, 422));
    renderAuth("register");

    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Ada" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "ada@example.test" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct horse battery staple" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Check this field.");
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-describedby", "email-error");
  });

  it("restores an existing session", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(response({ user: ada }));
    renderAuth("login");

    expect(await screen.findByRole("status")).toHaveTextContent("Ada Lovelace");
  });

  it("clears the user after logout", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(response({ user: ada }));
    fetchMock.mockResolvedValueOnce(response({}));
    renderAuth("login");

    await screen.findByText("Ada Lovelace");
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("anonymous"));
    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://localhost:8000/api/auth/logout",
      expect.objectContaining({ method: "POST", credentials: "include" }),
    );
  });
});

describe("browser language detection", () => {
  const language = Object.getOwnPropertyDescriptor(window.navigator, "language");
  const languages = Object.getOwnPropertyDescriptor(window.navigator, "languages");

  afterEach(() => {
    localStorage.clear();
    if (language) Object.defineProperty(window.navigator, "language", language);
    if (languages) Object.defineProperty(window.navigator, "languages", languages);
    vi.resetModules();
  });

  it("selects Spanish from the browser when no preference is stored", async () => {
    localStorage.clear();
    Object.defineProperty(window.navigator, "language", { configurable: true, value: "es-ES" });
    Object.defineProperty(window.navigator, "languages", { configurable: true, value: ["es-ES"] });
    vi.resetModules();

    const { default: i18n } = await import("@/i18n");
    await waitFor(() => expect(i18n.resolvedLanguage).toBe("es"));
  });

  it("falls back to English for an unsupported browser language", async () => {
    localStorage.clear();
    Object.defineProperty(window.navigator, "language", { configurable: true, value: "fr-FR" });
    Object.defineProperty(window.navigator, "languages", { configurable: true, value: ["fr-FR"] });
    vi.resetModules();

    const { default: i18n } = await import("@/i18n");
    await waitFor(() => expect(i18n.resolvedLanguage).toBe("en"));
  });
});
