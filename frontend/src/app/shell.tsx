import { NavLink, Outlet, useLocation } from "react-router";
import { useTranslation } from "react-i18next";
import { BookOpenIcon, ChevronsUpDownIcon, HistoryIcon, LogOutIcon, MessageCircleQuestionIcon, UsersRoundIcon } from "lucide-react";
import { Brand } from "@/components/brand";
import { GitHubLogo } from "@/components/github-logo";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { buttonVariants } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
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

function AppSidebar({ user, onLogout }: { user: AuthenticatedUser; onLogout: () => void }) {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const { setOpenMobile } = useSidebar();

  return (
    <Sidebar>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton render={<NavLink to="/" aria-label={t("app.name")} onClick={() => setOpenMobile(false)} />}>
              <Brand label={t("app.name")} />
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarMenu>
          {navigation.map(({ to, key, icon: Icon }) => (
            <SidebarMenuItem key={to}>
              <SidebarMenuButton
                render={<NavLink to={to} end={to === "/"} onClick={() => setOpenMobile(false)} />}
                isActive={to === "/" ? pathname === "/" : pathname.startsWith(to)}
              >
                <Icon aria-hidden="true" />
                <span>{t(`nav.${key}`)}</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger render={<SidebarMenuButton size="lg" aria-label={t("shell.accountMenu")} />}>
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
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}

export function AppShell({ user, onLogout }: { user: AuthenticatedUser; onLogout: () => void }) {
  const { t } = useTranslation();

  return (
    <SidebarProvider>
      <AppSidebar user={user} onLogout={onLogout} />
      <SidebarInset>
        <header className="flex h-14 items-center gap-3 border-b px-4">
          <SidebarTrigger aria-label={t("shell.openNavigation")} className="md:hidden" />
          <NavLink to="/" aria-label={t("app.name")} className="md:hidden">
            <Brand label={t("app.name")} />
          </NavLink>
          <div className="ml-auto">
            <a
              href="https://github.com/jlfernandezfernandez/knowli"
              aria-label={t("shell.repository")}
              rel="noreferrer"
              target="_blank"
              className={buttonVariants({ variant: "ghost", size: "icon" })}
            >
              <GitHubLogo aria-hidden="true" />
            </a>
          </div>
        </header>
        <Outlet />
      </SidebarInset>
    </SidebarProvider>
  );
}
