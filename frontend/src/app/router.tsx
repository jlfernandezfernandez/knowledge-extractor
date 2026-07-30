import { useMemo } from "react";
import { Navigate, RouterProvider, createBrowserRouter, type RouteObject } from "react-router";
import { useTranslation } from "react-i18next";
import { PageState } from "@/components/page-state";
import { AuthScreen } from "@/features/auth/auth-screen";
import { useAuth } from "@/features/auth/auth-provider";
import type { AuthenticatedUser } from "@/features/auth/types";
import { AppShell } from "./shell";

export type { AuthenticatedUser } from "@/features/auth/types";

type RouterOptions = {
  onLogout?: () => void;
};

function ProtectedRoute({ user, onLogout }: { user: AuthenticatedUser | null; onLogout?: () => void }) {
  if (!user) return <Navigate replace to="/login" />;
  return <AppShell user={user} onLogout={onLogout ?? (() => {})} />;
}

function PublicRoute({ user, register }: { user: AuthenticatedUser | null; register: boolean }) {
  if (user) return <Navigate replace to="/" />;
  return <AuthScreen mode={register ? "register" : "login"} />;
}

function RoutedPage({ page }: { page: "knowledge" | "ask" | "interviews" | "history" | "review" }) {
  const { t } = useTranslation();
  return <PageState title={t(`pages.${page}.title`)} description={t(`pages.${page}.description`)} />;
}

// oxlint-disable-next-line react/only-export-components -- route tests need the real route tree.
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
    { path: "/login", element: <PublicRoute user={user} register={false} /> },
    { path: "/register", element: <PublicRoute user={user} register /> },
    { path: "*", element: <Navigate replace to={user ? "/" : "/login"} /> },
  ];
}

export function AppRouter() {
  const { t } = useTranslation();
  const { user, status, logout } = useAuth();
  const router = useMemo(
    () => createBrowserRouter(createRoutes(user, { onLogout: () => void logout() })),
    [logout, user],
  );

  if (status === "loading") return <PageState loading title={t("pages.loading.title")} description={t("pages.loading.description")} />;
  return <RouterProvider router={router} />;
}
