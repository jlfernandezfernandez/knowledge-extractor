import { useMemo, useState } from "react";
import { Link, Navigate, RouterProvider, createBrowserRouter, type RouteObject } from "react-router";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageState } from "@/components/page-state";
import { API_URL, failure } from "@/lib/api/client";
import { AppShell } from "./shell";

export type AuthenticatedUser = {
  id: string;
  email: string;
  display_name: string;
};

type RouterOptions = {
  onAuthenticated?: () => Promise<void>;
  onLogout?: () => void;
};

function ProtectedRoute({ user, onLogout }: { user: AuthenticatedUser | null; onLogout?: () => void }) {
  if (!user) return <Navigate replace to="/login" />;
  return <AppShell user={user} onLogout={onLogout ?? (() => {})} />;
}

function PublicRoute({ user, register, onAuthenticated }: { user: AuthenticatedUser | null; register: boolean; onAuthenticated?: () => Promise<void> }) {
  if (user) return <Navigate replace to="/" />;
  return <AuthPage register={register} onAuthenticated={onAuthenticated ?? (async () => {})} />;
}

function RoutedPage({ page }: { page: "knowledge" | "ask" | "interviews" | "history" | "review" }) {
  const { t } = useTranslation();
  return <PageState title={t(`pages.${page}.title`)} description={t(`pages.${page}.description`)} />;
}

function AuthPage({ register, onAuthenticated }: { register: boolean; onAuthenticated: () => Promise<void> }) {
  const { t } = useTranslation();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    const body = Object.fromEntries(new FormData(event.currentTarget));

    try {
      const response = await fetch(`${API_URL}/api/auth/${register ? "register" : "login"}`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw await failure(response);
      await onAuthenticated();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("auth.failed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-sm items-center px-5">
      <Card className="w-full">
        <CardHeader>
          <CardTitle>
            <h1 className="text-inherit font-inherit">{t(register ? "auth.register.title" : "auth.login.title")}</h1>
          </CardTitle>
          <CardDescription>{t(register ? "auth.register.description" : "auth.login.description")}</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={submit}>
            {register && (
              <div className="flex flex-col gap-2">
                <Label htmlFor="display_name">{t("auth.displayName")}</Label>
                <Input id="display_name" name="display_name" required autoComplete="name" />
              </div>
            )}
            <div className="flex flex-col gap-2">
              <Label htmlFor="email">{t("auth.email")}</Label>
              <Input id="email" name="email" required type="email" autoComplete="email" />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">{t("auth.password")}</Label>
              <Input id="password" name="password" required type="password" minLength={8} autoComplete={register ? "new-password" : "current-password"} />
            </div>
            {error && <p className="text-sm text-destructive" role="alert">{error}</p>}
            <Button type="submit" disabled={submitting}>{t(register ? "auth.register.submit" : "auth.login.submit")}</Button>
            <Link className="text-center text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline" to={register ? "/login" : "/register"}>
              {t(register ? "auth.register.alternate" : "auth.login.alternate")}
            </Link>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}

export function createRoutes(user: AuthenticatedUser | null, options: RouterOptions = {}): RouteObject[] {
  return [
    {
      element: <ProtectedRoute user={user} onLogout={options.onLogout} />,
      children: [
        { path: "/", element: <RoutedPage page="knowledge" /> },
        { path: "/ask", element: <RoutedPage page="ask" /> },
        { path: "/interviews", element: <RoutedPage page="interviews" /> },
        { path: "/history", element: <RoutedPage page="history" /> },
        { path: "/review/:id", element: <RoutedPage page="review" /> },
      ],
    },
    { path: "/login", element: <PublicRoute user={user} register={false} onAuthenticated={options.onAuthenticated} /> },
    { path: "/register", element: <PublicRoute user={user} register onAuthenticated={options.onAuthenticated} /> },
    { path: "*", element: <Navigate replace to={user ? "/" : "/login"} /> },
  ];
}

export function AppRouter({ user, onAuthenticated, onLogout }: { user: AuthenticatedUser | null; onAuthenticated: () => Promise<void>; onLogout: () => void }) {
  const router = useMemo(
    () => createBrowserRouter(createRoutes(user, { onAuthenticated, onLogout })),
    [onAuthenticated, onLogout, user],
  );

  return <RouterProvider router={router} />;
}
