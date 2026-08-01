import { useMemo } from "react";
import { Navigate, RouterProvider, createBrowserRouter, type RouteObject } from "react-router";
import { useTranslation } from "react-i18next";
import { Skeleton } from "@/components/ui/skeleton";
import { AuthScreen } from "@/features/auth/auth-screen";
import { useAuth } from "@/features/auth/auth-provider";
import { HomePage } from "@/features/home/home-page";
import { InterviewsPage } from "@/features/interviews/interviews-page";
import { HistoryPage } from "@/features/history/history-page";
import { ReviewPage } from "@/features/review/review-page";
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

// oxlint-disable-next-line react/only-export-components -- route tests need the real route tree.
export function createRoutes(user: AuthenticatedUser | null, options: RouterOptions = {}): RouteObject[] {
  return [
    {
      element: <ProtectedRoute user={user} onLogout={options.onLogout} />,
      children: [
        { path: "/", element: <HomePage /> },
        { path: "/interviews", element: <InterviewsPage /> },
        { path: "/history", element: <HistoryPage /> },
        { path: "/review/:id", element: <ReviewPage /> },
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

  if (status === "loading") {
    return (
      <main className="flex min-h-dvh items-center justify-center">
        <div role="status">
          <Skeleton className="h-8 w-48" />
          <span className="sr-only">{t("pages.loading.title")}</span>
        </div>
      </main>
    );
  }
  return <RouterProvider router={router} />;
}
