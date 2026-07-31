import { useState } from "react";
import { NavLink, Outlet } from "react-router";
import { useTranslation } from "react-i18next";
import { BookOpenIcon, ChevronsUpDownIcon, HistoryIcon, LogOutIcon, MenuIcon, MessageCircleQuestionIcon, UsersRoundIcon } from "lucide-react";
import { Brand } from "@/components/brand";
import { GitHubLogo } from "@/components/github-logo";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import type { AuthenticatedUser } from "./router";

const navigation = [
  { to: "/", key: "home", icon: BookOpenIcon },
  { to: "/ask", key: "ask", icon: MessageCircleQuestionIcon },
  { to: "/interviews", key: "interviews", icon: UsersRoundIcon },
  { to: "/history", key: "history", icon: HistoryIcon },
] as const;

function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function Navigation({ onNavigate }: { onNavigate?: () => void }) {
  const { t } = useTranslation();

  return (
    <nav aria-label={t("shell.primaryNavigation")} className="flex flex-col gap-1">
      {navigation.map(({ to, key, icon: Icon }) => {
        return (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex h-9 items-center gap-2 rounded-lg px-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                isActive && "bg-muted text-foreground",
              )
            }
          >
            <Icon aria-hidden="true" />
            <span>{t(`nav.${key}`)}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}

export function AppShell({ user, onLogout }: { user: AuthenticatedUser; onLogout: () => void }) {
  const { t } = useTranslation();
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false);

  return (
    <div className="min-h-dvh bg-background md:grid md:grid-cols-[16rem_minmax(0,1fr)]">
        <aside className="hidden min-h-dvh flex-col border-r bg-muted/20 p-2 md:flex">
          <NavLink to="/" aria-label={t("app.name")} className="mb-4 flex h-9 items-center rounded-lg px-2">
            <Brand label={t("app.name")} />
          </NavLink>
          <Navigation />
          <div className="mt-auto">
            <DropdownMenu>
              <DropdownMenuTrigger render={<Button aria-label={t("shell.accountMenu")} variant="ghost" className="h-auto w-full justify-start px-2 py-2" />}>
                <Avatar size="lg">
                  <AvatarFallback>{initials(user.display_name)}</AvatarFallback>
                </Avatar>
                <span className="min-w-0 flex-1 text-left">
                  <span className="block truncate text-sm font-medium">{user.display_name}</span>
                  <span className="block truncate text-xs text-muted-foreground">{user.email}</span>
                </span>
                <ChevronsUpDownIcon aria-hidden="true" data-icon="inline-end" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" side="top">
                <DropdownMenuGroup>
                  <DropdownMenuLabel>
                    <div className="flex flex-col gap-0.5">
                      <span>{user.display_name}</span>
                      <span className="font-normal">{user.email}</span>
                    </div>
                  </DropdownMenuLabel>
                </DropdownMenuGroup>
                <DropdownMenuSeparator />
                <DropdownMenuGroup>
                  <DropdownMenuItem onClick={onLogout}>
                    <LogOutIcon aria-hidden="true" />
                    {t("shell.signOut")}
                  </DropdownMenuItem>
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </aside>

        <div className="min-w-0">
          <header className="flex h-14 items-center gap-3 border-b px-4">
            <div className="flex items-center gap-3 md:hidden">
              <Sheet open={mobileNavigationOpen} onOpenChange={setMobileNavigationOpen}>
                <SheetTrigger render={<Button aria-label={t("shell.openNavigation")} variant="ghost" size="icon" />}>
                  <MenuIcon aria-hidden="true" />
                </SheetTrigger>
                <SheetContent side="left" className="w-72 p-4" showCloseButton={false}>
                  <SheetHeader className="p-0">
                    <SheetTitle className="sr-only">{t("shell.primaryNavigation")}</SheetTitle>
                    <Brand label={t("app.name")} />
                  </SheetHeader>
                  <Navigation onNavigate={() => setMobileNavigationOpen(false)} />
                </SheetContent>
              </Sheet>
              <NavLink to="/" aria-label={t("app.name")}>
                <Brand label={t("app.name")} />
              </NavLink>
            </div>
            <div className="ml-auto">
              <Button
                aria-label={t("shell.repository")}
                variant="ghost"
                size="icon"
                render={<a href="https://github.com/jlfernandezfernandez/knowli" rel="noreferrer" target="_blank" />}
              >
                <GitHubLogo aria-hidden="true" />
              </Button>
            </div>
          </header>
          <main>
            <Outlet />
          </main>
        </div>
      </div>
  );
}
