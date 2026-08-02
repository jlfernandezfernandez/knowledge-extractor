import { Outlet } from "react-router";
import { Toaster } from "@/components/ui/toast";
import { ChatWidget } from "@/features/ask/chat-widget";
import { SiteHeader } from "./site-header";
import type { AuthenticatedUser } from "./router";

export function AppShell({ user, onLogout }: { user: AuthenticatedUser; onLogout: () => void }) {
  return (
    <>
      <SiteHeader user={user} onLogout={onLogout} />
      <main>
        <Outlet />
      </main>
      <ChatWidget />
      <Toaster />
    </>
  );
}
