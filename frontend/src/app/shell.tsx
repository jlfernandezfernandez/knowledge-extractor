import { NavLink, Outlet } from "react-router";
import { useTranslation } from "react-i18next";
import { BookOpenIcon, HistoryIcon, LogOutIcon, MenuIcon, MessageCircleQuestionIcon, SettingsIcon, UsersRoundIcon } from "lucide-react";
import { Brand } from "@/components/brand";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Sheet, SheetClose, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
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

function Navigation({ mobile = false }: { mobile?: boolean }) {
  const { t } = useTranslation();

  return (
    <nav aria-label={t("shell.primaryNavigation")} className="flex flex-col gap-1">
      {navigation.map(({ to, key, icon: Icon }) => {
        const link = (
          <NavLink
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "flex h-9 items-center gap-2 rounded-lg px-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                isActive && "bg-muted text-foreground",
                mobile ? "w-full" : "justify-center",
              )
            }
          >
            <Icon aria-hidden="true" />
            <span className={mobile ? "" : "sr-only"}>{t(`nav.${key}`)}</span>
          </NavLink>
        );

        if (mobile) {
          return (
            <SheetClose key={to} render={link} />
          );
        }

        return (
          <Tooltip key={to}>
            <TooltipTrigger render={link} />
            <TooltipContent>{t(`nav.${key}`)}</TooltipContent>
          </Tooltip>
        );
      })}
    </nav>
  );
}

export function AppShell({ user, onLogout }: { user: AuthenticatedUser; onLogout: () => void }) {
  const { t } = useTranslation();

  return (
    <TooltipProvider>
      <div className="min-h-dvh bg-background md:grid md:grid-cols-[4rem_minmax(0,1fr)]">
        <aside className="hidden min-h-dvh flex-col border-r bg-muted/20 p-2 md:flex">
          <NavLink to="/" aria-label={t("app.name")} className="mb-4 flex h-9 items-center justify-center rounded-lg">
            <Brand compact label={t("app.name")} />
          </NavLink>
          <Navigation />
          <div className="mt-auto">
            <DropdownMenu>
              <DropdownMenuTrigger render={<Button aria-label={t("shell.accountMenu")} variant="ghost" size="icon" className="w-full" />}>
                <Avatar>
                  <AvatarFallback>{initials(user.display_name)}</AvatarFallback>
                </Avatar>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" side="right">
                <DropdownMenuGroup>
                  <DropdownMenuItem disabled>
                    <SettingsIcon aria-hidden="true" />
                    {t("shell.settings")}
                  </DropdownMenuItem>
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
          <header className="flex h-14 items-center gap-3 border-b px-4 md:hidden">
            <Sheet>
              <SheetTrigger render={<Button aria-label={t("shell.openNavigation")} variant="ghost" size="icon" />}>
                <MenuIcon aria-hidden="true" />
              </SheetTrigger>
              <SheetContent side="left" className="w-72 p-4" showCloseButton={false}>
                <SheetHeader className="p-0">
                  <SheetTitle className="sr-only">{t("shell.primaryNavigation")}</SheetTitle>
                  <Brand label={t("app.name")} />
                </SheetHeader>
                <Navigation mobile />
              </SheetContent>
            </Sheet>
            <NavLink to="/" aria-label={t("app.name")}>
              <Brand label={t("app.name")} />
            </NavLink>
          </header>
          <main>
            <Outlet />
          </main>
        </div>
      </div>
    </TooltipProvider>
  );
}
