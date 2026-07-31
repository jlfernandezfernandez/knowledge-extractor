import { NavLink, Outlet, useLocation } from "react-router";
import { useTranslation } from "react-i18next";
import { BookOpenIcon, ChevronsUpDownIcon, HistoryIcon, LogOutIcon, UsersRoundIcon } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
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
  SidebarRail,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { Toaster } from "@/components/ui/toast";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ChatWidget } from "@/features/ask/chat-widget";
import type { AuthenticatedUser } from "./router";

const navigation = [
  { to: "/", key: "home", icon: BookOpenIcon },
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
  const { isMobile, setOpenMobile } = useSidebar();

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" render={<NavLink to="/" aria-label={t("app.name")} onClick={() => setOpenMobile(false)} />}>
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-zinc-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/60 shadow-2xs shrink-0 select-none">
                <span aria-hidden="true" className="text-base leading-none">🦉</span>
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-medium">{t("app.name")}</span>
              </div>
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
                tooltip={t(`nav.${key}`)}
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
              <DropdownMenuTrigger render={<SidebarMenuButton size="lg" aria-label={t("shell.accountMenu")} tooltip={user.display_name} />}>
                <Avatar>
                  <AvatarFallback>{initials(user.display_name)}</AvatarFallback>
                </Avatar>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-medium">{user.display_name}</span>
                  <span className="truncate text-xs text-muted-foreground">{user.email}</span>
                </div>
                <ChevronsUpDownIcon aria-hidden="true" className="ml-auto" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" side={isMobile ? "bottom" : "right"} sideOffset={4}>
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
      <SidebarRail />
    </Sidebar>
  );
}

export function AppShell({ user, onLogout }: { user: AuthenticatedUser; onLogout: () => void }) {
  const { t } = useTranslation();

  return (
    <TooltipProvider>
      <SidebarProvider>
        <AppSidebar user={user} onLogout={onLogout} />
        <SidebarInset className="relative">
          {/* No app header: on desktop the sidebar rail toggles it, so the trigger
              only has to exist where the sidebar is off-canvas. */}
          <SidebarTrigger
            aria-label={t("shell.openNavigation")}
            className="absolute start-2 top-2 z-10 md:hidden"
          />
          <Outlet />
          <ChatWidget />
        </SidebarInset>
        <Toaster />
      </SidebarProvider>
    </TooltipProvider>
  );
}
