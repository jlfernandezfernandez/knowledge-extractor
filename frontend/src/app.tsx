import { useCallback, useEffect, useState } from "react";
import { PageState } from "@/components/page-state";
import { AppRouter, type AuthenticatedUser } from "@/app/router";
import { API_URL, request } from "@/lib/api/client";
import { useTranslation } from "react-i18next";

export default function App() {
  const { t } = useTranslation();
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    try {
      const me = await request<{ user: AuthenticatedUser }>("/api/auth/me");
      setUser(me.user);
    } catch { setUser(null); } finally { setLoading(false); }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);
  const logout = useCallback(() => {
    void fetch(`${API_URL}/api/auth/logout`, { method: "POST", credentials: "include" }).finally(() => setUser(null));
  }, []);

  if (loading) return <PageState loading title={t("pages.loading.title")} description={t("pages.loading.description")} />;
  return <AppRouter user={user} onAuthenticated={refresh} onLogout={logout} />;
}
